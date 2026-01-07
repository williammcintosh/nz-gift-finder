#!/bin/zsh
cd "$(dirname "$0")"
python3 -m http.server 5500 > preview.log 2>&1 &
sleep 1
open "http://127.0.0.1:5500"
