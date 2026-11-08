"""Bridge v2: Renode's Telnet socket (Windows host) -> raw TCP for fprime-gds, serving every client.

usage: bridge_multi.py <renode_host> <renode_port> <listen_port>

Fixes bridge_wsl.py, which accepted only the first TCP client. Run 4 showed comm's connection stayed unaccepted
in the listen backlog while the bridge fed a different client (127.0.0.1:45098). Here each accepted client gets
the Renode byte stream, and client bytes go back to Renode with 0xFF escaped.
"""
import socket
import sys
import threading
import time

renode = None
renode_lock = threading.Lock()
clients = []
clients_lock = threading.Lock()
counter = {"renode_to_gds": 0, "gds_to_renode": 0, "chunks": 0, "raw_total": 0,
           "ff_raw": 0, "dropped": 0, "clients_seen": 0}


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


class TelnetStrip:
    def __init__(self):
        self.state = 0

    def feed(self, data):
        out = bytearray()
        for b in data:
            if self.state == 0:
                if b == 0xFF:
                    self.state = 1
                else:
                    out.append(b)
            elif self.state == 1:
                if b == 0xFF:
                    out.append(0xFF)
                    self.state = 0
                elif b in (0xFB, 0xFC, 0xFD, 0xFE):
                    self.state = 2
                elif b == 0xFA:
                    self.state = 3
                else:
                    self.state = 0
            elif self.state == 2:
                self.state = 0
            elif self.state == 3:
                if b == 0xFF:
                    self.state = 4
            elif self.state == 4:
                self.state = 0 if b == 0xF0 else 3
        return bytes(out)


def serve_client(sock, addr):
    with clients_lock:
        clients.append(sock)
    log(f"client {addr} serving")
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                break
            with renode_lock:
                renode.sendall(data.replace(b"\xff", b"\xff\xff"))
            counter["gds_to_renode"] += len(data)
    except OSError as exc:
        log(f"client {addr} error: {exc!r}")
    finally:
        with clients_lock:
            if sock in clients:
                clients.remove(sock)
        log(f"client {addr} gone")


def accept_loop(srv):
    while True:
        sock, addr = srv.accept()
        counter["clients_seen"] += 1
        log(f"client connected {addr}")
        threading.Thread(target=serve_client, args=(sock, addr), daemon=True).start()


def pump_renode():
    strip = TelnetStrip()
    while True:
        data = renode.recv(4096)
        if not data:
            log("renode closed")
            break
        clean = strip.feed(data)
        counter["raw_total"] += len(data)
        counter["ff_raw"] += data.count(0xFF)
        counter["dropped"] += len(data) - len(clean)
        if not clean:
            continue
        counter["renode_to_gds"] += len(clean)
        counter["chunks"] += 1
        # Send outside the lock: a client's serve thread needs the lock to unregister, so holding it during
        # sendall could hang the pump when that client stops reading.
        with clients_lock:
            snapshot = list(clients)
        dead = []
        for s in snapshot:
            try:
                s.sendall(clean)
            except OSError:
                dead.append(s)
        if dead:
            with clients_lock:
                for s in dead:
                    if s in clients:
                        clients.remove(s)


def report():
    while True:
        time.sleep(5)
        with clients_lock:
            n = len(clients)
        log(f"bytes renode_to_gds={counter['renode_to_gds']} gds_to_renode={counter['gds_to_renode']} "
            f"chunks={counter['chunks']} raw_total={counter['raw_total']} ff_raw={counter['ff_raw']} "
            f"dropped={counter['dropped']} clients_now={n} clients_seen={counter['clients_seen']}")


def main():
    global renode
    renode_host, renode_port, listen_port = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    renode = socket.create_connection((renode_host, renode_port), timeout=30)
    renode.settimeout(None)
    log(f"renode connected {renode_host}:{renode_port}")
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", listen_port))
    srv.listen(8)
    log(f"listening 127.0.0.1:{listen_port}")
    threading.Thread(target=accept_loop, args=(srv,), daemon=True).start()
    threading.Thread(target=report, daemon=True).start()
    pump_renode()


if __name__ == "__main__":
    main()
