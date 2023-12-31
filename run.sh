#!/bin/bash
source ./.venv/bin/activate

export PYTHONPATH=.

ryu-manager ./src/topology/manager.py ./src/controllers/netconf.py ./src/topology/classic.py ./src/topology/sdn.py