import re
import xml.etree.ElementTree as ET
import logging

from ryu.base import app_manager
from ncclient import manager

from src.events import EventControllerReady

# Responsible for managing NETCONF communication with NETCONF devices
class NetconfController(app_manager.RyuApp):
    _EVENTS = [EventControllerReady]

    def __init__(self, *args, **kwargs):
        super(NetconfController, self).__init__(*args, **kwargs)

        # Silent ncclient info logs
        logging.getLogger('ncclient').setLevel(logging.WARNING)
    
    def start(self):
        super(NetconfController, self).start()

        self.devices = self.connect_devices()
        self.send_event_to_observers(EventControllerReady(str(self.devices.keys())))

    # Read IP addresses from the config file, and returns list of valid IP addresses
    def read_config(self):
        addresses = []

        line_count = 0

        with open('config/netconf.txt', 'r') as file:
            for line in file.read().splitlines():
                if line.strip() == '' or line[0] == '#':
                    continue
                
                if line_count == 0:
                    self.user = line.split('=')[1].strip()
                    line_count += 1
                elif line_count == 1:
                    self.password = line.split('=')[1].strip()
                    line_count += 1
                elif re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', line):
                    addresses.append(line)
                else:
                    self.logger.error(f'Invalid IP address: {line}')
        return addresses
    
    # Establish NETCONF connections with devices, and returns a dictionary of NETCONF managers
    def connect_devices(self):
        devices = {}
        for ip_address in self.read_config():
            try:
                device_manager = manager.connect(
                    host=ip_address,
                    port=830,
                    username=self.user,
                    password=self.password,
                    hostkey_verify=False
                )
                devices[ip_address] = device_manager
            except Exception as e:
                self.logger.error(f'Failed to establish NETCONF connection with {ip_address}: {str(e)}')

        return devices

    # Enable global LLDP on device
    def enable_global_lldp(self, device, ip_address):
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
            device.edit_config(config=config)
        except Exception as e:
            self.logger.error(f'Failed to enable global LLDP on {ip_address}: {str(e)}')
    
    # Returns a list of interface names
    def get_interfaces(self, device, ip_address):
        # Use openconfig-lldp instead of openconfig-interfaces because the interest is only in LLDP-supported interfaces
        interface_filter = '''
                        <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                            <lldp xmlns="http://openconfig.net/yang/lldp">
                                <interfaces>
                                    <interface>
                                        <name></name>
                                        <state>
                                            <enabled></enabled>
                                        </state>
                                    </interface>
                                </interfaces>
                            </lldp>
                        </filter>
                        '''
        try:
            reply = ET.fromstring(device.get(interface_filter).data_xml)

            return [interface.find('.//{http://openconfig.net/yang/lldp}name').text for interface in reply.findall('.//{http://openconfig.net/yang/lldp}interface')]
        except Exception as e:
            self.logger.error(f'Failed to get interfaces from {ip_address}: {str(e)}')
    
    # Activate interfaces and enable LLDP on them
    def enable_interfaces_lldp(self, device, ip_address):
        interfaces = self.get_interfaces(device, ip_address)
        
        for interface in interfaces:
            config = f'''
                        <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                            <interfaces xmlns="http://openconfig.net/yang/interfaces">
                                <interface>
                                    <name>{interface}</name>
                                    <config>
                                        <enabled>true</enabled>
                                    </config>
                                </interface>
                            </interfaces>
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
                        </config>
                    '''
            try:
                device.edit_config(config=config)
            except Exception as e:
                self.logger.error(f'Failed to enable interface {interface} on {ip_address}: {str(e)}')

    # Return a list of interface-neighbor pairs
    def get_neighbors(self, ip_address):
        device = self.devices[ip_address]

        neighbors_filter = '''
                    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <lldp xmlns="http://openconfig.net/yang/lldp">
                            <interfaces>
                                <interface>
                                    <name></name>
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
        try:
            reply = ET.fromstring(device.get(neighbors_filter).data_xml)

            neighbors = []

            for interface in reply.findall('.//{http://openconfig.net/yang/lldp}interface'):
                interface_name = interface.find('.//{http://openconfig.net/yang/lldp}name').text
                
                for neighbor in interface.findall('.//{http://openconfig.net/yang/lldp}neighbor'):
                    neighbor_name = neighbor.find('.//{http://openconfig.net/yang/lldp}system-name').text

                    neighbors.append((neighbor_name, interface_name))

            return neighbors

        except Exception as e:
            self.logger.error(f'Failed to get neighbors from {ip_address}: {str(e)}')
        
    # Enable LLDP on device, globally and on interfaces
    def enable_lldp(self, ip_address):
        device = self.devices[ip_address]

        try:
            self.enable_global_lldp(device, ip_address)
            self.enable_interfaces_lldp(device, ip_address)
            device.commit()

        except Exception as e:
            self.logger.error(f'Failed to enable LLDP on {ip_address}: {str(e)}')
