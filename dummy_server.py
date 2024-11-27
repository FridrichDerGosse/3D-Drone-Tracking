from core import SInfDataMessage, SInfData, TResData, CamAngle, DataMessage, TResDataMessage
from threading import Thread
from core.tools import Vec3
import math as m
import socket
import time

running = True

s1_pos = Vec3.from_polar(0, 0, 10)
s2_pos = Vec3.from_polar((2*m.pi) / 3, 0, 10)
s3_pos = Vec3.from_polar((4*m.pi) / 3, 0, 10)

start = time.time()

stations = [
    SInfData(
        id=0,
        position=s1_pos.xyz,
        direction=(-s1_pos).xyz,
        fov=(.88888888, .5),
        resolution=(0, 0)
    ),
    SInfData(
        id=1,
        position=s2_pos.xyz,
        direction=(-s2_pos).xyz,
        fov=(.88888888, .5),
        resolution=(0, 0)
    ),
    SInfData(
        id=2,
        position=s3_pos.xyz,
        direction=(-s3_pos).xyz,
        fov=(.88888888, .5),
        resolution=(0, 0)
    )
]

result = TResData(
    track_id=0,
    cam_angles=[
        CamAngle(cam_id=0, direction=(.03, 0)),
        CamAngle(cam_id=1, direction=(.1, .01)),
        CamAngle(cam_id=2, direction=(.06, .1))
    ]
)

def handle_client(c: socket.socket, a: tuple):
    for station in stations:
        c.send(DataMessage(
            id=int(time.time() % 3),
            time=0,
            data=SInfDataMessage(
                data=station
            )
        ).model_dump_json().encode())

        # wait for ack
        c.recv(1024)

    def continually_send() -> None:
        time.sleep(2)
        while running:
            # send track stuff
            mod = time.time() - start

            c.send(DataMessage(
                id=int(time.time() % 3),
                time=time.time(),
                data=TResDataMessage(
                    data=TResData(
                        track_id=0,
                        cam_angles=[
                            CamAngle(cam_id=0, direction=(.03 + .1 * m.sin(.4 * mod), .1 + m.cos(.05 * mod) * .1)),
                            CamAngle(cam_id=1, direction=(.01 - .1 * m.sin(.4 * mod), .11 + m.cos(.05 * mod) * .1)),
                            CamAngle(cam_id=2, direction=(.06 + .1 * m.cos(.3 * mod), .15 + m.cos(.05 * mod) * .1))
                        ]
                    )
                )
            ).model_dump_json().encode())

            time.sleep(.2)

    Thread(target=continually_send).start()

    c.settimeout(.2)
    while running:
        try:
            msg = c.recv(1024)

        except TimeoutError:
            continue

        except ConnectionResetError:
            c.shutdown(0)
            return

        if msg == b"":
            print(f"client disconnect")
            c.shutdown(0)
            return

        print(f"received from \"{a}\":", msg)

def accept():
    print("listening")
    while running:
        try:
            Thread(target=handle_client, args=[*s.accept()]).start()

        except TimeoutError:
            continue

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("127.0.0.1", 10_000))
s.settimeout(.2)
s.listen()

print("socket setup")

Thread(target=accept).start()
print(f"server started")

input("press enter to close")
running = False
