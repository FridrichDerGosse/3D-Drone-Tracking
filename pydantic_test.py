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

from core.comms._data_client import try_find_id

try_find_id('{"id":173024,"time":"2024.11.22-11:25:01","station_id":1,"temperature":-2.6,"temperature_index":-4.46,"humidity":89.7,"air_pressure":null}')
try_find_id('{"id":173024,"time":"2024.1')

exit()
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
