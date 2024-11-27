"""
main.py
19. November 2024

Converts three camera angles to one 3-dimensional point

Author:
Nilusink
"""
from core import DataClient, TrackingMaster, debugger, DebugLevel, DataServer
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from icecream import ic


SERVER_ADDR: tuple[str, int] = ("127.0.0.1", 10_000)
DATA_SERVER_ADDR: tuple[str, int] = ("127.0.0.1", 20_000)


def main():
    # debugging setup
    start = perf_counter()

    def time_since_start() -> str:
        """
        stylized time since game start
        gamestart being time since `mainloop` was called
        """
        t_ms = round(perf_counter() - start, 4)

        t1, t2 = str(t_ms).split(".")
        return f"{t1: >4}.{t2: <4} |> "

    ic.configureOutput(prefix=time_since_start)
    debugger.init("./tracking.log", write_debug=False, debug_level=DebugLevel.info)

    # threading stuff
    pool = ThreadPoolExecutor()

    ds = DataServer(
        DATA_SERVER_ADDR,
        pool
    )

    # tracks
    tm = TrackingMaster(ds)

    # start socket stuff
    dc = DataClient(
        SERVER_ADDR,
        tm.update_tracks,
        tm.update_cams,
        pool
    )

    # start program
    dc.start()
    ds.start()

    input("press enter to stop")

    dc.stop()
    ds.stop()

    debugger.trace("shutting down threadpool")
    pool.shutdown(wait=True)
    debugger.info("Threadpool shutdown complete")


if __name__ == '__main__':
    main()

"""

"""