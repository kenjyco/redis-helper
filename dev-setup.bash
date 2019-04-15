#!/usr/bin/env bash

# Get the directory where this script lives
DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$DIR"
[[ ! -d "venv" ]] && python3 -m venv venv && venv/bin/pip3 install pip wheel --upgrade
venv/bin/pip3 install -r requirements.txt --upgrade
venv/bin/python3 setup.py develop

if [[ ! -f "$HOME/.config/redis-helper/settings.ini" ]]; then
    mkdir -pv "$HOME/.config/redis-helper"
    cp -av redis_helper/settings.ini "$HOME/.config/redis-helper"
fi
