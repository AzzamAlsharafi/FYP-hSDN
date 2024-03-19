from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from typing import List

import uvicorn

import src.api.host as host

app = FastAPI()

origins = [
    '*'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

topology = {
    "devices": [],
    "links": []
}

configurations = {
    "classic": {},
    "sdn": {}
}

policies = {
    "policies": []
}

@app.get("/")
def read_root():
    return {"Hello": "Ryu"}

@app.get("/topology")
def read_topology():
    return topology

@app.put("/topology")
def update_topology(devices: List[dict], links: List[dict]):
    topology["devices"] = devices
    topology["links"] = links
    return {"topology": topology}

@app.get("/configurations")
def read_configurations():
    return configurations

@app.put("/configurations/classic")
def update_classic_configurations(classic_conf: dict):
    configurations["classic"] = classic_conf
    return {"classic": configurations["classic"]}

@app.put("/configurations/sdn")
def update_sdn_configurations(sdn_conf: dict):
    configurations["sdn"] = sdn_conf
    return {"sdn": configurations["sdn"]}

@app.get("/policies")
def read_policies():
    return policies["policies"]

@app.put("/policies")
def update_policies(new_policies: List[dict]):
    policies["policies"] = new_policies
    return {"policies": policies}

uvicorn.run(app, host=host.host)