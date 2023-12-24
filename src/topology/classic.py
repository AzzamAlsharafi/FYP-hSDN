import time

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls

from src.events import RequestNetconfDiscovery

# Handles topology discovery for classic (NETCONF) devices
class ClassicTopologyDiscovery(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(ClassicTopologyDiscovery, self).__init__(*args, **kwargs)

    def start(self):
        super(ClassicTopologyDiscovery, self).start()

        self.run()

    # Continuously calls NetconfController to run topology discovery every 30 seconds
    def run(self):
        while True:
            start = time.time()
            rep = self.send_request(RequestNetconfDiscovery())
            end = time.time()

            self.logger.info(f'NETCONF topology discovery took {end - start} seconds')
            self.logger.info(f'NETCONF topology: {rep.topology}')

            time.sleep(30 - (end - start))

    # Runs after NETCONF controller establishes connection with devices
    # @set_ev_cls(EventControllerReady)
    # def netconf_controller_ready(self, ev):
    #     # Enable LLDP on all devices
    #     for ip_address in ev.ip_addresses:
    #         self.send_request(RequestEnableLldp(ip_address))