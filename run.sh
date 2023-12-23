#!/bin/bash
source ./.venv/bin/activate

export PYTHONPATH=.

ryu-manager --verbose ./src/controllers/netconf.py ./src/topology/classic.py 