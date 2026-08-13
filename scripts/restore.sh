#!/usr/bin/env sh
set -eu
python3 "$(dirname "$0")/restore.py" --archive "$1" --destination "$2"

