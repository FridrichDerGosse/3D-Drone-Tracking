"""
_data_server.py
26. November 2024

Provides the Data to the GUI

Author:
Nilusink
"""
from concurrent.futures import ThreadPoolExecutor, Future
from contextlib import suppress
from uuid import getnode
from time import sleep
import typing as tp
import socket

from ..tools import debugger, run_with_debug, SimpleLock
from ..tools.comms import *


if tp.TYPE_CHECKING:
    from ..tracking import TrackingMaster


DEVICE_MAC: int = getnode()


class DataServer(socket.socket):
    encoding: str = "utf-8"
    _pending_replies: dict[int, MessageFuture]
    _pending_updates: list[TRes3Data | SInfData]

    def __init__(self, address: tuple[str, int], pool: ThreadPoolExecutor) -> None:
        self._clients: list[socket.socket] = []
        self._address = address
        self._pool = pool

        self.tm: TrackingMaster = ...

        # initialize socket
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(self._address)
        self.settimeout(.2)
        self.listen()

        # threading stuff
        self._receive_future: Future = ...
        self._update_future: Future = ...
        self._running = False

        self._pending_updates = []
        self._pending_updates_sem = SimpleLock()
        self._pending_replies = {}
        self._pending_replies_sem = SimpleLock()

    def start(self) -> None:
        """
        start the server
        """
        self._running = True

        self._receive_future = self._pool.submit(self._receive_loop)
        self._update_future = self._pool.submit(self._client_update_loop)

        debugger.info("DataServer started")

    @run_with_debug(show_finish=True, reraise_errors=True)
    def _client_update_loop(self) -> None:
        """
        update all clients with track updates
        """
        while self._running:
            if len(self._pending_updates) <= 0:
                sleep(.01)
                debugger.trace(f"waiting on update, clients: {len(self._clients)}")
                continue

            debugger.log(f"server: updating clients, {self._pending_updates}")

            # get updates from list
            debugger.trace("waiting for sem")
            self._pending_updates_sem.acquire()

            updates = self._pending_updates
            self._pending_updates = []

            self._pending_updates_sem.release()
            debugger.trace("got sam")

            # send all updates to all clients
            for update in updates:
                debugger.trace(f"update: {update}")

                # iterate clients
                futures = []
                for client in self._clients:
                    debugger.trace(f"sending to {client}")
                    with suppress(Exception):
                        fut = self.send_message(update, client)
                        futures.append(fut)

                # wait for all clients to reply
                for future in futures:
                    debugger.trace(f"waiting for {future.origin_message.id}")

                    # wait for client
                    if not future.wait_until_done(.001, .2):
                        debugger.warning(f"Timeout while waiting for client ack")
                        continue

                    debugger.trace(f"got {future.origin_message.id}")

    @run_with_debug(show_finish=True, reraise_errors=True)
    def _receive_loop(self) -> None:
        """
        not meant to be called, should be run in a thread
        """
        while self._running:
            try:
                cl, addr = self.accept()

            except socket.timeout:
                continue

            except (ConnectionResetError, OSError, ConnectionAbortedError):
                debugger.error("DataServer: fatal network error")
                return self.stop()

            except Exception:
                debugger.error("DataServer: fatal error on receive")
                self.stop()
                raise

            self._pool.submit(self._handle_client, cl, addr)

    def _handle_client(
            self,
            client: socket.socket,
            addr: tuple[str, int]
    ) -> None:
        """
        handles a client
        """
        debugger.info(f"client {addr} connected")

        def send_sinf() -> None:
            # send all currently available camera info to client
            debugger.info(f"sending station information to client")
            for cam in self.tm.cams:
                debugger.trace(f"sending {cam} to {client}")
                fut = self.send_message(cam, client)

                # wait for ack
                fut.wait_until_done(.01)

            self._clients.append(client)


        self._pool.submit(send_sinf)

        while self._running:
            # receive message
            try:
                message = receive_message(
                    client,
                    lambda m: self.send_message(m, client),
                    self.encoding
                )

                if message is ...:
                    continue

            # disconnect client on message errors
            except RuntimeError:
                self._clients.remove(client)
                client.shutdown(0)
                return

            self._handle_message(message, client)

    def _handle_message(self, message: Message, client: socket.socket) -> None:
        """
        handle a verified message (should only be receiving acknowledgements)
        """
        debugger.log(f"handling: {message}")

        # create acknowledgements
        # ack = AckData(to=message.id, ack=True)
        nack = AckData(to=message.id, ack=False)

        # message handling
        match message:
            case ReqMessage(type="req", id=_, time=_, data=_):
                debugger.warning("DataServer client requested \"req\"")
                return self.send_message(nack, client)

            case AckMessage(type="ack", id=_, time=_, data=_):
                debugger.trace("Matched an AckMessage!")
                debugger.trace(f"Ack to: {message.data.to}, Ack status: {message.data.ack}")

                self._try_match_reply(message)
                return  # don't send acknowledgements to an acknowledgement

            case ReplMessage(type="repl", id=_, time=_, data=_):
                debugger.warning("DataServer client requested \"repl\"")

                self._try_match_reply(message)
                return self.send_message(nack, client)

            case DataMessage(type="data", id=_, time=_, data=_):
                debugger.warning("DataServer client requested \"data\"")
                return self.send_message(nack, client)

            case _:
                debugger.warning("unknown message type")
                return self.send_message(nack, client)

    # @run_with_debug(show_finish=True, reraise_errors=True)
    def send_message(
            self,
            data: MessageData,
            client: socket.socket
    ) -> MessageFuture | None:
        """
        send a message to the client
        """
        debugger.trace(f"DataServer: sending {data}")

        def append_to_queue(f: MessageFuture) -> None:
            # make sure no one else is writing to pending_replies
            self._pending_replies_sem.acquire()
            self._pending_replies[f.origin_message.id] = f
            self._pending_replies_sem.release()

        message, future = prepare_message(data, append_to_queue)

        debugger.log(f"DataServer: sending: {message}")

        # send message to server
        client.send(message.model_dump_json(
            exclude_unset=False
        ).encode(self.encoding))

        debugger.trace(f"DataServer: sent message")
        return future

    def update_clients(self, update: TRes3Data | SInfData) -> None:
        """
        send update to clients
        """
        debugger.trace(f"adding update")
        # check for write permissions
        self._pending_updates_sem.acquire()
        self._pending_updates.append(update)
        self._pending_updates_sem.release()

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
        debugger.trace("shutting down DataServer")

        self._running = False

        self._receive_future.cancel()
        self._update_future.cancel()

        debugger.info("DataServer shut down")
