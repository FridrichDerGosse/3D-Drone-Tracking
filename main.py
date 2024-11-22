"""
main.py
19. November 2024

Converts three camera angles to one 3-dimensional point

Author:
Nilusink
"""
from concurrent.futures import ThreadPoolExecutor
from core import DataClient, TrackingMaster


SERVER_ADDR: tuple[str, int] = ("127.0.0.1", 2)


def main():
    tm = TrackingMaster()

    # threading stuff
    pool = ThreadPoolExecutor()

    # start socket stuff
    dc = DataClient(SERVER_ADDR, tm.update_tracks, pool)


if __name__ == '__main__':
    main()
