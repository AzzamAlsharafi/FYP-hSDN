import logging
import time

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.ofproto import ofproto_v1_3

from scapy.layers.l2 import Ether, ARP
from scapy.contrib import lldp

from src.events import EventPolicyDeviceAPI, EventSdnDeviceAPI, EventSdnTopology, EventSdnConfigurations

# Handles topology discovery for SDN (OpenFlow) devices
class SdnTopologyDiscovery(app_manager.RyuApp):
    _EVENTS = [EventSdnTopology, EventPolicyDeviceAPI]

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SdnTopologyDiscovery, self).__init__(*args, **kwargs)

        self.logger.setLevel(logging.INFO)

        # Mapping datapath ID to label
        self.labels = {}

        # Mapping label to datapath object
        self.datapaths = {}
        
        self.load_all_labels()
        
        self.ports = {} # {label: [{'port_no': 1, 'hw_addr': 'aa:aa:aa:aa:aa:aa'}, ...]
        
        # LLDP database. 
        # Can be considered 2D dictonary, where first key is the label of the switch, and second key is the system name of the neighbor
        # {'label': {'system_name': {'port': 1, 'ttl': 120}, ...}, ...}
        self.lldp = {}

        # Dictionary for applied configurations
        # {label: [config1, config2, ...], ...}
        self.configurations = {}

        # Stores current time. Used for LLDP timeout
        self.time = time.time()

    # TODO: move this to a separate app. Shouldn't be part of topology discovery
    # Configure SDN devices with received configurations
    @set_ev_cls(EventSdnConfigurations)
    def configure_devices(self, ev):
        configurations = ev.configurations

        for label in configurations:
            if label != 'B2b':
                continue

            if label in self.configurations:
                for conf in self.configurations[label]:
                    if conf not in configurations[label]:
                        self.configure(label, conf, deconf=True)

            for conf in configurations[label]:
                self.configure(label, conf)
    
    # Run device instruction from API
    @set_ev_cls(EventSdnDeviceAPI)
    def process_device_api(self, ev):
        words = ev.words

        if words[0] == 'edit':
            separator = words.index('old')
            new_name = ' '.join(words[1:separator])
            old_name = ' '.join(words[separator+1:])

            self.datapaths[new_name] = self.datapaths.pop(old_name)
            dp = self.datapaths[new_name]

            self.labels[dp.id] = new_name
            self.all_labels[dp.id] = new_name
            
            self.ports[new_name] = self.ports.pop(old_name)
            self.lldp[new_name] = self.lldp.pop(old_name)

            lines = []

            with open('config/sdn.txt', 'r') as file:
                for line in file.readlines():
                    if line.strip() == f'{dp.id}:{old_name}':
                        lines.append(f'{dp.id}:{new_name}\n')
                    else:
                        lines.append(line)
            
            with open('config/sdn.txt', 'w') as file:
                file.writelines(lines)

            self.send_event_to_observers(EventPolicyDeviceAPI(old_name, new_name))

    # Configure device
    def configure(self, label, config, deconf=False):
        if not deconf and (label in self.configurations and config in self.configurations[label]):
            return # Configuration already applied
        
        split = config.split(' ')

        if split[0] == 'address':
            interface = split[1]
            (address, prefix) = split[2].split('/')

            if self.configure_address(label, interface, address, prefix, deconf=deconf):
                if deconf:
                    self.remove_dict_list(self.configurations, label, config)
                else:
                    self.append_dict_list(self.configurations, label, config)

        elif split[0] == 'route':
            (address, prefix) = split[1].split('/')
            destination = self.get_network_address(address, prefix)

            interface = split[2]

            if self.configure_route(label, destination, prefix, interface, deconf=deconf):
                if deconf:
                    self.remove_dict_list(self.configurations, label, config)
                else:
                    self.append_dict_list(self.configurations, label, config)
        else:
            self.logger.error(f'Invalid configuration for device {label}: {config}')

    # Configure address on device
    def configure_address(self, label, interface, address, prefix, deconf=False):
        # Install flow to send ARP requests for the configured address to the controller
        datapath = self.datapaths[label]
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        actions = [ofp_parser.OFPActionOutput(ofp.OFPP_CONTROLLER)]
        match = ofp_parser.OFPMatch(eth_type=0x0806, in_port=int(interface), arp_tpa=address, arp_op=1)
        instructions = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        
        if deconf:
            datapath.send_msg(ofp_parser.OFPFlowMod(datapath=datapath, match=match, instructions=instructions, 
                                                    command=ofp.OFPFC_DELETE, out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY))
        else:
            datapath.send_msg(ofp_parser.OFPFlowMod(datapath=datapath, match=match, instructions=instructions))
        
        # Configure route to the configured address
        destination = self.get_network_address(address, prefix)
        self.configure_route(label, destination, prefix, interface, deconf=deconf)

        self.logger.debug(f'Configured ({not deconf}) address {address} on {interface} for {label}')
        return True

    # Configure route on device
    def configure_route(self, label, destination, prefix, interface, deconf=False):
        # Install flow to route packets to the configured destination to the configured interface
        datapath = self.datapaths[label]
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        actions = [
            ofp_parser.OFPActionSetField(eth_dst='ff:ff:ff:ff:ff:ff'), # Broadcast MAC address to not deal with ARP
            ofp_parser.OFPActionOutput(int(interface))]
        match = ofp_parser.OFPMatch(eth_type=0x0800, ipv4_dst=f'{destination}/{prefix}')
        instructions = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        
        if deconf:
            datapath.send_msg(ofp_parser.OFPFlowMod(datapath=datapath, match=match, instructions=instructions, 
                                                    command=ofp.OFPFC_DELETE, out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY))
        else:
            datapath.send_msg(ofp_parser.OFPFlowMod(datapath=datapath, match=match, instructions=instructions))

        self.logger.debug(f'Configured ({not deconf}) route {destination}/{prefix} to {interface} for {label}')
        return True

    # Load SDN devices labels from previous sessions
    def load_all_labels(self):
        labels = {}
        count = 0

        try:
            with open('config/sdn.txt', 'r') as file:
                lines = file.read().splitlines()
                for line in lines:
                    split = line.split(':')
                    labels[int(split[0])] = split[1]
                count = len(lines)
        except FileNotFoundError:
            self.logger.debug('config/sdn.txt does not exist.')
        except:
            self.logger.error('Error loading from config/sdn.txt')
        
        self.all_labels = labels
        self.labels_count = count

    # Listener for new switch connections. Add them to topology, and start LLDP discovery
    # Also used for removing disconnected switches from topology
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def new_switch_handler(self, ev):
        datapath = ev.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        # TODO: What happens when SDN device label is changed while the network is running (using GUI)?
        #       What become of the old LLDP relationships? And how will that affect the flow of the program?
        if ev.state == MAIN_DISPATCHER:
            if datapath.id in self.all_labels:
                label = self.all_labels[datapath.id]

                self.labels[datapath.id] = label
                self.datapaths[label] = datapath

                self.logger.debug(f'Found existing SDN device: {datapath.id} ({label})')
            else:
                label = f'S{self.labels_count}'
                self.labels_count += 1

                self.labels[datapath.id] = label
                self.all_labels[datapath.id] = label

                self.logger.debug(f'Found new SDN device: {datapath.id} ({label})')

                try:
                    with open('config/sdn.txt', 'a') as file:
                        file.write(f'{datapath.id}:{label}\n')
                except:
                    self.logger.error(f'Error writing {label} to config/sdn.txt')

            self.ports[label] = []

            # Request switch ports, and start LLDP discovery on reply
            req = ofp_parser.OFPPortDescStatsRequest(datapath, 0)
            datapath.send_msg(req)

            # Install flow to send received LLDP packets to controller
            actions = [ofp_parser.OFPActionOutput(ofp.OFPP_CONTROLLER)]
            match = ofp_parser.OFPMatch(eth_type=0x88cc)
            instructions = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
            datapath.send_msg(ofp_parser.OFPFlowMod(datapath=datapath, match=match, instructions=instructions))

            self.logger.debug(f'Datapath {datapath.id} connected, label: {self.labels[datapath.id]}')
        else:
            self.ports.pop(self.labels[datapath.id])
            self.lldp.pop(self.labels[datapath.id])

            self.datapaths.pop(self.labels[datapath.id])
            self.labels.pop(datapath.id)

            self.logger.debug(f'Datapath {datapath.id} disconnected')


    # Listener for port description requests, starts LLDP discovery
    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_reply_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        
        ports = []
        for p in msg.body:
            p.port_no, p.hw_addr

            # Skip OpenFlow local port
            if p.port_no == ofp.OFPP_LOCAL:
                continue

            ports.append({'port_no': p.port_no, 'hw_addr': p.hw_addr})

        self.ports[self.labels[datapath.id]] = ports
        self.lldp[self.labels[datapath.id]] = {}

        # Start LLDP discovery
        self.start_lldp(datapath, timeout=1)

        self.logger.debug(f'Datapath {datapath.id} ({self.labels[datapath.id]}) ports: {ports}')

    # Start LLDP for a switch
    # The purpose of this function is to periodically send LLDP packets out of all ports of a switch,
    # it works by installing a dummy flow with a hard timeout, which will trigger a flow removed event,
    # then the flow removed event handler will send the LLDP packets, and will call this function again,
    # thus creating an infinite loop with constant intervals.
    # This function is also used to update LLDP timers, and send topology to TopologyManager, since it's already running periodically
    def start_lldp(self, datapath, timeout=15):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        instructions = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, [])]
        datapath.send_msg(ofp_parser.OFPFlowMod(datapath=datapath, priority=10, hard_timeout=timeout, instructions=instructions, flags=ofp.OFPFF_SEND_FLOW_REM))

        self.update_lldp_database()

        self.logger.debug(f'Starting LLDP on {self.labels[datapath.id]} ({self.labels[datapath.id]}). Timeout: {timeout}')

    # Flow removed event handler, used for sending periodic LLDP packets
    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def flow_removed_send_lldp(self, ev):
        msg = ev.msg
        reason = msg.reason
        datapath = msg.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        if reason == ofp.OFPRR_HARD_TIMEOUT:
            for p in self.ports[self.labels[datapath.id]]:
                pkt = self.craft_lldp(self.labels[datapath.id], p)
                actions = [ofp_parser.OFPActionOutput(p['port_no'])]
                packet_out = ofp_parser.OFPPacketOut(datapath=datapath, buffer_id=ofp.OFP_NO_BUFFER, in_port=ofp.OFPP_CONTROLLER, actions=actions, data=pkt.build())
                
                datapath.send_msg(packet_out)

            self.start_lldp(datapath)
        
        self.logger.debug(f'OFPFlowRemoved received ({reason})')

    # Listener for incoming packets
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        port_in = msg.match['in_port']

        pkt = Ether(msg.data)

        if pkt.type == 0x88cc: # LLDP EtherType
            system_name = pkt[lldp.LLDPDUSystemName].system_name.decode()
            time_to_live = pkt[lldp.LLDPDUTimeToLive].ttl

            self.lldp[self.labels[datapath.id]][system_name] = {'port': port_in, 'ttl': time_to_live}

            self.logger.debug(f'LLDP packet received on {self.labels[datapath.id]} ({self.labels[datapath.id]}), port: {port_in}, system name: {system_name} TTL: {time_to_live}')

        elif pkt.type == 0x0806: # ARP EtherType
            arp_reply = self.craft_arp_reply(self.labels[datapath.id], port_in, pkt)
            datapath.send_msg(datapath.ofproto_parser.OFPPacketOut(datapath=datapath, buffer_id=datapath.ofproto.OFP_NO_BUFFER, in_port=ofp.OFPP_CONTROLLER, actions=[datapath.ofproto_parser.OFPActionOutput(port_in)], data=arp_reply.build()))

            self.logger.debug(f'ARP packet received on {datapath.id} ({self.labels[datapath.id]}), port: {port_in}, packet: {pkt}')

        else:
            self.logger.debug(f'Packet in received on {datapath.id} ({self.labels[datapath.id]}), port: {port_in}, packet: {pkt}')
        
    # Update LLDP timers, remove expired entries, and send topology to TopologyManager
    def update_lldp_database(self):
        passed_time = time.time() - self.time
        
        # Stop function if it has been called less than 1 second ago
        if passed_time < 1:
            return
        
        self.time = time.time()

        for (label, neighbors) in self.lldp.items():
            for system_name in list(neighbors): # list() is used to create a copy of the list, so it can be modified while iterating
                neighbors[system_name]['ttl'] -= passed_time

                if neighbors[system_name]['ttl'] <= 0:
                    neighbors.pop(system_name)

                    self.logger.debug(f'LLDP entry expired, label: {label}, system name: {system_name}')
        
        self.send_topology()
        
        self.logger.debug(f'LLDP database updated, passed time: {passed_time} seconds')

    # Send topology to TopologyManager
    def send_topology(self):
        topology = {'ports': self.ports, 'neighbors': self.lldp}
        self.send_event_to_observers(EventSdnTopology(topology))

    # Craft LLDP packet
    def craft_lldp(self, label, port):
        port_no = port['port_no']
        hw_addr = port['hw_addr']

        return Ether(dst='01:80:c2:00:00:0e', src=hw_addr, type=0x88cc) / lldp.LLDPDU() \
        / lldp.LLDPDUChassisID(subtype=lldp.LLDPDUChassisID.SUBTYPE_MAC_ADDRESS, id=hw_addr) \
        / lldp.LLDPDUPortID(subtype=lldp.LLDPDUPortID.SUBTYPE_INTERFACE_NAME, id=str(port_no)) \
        / lldp.LLDPDUTimeToLive(ttl=120) \
        / lldp.LLDPDUSystemName(system_name=label) \
        / lldp.LLDPDUPortDescription(description=f'OFPort-{port_no}') \
        / lldp.LLDPDUEndOfLLDPDU()

    # Carft ARP reply packet
    def craft_arp_reply(self, label, port_in, pkt):
        hw_addr = next((p['hw_addr'] for p in self.ports[label] if p['port_no'] == port_in), None)

        return Ether(dst=pkt[Ether].src, src=hw_addr) \
        / ARP(op=2, hwsrc=hw_addr, psrc=pkt[ARP].pdst, hwdst=pkt[ARP].hwsrc, pdst=pkt[ARP].psrc)

    def append_dict_list(self, dict, key, item):
        if key in dict:
            dict[key].append(item)
        else:
            dict[key] = [item]
    
    def remove_dict_list(self, dict, key, item):
        if key in dict:
            dict[key].remove(item)

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