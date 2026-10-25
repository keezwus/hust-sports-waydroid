#!/usr/bin/env python3
"""Send an image to a QQ C2C user via the official QQ Bot REST API."""
import base64
import json
import os
import sys
import urllib.request

APPID = os.environ["QQ_APP_ID"]
SECRET = os.environ["QQ_CLIENT_SECRET"]
OPENID = sys.argv[1]
PATH = sys.argv[2]
CAPTION = sys.argv[3] if len(sys.argv) > 3 else ""


def post(url, body, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "QQBot " + token
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


tok = post("https://bots.qq.com/app/getAppAccessToken",
           {"appId": APPID, "clientSecret": SECRET})["access_token"]
b64 = base64.b64encode(open(PATH, "rb").read()).decode()
up = post("https://api.sgroup.qq.com/v2/users/%s/files" % OPENID,
          {"file_type": 1, "file_data": b64, "srv_send_msg": False}, tok)
print("upload:", json.dumps(up, ensure_ascii=False)[:400])
fi = up.get("file_info") or (up.get("data") or {}).get("file_info")
if not fi:
    print("no file_info")
    sys.exit(1)
msg = post("https://api.sgroup.qq.com/v2/users/%s/messages" % OPENID,
           {"msg_type": 7, "media": {"file_info": fi}, "content": CAPTION, "msg_seq": 1}, tok)
print("message:", json.dumps(msg, ensure_ascii=False)[:400])
