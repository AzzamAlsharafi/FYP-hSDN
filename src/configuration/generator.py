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

        # Lists of address policies for each device. 
        # Contains valid policies (based on topology), and use interface name instead of ID.
        # {'C1': [(address, interface), ...], 'C2': [...], ...}
        self.addresses = {}

        # Keep track of the number of used link networks
        self.used_link_networks = 0

        # Link addresses 2D dictionary. First key is device with lower name (using sorted()).
        # {'C1-GigabitEthernet1': {'C2-GigabitEthernet1': ('192.168.99.1/30', '192.168.99.2/30'), ....}, ...}'
        self.link_addresses = {}
    
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

        self.addresses = {}
        self.configurations = {}

        for policy in self.policies:
            self.apply_policy(policy)

        self.global_routing()

        self.logger.debug(f'Generated configurations: {self.configurations}')
        
    # Apply policy and do some processing
    def apply_policy(self, policy):
        if policy.type == 'address':
            self.apply_address_policy(policy)
    
    def apply_address_policy(self, policy):
        device = policy.device
        interface = policy.interface

        d = self.get_device(device)

        if d and (len(d['ports']) > interface):            
            port = d['ports'][interface]

            if d['type'] == 'Classic':
                port = port['interface_name']
            else:
                port = port['port_no']

            add = (policy.address, port)
            conf = f'address {port} {policy.address}'

            self.append_dict_list(self.addresses, device, add)
            self.append_dict_list(self.configurations, device, conf)

            self.logger.debug(f'Added AddressPolicy for {device}: {add}')
        else:
            self.logger.debug(f'Skipped AddressPolicy: {policy.device} {policy.interface} {policy.address}')

    # Run global routing algorithm based on collected address policies
    def global_routing(self):
        # Addresses configurations for links
        for link in self.links:
            ((device1, port1), (device2, port2)) = link
            (add1, add2) = self.get_link_addresses(link)

            conf1 = f'address {port1} {add1}'
            conf2 = f'address {port2} {add2}'

            self.append_dict_list(self.configurations, device1, conf1)
            self.append_dict_list(self.configurations, device2, conf2)
        
        # Route configurations for every device to all address policies interfaces
        for device in self.devices:
            # TODO: this runs dijkstra for every device everytime.
            # It should be optimized to run only once for every topology change.
            distances = self.run_dijkstra(device['name'])
            
            for policy_device in self.addresses:
                if device['name'] == policy_device: # Skip device if it's the same as the policy device
                    continue
                
                # Find next hop device to policy device
                next_hop = self.find_next_hop_device(distances, policy_device)
                if next_hop:
                    
                    # If next hop is the same as the device, then link is direct
                    # and next hop is the policy device
                    if next_hop == device['name']:
                        next_hop = policy_device

                    # Find exit interface and next hop address
                    (exit_interface, next_hop_add) = self.get_exit_interface_next_hop(device['name'], next_hop)
                    if exit_interface:
                        
                        # Add route configuration for every address policy of policy device
                        for (address, _) in self.addresses[policy_device]:
                            conf = f'route {address} {exit_interface} {next_hop_add}'
                            self.append_dict_list(self.configurations, device['name'], conf)

    # Returns next available IPv4 addresses from links subnet.
    # TODO: Links subnet can be configured by user. Use 192.168.99.0/24 for now
    def next_link_addresses(self):
        add1 = f'192.168.99.{(self.used_link_networks * 4) + 1}/30'
        add2 = f'192.168.99.{(self.used_link_networks * 4) + 2}/30'

        self.used_link_networks += 1

        return (add1, add2)
    
    # Returns link addresses if exists, otherwise generates new ones
    def get_link_addresses(self, link):
        ((device1, port1), (device2, port2)) = link

        key1 = f'{device1}-{port1}'
        key2 = f'{device2}-{port2}'

        # Ensure order consistency
        keys = sorted([key1, key2])

        addresses = None

        try:
            addresses = self.link_addresses[keys[0]][keys[1]]
        except:
            addresses = self.next_link_addresses()
            if keys[0] in self.link_addresses:
                self.link_addresses[keys[0]][keys[1]] = addresses
            else:
                self.link_addresses[keys[0]] = {keys[1]: addresses}
        
        return addresses
    
    # Find next hop device to a device based on Dijkstra's distances table
    def find_next_hop_device(self, distances, device):
        (distance, reach_by) = distances[device]

        while distance > 2 and reach_by is not None:
            (distance, reach_by) = distances[reach_by]
        
        return reach_by

    # Find exit interface and next hop address from device to another device
    def get_exit_interface_next_hop(self, device, next_hop):
        for link in self.links:
            ((device1, port1), (device2, port2)) = link

            if device1 == device and device2 == next_hop:
                add2 = self.get_link_addresses(link)[1]
                return (port1, add2)
            elif device2 == device and device1 == next_hop:
                add1 = self.get_link_addresses(link)[0]
                return (port2, add1)
        
        return (None, None)

    # Run Dijkstra's algorithm for a device
    def run_dijkstra(self, device):
        # Dijkstra's distances table
        # {'C1': (0, None), 'C2': (5, 'C1'), ...}
        distances = {}

        # List of unvisited nodes
        unvisited = [device['name'] for device in self.devices]

        # Initialize distances
        for u in unvisited:
            distances[u] = (float('inf'), None)

        # Set distance to self to 0
        distances[device] = (0, None)

        # Run Dijkstra's algorithm
        while unvisited:
            # Find node with smallest distance
            minimum = min(unvisited, key=lambda x: distances[x][0])

            neighbours = self.get_neighbours(minimum)

            # Update distances of unvisited neighbours
            for n in neighbours:
                if n in unvisited:
                    distance = distances[minimum][0] + 1

                    if distance < distances[n][0]:
                        distances[n] = (distance, minimum)
            
            # Mark node as visited
            unvisited.remove(minimum)
        
        return distances

    # Returns list of neighbours for a device
    def get_neighbours(self, device):
        neighbours = []
        for link in self.links:
            ((device1, _), (device2, _)) = link
            

            if device1 == device:
                neighbours.append(device2)
            elif device2 == device:
                neighbours.append(device1)
        
        return neighbours

    # Returns device from list by name
    def get_device(self, name):
        return next((device for device in self.devices if device["name"] == name), None)
    
    # Append item to a list in a dictionary
    def append_dict_list(self, dict, key, item):
        if key in dict:
            dict[key].append(item)
        else:
            dict[key] = [item]