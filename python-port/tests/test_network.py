import sys
from pathlib import Path
import socket
import threading
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from network import (
    udp_send,
    tcp_listen,
    tcp_accept,
    tcp_connect,
    tcp_send,
    tcp_receive,
    http_get,
    http_post,
    audio_broadcast,
    SubscriptionServer,
)


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


def test_tcp_echo():
    server = tcp_listen(0)
    port = server.getsockname()[1]

    def server_thread():
        conn = tcp_accept(server)
        data = tcp_receive(conn).strip()
        tcp_send(conn, data.upper())
        conn.close()

    t = threading.Thread(target=server_thread)
    t.start()
    client = tcp_connect("127.0.0.1", port)
    tcp_send(client, "hello")
    resp = tcp_receive(client).strip()
    client.close()
    t.join()
    server.close()
    assert resp == "HELLO"


def test_http_get_post():
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # type: ignore[override]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def do_POST(self):  # type: ignore[override]
            length = int(self.headers["Content-Length"])
            data = self.rfile.read(length)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(data)

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()

    try:
        assert http_get(f"http://127.0.0.1:{port}") == "ok"
        assert http_post(f"http://127.0.0.1:{port}", "hello") == "hello"
    finally:
        httpd.shutdown()
        thread.join()


def test_audio_broadcast_local():
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(("127.0.0.1", 0))
    port = recv_sock.getsockname()[1]
    data: list[bytes] = []

    def receiver():
        pkt, _ = recv_sock.recvfrom(1024)
        data.append(pkt)

    t = threading.Thread(target=receiver)
    t.start()
    audio_broadcast(b"abc", port=port, address="127.0.0.1")
    t.join(timeout=1)
    recv_sock.close()
    assert data == [b"abc"]


def test_subscription_server():
    server = SubscriptionServer(port=0)

    s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s1.bind(("127.0.0.1", 0))
    s1.settimeout(2)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s2.bind(("127.0.0.1", 0))
    s2.settimeout(2)

    s1.sendto(b"SUBSCRIBE", ("127.0.0.1", server.port))
    s2.sendto(b"SUBSCRIBE", ("127.0.0.1", server.port))

    import time

    time.sleep(0.1)
    udp_send("hello", "127.0.0.1", server.port)

    msg1 = s1.recv(1024)
    msg2 = s2.recv(1024)
    s1.close()
    s2.close()
    server.stop()
    assert msg1 == b"hello"
    assert msg2 == b"hello"
