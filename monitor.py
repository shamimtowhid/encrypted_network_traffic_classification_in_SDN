from operator import attrgetter
from datetime import datetime
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.lib.packet import packet
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet import udp
from ryu.lib.packet import arp
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types


class Monitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Monitor, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)
        self.fields = {'time':'','datapath':'','src_port':'','ipv4_src':'','ipv4_dst':'','dst_port':'',
                'total_packets':0,'total_bytes':0}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions) # this rule is for any unknown packet

    def add_flow(self, datapath, priority, match, actions, buffer_id=None, timeout=0):
        #import pdb;pdb.set_trace()
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match, idle_timeout=timeout,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, idle_timeout=timeout,
                                    match=match, instructions=inst)
#        print("sending ", match)
        datapath.send_msg(mod)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        src = eth.src
        dst = eth.dst

        src_port = None
        dst_port = None
        src_ip = None
        dst_ip = None
        u = None

        dpid = format(datapath.id, "d").zfill(16)
        self.mac_to_port.setdefault(dpid, {})

        ip = pkt.get_protocol(ipv4.ipv4)
        if ip is not None and ip.proto ==17:
            src_ip = ip.src
            dst_ip = ip.dst
            u = pkt.get_protocol(udp.udp)
            src_port = u.src_port
            dst_port = u.dst_port

        # Learn mac address to avoid flood message next time
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid] and u is not None:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:

            match = parser.OFPMatch(eth_type=eth.ethertype, ipv4_src=src_ip, ipv4_dst=dst_ip, ip_proto=17, udp_src=src_port, udp_dst=dst_port)

            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id, timeout=10)
                return
            else:
                self.add_flow(datapath, 1, match, actions, timeout=10)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)


    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _monitor(self):
        self.logger.info('time\tdatapath\tsrc_port\tipv4_src\tipv4_dst\tdst_port\ttotal_packets\ttotal_bytes')
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(1)

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)


    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        try:
            for stat in [flow for flow in body if flow.priority == 1]:
                self.fields['time'] = datetime.utcnow().strftime('%s')
                self.fields['datapath'] = ev.msg.datapath.id
                self.fields['ipv4_src'] = stat.match['ipv4_src']
                self.fields['ipv4_dst'] = stat.match['ipv4_dst']
                if 'udp_src' in stat.match:
                    self.fields['src_port'] = stat.match['udp_src']
                    self.fields['dst_port'] = stat.match['udp_dst']
                self.fields['total_packets'] = stat.packet_count
                self.fields['total_bytes'] = stat.byte_count

                self.logger.info('data\t%s\t%x\t%s\t%s\t%s\t%s\t%d\t%d',self.fields['time'],self.fields['datapath'],self.fields['src_port'],self.fields['ipv4_src'],self.fields['ipv4_dst'],self.fields['dst_port'],self.fields['total_packets'],self.fields['total_bytes'])
        except Exception as ex:
            print("Error")
