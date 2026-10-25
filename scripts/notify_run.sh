#!/bin/bash
set -a
. "${NOTIFY_ENV:-$HOME/.hermes/.env}"
set +a
python3 $HOME/tiyu/qq_send_image.py "$1" "$2" "$3"
