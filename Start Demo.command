#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  python3 demo.py setup || exit 1
fi
python3 demo.py run --open
