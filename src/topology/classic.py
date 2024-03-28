import logging
import time

from ryu.base import app_manager
from ryu.lib import hub

from src.events import RequestNetconfDiscovery, EventNetconfTopology

# Handles topology discovery for classic (NETCONF) devices
class ClassicTopologyDiscovery(app_manager.RyuApp):
    _EVENTS = [EventNetconfTopology]

    def __init__(self, *args, **kwargs):
        super(ClassicTopologyDiscovery, self).__init__(*args, **kwargs)

        self.logger.setLevel(logging.INFO)

    def start(self):
        super(ClassicTopologyDiscovery, self).start()

        # Runs topology discovery in separate thread, otherwise it would block Ryu
        self.task = hub.spawn(self.run)

    # Continuously calls NetconfController to run topology discovery every 1 second
    def run(self):
        interval = 1
        
        while True:
            start = time.time()
            rep = self.send_request(RequestNetconfDiscovery())
            end = time.time()

            self.send_event_to_observers(EventNetconfTopology(rep.topology))

            self.logger.debug(f'NETCONF topology discovery took {end - start} seconds')

            if (end - start) < interval:
                hub.sleep(interval - (end - start))