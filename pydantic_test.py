"""
pydantic_test.py
20. November 2024

Test for using pydantic to validate comm messages

Author:
Nilusink
"""
from concurrent.futures import ThreadPoolExecutor
from pydantic import TypeAdapter
from core.comms import *
import typing as tp


def handle_msg(msg: TResData):
    print("callback: ", msg)


pool = ThreadPoolExecutor()
dc = DataClient(("", 1), handle_msg, pool)


message_adapter = TypeAdapter(Message)

x = message_adapter.validate_python({
    "type": "data",
    "id": 0,
    "time": 0,
    "data": {
        "type": "tres",
        "data": {
            "track_id": 0,
            "cam_angles": [
                {
                    "cam_id": 0,
                    "direction": [1.1, 1.1]
                }
            ]
        }
    }
})

print(x)
dc._handle_message(x)
