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
    'CYAN': '\033[96m',
    'MAGENTA': '\033[95m',
    'GREEN': '\033[92m',
    'GREY': '\033[90m',
    'BLACK': '\033[30m',
    'WHITE': '\033[97m',
    'LIGHT_GREEN': '\033[92;1m',
    "RESET": '\033[0m'
}

log = core.getLogger()

POLICY_FILE_PATH = "./firewall-policies.json"

DL_TYPE = {
    "ipv4": pkt.ethernet.IP_TYPE,
    "ipv6": pkt.ethernet.IPV6_TYPE,
}

NW_PROTO = {
    "tcp": pkt.ipv4.TCP_PROTOCOL,
    "udp": pkt.ipv4.UDP_PROTOCOL,
    "icmp": pkt.ipv4.ICMP_PROTOCOL,
    "icmpv6": pkt.ipv6.ICMP6_PROTOCOL,
}


class Firewall (EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)
        self.load_policies()
        log.info("Enabling Firewall Module")
        #PacketIn -> cuando llega un paquete al controlador
        core.openflow.addListenerByName("PacketIn", self._handle_PacketIn)

    def __get_destination(self, ip_packet):
        """
        Determina el protocolo y los puertos de origen y destino del paquete IP.
        Retorna una tupla con el protocolo, puerto de origen y puerto de destino.
        Si no se encuentra el protocolo o los puertos, retorna una tupla con valores vacíos.
        """
        if ip_packet.__class__.__name__ == 'ipv4':
            protocol = ip_packet.protocol
        elif ip_packet.__class__.__name__ == 'ipv6':
            protocol = ip_packet.next_header_type
        else:
            return (str(type(ip_packet)), '', '')

        if protocol in (pkt.ipv4.TCP_PROTOCOL, pkt.ipv6.TCP_PROTOCOL):
            tcp_packet = ip_packet.find('tcp')
            if tcp_packet:
                src_port = tcp_packet.srcport
                dst_port = tcp_packet.dstport
                return ("TCP", src_port, dst_port)
        elif protocol in (pkt.ipv4.UDP_PROTOCOL, pkt.ipv6.UDP_PROTOCOL):
            udp_packet = ip_packet.find('udp')
            if udp_packet:
                src_port = udp_packet.srcport
                dst_port = udp_packet.dstport
                return ("UDP", src_port, dst_port)

        if protocol in (pkt.ipv4.ICMP_PROTOCOL, pkt.ipv6.ICMP6_PROTOCOL):
            return ("ICMP", '', '')

        return (str(protocol), '', '')

    def _handle_PacketIn(self, event):
        # Se llama cada vez que llega un paquete al controlador
        packet = event.parsed.find('ipv4')
        if not packet:
            packet = event.parsed.find('ipv6')
        if not packet:
            return

        (protocol, src_port, dst_port) = self.__get_destination(packet)

        sender = COLOR_CODES["CYAN"] + \
            str(packet.srcip) + f':{src_port}' + COLOR_CODES["RESET"]
        receiver = COLOR_CODES["MAGENTA"] + \
            str(packet.dstip) + f':{dst_port}' + COLOR_CODES["RESET"]

        dpid = COLOR_CODES['GREEN'] + str(event.dpid) + COLOR_CODES['RESET']
        protocol = COLOR_CODES['GREY'] + protocol + COLOR_CODES['RESET']

        log.info(
            f"{COLOR_CODES['WHITE']}[SW:{COLOR_CODES['GREEN']}{dpid}{COLOR_CODES['WHITE']}] "
            f"PROTO:{COLOR_CODES['GREY']}{protocol}{COLOR_CODES['WHITE']} "
            f"SRC:{COLOR_CODES['CYAN']}{sender}{COLOR_CODES['WHITE']} "
            f"DST:{COLOR_CODES['LIGHT_GREEN']}{receiver}{COLOR_CODES['WHITE']}{COLOR_CODES['RESET']}"
        )
        
    def _handle_ConnectionUp(self, event):
        """
        Se ejecuta cuando un switch se conecta al controlador
        Si el switch es el que tiene las políticas de firewall, se instalan las reglas
        """
        if event.dpid == self.switch_id:
            self.set_policies(event)
            log.info("Firewall rules installed on %s", dpidToStr(event.dpid))

    def load_policies(self):
        """
        Lee el JSON de las políticas de firewall y las carga en la instancia
        """
        with open(POLICY_FILE_PATH, 'r') as f:
            content = json.load(f)
            self.policies = content["discard_policies"]
            self.switch_id = content["firewall_switch_id"]

    def set_policies(self, event):
        """
        Establece las políticas de firewall en el evento, si no hay nw_proto o dl_type en la política, genera todas las variantes
        """

        # #Bloquea todo el tráfico IPv6 que no coincida con las políticas
        # r = of.ofp_flow_mod()
        # r.match.__setattr__("dl_type", pkt.ethernet.IPV6_TYPE)
        # event.connection.send(r)

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
        Traduce una politica del JSON a una regla de OpenFlow
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
        Si una politica no especifica un campo, genera variantes para
        todos los valores posibles (TCP, UDP, ICMP).
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
    Lanza el firewall al iniciar el controlador
    '''
    core.registerNew(Firewall)
