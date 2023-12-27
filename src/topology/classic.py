import time

from ryu.base import app_manager

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
        interval = 30
        
        while True:
            start = time.time()
            rep = self.send_request(RequestNetconfDiscovery())
            end = time.time()

            self.logger.info(f'NETCONF topology discovery took {end - start} seconds')
            self.logger.info(f'NETCONF topology: {rep.topology}')

            if (end - start) < interval:
                time.sleep(interval - (end - start))