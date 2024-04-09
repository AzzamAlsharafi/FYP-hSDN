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
                device.configure_list(configurations[device_name])
    
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
        self.seq_ids = {} # Map block configurations to sequence IDs
        self.route_map_statements = 0 # Number of route-map statements
        self.route_map_ids = {} # Map route-map configurations to IDs
        self.disabled = [] # List of disabled interfaces

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

    # Configure list of configurations. Deconfigure old and configure new.
    def configure_list(self, confs):
        self.logger.debug(f'Configuring device {self.hostname} with [NEW] {confs}. [OLD] {self.configurations}.')

        for conf in self.configurations:
            if conf not in confs:
                self.configure(conf, deconf=True)

        for conf in confs:
            self.configure(conf)

    # Configure/deconfigure device with received configuration
    def configure(self, conf, deconf=False):
        if not deconf and conf in self.configurations:
            return # Configuration already applied

        split = conf.split(' ')

        if split[0] == 'address':
            interface = split[1]
            (address, prefix) = split[2].split('/')

            if self.configure_address(interface, address, prefix, deconf=deconf):
                if deconf:
                    self.configurations.remove(conf)
                else:
                    self.configurations.append(conf)

        elif split[0] == 'route':
            (address, prefix) = split[1].split('/')
            destination = self.get_network_address(address, prefix)

            interface = split[2]
            next_hop = split[3]

            if self.configure_route(destination, prefix, interface, next_hop, deconf=deconf):
                if deconf:
                    self.configurations.remove(conf)
                else:
                    self.configurations.append(conf)

        elif split[0] == 'block':
            (src_ip, dst_ip, proto, src_port, dst_port) = split[1:]

            if self.configure_block(src_ip, dst_ip, proto, src_port, dst_port, deconf=deconf):
                if deconf:
                    self.configurations.remove(conf)
                else:
                    self.configurations.append(conf)
        
        elif split[0] == 'route-f':
            (src_ip, dst_ip, proto, src_port, dst_port, port) = split[1:]

            if self.configure_route_map(src_ip, dst_ip, proto, src_port, dst_port, port, deconf=deconf):
                if deconf:
                    self.configurations.remove(conf)
                else:
                    self.configurations.append(conf)
        
        elif split[0] == 'disable':
            port = split[1]

            if self.configure_disable(port, deconf=deconf):
                if deconf:
                    self.configurations.remove(conf)
                else:
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
            self.load_configurations()
            self.enable_lldp()
        except Exception as e:
            # Use debug instead of error, as it's expected that some devices will be unreachable (e.g. shutdown)
            self.logger.debug(f'Failed to establish NETCONF connection with {self.ip_address} ({self.hostname}): {str(e)}')
    
    # Load device configurations
    def load_configurations(self):
        self.deconfigure_routes()
        self.deconfigure_acls()
        self.deconfigre_route_map()
        self.load_configured_addresses()

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

                # Make sure ACL is applied/not applied to interface when there is (no) ACL statements
                if self.acl_statements > 0:
                    if acl_reply.find('.//{http://openconfig.net/yang/acl}interface[{http://openconfig.net/yang/acl}id="' + interface_name + '"]') is None:
                        self.apply_acl_interface(interface_name)
                else:
                    if acl_reply.find('.//{http://openconfig.net/yang/acl}interface[{http://openconfig.net/yang/acl}id="' + interface_name + '"]') is not None:
                        self.apply_acl_interface(interface_name, deconf=True)

                # Add interface to interfaces
                self.interfaces.append({'interface_name': interface_name, 'hw_addr': mac_address})

                # Check if interface is disabled or LLDP is disabled (Make sure interface is not disabled by policy first)
                if interface_name in self.disabled:
                    continue

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
    def configure_address(self, interface, address, prefix, deconf=False):
        deconf_str = ' operation="delete"' if deconf else ''

        config = f'''
                    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <interfaces xmlns="http://openconfig.net/yang/interfaces">
                            <interface>
                                <name>{interface}</name>
                                <subinterfaces>
                                    <subinterface>
                                        <index>0</index>
                                        <ipv4 xmlns="http://openconfig.net/yang/interfaces/ip">
                                            <addresses{deconf_str}>
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

            self.logger.debug(f'Configured ({not deconf}) address {address}/{prefix} on {interface} on {self.ip_address} ({self.hostname})')

            return True
        except Exception as e:
            self.logger.error(f'Failed to configure ({not deconf}) address {address}/{prefix} on {interface} on {self.ip_address} ({self.hostname}): {str(e)}.\n{config}')

            return False
    
    # Load already-configured address configurations
    def load_configured_addresses(self):
        filter = f'''
                    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <interfaces xmlns="http://openconfig.net/yang/interfaces">
                            <interface>
                                <name></name>
                                <subinterfaces>
                                    <subinterface>
                                        <index>0</index>
                                        <ipv4 xmlns="http://openconfig.net/yang/interfaces/ip">
                                            <addresses>
                                                <address>
                                                    <ip></ip>
                                                    <config>
                                                        <ip></ip>
                                                        <prefix-length></prefix-length>
                                                    </config>
                                                </address>
                                            </addresses>
                                        </ipv4>
                                    </subinterface>
                                </subinterfaces>
                            </interface>
                        </interfaces>
                    </filter>
                '''
        
        try:
            interface_reply = ET.fromstring(self.manager.get(filter).data_xml)

            for (i, interface) in enumerate(interface_reply.findall('.//{http://openconfig.net/yang/interfaces}interface')):
                interface_name = interface.find('.//{http://openconfig.net/yang/interfaces}name').text
                address = interface.find('.//{http://openconfig.net/yang/interfaces/ip}ip')

                # Skip management interface
                if i == 0:
                    continue

                if address is not None:
                    address = address.text
                    prefix = interface.find('.//{http://openconfig.net/yang/interfaces/ip}prefix-length').text

                    self.configurations.append(f'address {interface_name} {address}/{prefix}')
            
            self.logger.debug(f'Loaded configured addresses on {self.ip_address} ({self.hostname})')

        except Exception as e:
            self.logger.error(f'Failed to load configured addresses on {self.ip_address} ({self.hostname}): {str(e)}')
            return

    # Configure route on device
    def configure_route(self, destination, prefix, interface, next_hop, deconf=False):
        deconf_str = ' operation="delete"' if deconf else ''
        conf_str = f'''
                                            <next-hops>
                                                <next-hop>
                                                    <index>{interface}_{next_hop}_{destination}_{prefix}</index>
                                                    <config>
                                                        <index>{interface}_{next_hop}_{destination}_{prefix}</index>
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
''' if not deconf else ''

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
                                        <static{deconf_str}>
                                            <prefix>{destination}/{prefix}</prefix>
                                            <config>
                                                <prefix>{destination}/{prefix}</prefix>
                                            </config>{conf_str}
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

            self.logger.debug(f'Configured ({not deconf}) route {destination}/{prefix} via {next_hop} on {interface} on {self.ip_address} ({self.hostname})')

            return True
        except Exception as e:
            self.logger.error(f'Failed to configure ({not deconf}) route {destination}/{prefix} via {next_hop} on {interface} on {self.ip_address} ({self.hostname}): {str(e)}.\n{config}')

            return False
    
    # Deconfigure already-configured route configurations
    def deconfigure_routes(self):
        filter = f'''
                    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <network-instances xmlns="http://openconfig.net/yang/network-instance">
                            <network-instance>
                                <name>default</name>
                                <protocols>
                                    <protocol>
                                        <identifier xmlns:oc-pol-types="http://openconfig.net/yang/policy-types">
                                            oc-pol-types:STATIC</identifier>
                                        <name>DEFAULT</name>
                                        <static-routes>
                                        </static-routes>
                                    </protocol>
                                </protocols>
                            </network-instance>
                        </network-instances>
                    </filter>
        '''

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
                                        <static-routes operation="delete">
                                        </static-routes>
                                    </protocol>
                                </protocols>
                            </network-instance>
                        </network-instances>
                    </config>
                '''
        
        try:
            route_reply = ET.fromstring(self.manager.get(filter).data_xml)

            if route_reply.find('.//{http://openconfig.net/yang/network-instance}static-route') is not None:
                self.manager.edit_config(config=config)
                self.manager.commit()
            
            self.logger.debug(f'Deconfigured routes on {self.ip_address} ({self.hostname})')

        except Exception as e:
            self.logger.error(f'Failed to Deconfigured routes on {self.ip_address} ({self.hostname}): {str(e)}')
            return
    
    # Configure ACL statement on device
    def configure_acl(self, acl_name, seq, rules, permit=False, deconf=False):
        deconf_str = ' operation="delete"' if deconf else ''

        (src_ip, dst_ip, proto, src_port, dst_port) = rules

        src_ip = src_ip if src_ip != '*' else '0.0.0.0/0'
        dst_ip = dst_ip if dst_ip != '*' else '0.0.0.0/0'
        src_port = src_port if src_port != '*' else 'ANY'
        dst_port = dst_port if dst_port != '*' else 'ANY'
        proto = proto if proto != '*' else 'IP'

        transport_block = f'''
                                            <transport>
                                                <config>
                                                    <source-port>{src_port}</source-port>
                                                    <destination-port>{dst_port}</destination-port>
                                                </config>
                                            </transport>
                                            ''' if proto == '6' or proto == '17' else ''
        
        forwarding_action = 'ACCEPT' if permit else 'DROP'

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
                                        <acl-entry{deconf_str}>
                                            <sequence-id>{seq}</sequence-id>
                                            <config>
                                                <sequence-id>{seq}</sequence-id>
                                            </config>
                                            <ipv4>
                                                <config>
                                                    <source-address>{src_ip}</source-address>
                                                    <destination-address>{dst_ip}</destination-address>
                                                    <protocol>{proto}</protocol>
                                                </config>
                                            </ipv4>{transport_block}
                                            <actions>
                                                <config>
                                                    <forwarding-action>{forwarding_action}</forwarding-action>
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
            
            self.logger.debug(f'Configured ({not deconf}) ACL {acl_name} statement {seq}: {src_ip} {dst_ip} {proto} {src_port} {dst_port} on {self.ip_address} ({self.hostname})')

            return True
        except Exception as e:
            self.logger.error(f'Failed to configure ({not deconf}) ACL {acl_name} statement {seq}: {src_ip} {dst_ip} {proto} {src_port} {dst_port} on {self.ip_address} ({self.hostname}): {str(e)}.\n{config}')

            return False

    # Configure block on device
    def configure_block(self, src_ip, dst_ip, proto, src_port, dst_port, deconf=False):
        key = f'{src_ip}_{dst_ip}_{proto}_{src_port}_{dst_port}'

        acl_name = f'ACL_{self.hostname}'
        sequence_id = (self.acl_statements * 10) + 10 if not deconf else self.seq_ids[key]

        if self.configure_acl(acl_name, sequence_id, (src_ip, dst_ip, proto, src_port, dst_port), deconf=deconf):
            self.acl_statements += (1 if not deconf else -1)
            self.seq_ids[key] = sequence_id

            self.logger.debug(f'Configured ({not deconf}) block on {self.ip_address} ({self.hostname})')

            return True
        else:
            self.logger.error(f'Failed to configure ({not deconf}) block on {self.ip_address} ({self.hostname})')

            return False

    # Deconfigure already-configured ACLs
    def deconfigure_acls(self):
        filter = f'''
                    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <acl xmlns="http://openconfig.net/yang/acl">
                            <acl-sets>
                                <acl-set>
                                    <name></name>
                                    <type>ACL_IPV4</type>
                                </acl-set>
                            </acl-sets>
                        </acl>
                    </filter>
        '''

        try:
            acl_reply = ET.fromstring(self.manager.get(filter).data_xml)

            for acl in acl_reply.findall('.//{http://openconfig.net/yang/acl}acl-set'):
                acl_name = acl.find('.//{http://openconfig.net/yang/acl}name').text

                config = f'''
                            <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                                <acl xmlns="http://openconfig.net/yang/acl">
                                    <acl-sets>
                                        <acl-set operation="delete">
                                            <name>{acl_name}</name>
                                            <type>ACL_IPV4</type>
                                        </acl-set>
                                    </acl-sets>
                                </acl>
                            </config>
                '''

                self.manager.edit_config(config=config)
                
                self.logger.debug(f'Deconfigured ACL ({acl_name}) on {self.ip_address} ({self.hostname})')

        except Exception as e:
            self.logger.error(f'Failed to deconfigured ACL ({acl_name}) on {self.ip_address} ({self.hostname}): {str(e)}.\n{config}')
            return
    
    def apply_acl_interface(self, interface, deconf=False):
        deconf_str = ' operation="delete"' if deconf else ''

        config = f'''
                    <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                        <acl xmlns="http://openconfig.net/yang/acl">
                            <interfaces{deconf_str}>
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

            self.logger.debug(f'Configured ACL ({not deconf}) on interface {interface} on {self.ip_address} ({self.hostname})')
        except Exception as e:
            self.logger.error(f'Failed to configure ACL ({not deconf}) on interface  {interface} on {self.ip_address} ({self.hostname}): {str(e)}.\n{config}')    

    # Configure route-map on device
    def configure_route_map(self, src_ip, dst_ip, proto, src_port, dst_port, port, deconf=False):
        route_map_name = f'MAP_{self.hostname}'
        
        key = f'{src_ip}_{dst_ip}_{proto}_{src_port}_{dst_port}_{port}'
        id = (self.route_map_statements * 10) + 10 if not deconf else self.route_map_ids[key]
        acl_name = f'ACL_route-f_{self.hostname}_{id}'

        if self.configure_acl(acl_name, 10, (src_ip, dst_ip, proto, src_port, dst_port), permit=True, deconf=deconf):
            next_hop = self.get_next_hop_from_port(port)

            if next_hop is not None:
                config = f'''
                        <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                            <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                                <route-map>
                                    <name>{route_map_name}</name>
                                    <route-map-without-order-seq xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-route-map">
                                        <seq_no>{id}</seq_no>
                                        <operation>permit</operation>
                                        <set>
                                            <ip>
                                                <next-hop>
                                                    <address>{next_hop}</address>
                                                </next-hop>
                                            </ip>
                                        </set>
                                        <match>
                                            <ip>
                                                <address>
                                                    <access-list>{acl_name}</access-list>
                                                </address>
                                            </ip>
                                        </match>
                                    </route-map-without-order-seq>
                                </route-map>
                            </native>
                        </config>
                        '''
                
                try:
                    self.manager.edit_config(config=config)
                    self.manager.commit()

                    self.route_map_statements += (1 if not deconf else -1)
                    self.route_map_ids[key] = id

                    self.logger.debug(f'Configured ({not deconf}) route-map to port {port} on {self.ip_address} ({self.hostname})')

                    return True
                except Exception as e:
                    self.logger.error(f'Failed to configure ({not deconf}) route-map to port {port} on {self.ip_address} ({self.hostname}): {str(e)}.\n{config}')

                    return False
            else:
                self.logger.error(f'Failed to configure ({not deconf}) route-map to port {port} on {self.ip_address} ({self.hostname}): No next hop found')
                return False
        else:
            self.logger.error(f'Failed to configure ({not deconf}) ACL for route-map to port {port} on {self.ip_address} ({self.hostname})')
            return False
        

    # Deconfigure already-configured route-map configurations
    def deconfigre_route_map(self):
        filter = f'''
                    <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                            <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                                <route-map>
                                    <name></name>
                                </route-map>
                            </native>
                    </filter>
        '''

        try:
            route_map_reply = ET.fromstring(self.manager.get(filter).data_xml)

            for route_map in route_map_reply.findall('.//{http://cisco.com/ns/yang/Cisco-IOS-XE-native}route-map'):
                route_map_name = route_map.find('.//{http://cisco.com/ns/yang/Cisco-IOS-XE-native}name').text

                config = f'''
                            <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                                <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
                                    <route-map operation="delete">
                                        <name>{route_map_name}</name>
                                    </route-map>
                                </native>
                            </config>
                '''

                self.manager.edit_config(config=config)
            
            self.logger.debug(f'Deconfigured route-map on {self.ip_address} ({self.hostname})')

        except Exception as e:
            self.logger.error(f'Failed to deconfigure route-map on {self.ip_address} ({self.hostname}): {str(e)}.\n{config}')
            return
    
    # Configure disable on device
    def configure_disable(self, port, deconf=False):
        filter = f'''
                        <filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                            <interfaces xmlns="http://openconfig.net/yang/interfaces">
                                <interface>
                                    <name>{port}</name>
                                    <state>
                                        <enabled></enabled>
                                    </state>
                                </interface>
                            </interfaces>
                        </filter>
                        '''
        
        try:
            interface_reply = ET.fromstring(self.manager.get(filter).data_xml)

            if interface_reply.find('.//{http://openconfig.net/yang/interfaces}enabled').text == 'true' and not deconf:
                config = f'''
                            <config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
                                <interfaces xmlns="http://openconfig.net/yang/interfaces">
                                    <interface>
                                        <name>{port}</name>
                                        <config>
                                            <name>{port}</name>
                                            <enabled>false</enabled>
                                        </config>
                                    </interface>
                                </interfaces>
                            </config>
                        '''
                
                self.manager.edit_config(config=config)
                self.manager.commit()
            
            if not port in self.disabled and not deconf:
                self.disabled.append(port)
            elif port in self.disabled and deconf:
                self.disabled.remove(port)

            self.logger.debug(f'Configured ({not deconf}) disable interface {port} on {self.ip_address} ({self.hostname})')

            return True

        except Exception as e:
            self.logger.error(f'Failed to configure ({not deconf}) disable interface {port} on {self.ip_address} ({self.hostname}): {str(e)}')
            return False

    # TODO: temporary solution, assumes exit port network is /30, so there's only one possible next hop address
    # Get next hop address from exit port
    def get_next_hop_from_port(self, port):
        for c in self.configurations:
            split = c.split(' ')
            if split[0] == 'address' and split[1] == port:
                (address, prefix) = split[2].split('/')
                other = self.get_other_address(address)
                return other
                

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
    
    # Returns other address of /30 network
    def get_other_address(self, address):
        address = address.split('.')
        prefix = 30

        # Convert address to binary
        address = ''.join(format(int(octet), '08b') for octet in address)

        # Get network address
        network_address = address[:prefix] + '0' * (32 - prefix)

        address = int(address, 2)
        network_address = int(network_address, 2)

        if address - 1 == network_address:
            address = address + 1
        else:
            address = address - 1
        
        address = str(bin(address))[2:]

        other_address = [str(int(address[i:i+8], 2)) for i in range(0, 32, 8)]

        return '.'.join(other_address)