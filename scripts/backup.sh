#!/usr/bin/env sh
set -eu
python3 "$(dirname "$0")/backup.py" --destination "$1"

