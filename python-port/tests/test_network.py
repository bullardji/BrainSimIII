import sys
from pathlib import Path
import socket
import threading
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from network import udp_send


def test_udp_send_local():
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(("127.0.0.1", 0))
    port = recv_sock.getsockname()[1]
    messages = []

    def receiver():
        data, _ = recv_sock.recvfrom(1024)
        messages.append(data.decode())

    t = threading.Thread(target=receiver)
    t.start()
    udp_send("hello", "127.0.0.1", port)
    t.join(timeout=1)
    recv_sock.close()
    assert messages == ["hello"]
