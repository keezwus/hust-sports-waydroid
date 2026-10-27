#!/usr/bin/env python3
"""Send a plain text message to a QQ user via the official Bot API.

Usage: qq_send_text.py "message" [qqbot:<openid>]
Credentials: QQ_APP_ID / QQ_CLIENT_SECRET / QQ_TARGET (qqbot:<openid>),
or ~/.config/tiyu/notify.env / ~/.hermes/.env with the same keys.
"""
import json
import os
import sys
import urllib.request

ENV_FILES = [os.path.expanduser("~/.config/tiyu/notify.env"),
             os.path.expanduser("~/.hermes/.env")]


def load_env():
    for path in ENV_FILES:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def post(url, body, token=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "QQBot " + token)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def main():
    load_env()
    msg = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    target = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("QQ_TARGET", "")
    if not target:
        sys.exit("QQ_TARGET missing")
    openid = target.split(":", 1)[-1]
    tok = post("https://bots.qq.com/app/getAppAccessToken",
               {"appId": os.environ["QQ_APP_ID"],
                "clientSecret": os.environ["QQ_CLIENT_SECRET"]})["access_token"]
    r = post("https://api.sgroup.qq.com/v2/users/%s/messages" % openid,
             {"content": msg, "msg_type": 0}, tok)
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
