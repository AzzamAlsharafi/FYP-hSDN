#!/bin/bash
python3.9 -m venv .venv
source .venv/bin/activate

git clone https://github.com/faucetsdn/ryu.git
cd ryu
git checkout d6cda4f427ff8de82b94c58aa826824a106014c2
pip install .
pip install -r ./tools/optional-requires
pip install scapy