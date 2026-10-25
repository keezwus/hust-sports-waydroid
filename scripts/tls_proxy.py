"""TLS intercept proxy for petzjk.hust.edu.cn.

Listens on 0.0.0.0:443 with a cert signed by our CA, forwards to the real
server over HTTPS, and logs full request/response bodies to ./cap/.
"""
import http.client
import os
import socket
import ssl
import threading
import time

HERE = os.path.expanduser("~/tiyu/mitm")
CERT = os.path.join(HERE, "srv-chain.pem")
KEY = os.path.join(HERE, "srv.key")
CAP = os.path.join(HERE, "cap")
UP = "petzjk.hust.edu.cn"
os.makedirs(CAP, exist_ok=True)
seq = 0


def read_request(f):
    line = f.readline()
    if not line:
        return None
    reqline = line.decode("latin1").strip()
    headers = {}
    while True:
        h = f.readline()
        if h in (b"\r\n", b"\n", b""):
            break
        k, _, v = h.decode("latin1").partition(":")
        headers[k.strip()] = v.strip()
    try:
        method, path, _ = reqline.split(" ", 2)
    except ValueError:
        return None
    body = b""
    if headers.get("Transfer-Encoding", "").lower() == "chunked":
        while True:
            szline = f.readline().strip()
            if not szline:
                break
            sz = int(szline, 16)
            if sz == 0:
                f.readline()
                break
            body += f.read(sz)
            f.read(2)
    elif "Content-Length" in headers:
        body = f.read(int(headers["Content-Length"]))
    return method, path, headers, body


def handle(conn):
    global seq
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT, KEY)
    try:
        tls = ctx.wrap_socket(conn, server_side=True)
    except Exception as e:
        print("tls handshake failed:", e, flush=True)
        conn.close()
        return
    f = tls.makefile("rwb")
    try:
        while True:
            req = read_request(f)
            if not req:
                break
            method, path, headers, body = req
            seq += 1
            tag = "%s_%04d" % (time.strftime("%H%M%S"), seq)
            with open(os.path.join(CAP, tag + "_req.meta"), "w") as m:
                m.write("%s %s\n" % (method, path))
                for k, v in headers.items():
                    m.write("%s: %s\n" % (k, v))
            if body:
                open(os.path.join(CAP, tag + "_req.bin"), "wb").write(body)

            hdrs = {k: v for k, v in headers.items()
                    if k.lower() not in ("host", "connection", "content-length",
                                         "accept-encoding", "transfer-encoding")}
            hdrs["Accept-Encoding"] = "identity"
            try:
                c2 = http.client.HTTPSConnection(UP, 443, timeout=40)
                c2.request(method, path, body=body if body else None, headers=hdrs)
                r = c2.getresponse()
                data = r.read()
                status, reason, rh = r.status, r.reason, r.getheaders()
                c2.close()
            except Exception as e:
                data = ("proxy upstream error: %s" % e).encode()
                status, reason, rh = 502, "Bad Gateway", []
            open(os.path.join(CAP, tag + "_resp.bin"), "wb").write(data)
            with open(os.path.join(CAP, tag + "_resp.meta"), "w") as m:
                m.write("%d %s\n" % (status, path))

            out = ["HTTP/1.1 %d %s" % (status, reason)]
            for k, v in rh:
                if k.lower() in ("transfer-encoding", "content-encoding",
                                 "content-length", "connection"):
                    continue
                out.append("%s: %s" % (k, v))
            out.append("Content-Length: %d" % len(data))
            out.append("Connection: keep-alive")
            f.write(("\r\n".join(out) + "\r\n\r\n").encode("latin1"))
            f.write(data)
            f.flush()
    except Exception as e:
        print("conn error:", e, flush=True)
    finally:
        try:
            f.close()
            tls.close()
        except Exception:
            pass


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 443))
    s.listen(50)
    print("TLS proxy on 443 ->", UP, flush=True)
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
