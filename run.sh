#!/bin/bash
source ./.venv/bin/activate

export PYTHONPATH=.

python ./src/api/rest.py &
api_pid=$!

ryu-manager ./src/topology/manager.py \
            ./src/controllers/netconf.py \
            ./src/topology/classic.py \
            ./src/topology/sdn.py \
            ./src/policy/manager.py \
            ./src/configuration/generator.py \
            ./src/configuration/classic.py \
            ./src/configuration/sdn.py \
            ./src/api/connector.py &
ryu_pid=$!

trap "kill $api_pid $ryu_pid" SIGINT SIGTERM
wait $api_pid $ryu_pid