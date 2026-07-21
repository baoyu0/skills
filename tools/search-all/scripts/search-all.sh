#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$DIR/search-all.py" "$@"
