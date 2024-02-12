from enum import Enum
import re

# Define policies classes

# Parent class for all policies
class Policy:
    def __init__(self, type):
        self.type = type

# Enum of available global commands
class GlobalCommand(Enum):
    ROUTING = 1 # When enabled, routing/reachability will be configured between all devices in the network.

# Global policy. Used to enable a global command.
class GlobalPolicy(Policy):
    def __init__(self, command):
        super(GlobalPolicy, self).__init__('global')
        
        if command == 'routing':
            self.command = GlobalCommand.ROUTING
        else:
            raise ValueError(f'Invalid global command: {command}')

    def __str__(self):
        return f'GlobalPolicy: {self.command}'

# Address policy. Used to configure an address on interface on a device.
class AddressPolicy(Policy):
    def __init__(self, device, interface, address):
        super(AddressPolicy, self).__init__('address')
        
        try:
            interface = int(interface)
            split = address.split('/') # Split address and mask
            mask = int(split[1])
            assert re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', split[0]) # IPv4 address regex
        except Exception:
            raise ValueError(f'Invalid input values')
        
        self.device = device
        self.interface = interface
        self.address = address

    def __str__(self):
        return f'AddressPolicy: {self.device} {self.interface} {self.address}'

# Flow policy. Used to define a flow in the network. TODO
class FlowPolicy(Policy):
    def __init__(self, name, src_ip, dst_ip, protocol, src_port, dst_port):
        super(FlowPolicy, self).__init__('flow')
        self.name = name
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.protocol = protocol
        self.src_port = src_port
        self.dst_port = dst_port

    def __str__(self):
        return f'FlowPolicy ({self.name}): {self.src_ip} -> {self.dst_ip} ({self.protocol}) {self.src_port} -> {self.dst_port}'

# Block policy. Used to block a flow in a specific device or zone. TODO
class BlockPolicy(Policy):
    def __init__(self, target, flow):
        super(BlockPolicy, self).__init__('block')
        self.target = target
        self.flow = flow
    
    def __str__(self):
        return f'BlockPolicy: {self.target} {self.flow}'

# Route policy. Used to route a flow through interface on a device. TODO
class RoutePolicy(Policy):
    def __init__(self, device, flow, interface):
        super(RoutePolicy, self).__init__('route')
        self.device = device
        self.flow = flow
        self.interface = interface

    def __str__(self):
        return f'RoutePolicy: {self.device} {self.flow} {self.interface}'

# Zone policy. Used to add a device to a zone. TODO
class ZonePolicy(Policy):
    def __init__(self, device, zone):
        super(ZonePolicy, self).__init__('zone')
        self.device = device
        self.zone = zone
    
    def __str__(self):
        return f'ZonePolicy: {self.device} {self.zone}'

# Disable policy. Used to disable interface on a device. TODO
class DisablePolicy(Policy):
    def __init__(self, device, interface):
        super(DisablePolicy, self).__init__('disable')
        self.device = device
        self.interface = interface

    def __str__(self):
        return f'DisablePolicy: {self.device} {self.interface}'