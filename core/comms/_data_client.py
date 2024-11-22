"""
_data_client.py
19. November  2024

retrieves data from camera tracking

Author:
Nilusink
"""
from concurrent.futures import ThreadPoolExecutor, Future
from pydantic import TypeAdapter, ValidationError
import socket as s

from ..maths import CameraResult
from ._message_types import *


class DataClient(s.socket):
    def __init__(
            self,
            server_address: tuple[str, int],
            on_receive_callback: tp.Callable[[TResData], None],
            pool: ThreadPoolExecutor
    ) -> None:
        self._server_address = server_address
        self._callback = on_receive_callback
        self._pool = pool

        # initialize socket
        super().__init__(s.AF_INET, s.SOCK_STREAM)

        # threading stuff
        self._receive_future: Future = ...
        self._running = False

    def start(self) -> None:
        """
        connects to the server and starts background threads
        """
        # connect to server
        self.connect(self._server_address)

        # start thread
        self._running = True
        self._receive_future = self._pool.submit(self._receive_loop)

    def _receive_loop(self) -> None:
        """
        not meant to be called, should be run in a thread
        """
        # pydantic valitator
        message_adapter = TypeAdapter(Message)

        while self._running:
            # receive message
            try:
                data = self.recv(1024).decode()

            except self.timeout:
                print(f"client timeout")
                return self.stop()

            # validate message
            try:
                validated_data = message_adapter.validate_json(data)

            except ValidationError:
                print(f"received invalid json: {data}")
                continue

            self._handle_message(validated_data)

    def _handle_message(self, message: Message) -> None:
        """

        :param message:
        :return:
        """

        # message handling
        match message:
            case ReqMessage(type="req", id=_, time=_, data=_):
                print("Matched a ReqMessage!")
                print(f"Request type: {message.data.req}")
                raise RuntimeWarning("not handled")

            case AckMessage(type="ack", id=_, time=_, data=_):
                print("Matched an AckMessage!")
                print(f"Ack to: {message.data.to}, Ack status: {message.data.ack}")
                raise RuntimeWarning("not handled")

            case ReplMessage(type="repl", id=_, time=_, data=_):
                print("Matched a ReplMessage!")
                print(f"Reply data: {message.data.data}")
                raise RuntimeWarning("not handled")

            case DataMessage(type="data", id=_, time=_, data=_):
                print("Matched a DataMessage!")
                print(f"Data message type: {message.data.type}")

                match message.data:
                    case TResDataMessage(type="tres", data=_):
                        print(f"Track result, data: {message.data.data}")
                        self._callback(message.data.data)

                    case SInfDataMessage(type="sinf", data=_):
                        print(f"station information data: {message.data.data}")
                        raise RuntimeWarning("not handled")

            case _:
                print("Unknown message type")

    def stop(self) -> None:
        """
        stop the client
        """
        self._running = False
        self.shutdown(0)

        self._receive_future.cancel()
