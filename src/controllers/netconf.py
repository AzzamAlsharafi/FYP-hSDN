import re
import xml.etree.ElementTree as ET
import logging

from ryu.base import app_manager
from ncclient import manager
from ryu.controller.handler import set_ev_cls

from src.events import EventClassicDeviceAPI, EventPolicyDeviceAPI, RequestNetconfDiscovery, ReplyNetconfDiscovery, EventNetconfConfigurations

# Responsible for managing NETCONF communication with NETCONF devices
class NetconfController(app_manager.RyuApp):
    _EVENTS = [EventPolicyDeviceAPI]

    def __init__(self, *args, **kwargs):
        super(NetconfController, self).__init__(*args, **kwargs)

        # Silent ncclient info logs
        logging.getLogger('ncclient').setLevel(logging.WARNING)

        self.read_config()

    # Load NETCONF credentials and IP addresses from config/netconf.txt
    def read_config(self):
        self.devices = []

        line_count = 0
        self.nc_user = ''
        self.nc_password = ''

        with open('config/netconf.txt', 'r') as file:
            for line in file.read().splitlines():
                if line.strip() == '' or line[0] == '#':
                    continue
                
                if line_count == 0:
                    self.nc_user = line.split('=')[1].strip()
                    line_count += 1
                elif line_count == 1:
                    self.nc_password = line.split('=')[1].strip()
                    line_count += 1
                else:
                    split = line.split(' ')
                    address = split[0]
                    host = split[1]
                    if re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', address): # Regex for IPv4 address
                        self.devices.append(Device(address, host, self.nc_user, self.nc_password))
                    else:
                        self.logger.error(f'Invalid device configuration: {line}')
    
    # Runs discovery on all devices
    def discover_all(self):
        all_interfaces = {}
        all_neighbors = {}

        for device in self.devices:
            device.discover()

            if device.manager and device.lldp:
                all_interfaces[device.hostname] = device.interfaces
                all_neighbors[device.hostname] = device.neighbors
            elif device.manager:
                all_interfaces[device.hostname] = ['LLDP disabled']
                all_neighbors[device.hostname] = ['LLDP disabled']

        return {'interfaces': all_interfaces, 'neighbors': all_neighbors}

    @set_ev_cls(RequestNetconfDiscovery)
    def request_enable_lldp(self, req):
        self.reply_to_request(req, ReplyNetconfDiscovery(self.discover_all()))

    # Configure NETCONF device with received configurations
    @set_ev_cls(EventNetconfConfigurations)
    def configure_devices(self, ev):
        configurations = ev.configurations

        for device_name in configurations:
            device = next((d for d in self.devices if d.hostname == device_name), None)

            if device and device.manager:
                for conf in configurations[device_name]:
                    device.configure(conf)
    
    # Run device instruction from API
    @set_ev_cls(EventClassicDeviceAPI)
    def process_device_api(self, ev):
        words = ev.words

        if words[0] == 'new':
            name = words[1]
            ip = words[2]

            self.devices.append(Device(ip, name, self.nc_user, self.nc_password))

            lines = []

            with open('config/netconf.txt', 'a') as file:
                file.write(f'{ip} {name}\n')

        elif words[0] == 'edit':
            separator = words.index('old')
            new_name = ' '.join(words[1:separator])
            old_name = ' '.join(words[separator+1:])

            device = next((d for d in self.devices if d.hostname == old_name), None)

            device.hostname = new_name

            lines = []

            with open('config/netconf.txt', 'r') as file:
                for line in file.readlines():
                    if line.strip() == f'{device.ip_address} {old_name}':
                        lines.append(f'{device.ip_address} {new_name}\n')
                    else:
                        lines.append(line)
            
            with open('config/netconf.txt', 'w') as file:
                file.writelines(lines)

            self.send_event_to_observers(EventPolicyDeviceAPI(old_name, new_name))
            
        elif words[0] == 'delete':
            device = next((d for d in self.devices if d.hostname == words[1]))
            name = device.hostname
            ip = device.ip_address

            self.devices.remove(device)

            lines = []

            with open('config/netconf.txt', 'r') as file:
                for line in file.readlines():
                    if line.strip() != f'{ip} {name}':
                        lines.append(line)
            
            with open('config/netconf.txt', 'w') as file:
                file.writelines(lines)


class Device:
    def __init__(self, ip_address, hostname, user, password):
        self.ip_address = ip_address
        self.hostname = hostname # Hostname of device
        self.user = user # NETCONF username
        self.password = password # NETCONF password
        self.manager = None # NETCONF manager (ncclient)
        self.lldp = False # LLDP enabled or disabled
        self.interfaces = [] # [{'interface_name': 'Gi2', 'hw_addr': 'aa:aa:aa:aa:aa:aa'}]
        self.neighbors = {} # {neighbor_name: interface_name, ...}

        self.configurations = [] # List of applied device configurations
        self.acl_statements = 0 # Number of ACL statements

        self.logger = logging.getLogger(f'NetconfController-{self.ip_address}')
        self.logger.setLevel(logging.INFO)

    # Perform topology discovery on this device
    def discover(self):
        if self.manager is None: # NETCONF connection not established
            self.connect()
        elif not self.lldp: # LLDP disabled
            self.enable_lldp()
        else: # LLDP enabled, discover neighbors
            self.get_neighbors()

    # TODO: handle chaning configurations. Deconfigure old and configure new. (?)
    # Configure device with received configuration
    def configure(self, conf):
        if conf in self.configurations:
            return # Configuration already applied

        split = conf.split(' ')

        if split[0] == 'address':
            interface = split[1]
            (address, prefix) = split[2].split('/')

            if self.configure_address(interface, address, prefix):
                self.configurations.append(conf) # Add successful configuration

        elif split[0] == 'route':
            (address, prefix) = split[1].split('/')
            destination = self.get_network_address(address, prefix)

            interface = split[2]
            (next_hop, next_hop_prefix) = split[3].split('/')

            if self.configure_route(destination, prefix, interface, next_hop, next_hop_prefix):
                self.configurations.append(conf) # Add successful configuration

        elif split[0] == 'block':
            (src_ip, dst_ip, proto, src_port, dst_port) = split[1:]

            if self.configure_block(src_ip, dst_ip, proto, src_port, dst_port, deconf=deconf):
                self.configurations.append(conf)
        
        else:
            self.logger.error(f'Invalid configuration for device {self.hostname}: {conf}')

    # Establish NETCONF connection with device
    def connect(self):
        try:
            self.manager = manager.connect(
                host=self.ip_address,
                port=830,
                username=self.user,
                password=self.password,
                hostkey_verify=False,
                timeout=10
            )
            self.logger.debug(f'Established NETCONF connection with {self.ip_address} ({self.hostname})')
            self.enable_lldp()
        except Exception as e:
            # Use debug instead of error, as it's expected that some devices will be unreachable (e.g. shutdown)
            self.logger.debug(f'Failed to establish NETCONF connection with {self.ip_address} ({self.hostname}): {str(e)}')
    
    # Enable LLDP on device
    def enable_lldp(self):
        filter = '''
                    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <lldp xmlns="http://openconfig.net/yang/lldp">
                            <config>
                                <enabled></enabled>
                            </config>
                        </lldp>
                    </filter>
                '''

        config='''
                    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <lldp xmlns="http://openconfig.net/yang/lldp">
                            <config>
                                <enabled>true</enabled>
                            </config>
                        </lldp>
                    </config>
                '''        
        try:
            lldp_reply = ET.fromstring(self.manager.get(filter).data_xml)

            if lldp_reply.find('.//{http://openconfig.net/yang/lldp}enabled').text != 'true':
                self.manager.edit_config(config=config)
                self.manager.commit()

            self.lldp = True
            self.logger.debug(f'Enabled LLDP on {self.ip_address} ({self.hostname})')
            self.get_neighbors()
        except Exception as e:
            # Assume any exception means device got disconnected
            self.manager = None
            self.logger.debug(f'Failed to enable LLDP on {self.ip_address} ({self.hostname}): {str(e)}')

    # Get LLDP neighbors, and check for disabled (newly added) interfaces
    def get_neighbors(self):
        
        # Note: Used two filters instead of one because a single filter doesn't get a respond 
        #       from a virtual device in a different server than the server running this system.
        #       Not sure what's the cause, but a possible theory is that the packet size is too big,
        #       as the different servers are connected using VXLAN tunnels, which adds extra overhead to the packets.
        
        lldp_filter = '''
                    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <lldp xmlns="http://openconfig.net/yang/lldp">
                            <interfaces>
                                <interface>
                                    <name></name>
                                    <state>
                                        <enabled></enabled>
                                    </state>
                                    <neighbors>
                                        <neighbor>
                                            <state>
                                                <system-name></system-name>
                                            </state>
                                        </neighbor>
                                    </neighbors>
                                </interface>
                            </interfaces>
                        </lldp>
                    </filter>
                    '''
        
        interfaces_filter = '''
                        <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                            <interfaces xmlns="http://openconfig.net/yang/interfaces">
                                <interface>
                                    <name></name>
                                    <state>
                                        <enabled></enabled>
                                    </state>
                                    <ethernet xmlns="http://openconfig.net/yang/interfaces/ethernet">
                                        <state>
                                            <mac-address></mac-address>
                                        </state>
                                    </ethernet>
                                </interface>
                            </interfaces>
                        </filter>
                        '''
        
        acl_filter = '''
                    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <acl xmlns="http://openconfig.net/yang/acl">
                            <interfaces>
                            </interfaces>
                        </acl>
                    </filter>
                    '''

        try:
            lldp_reply = ET.fromstring(self.manager.get(lldp_filter).data_xml)
            interfaces_reply = ET.fromstring(self.manager.get(interfaces_filter).data_xml)
            acl_reply = ET.fromstring(self.manager.get(acl_filter).data_xml)

            disabled_interfaces = []

            # Clears neighbors and interfaces
            self.neighbors = {}
            self.interfaces = []

            for interface in lldp_reply.findall('.//{http://openconfig.net/yang/lldp}interface'):
                interface_name = interface.find('.//{http://openconfig.net/yang/lldp}name').text
                
                # Same interface but in openconfig-interfaces tree, instead of openconfig-lldp
                non_lldp_interface = interfaces_reply.find('.//{http://openconfig.net/yang/interfaces}interface[{http://openconfig.net/yang/interfaces}name="' + interface_name +'"]')

                mac_address = non_lldp_interface.find('.//{http://openconfig.net/yang/interfaces/ethernet}mac-address').text

                # Make sure ACL is applied to interface when there is ACL statements
                if self.acl_statements > 0:
                    if acl_reply.find('.//{http://openconfig.net/yang/acl}interface[{http://openconfig.net/yang/acl}id="' + interface_name + '"]') is None:
                        self.apply_acl_interface(interface_name)

                # Add interface to interfaces
                self.interfaces.append({'interface_name': interface_name, 'hw_addr': mac_address})

                # Check if interface is disabled or LLDP is disabled
                if not (non_lldp_interface.find('.//{http://openconfig.net/yang/interfaces}enabled').text == 'true'
                    and interface.find('.//{http://openconfig.net/yang/lldp}enabled').text == 'true'):
                    disabled_interfaces.append(interface_name)
                    continue
                
                neighbor_count = 0
                for neighbor in interface.findall('.//{http://openconfig.net/yang/lldp}neighbor'):
                    neighbor_name = neighbor.find('.//{http://openconfig.net/yang/lldp}system-name').text

                    neighbor_count += 1

                    # Add neighbor to neighbors
                    self.neighbors[neighbor_name] = interface_name

                self.logger.debug(f'Found {neighbor_count} neighbors on {interface_name} {self.ip_address} ({self.hostname})')
            if len(disabled_interfaces) > 0:
                self.logger.debug(f'Found {len(disabled_interfaces)} disabled interfaces on {self.ip_address} ({self.hostname})')
                self.activate_interfaces(disabled_interfaces)
        except Exception as e:
            # Assume any exception means device is disconnected
            self.manager = None
            self.logger.debug(f'Failed to get neighbors from {self.ip_address} ({self.hostname}): {str(e)}')

    # Activate interfaces and enable LLDP
    def activate_interfaces(self, disabled_interfaces):        
        for interface in disabled_interfaces:
            config = f'''
                        <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                            <lldp xmlns="http://openconfig.net/yang/lldp">
                                <interfaces>
                                    <interface>
                                        <name>{interface}</name>
                                        <config>
                                            <enabled>true</enabled>
                                        </config>
                                    </interface>
                                </interfaces>
                            </lldp>
                            <interfaces xmlns="http://openconfig.net/yang/interfaces">
                                <interface>
                                    <name>{interface}</name>
                                    <config>
                                        <enabled>true</enabled>
                                    </config>
                                </interface>
                            </interfaces>
                        </config>
                    '''
            
            filter = f'''
                        <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                            <interfaces xmlns="http://openconfig.net/yang/interfaces">
                                <interface>
                                    <name>{interface}</name>
                                    <ethernet xmlns="http://openconfig.net/yang/interfaces/ethernet">
                                        <state>
                                            <mac-address></mac-address>
                                        </state>
                                    </ethernet>
                                </interface>
                            </interfaces>
                        </filter>        
                    '''

            try:
                self.manager.edit_config(config=config)

                interfaces_reply = ET.fromstring(self.manager.get(filter).data_xml)

                mac_address = interfaces_reply.find('.//{http://openconfig.net/yang/interfaces/ethernet}mac-address').text

                self.interfaces.append({'interface_name': interface, 'hw_addr': mac_address})

                self.logger.debug(f'Activated interface {interface} on {self.ip_address} ({self.hostname})')
            except Exception as e:
                self.logger.error(f'Failed to activate interface {interface} on {self.ip_address} ({self.hostname}): {str(e)}')

        self.manager.commit()
    
    # Configure address on interface
    def configure_address(self, interface, address, prefix):
        config = f'''
                    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <interfaces xmlns="http://openconfig.net/yang/interfaces">
                            <interface>
                                <name>{interface}</name>
                                <subinterfaces>
                                    <subinterface>
                                        <index>0</index>
                                        <ipv4 xmlns="http://openconfig.net/yang/interfaces/ip">
                                            <addresses>
                                                <address>
                                                    <ip>{address}</ip>
                                                    <config>
                                                        <ip>{address}</ip>
                                                        <prefix-length>{prefix}</prefix-length>
                                                    </config>
                                                </address>
                                            </addresses>
                                        </ipv4>
                                    </subinterface>
                                </subinterfaces>
                            </interface>
                        </interfaces>
                    </config>
                '''
        
        try:
            self.manager.edit_config(config=config)
            self.manager.commit()

            self.logger.debug(f'Configured address {address}/{prefix} on {interface} on {self.ip_address} ({self.hostname})')

            return True
        except Exception as e:
            self.logger.error(f'Failed to configure address {address}/{prefix} on {interface} on {self.ip_address} ({self.hostname}): {str(e)}')

            return False
    
    # Configure route on device
    def configure_route(self, destination, prefix, interface, next_hop, next_hop_prefix):
        config = f'''
                    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                    <network-instances xmlns="http://openconfig.net/yang/network-instance">
                        <network-instance>
                            <name>default</name>
                            <protocols>
                                <protocol>
                                    <identifier xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">
                                        oc-pol-types:STATIC</identifier>
                                    <name>DEFAULT</name>
                                    <static-routes>
                                        <static>
                                            <prefix>{destination}/{prefix}</prefix>
                                            <config>
                                                <prefix>{destination}/{prefix}</prefix>
                                            </config>
                                            <next-hops>
                                                <next-hop>
                                                    <index>{interface}_{next_hop}</index>
                                                    <config>
                                                        <index>{interface}_{next_hop}</index>
                                                        <next-hop>{next_hop}</next-hop>
                                                        <metric>1</metric>
                                                    </config>
                                                    <interface-ref>
                                                        <config>
                                                            <interface>{interface}</interface>
                                                        </config>
                                                    </interface-ref>
                                                </next-hop>
                                            </next-hops>
                                        </static>
                                    </static-routes>
                                </protocol>
                            </protocols>
                        </network-instance>
                    </network-instances>
                </config>
            '''
        
        try:
            self.manager.edit_config(config=config)
            self.manager.commit()

            self.logger.debug(f'Configured route {destination}/{prefix} via {next_hop} on {interface} on {self.ip_address} ({self.hostname})')

            return True
        except Exception as e:
            self.logger.error(f'Failed to configure route {destination}/{prefix} via {next_hop} on {interface} on {self.ip_address} ({self.hostname}): {str(e)}')

            return False
    
    # Configure block on device
    def configure_block(self, src_ip, dst_ip, proto, src_port, dst_port, deconf=False):
        acl_name = f'ACL_{self.hostname}'
        sequence_id = (self.acl_statements * 10) + 10

        src_ip = src_ip if src_ip != '*' else '0.0.0.0/0'
        dst_ip = dst_ip if dst_ip != '*' else '0.0.0.0/0'
        src_port = src_port if src_port != '*' else 'ANY'
        dst_port = dst_port if dst_port != '*' else 'ANY'

        proto_line = f'<protocol>{proto}</protocol>' if proto != '*' else ''

        config = f'''
                    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <acl xmlns="http://openconfig.net/yang/acl">
                            <acl-sets>
                                <acl-set>
                                    <name>{acl_name}</name>
                                    <type>ACL_IPV4</type>
                                    <config>
                                        <name>{acl_name}</name>
                                        <type>ACL_IPV4</type>
                                    </config>
                                    <acl-entries>
                                        <acl-entry>
                                            <sequence-id>{sequence_id}</sequence-id>
                                            <config>
                                                <sequence-id>{sequence_id}</sequence-id>
                                            </config>
                                            <ipv4>
                                                <config>
                                                    <source-address>{src_ip}</source-address>
                                                    <destination-address>{dst_ip}</destination-address>
                                                    {proto_line}
                                                </config>
                                            </ipv4>
                                            <transport>
                                                <config>
                                                    <source-port>{src_port}</source-port>
                                                    <destination-port>{dst_port}</destination-port>
                                                </config>
                                            </transport>
                                            <actions>
                                                <config>
                                                    <forwarding-action>DROP</forwarding-action>
                                                    <log-action>LOG_NONE</log-action>
                                                </config>
                                            </actions>
                                        </acl-entry>
                                    </acl-entries>
                                </acl-set>
                            </acl-sets>
                        </acl>
                    </config>
        '''

        try:
            self.manager.edit_config(config=config)
            self.manager.commit()
            self.acl_statements += 1

            self.logger.debug(f'Configured block {src_ip} {dst_ip} {proto} {src_port} {dst_port} on {self.ip_address} ({self.hostname})')

            return True
        except Exception as e:
            self.logger.error(f'Failed to configure block {src_ip} {dst_ip} {proto} {src_port} {dst_port} on {self.ip_address} ({self.hostname}): {str(e)}')

            return False
    
    def apply_acl_interface(self, interface):
        config = f'''
                    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <acl xmlns="http://openconfig.net/yang/acl">
                            <interfaces>
                                <interface>
                                    <id>{interface}</id>
                                    <config>
                                        <id>{interface}</id>
                                    </config>
                                    <interface-ref>
                                        <config>
                                            <interface>{interface}</interface>
                                            <subinterface>0</subinterface>
                                        </config>
                                    </interface-ref>
                                    <egress-acl-sets>
                                        <egress-acl-set>
                                            <set-name>ACL_{self.hostname}</set-name>
                                            <type>ACL_IPV4</type>
                                            <config>
                                                <set-name>ACL_{self.hostname}</set-name>
                                                <type>ACL_IPV4</type>
                                            </config>
                                        </egress-acl-set>
                                    </egress-acl-sets>
                                </interface>
                            </interfaces>
                        </acl>
                    </config>
        '''

        try:
            self.manager.edit_config(config=config)
            self.manager.commit()

            self.logger.debug(f'Configured ACL on interface {interface} on {self.ip_address} ({self.hostname})')
        except Exception as e:
            self.logger.error(f'Failed to configure ACL on interface  {interface} on {self.ip_address} ({self.hostname}): {str(e)}')    

    # TODO: Move to a helper class
    # Get network address from host address and prefix
    def get_network_address(self, address, prefix):
        address = address.split('.')
        prefix = int(prefix)

        # Convert address to binary
        address = ''.join(format(int(octet), '08b') for octet in address)

        # Get network address
        network_address = address[:prefix] + '0' * (32 - prefix)

        # Convert network address to decimal
        network_address = [str(int(network_address[i:i+8], 2)) for i in range(0, 32, 8)]

        return '.'.join(network_address)