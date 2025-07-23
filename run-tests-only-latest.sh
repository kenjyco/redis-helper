#!/usr/bin/env bash

VENV_NAMES=(
    venv_py3.5.10
    venv_py3.6.15
    venv_py3.7.17
    venv_py3.8.20
    venv_py3.9.20
    venv_py3.10.15
    venv_py3.11.10
    venv_py3.12.7
    venv_py3.13.5
)

echo -e "\n\n\n\n\n\n\n\n\n"
for venv_name in ${VENV_NAMES[@]}; do
    echo -e "\n\n\n%%%%%%%%%%%%%%%\n  $(echo $venv_name | tr '[a-z]' '[A-Z]')\n%%%%%%%%%%%%%%%"
    ${venv_name}/bin/pytest
done
