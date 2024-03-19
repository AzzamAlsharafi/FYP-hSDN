import logging
import requests

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls

from src.events import EventPolicies, EventTopology, EventClassicConfigurations, EventSdnConfigurations
import src.api.host as host

url = f'http://{host.host}:8000'

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
            requests.put(f'{url}/topology', json={'devices': devices, 'links': links})
        except Exception as e:
            self.logger.error(f'Failed to send topology to API: {str(e)}')

    @set_ev_cls(EventClassicConfigurations)
    def classic_configurations_handler(self, ev):
        try:
            requests.put(f'{url}/configurations/classic', json=ev.configurations)
        except Exception as e:
            self.logger.error(f'Failed to send classic configurations to API: {str(e)}')

    @set_ev_cls(EventSdnConfigurations)
    def sdn_configurations_handler(self, ev):
        try:
            requests.put(f'{url}/configurations/sdn', json=ev.configurations)
        except Exception as e:
            self.logger.error(f'Failed to send SDN configurations to API: {str(e)}')
    
    @set_ev_cls(EventPolicies)
    def policies_handler(self, ev):
        try:
            policies = []

            for policy in ev.policies:
                policies.append(policy.to_dict())

            requests.put(f'{url}/policies', json=policies)
        except Exception as e:
            self.logger.error(f'Failed to send policies to API: {str(e)}')