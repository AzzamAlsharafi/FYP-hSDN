#!/bin/bash
python3.9 -m venv .venv
source .venv/bin/activate

git clone https://github.com/faucetsdn/ryu.git
git checkout d6cda4f427ff8de82b94c58aa826824a106014c2
pip install ./ryu
pip install -r ./ryu/tools/optional-requires
