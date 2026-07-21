#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$DIR/x-clip-purify.py" "$@"
