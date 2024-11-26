"""
_data_client.py
19. November  2024

retrieves data from camera tracking

Author:
Nilusink
"""
from concurrent.futures import ThreadPoolExecutor, Future
from pydantic import TypeAdapter, ValidationError
from contextlib import suppress
from threading import Semaphore
from uuid import getnode
from time import time
import socket as s
import json

from ..tools import debugger, run_with_debug
from ._message_future import MessageFuture
from ._message_types import *


DEVICE_MAC: int = getnode()


def try_find_id(message: str) -> int:
    """
    tries to find an id in an invalid message
    :return: id if found, -1 if not
    """
    # try to read as normal json
    try:
        data = json.loads(message)
        mid = data["id"]

        debugger.trace(f"found id in message (json): \"{mid}\"")
        return mid

    except (json.JSONDecodeError, TypeError):
        sid = '"id":'

        # if json fails, try to manually find it
        if sid in message:
            # try to find id key in message
            string_pos = message.find(sid) + len(sid)
            id_message = message[string_pos:].lstrip()

            # scan message until next non-digit
            pos = 0
            while id_message[pos].isdigit():
                pos += 1

            # cut message and try to convert to int
            with suppress(ValueError):
                mid = int(id_message[:pos])

                debugger.trace(f"found id in message (manual): \"{mid}\"")
                return mid

    # if message is completely unreadable, return -1
    return -1


class DataClient(s.socket):
    encoding: str = "utf-8"
    _pending_replies: dict[int, MessageFuture]

    def __init__(
            self,
            server_address: tuple[str, int],
            on_receive_callback: tp.Callable[[TResData], None],
            pool: ThreadPoolExecutor,
    ) -> None:
        self._server_address = server_address
        self._callback = on_receive_callback
        self._pool = pool

        # initialize socket
        super().__init__(s.AF_INET, s.SOCK_STREAM)
        self.settimeout(.2)

        # threading stuff
        self._receive_future: Future = ...
        self._running = False

        self._pending_replies = {}
        self._pending_replies_sem = Semaphore()

    def start(self) -> None:
        """
        connects to the server and starts background threads
        """
        # connect to server
        self.connect(self._server_address)
        debugger.info("connected to server")

        # start thread
        self._running = True
        self._receive_future = self._pool.submit(self._receive_loop)

    @run_with_debug(show_finish=True, reraise_errors=True)
    def _receive_loop(self) -> None:
        """
        not meant to be called, should be run in a thread
        """
        # pydantic validator
        message_adapter = TypeAdapter(Message)

        while self._running:
            # receive message
            try:
                data = self.recv(1024).decode(self.encoding)

            except s.timeout:
                continue

            except (ConnectionResetError, OSError, ConnectionAbortedError):
                debugger.error("fatal network error")
                return self.stop()

            except Exception:
                self.stop()
                raise

            # validate message
            try:
                validated_data = message_adapter.validate_json(data)

            except ValidationError:
                debugger.error(f"received invalid message: {data}")

                # send NACK to server
                self.send_message(AckMessage(
                    data=AckData(to=try_find_id(data), ack=False)
                ))
                continue

            self._handle_message(validated_data)

    def send_message(self, data: MessageData) -> MessageFuture | None:
        """
        send a message to the server
        """
        type_name: str
        message_type: Message
        match data:
            case ReqData(req=_):
                type_name = "req"
                message_type = ReqMessage

            case AckData(to=_, ack=_):
                type_name = "ack"
                message_type = AckMessage

            case ReplData(to=_, data=_):
                type_name = "repl"
                message_type = ReplMessage

            case DataDataMessage():
                type_name = "data"
                message_type = DataMessage

            case _:
                debugger.error("invalid message data for send")
                raise ValueError("invalid message data")

        t = time()
        message = message_type(
            type=type_name,
            id=int(t + DEVICE_MAC),
            time=t,
            data=data
        )

        # if message wants a reply, add it to pending
        if message.type == "req":
            future = MessageFuture(message)

            # make sure no one else is writing to pending_replies
            self._pending_replies_sem.acquire()
            self._pending_replies[message.id] = future
            self._pending_replies_sem.release()

            return future

        debugger.log(f"sending: {message}")

        # send message to server
        self.send(message.model_dump_json(
            exclude_unset=True
        ).encode(self.encoding))

    def _handle_message(self, message: Message) -> None:
        """
        handle a verified message
        """
        # create acknowledgements
        ack = AckData(to=message.id, ack=True)
        nack = AckData(to=message.id, ack=False)

        # message handling
        match message:
            case ReqMessage(type="req", id=_, time=_, data=_):
                debugger.trace("Matched a ReqMessage!")
                debugger.trace(f"Request type: {message.data.req}")
                raise RuntimeWarning("not handled")

            case AckMessage(type="ack", id=_, time=_, data=_):
                debugger.trace("Matched an AckMessage!")
                debugger.trace(f"Ack to: {message.data.to}, Ack status: {message.data.ack}")

                self._try_match_reply(message)
                return  # don't send acknowledgements to an acknowledgement

            case ReplMessage(type="repl", id=_, time=_, data=_):
                debugger.trace("Matched a ReplMessage!")
                debugger.trace(f"Reply data: {message.data.data}")

                self._try_match_reply(message)

            case DataMessage(type="data", id=_, time=_, data=_):
                debugger.trace("Matched a DataMessage!")
                debugger.trace(f"Data message type: {message.data.type}")

                match message.data:
                    case TResDataMessage(type="tres", data=_):
                        debugger.trace(f"Track result, data: {message.data.data}")

                        # forward message to callback
                        self._pool.submit(self._callback, message.data.data)

                    case SInfDataMessage(type="sinf", data=_):
                        debugger.trace(f"station information data: {message.data.data}")
                        debugger.warning("sinf not handled")
                        raise RuntimeWarning("not handled")

                    case _:
                        debugger.warning("unknown data type")
                        return self.send_message(nack)

            case _:
                debugger.warning("unknown message type")
                return self.send_message(nack)

        # send ack
        self.send_message(ack)

    def _try_match_reply(self, message: AckMessage | ReplMessage) -> None:
        """
        try to match a reply type message to an already sent message
        """
        debugger.log(f"matching {message}")

        if message.data.to in self._pending_replies:
            # make sure no one else is writing to pending_replies
            self._pending_replies_sem.acquire()

            # remove reply from pending
            reply = self._pending_replies[message.data.to]
            self._pending_replies.pop(message.data.to)

            self._pending_replies_sem.release()

            # finish message future
            reply.message = message
            return

        debugger.warning("Unable to match reply: ", message)

    def stop(self) -> None:
        """
        stop the client
        """
        self._running = False
        self.shutdown(0)

        self._receive_future.cancel()
