import re
import xml.etree.ElementTree as ET
import logging

from ryu.base import app_manager
from ncclient import manager
from ryu.controller.handler import set_ev_cls

from src.events import RequestNetconfDiscovery, ReplyNetconfDiscovery

# Responsible for managing NETCONF communication with NETCONF devices
class NetconfController(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(NetconfController, self).__init__(*args, **kwargs)

        # Silent ncclient info logs
        logging.getLogger('ncclient').setLevel(logging.WARNING)

        self.read_config()

    # Load NETCONF credentials and IP addresses from config/netconf.txt
    def read_config(self):
        self.devices = []

        line_count = 0
        user = ''
        password = ''

        with open('config/netconf.txt', 'r') as file:
            for line in file.read().splitlines():
                if line.strip() == '' or line[0] == '#':
                    continue
                
                if line_count == 0:
                    user = line.split('=')[1].strip()
                    line_count += 1
                elif line_count == 1:
                    password = line.split('=')[1].strip()
                    line_count += 1
                else:
                    split = line.split(' ')
                    address = split[0]
                    host = split[1]
                    if re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', address): # Regex for IPv4 address
                        self.devices.append(Device(address, host, user, password))
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
                all_interfaces[device.hostname] = 'LLDP disabled'
                all_neighbors[device.hostname] = 'LLDP disabled'
            else:
                all_interfaces[device.hostname] = 'Disconnected'
                all_neighbors[device.hostname] = 'Disconnected'

        return {'interfaces': all_interfaces, 'neighbors': all_neighbors}

    @set_ev_cls(RequestNetconfDiscovery)
    def request_enable_lldp(self, req):
        self.reply_to_request(req, ReplyNetconfDiscovery(self.discover_all()))

# TODO: Better support and handling for dynamic topology changes (device get enabled, disabled, etc...)
#       Way for detecting device shutdown
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
            self.logger.error(f'Failed to establish NETCONF connection with {self.ip_address} ({self.hostname}): {str(e)}')
    
    # Enable LLDP on device
    def enable_lldp(self):
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
            self.manager.edit_config(config=config)
            self.manager.commit()
            self.lldp = True
            self.logger.debug(f'Enabled LLDP on {self.ip_address} ({self.hostname})')
            self.get_neighbors()
        except Exception as e:
            self.logger.error(f'Failed to enable LLDP on {self.ip_address} ({self.hostname}): {str(e)}')

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
        try:
            lldp_reply = ET.fromstring(self.manager.get(lldp_filter).data_xml)
            interfaces_reply = ET.fromstring(self.manager.get(interfaces_filter).data_xml)

            disabled_interfaces = []

            # Clears neighbors and interfaces
            self.neighbors = {}
            self.interfaces = []

            for interface in lldp_reply.findall('.//{http://openconfig.net/yang/lldp}interface'):
                interface_name = interface.find('.//{http://openconfig.net/yang/lldp}name').text
                
                # Same interface but in openconfig-interfaces tree, instead of openconfig-lldp
                non_lldp_interface = interfaces_reply.find('.//{http://openconfig.net/yang/interfaces}interface[{http://openconfig.net/yang/interfaces}name="' + interface_name +'"]')

                mac_address = non_lldp_interface.find('.//{http://openconfig.net/yang/interfaces/ethernet}mac-address').text

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
            self.logger.error(f'Failed to get neighbors from {self.ip_address}  ({self.hostname}): {str(e)}')

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