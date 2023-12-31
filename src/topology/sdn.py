import logging
import time

from ryu.base import app_manager
from ryu.controller.handler import set_ev_cls
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.ofproto import ofproto_v1_3

from scapy.layers.l2 import Ether
from scapy.contrib import lldp

from src.events import EventSdnTopology

# Handles topology discovery for SDN (OpenFlow) devices
class SdnTopologyDiscovery(app_manager.RyuApp):
    _EVENTS = [EventSdnTopology]

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SdnTopologyDiscovery, self).__init__(*args, **kwargs)

        self.logger.setLevel(logging.INFO)

        # Mapping datapath ID to label
        self.label_count = 0
        self.labels = {}
        
        self.ports = {} # {label: [{'port_no': 1, 'hw_addr': 'aa:aa:aa:aa:aa:aa'}, ...]
        
        # LLDP database. 
        # Can be considered 2D dictonary, where first key is the label of the switch, and second key is the system name of the neighbor
        # {'label': {'system_name': {'port': 1, 'ttl': 120}, ...}, ...}
        self.lldp = {}

        # Stores current time. Used for LLDP timeout
        self.time = time.time()
    
    # Listener for new switch connections. Add them to topology, and start LLDP discovery
    # Also used for removing disconnected switches from topology
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def new_switch_handler(self, ev):
        datapath = ev.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        if ev.state == MAIN_DISPATCHER:
            label = f'S{self.label_count}'
            self.label_count += 1

            self.labels[datapath.id] = label

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
        datapath.send_msg(ofp_parser.OFPFlowMod(datapath=datapath, hard_timeout=timeout, instructions=instructions, flags=ofp.OFPFF_SEND_FLOW_REM))

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

    # Listener for incoming packets (just LLDP for now)
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        port_in = msg.match['in_port']

        pkt = Ether(msg.data)

        if pkt.type == 0x88cc: # LLDP EtherType
            system_name = pkt[lldp.LLDPDUSystemName].system_name.decode()
            time_to_live = pkt[lldp.LLDPDUTimeToLive].ttl

            self.lldp[self.labels[datapath.id]][system_name] = {'port': port_in, 'ttl': time_to_live}

            self.logger.debug(f'LLDP packet received on {self.labels[datapath.id]} ({self.labels[datapath.id]}), port: {port_in}, system name: {system_name} TTL: {time_to_live}')

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
