#!/usr/bin/env python3
"""Rebuild the patched APK: apktool build -> splice classes5.dex -> align -> sign.

Usage:
  python3 build_apk.py --base original.apk --decoded apktool-out --tag v51

Environment:
  ANDROID_HOME   Android SDK root (default ~/Android/Sdk)
  KEYSTORE       debug keystore (default ~/.android/debug.keystore)
  KEY_ALIAS      default androiddebugkey
  KEY_PASS       default android
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile


def find_build_tools(sdk):
    bt = os.path.join(sdk, "build-tools")
    if not os.path.isdir(bt):
        sys.exit("build-tools not found under %s" % sdk)
    versions = sorted(os.listdir(bt))
    return os.path.join(bt, versions[-1])


def run(cmd, label):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("%s: rc=%d" % (label, r.returncode))
    if r.returncode:
        print((r.stdout or "") + (r.stderr or ""))
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="official signed APK")
    ap.add_argument("--decoded", required=True, help="apktool decoded directory")
    ap.add_argument("--tag", default="patched")
    ap.add_argument("--apktool", default=None, help="path to apktool.jar")
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()

    sdk = os.environ.get("ANDROID_HOME", os.path.expanduser("~/Android/Sdk"))
    bt = find_build_tools(sdk)
    apktool = args.apktool or os.path.join(os.path.dirname(__file__), "..", "tools", "apktool_3.0.3.jar")
    keystore = os.environ.get("KEYSTORE", os.path.expanduser("~/.android/debug.keystore"))
    alias = os.environ.get("KEY_ALIAS", "androiddebugkey")
    kpass = os.environ.get("KEY_PASS", "android")

    work = os.path.join(args.outdir, "_build_" + args.tag)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    full = os.path.join(work, "full.apk")
    if run(["java", "-Xmx4g", "-jar", apktool, "b", args.decoded, "-o", full], "apktool b"):
        sys.exit(1)

    with zipfile.ZipFile(full) as z:
        new5 = z.read("classes5.dex")
    print("classes5.dex", len(new5), hashlib.md5(new5).hexdigest())

    unsigned = os.path.join(args.outdir, "hust-sports-%s-unsigned.apk" % args.tag)
    with zipfile.ZipFile(args.base) as base, zipfile.ZipFile(unsigned, "w", allowZip64=True) as out:
        for info in base.infolist():
            if info.filename == "classes5.dex":
                ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                ni.compress_type = info.compress_type
                ni.external_attr = info.external_attr
                out.writestr(ni, new5)
            else:
                out.writestr(info, base.read(info.filename))

    aligned = os.path.join(work, "aligned.apk")
    signed = os.path.join(args.outdir, "hust-sports-%s.apk" % args.tag)
    subprocess.run([os.path.join(bt, "zipalign"), "-p", "-f", "4", unsigned, aligned], check=True)
    subprocess.run([os.path.join(bt, "apksigner"), "sign",
                    "--ks", keystore, "--ks-pass", "pass:" + kpass,
                    "--key-pass", "pass:" + kpass, "--ks-key-alias", alias,
                    "--out", signed, aligned], check=True)
    print("signed:", signed, os.path.getsize(signed))


if __name__ == "__main__":
    main()
