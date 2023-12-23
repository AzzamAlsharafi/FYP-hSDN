
from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls

from src.events import EventControllerReady, RequestEnableLldp

# Handles topology discovery for classic (NETCONF) devices
class ClassicTopologyDiscovery(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(ClassicTopologyDiscovery, self).__init__(*args, **kwargs)

    # Runs after NETCONF controller establishes connection with devices
    @set_ev_cls(EventControllerReady)
    def netconf_controller_ready(self, ev):
        # Enable LLDP on all devices
        for ip_address in ev.ip_addresses:
            self.send_request(RequestEnableLldp(ip_address))