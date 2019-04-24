#!/usr/bin/env bash

# Get the directory where this script lives
DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$DIR"
[[ ! -d "venv" ]] && python3 -m venv venv && venv/bin/pip3 install pip wheel --upgrade
pip_args=(--upgrade)
pip_version=$(venv/bin/pip3 --version | egrep -o 'pip (\d+)' | cut -c 5-)
[[ -z "$pip_version" ]] && pip_version=$(venv/bin/pip3 --version | perl -pe 's/^pip\s+(\d+).*/$1/')
[[ -z "$pip_version" ]] && pip_version=0
[[ $pip_version -gt 9 ]] && pip_args=(--upgrade --upgrade-strategy eager)
venv/bin/pip3 install -r requirements.txt ${pip_args[@]}
venv/bin/python3 setup.py develop

if [[ ! -f "$HOME/.config/redis-helper/settings.ini" ]]; then
    mkdir -pv "$HOME/.config/redis-helper"
    cp -av redis_helper/settings.ini "$HOME/.config/redis-helper"
fi
