'''
Coursera:
- Software Defined Networking (SDN) course
-- Programming Assignment: Layer-2 Firewall Application

Professor: Nick Feamster
Teaching Assistant: Arpit Gupta
'''
import os

from pox.lib.addresses import EthAddr, IPAddr6
from pox.lib.util import dpidToStr
from pox.lib.revent import *
from pox.lib.addresses import IPAddr
import pox.openflow.libopenflow_01 as of
from pox.core import core

import pox.lib.packet as pkt
import json

COLOR_CODES = {
    'BLUE': '\033[94m',  # Blue
    'GREEN': '\033[92m',   # Green
    'YELLOW': '\033[93m',  # Yellow
    'RED': '\033[91m',   # Red
    "RESET": '\033[0m'
}

log = core.getLogger()
policyFile = "%s/pox/pox/misc/firewall-policies.csv" % os.environ['HOME']

POLICY_FILE_PATH = "./firewall-policies.json"

DL_TYPE = {
    "ipv4": pkt.ethernet.IP_TYPE
}

NW_PROTO = {
    "tcp": pkt.ipv4.TCP_PROTOCOL,
    "udp": pkt.ipv4.UDP_PROTOCOL,
    "icmp": pkt.ipv4.ICMP_PROTOCOL
}


class Firewall (EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)
        self.load_policies()
        log.info("Enabling Firewall Module")
        core.openflow.addListenerByName("PacketIn", self._handle_PacketIn)

    def __get_destination(self, ip_packet):
        # Check if the IP packet is a TCP or UDP packet
        protocol = ip_packet.protocol

        if protocol == pkt.ipv4.TCP_PROTOCOL:
            tcp_packet = ip_packet.find('tcp')
            if tcp_packet:
                src_port = tcp_packet.srcport
                dst_port = tcp_packet.dstport
                return ("TCP", src_port, dst_port)
        elif protocol == pkt.ipv4.UDP_PROTOCOL:
            udp_packet = ip_packet.find('udp')
            if udp_packet:
                src_port = udp_packet.srcport
                dst_port = udp_packet.dstport
                return ("UDP", src_port, dst_port)

        return ("ICMP" if protocol == pkt.ipv4.ICMP_PROTOCOL else str(protocol), '', '')

    def _handle_PacketIn(self, event):
        packet = event.parsed.find('ipv4')

        if not packet:
            return

        (protocol, src_port, dst_port) = self.__get_destination(packet)

        sender = COLOR_CODES["BLUE"] + \
            str(packet.srcip) + f':{src_port}' + COLOR_CODES["RESET"]
        receiver = COLOR_CODES["YELLOW"] + \
            str(packet.dstip) + f':{dst_port}' + COLOR_CODES["RESET"]

        dpid = COLOR_CODES['GREEN'] + str(event.dpid) + COLOR_CODES['RESET']
        protocol = COLOR_CODES['RED'] + protocol + COLOR_CODES['RESET']

        log.info(f"{dpid}:Packet: {protocol} {sender + ' --> ' + receiver}")

    def _handle_ConnectionUp(self, event):
        if event.dpid == self.switch_id:
            self.set_policies(event)
            log.info("Firewall rules installed on %s", dpidToStr(event.dpid))

    def load_policies(self):
        """
        Load the firewall policies from the file
        """
        with open(POLICY_FILE_PATH, 'r') as f:
            content = json.load(f)
            self.policies = content["discard_policies"]
            self.switch_id = content["firewall_switch_id"]

    def set_policies(self, event):
        """
        Set the firewall policies on the event, if there is no nw_proto or dl_type in the policy, generate all variants
        """

        r = of.ofp_flow_mod()
        r.match.__setattr__("dl_type", pkt.ethernet.IPV6_TYPE)
        event.connection.send(r)

        for policy in self.policies:

            policy_variants = [policy]
            if "nw_proto" not in policy:
                policy_variants = self._generate_variants(
                    policy_variants, "nw_proto", NW_PROTO.keys())

            if "dl_type" not in policy:
                policy_variants = self._generate_variants(
                    policy_variants, "dl_type", DL_TYPE.keys())

            for policy_variant in policy_variants:
                rule = self._rule_from_policy(policy_variant)
                event.connection.send(rule)

    def _rule_from_policy(self, policy):
        """
        Generate a rule from the policy
        """
        rule = of.ofp_flow_mod()
        for (field, value) in sorted(policy.items()):
            parsed_value = self._parse_field_value(field, value)

            if parsed_value is None:
                continue

            rule.match.__setattr__(field, parsed_value)
        return rule

    def _parse_field_value(self, field, value: str):
        """
        Parse the field value based on the field
        """
        match (field):
            case "tp_dst":
                return int(value)
            case "tp_src":
                return int(value)
            case "nw_proto":
                return NW_PROTO.get(value, None)
            case "dl_src":
                return EthAddr(value)
            case "dl_dst":
                return EthAddr(value)
            case "nw_src":
                return IPAddr(value) if '.' in value else IPAddr6(value)
            case "nw_dst":
                return IPAddr(value) if '.' in value else IPAddr6(value)
            case "dl_type":
                return DL_TYPE.get(value, None)

    def _generate_variants(self, policies, field, values):
        """
        Generate all variants of the policies with the field set to the values
        """
        new_policies = []

        for policy in policies:
            for value in values:
                __policy = policy.copy()
                __policy[field] = value
                new_policies.append(__policy)

        return new_policies


def launch():
    '''
    Starting the Firewall module
    '''
    core.registerNew(Firewall)
