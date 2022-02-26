from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import ethernet
from ryu.lib.packet import packet
from ryu.lib.dpid import dpid_to_str
from ryu.ofproto import ofproto_v1_3

class L2Switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L2Switch, self).__init__(*args, **kwargs)
        self.cache = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, event):
        """
        Handshake: Features Request Response Handler

        Installs a low level (0) flow table modification that pushes packets to
        the controller. This acts as a rule for flow-table misses.
        """
        actions = [event.msg.datapath.ofproto_parser.OFPActionOutput(event.msg.datapath.ofproto.OFPP_CONTROLLER, event.msg.datapath.ofproto.OFPCML_NO_BUFFER)]
        self.logger.info("Handshake taken place with {}".format(dpid_to_str(event.msg.datapath.id)))
        self.__add_flow(datapath=event.msg.datapath, priority=0, match=event.msg.datapath.ofproto_parser.OFPMatch(), actions=actions)
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        eth_header = packet.Packet(event.msg.data).get_protocol(ethernet.ethernet)
        src = eth_header.src
        dst = eth_header.dst   
        datapath = event.msg.datapath
        parser = datapath.ofproto_parser
        in_port = event.msg.match['in_port']

        self.logger.info("(Event) inbound packet: switch %s, src %s, dest %s, port %s", datapath.id, src, dst, in_port)

        # Identify the switch
        self.cache.setdefault(datapath.id, {})

        # If the destination MAC address is found in the cache, then forward it to the specified 
        # destination port. Otherwise, update the cache and flood all ports
        if dst in self.cache[datapath.id]:
            actions = [parser.OFPActionOutput(self.cache[datapath.id][dst])]
            # Add an entry to the flow table
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            self.__add_flow(datapath=datapath, priority=1, match=match, actions=actions)
        else:
            # Learn the MAC address for next time
            self.cache[datapath.id][src] = in_port
            # Flood 
            actions = [parser.OFPActionOutput(datapath.ofproto.OFPP_FLOOD)]

        # Send the packet
        msg = parser.OFPPacketOut(datapath=datapath, buffer_id=event.msg.buffer_id, in_port=in_port, actions=actions, data=event.msg.data)
        self.logger.info("Sending packet out")
        datapath.send_msg(msg)
            
    def __add_flow(self, datapath, priority, match, actions, idle_timeout=30, hard_timeout=0):
        """
        Install Flow Table Modification

        Takes a set of OpenFlow Actions and a OpenFlow Packet Match and creates
        the corresponding Flow-Mod. This is then installed to a given datapath
        at a given priority.
        """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst, hard_timeout=hard_timeout, idle_timeout=idle_timeout)
        self.logger.info("Flow-Mod written to {}".format(dpid_to_str(datapath.id)))
        datapath.send_msg(mod)
