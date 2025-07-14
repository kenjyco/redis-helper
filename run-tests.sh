#!/usr/bin/env bash

echo -e "\n\n\n\n\n\n\n\n\n"
for venv_name in venv_py[0-9\.]*_**; do
# for venv_name in venv_py3.12*; do
# for venv_name in venv_py3.[5-9]*hiredis1.1.0*; do
    echo -e "\n\n\n%%%%%%%%%%%%%%%\n  $(echo $venv_name | tr '[a-z]' '[A-Z]')\n%%%%%%%%%%%%%%%"
    ${venv_name}/bin/pytest
done