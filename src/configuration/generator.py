import logging
import time

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls

from src.events import EventPolicies, EventTopology
from src.policy.policies import AddressPolicy

class ConfigurationGenerator(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(ConfigurationGenerator, self).__init__(*args, **kwargs)

        self.logger.setLevel(logging.INFO)

        self.time = time.time()

        self.policies = []
        self.devices = []
        self.links = []

        # Dictionary of devices configurations: {'C1': [conf1, conf2, conf3, ...], ...}
        self.configurations = {}
    
    # Listens for policies from PolicyManager
    @set_ev_cls(EventPolicies)
    def policies_handler(self, ev):
        # TODO: confirm == is actually running as intended
        if not self.policies == ev.policies:
            self.policies = ev.policies
            self.update()
    
    # Listens for topology from TopologyManager
    @set_ev_cls(EventTopology)
    def topo_handler(self, ev):
        # TODO: confirm == is actually running as intended
        if (not self.devices == ev.devices) or (not self.links == ev.links):
            self.devices = ev.devices
            self.links = ev.links
            self.update()

    # Update generated configuration
    def update(self):
        passed_time = time.time() - self.time

        # Stop function if it has been called less than 1 second ago
        if passed_time < 1:
            return
        
        self.time = time.time()

        self.configurations = {}

        for policy in self.policies:
            self.apply_policy(policy)

        self.logger.debug(f'Generated configurations: {self.configurations}')
        
    # Apply policy and generate configurations for it
    def apply_policy(self, policy):
        if policy.type == 'address':
            device = policy.device
            interface = policy.interface

            d = self.get_device(device)

            if d and (len(d['ports']) > interface):
                if not device in self.configurations:
                    self.configurations[device] = []
                
                port = d['ports'][interface]

                if d['type'] == 'Classic':
                    port = port['interface_name']
                else:
                    port = port['port_no']

                conf = f'address {port} {policy.address}'
                self.configurations[device].append(conf)

                self.logger.debug(f'Generated configuration for {device}: {conf}')
            else:
                self.logger.debug(f'Skipped AddressPolicy: {policy.device} {policy.interface} {policy.address}')
    
    def get_device(self, name):
        return next((device for device in self.devices if device["name"] == name), None)
