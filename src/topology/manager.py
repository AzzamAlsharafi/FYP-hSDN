from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls

from src.events import EventNetconfTopology, EventSdnTopology


class TopologyManager(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(TopologyManager, self).__init__(*args, **kwargs)

    # Listens for NETCONF topology events
    @set_ev_cls(EventNetconfTopology)
    def netconf_topology_handler(self, ev):
        self.logger.info(f'NETCONF topology: {ev.topology}')
    
    # Listens for SDN topology events
    @set_ev_cls(EventSdnTopology)
    def sdn_topology_handler(self, ev):
        self.logger.info(f'SDN topology: {ev.topology}')