from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from typing import List

import uvicorn

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

uvicorn.run(app)