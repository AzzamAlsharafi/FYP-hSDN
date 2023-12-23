#!/bin/bash
source ./.venv/bin/activate

export PYTHONPATH=.

ryu-manager --verbose ./src/topology/classic.py ./src/controllers/netconf.py 