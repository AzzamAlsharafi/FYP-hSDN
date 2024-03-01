import logging
import requests

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls

from src.events import EventTopology, EventClassicConfigurations, EventSdnConfigurations

# Responsible for communication between Ryu and FastAPI
class ApiConnector(app_manager.RyuApp):

    def __init__(self, *args, **kwargs):
        super(ApiConnector, self).__init__(*args, **kwargs)

        self.logger.setLevel(logging.INFO)

    @set_ev_cls(EventTopology)
    def topology_handler(self, ev):        
        devices = ev.devices
        
        links = []

        for link in ev.links:
            ((device1, port1), (device2, port2)) = link
            links.append({'device1': device1, 'port1': port1, 'device2': device2, 'port2': port2})

        try:
            requests.put('http://localhost:8000/topology', json={'devices': devices, 'links': links})
        except Exception as e:
            self.logger.error(f'Failed to send topology to API: {str(e)}')

    @set_ev_cls(EventClassicConfigurations)
    def classic_configurations_handler(self, ev):
        try:
            requests.put('http://localhost:8000/configurations/classic', json=ev.configurations)
        except Exception as e:
            self.logger.error(f'Failed to send classic configurations to API: {str(e)}')

    @set_ev_cls(EventSdnConfigurations)
    def sdn_configurations_handler(self, ev):
        try:
            requests.put('http://localhost:8000/configurations/sdn', json=ev.configurations)
        except Exception as e:
            self.logger.error(f'Failed to send SDN configurations to API: {str(e)}')