"""
pydantic_test.py
20. November 2024

Test for using pydantic to validate comm messages

Author:
Nilusink
"""
from concurrent.futures import ThreadPoolExecutor
from core.tools import debugger, DebugLevel
from pydantic import TypeAdapter
from time import perf_counter
from core.comms import *
from icecream import ic

start = perf_counter()

def time_since_start() -> str:
    """
    styleized time since game start
    gamestart being time since `mainloop` was called
    """
    t_ms = round(perf_counter() - start, 4)

    t1, t2 = str(t_ms).split(".")
    return f"{t1: >4}.{t2: <4} |> "

ic.configureOutput(prefix=time_since_start)


# from core.comms._data_client import try_find_id

# try_find_id('{"id":173024,"time":"2024.11.22-11:25:01","station_id":1,"temperature":-2.6,"temperature_index":-4.46,"humidity":89.7,"air_pressure":null}')
# try_find_id('{"id":173024,"time":"2024.1')
#
# exit()

def handle_msg(msg: TResData):
    print("callback: ", msg)

debugger.init("./test.log", write_debug=True, debug_level=DebugLevel.trace)

pool = ThreadPoolExecutor()
dc = DataClient(("127.0.0.1", 10_000), handle_msg, pool)
dc.start()


message_adapter = TypeAdapter(Message)

# data = {
#     "type": "data",
#     "id": 0,
#     "time": 0,
#     "data": {
#         "type": "tres",
#         "data": {
#             "track_id": 0,
#             "cam_angles": [
#                 {
#                     "cam_id": 0,
#                     "direction": [1.1, 1.1]
#                 }
#             ]
#         }
#     }
# }

# data = {
#     "type": "req",
#     "id": 0,
#     "time": 0,
#     "data": {
#         "req": "sinfo"
#     }
# }

data = {
    "type": "ack",
    "id": 0,
    "time": 0,
    "data": {
        "to": 120934,
        "ack": 1
    }
}

# message matching test
dc.send_message(ReplData(to=324, data={}))
x = message_adapter.validate_python(data)

try:
    dc._handle_message(x)

except RuntimeWarning:
    ...

dc.stop()
