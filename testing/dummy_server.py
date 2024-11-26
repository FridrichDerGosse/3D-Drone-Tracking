from threading import Thread
import socket

running = True

def handle_client(c: socket.socket, a: tuple):
    c.settimeout(.2)

    while running:
        try:
            print(f"received from \"{a}\":", c.recv(1024))

        except TimeoutError:
            continue

        except ConnectionResetError:
            c.shutdown()
            return

def accept():
    while running:
        try:
            Thread(target=handle_client, args=[*s.accept()]).start()

        except TimeoutError:
            continue

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("127.0.0.1", 10_000))
s.settimeout(.2)
s.listen()


Thread(target=accept).start()
print(f"server started")

input("press enter to close")
running = False
