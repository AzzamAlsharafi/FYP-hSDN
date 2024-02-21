import logging

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls

from src.events import EventClassicConfigurations, EventNetconfConfigurations

class ClassicConfigurator(app_manager.RyuApp):

    _EVENTS = [EventNetconfConfigurations]

    def __init__(self, *args, **kwargs):
        super(ClassicConfigurator, self).__init__(*args, **kwargs)
    
        self.logger.setLevel(logging.INFO)
    
    # Listens for classic devices configurations from ConfigurationGenerator
    @set_ev_cls(EventClassicConfigurations)
    def classic_configurations_handler(self, ev):
        self.send_event_to_observers(EventNetconfConfigurations(ev.configurations))