import logging

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls

from src.events import EventNetconfTopology, EventSdnTopology, EventTopology


class TopologyManager(app_manager.RyuApp):
    _EVENTS = [EventTopology]

    def __init__(self, *args, **kwargs):
        super(TopologyManager, self).__init__(*args, **kwargs)

        self.logger.setLevel(logging.INFO)

        self.netconf_topo = {'interfaces': {}, 'neighbors': {}}
        self.sdn_topo = {'ports': {}, 'neighbors': {}}

         # Global topology
        self.devices = [] # [{'name': X, 'type': X, 'ports': []}, ...]
        self.links = [] # [{(X, P)), (X, P)}, ...]

    # Listens for NETCONF topology events
    @set_ev_cls(EventNetconfTopology)
    def netconf_topology_handler(self, ev):
        self.netconf_topo = ev.topology
        self.update_topo()

        self.logger.debug(f'NETCONF topology: {ev.topology}')
    
    # Listens for SDN topology events
    @set_ev_cls(EventSdnTopology)
    def sdn_topology_handler(self, ev):
        self.sdn_topo = ev.topology
        self.update_topo()

        self.logger.debug(f'SDN topology: {ev.topology}')

    # Combine NETCONF and SDN topologies
    def update_topo(self):
        self.devices = []
        self.links = []

        netconf_interfaces = self.netconf_topo['interfaces']
        netconf_neighbors = self.netconf_topo['neighbors']

        sdn_ports = self.sdn_topo['ports']
        sdn_neighbors = self.sdn_topo['neighbors']

        # Add devices info
        for hostname, interfaces in netconf_interfaces.items():
            self.devices.append({
                'name': hostname,
                'type': 'Classic',
                'ports': interfaces
            })
        
        for label, ports in sdn_ports.items():
            self.devices.append({
                'name': label,
                'type': 'SDN',
                'ports': sorted(ports, key=lambda port: port['port_no'])
            })

        # Add links info. Only add bidirectional neighbors,
        # meaning that if link A->B exists, then link B->A must also exist
        for hostname, neighbors in netconf_neighbors.items():
            for neighbor in neighbors:
                link = (hostname, neighbor)
                self.add_link(link, 'netconf', netconf_neighbors, sdn_neighbors)
        
        for label, neighbors in sdn_neighbors.items():
            for neighbor in neighbors:
                link = (label, neighbor)
                self.add_link(link, 'sdn', netconf_neighbors, sdn_neighbors)

        self.send_topo()

        self.logger.debug(f'Topology updated: {self.devices}\n{self.links}')
    
    # Add link if it is bidirectional and new
    def add_link(self, link, source, netconf_neighbors, sdn_neighbors):
        bidirectional = self.check_bidrectional(link, netconf_neighbors, sdn_neighbors)

        if not bidirectional:
            return

        endpoint_1 = None
        endpoint_2 = None

        if source == 'netconf':
            endpoint_1 = (link[0], netconf_neighbors[link[0]][link[1]])
        else:
            endpoint_1 = (link[0], sdn_neighbors[link[0]][link[1]]['port'])

        if bidirectional == 'netconf':
            endpoint_2 = (link[1], netconf_neighbors[link[1]][link[0]])
        else:
            endpoint_2 = (link[1], sdn_neighbors[link[1]][link[0]]['port'])

        new_link = {endpoint_1, endpoint_2}
        
        if new_link not in self.links:
            self.links.append(new_link)
            
            self.logger.debug(f'Link found: {endpoint_1} <-> {endpoint_2}')

    # Check if a neighbor relation is bidirectional, and return source of reverse neighbor 
    def check_bidrectional(self, link, netconf_neighbors, sdn_neighbors):
        (label, neighbor) = link

        try:
            _ = netconf_neighbors[neighbor][label]
            return 'netconf'
        except:
            try:
                _ = sdn_neighbors[neighbor][label]
                return 'sdn'
            except:
                self.logger.debug(f'Unidirectional neighbors found, hostname: {label}, neighbor: {neighbor}')
                return None

    # Print topology in a readable format
    def print_topo(self):
        self.logger.info('='*150)
        self.logger.info('Topology:')
        self.logger.info(f'\tDevices ({len(self.devices)}):')
        for device in self.devices:
            self.logger.info(f'\t\t{device["name"]} ({device["type"]})')
            for port in device['ports']:
                self.logger.info(f'\t\t\t{port}')
        
        self.logger.info(f'\tLinks ({len(self.links)}):')
        for link in self.links:
            self.logger.info(f'\t\t{link}')
        self.logger.info('='*150)
        self.logger.info('')

    # Send topology to ConfigurationGenerator
    def send_topo(self):
        self.send_event_to_observers(EventTopology(self.devices, self.links))