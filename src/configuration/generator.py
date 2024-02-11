import logging

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls

from src.events import EventPolicies

class ConfigurationGenerator(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(ConfigurationGenerator, self).__init__(*args, **kwargs)

        self.logger.setLevel(logging.INFO)
    
    @set_ev_cls(EventPolicies)
    def policies_handler(self, ev):
        self.logger.info(f'Received Policies: {ev.policies}')