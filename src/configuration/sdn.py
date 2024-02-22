import logging

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls

from src.events import EventSdnConfigurations

class SdnConfigurator(app_manager.RyuApp):

    def __init__(self, *args, **kwargs):
        super(SdnConfigurator, self).__init__(*args, **kwargs)
    
        self.logger.setLevel(logging.INFO)
    
    # TODO: Currently configure from SdnTopologyDiscovery. Temporary solution.
    # Listens for classic devices configurations from ConfigurationGenerator
    # @set_ev_cls(EventSdnConfigurations)
    # def netconf_configurations_handler(self, ev):
    #     configurations = ev.configurations