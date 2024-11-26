"""
_data_client.py
19. November  2024

retrieves data from camera tracking

Author:
Nilusink
"""
from concurrent.futures import ThreadPoolExecutor, Future
from pydantic import TypeAdapter
import typing as tp
import socket as s

from ..tools import debugger, run_with_debug, SimpleLock
from ..tools.comms import *


class DataClient(s.socket):
    encoding: str = "utf-8"
    _pending_replies: dict[int, MessageFuture]

    def __init__(
            self,
            server_address: tuple[str, int],
            on_receive_tres_callback: tp.Callable[[TResData], None],
            on_receive_sinf_callback: tp.Callable[[SInfData], None],
            pool: ThreadPoolExecutor,
    ) -> None:
        self._server_address = server_address
        self._tres_callback = on_receive_tres_callback
        self._sinf_callback = on_receive_sinf_callback
        self._pool = pool

        # initialize socket
        super().__init__(s.AF_INET, s.SOCK_STREAM)
        self.settimeout(.2)

        # threading stuff
        self._receive_future: Future = ...
        self._running = False

        self._pending_replies = {}
        self._pending_replies_sem = SimpleLock()

    def start(self) -> None:
        """
        connects to the server and starts background threads
        """
        # connect to server
        try:
            self.connect(self._server_address)

        except TimeoutError:
            debugger.error("DataClient timed out trying to connect to server")
            raise

        debugger.info("DataClient connected to server")

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
                message = receive_message(self, self.send_message, self.encoding)

                if message is ...:
                    continue

            except RuntimeError:
                return self.stop()

            self._handle_message(message)

    def _handle_message(self, message: Message) -> None:
        """
        handle a verified message
        """
        debugger.log(f"handling: {message}")

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
                        self._pool.submit(self._tres_callback, message.data.data)

                    case SInfDataMessage(type="sinf", data=_):
                        debugger.trace(f"station information data: {message.data.data}")

                        # forward message to callback
                        self._pool.submit(self._sinf_callback, message.data.data)

                    case _:
                        debugger.warning("unknown data type")
                        return self.send_message(nack)

            case _:
                debugger.warning("unknown message type")
                return self.send_message(nack)

        # send ack
        self.send_message(ack)

    def send_message(self, data: MessageData) -> MessageFuture | None:
        """
        send a message to the server
        """

        def append_to_queue(f: MessageFuture) -> None:
            # make sure no one else is writing to pending_replies
            self._pending_replies_sem.acquire()
            self._pending_replies[f.origin_message.id] = f
            self._pending_replies_sem.release()

        message, future = prepare_message(data, append_to_queue)

        debugger.log(f"DataClient: sending: {message}")

        # send message to server
        self.send(message.model_dump_json(
            exclude_unset=True
        ).encode(self.encoding))

        debugger.trace(f"DataClient: sent message")
        return future

    def _try_match_reply(self, message: AckMessage | ReplMessage) -> None:
        """
        try to match a reply type message to an already sent message
        """
        debugger.trace(f"matching {message}")
        debugger.trace(f"pending: {self._pending_replies.keys()}")

        if message.data.to in self._pending_replies:
            # make sure no one else is writing to pending_replies
            self._pending_replies_sem.acquire()

            # remove reply from pending
            reply = self._pending_replies[message.data.to]
            self._pending_replies.pop(message.data.to)

            self._pending_replies_sem.release()

            # finish message future
            reply.message = message

            debugger.log(f"matched reply to: {message.data.to}")
            return

        debugger.warning("Unable to match reply: ", message)

    def stop(self) -> None:
        """
        stop the client
        """
        debugger.trace("shutting down DataClient")

        self._running = False
        self.shutdown(0)

        self._receive_future.cancel()
        debugger.info("DataClient shut down")
