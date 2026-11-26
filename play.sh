#!/usr/bin/env sh
# Play Entwined. Options are passed on, e.g.  ./play.sh --hero kael
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
    exec python3 -m game "$@"
elif command -v python >/dev/null 2>&1; then
    exec python -m game "$@"
else
    echo "Entwined needs Python 3: https://www.python.org/downloads/"
    exit 1
fi
