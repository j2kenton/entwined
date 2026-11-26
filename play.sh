#!/usr/bin/env sh
# Play the Entwined prototype. Options are passed on, e.g.  ./play.sh --sixel
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
    exec python3 prototype/play.py "$@"
elif command -v python >/dev/null 2>&1; then
    exec python prototype/play.py "$@"
else
    echo "Entwined needs Python 3: https://www.python.org/downloads/"
    exit 1
fi
