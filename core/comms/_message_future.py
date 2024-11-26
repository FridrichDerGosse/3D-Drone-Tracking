"""
_message_future.py
"""
from threading import Semaphore
from time import sleep

from ._message_types import Message


class MessageFuture:
    _message: Message

    def __init__(self, origin_message: Message | None = None) -> None:
        self._message = ...
        self._sem = Semaphore()
        self._origin_message = origin_message

    def done(self) -> bool:
        return self._message is not ...

    def wait_until_done(self, check_interval: float = .01) -> None:
        """
        wait until the Future has been set
        """
        while not self.done():
            sleep(check_interval)

    @property
    def message(self) -> Message:
        if self.done():
            return self._message

        raise RuntimeError("Message not set")

    @message.setter
    def message(self, message: Message) -> None:
        # make sure the message can only be set once across threads
        if self.done() or not self._sem.acquire(timeout=.01):
            raise RuntimeError("Message has already been set!")

        self._message = message
        self._sem.release()

    @property
    def origin_message(self) -> Message:
        return self._origin_message.copy()
