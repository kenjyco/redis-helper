#!/usr/bin/env bash


run_cmd() {
    if [[ -z "$@" ]]; then
        echo "No python command passed in"
        return 1
    fi
	for venv_name in venv_py*; do
		echo -e "\n\n\n%%%%%%%%%%%%%%%\n  $(echo $venv_name | tr '[a-z]' '[A-Z]')\n%%%%%%%%%%%%%%%"
        echo $@
        ${venv_name}/bin/python -c "$@"
	done
}

run_cmd "import redis_helper as rh; import redis; import hiredis; print('redis: {}, hiredis: {}'.format(redis.__version__, hiredis.__version__))"
