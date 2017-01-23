#!/usr/bin/env bash

# Get the directory where this script lives
DIR="$(cd "$(dirname "$0")" && pwd)"

[[ ! -d "venv" ]] && python3 -m venv venv && venv/bin/pip3 install wheel
venv/bin/pip3 install pip --upgrade
venv/bin/pip3 install -r requirements.txt --upgrade

# Save the full path to this repository to `~/.beu_path`
echo "$DIR" > $HOME/.redis_helper_path
