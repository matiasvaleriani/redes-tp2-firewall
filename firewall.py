'''
Coursera:
- Software Defined Networking (SDN) course
-- Programming Assignment: Layer-2 Firewall Application

Professor: Nick Feamster
Teaching Assistant: Arpit Gupta
'''
import os
import logging
logging.getLogger('libopenflow_01').setLevel(logging.ERROR)

from pox.lib.addresses import EthAddr, IPAddr6
from pox.lib.util import dpidToStr
from pox.lib.revent import *
from pox.lib.addresses import IPAddr
import pox.openflow.libopenflow_01 as of
from pox.core import core
from constants import (
    DATA_LINK_TYPE, TRANSPORT_PROTO, DEST_PORT, SOURCE_PORT, DATA_LINK_SRC, DATA_LINK_DEST, SOURCE_IP, DESTINATION_IP
)
import pox.lib.packet as pkt
import json
from tabulate import tabulate

COLORS = {
    'WHITE': '\033[97m',
    'GREY': '\033[90m',
    'BLACK': '\033[30m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'GREEN': '\033[92m',
    'LIGHT_GREEN': '\033[92;1m',
    "RESET": '\033[0m'
}

log = core.getLogger()

POLICIES_FILE = "./policies.json"

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
        core.openflow.addListenerByName("FlowStatsReceived", self._handle_FlowStatsReceived)

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

    def print_routing_table(self, connection):
        # Solicita la tabla de flujos al switch
        stats_request = of.ofp_stats_request(body=of.ofp_flow_stats_request())
        connection.send(stats_request)

    def _handle_FlowStatsReceived(self, event):
        headers = ["Match", "Actions", "Priority", "Packets", "Bytes"]
        table = []
        for stat in event.stats:
            match = str(stat.match)
            actions = ', '.join([str(a) for a in stat.actions])
            priority = stat.priority
            packets = stat.packet_count
            bytes_ = stat.byte_count
            table.append([match, actions, priority, packets, bytes_])
        log.info("Tabla de enrutamiento (flow table) del switch %s:\n%s",
                 dpidToStr(event.connection.dpid),
                 tabulate(table, headers=headers, tablefmt="fancy_grid"))

    def _handle_PacketIn(self, event):
        # Se llama cada vez que llega un paquete al controlador
        packet = event.parsed.find('ipv4')
        if not packet:
            packet = event.parsed.find('ipv6')
        if not packet:
            return

        (protocol, src_port, dst_port) = self.__get_destination(packet)

        source = COLORS["CYAN"] + \
            str(packet.srcip) + f':{src_port}' + COLORS["RESET"]
        destination = COLORS["MAGENTA"] + \
            str(packet.dstip) + f':{dst_port}' + COLORS["RESET"]

        switch = COLORS['GREEN'] + str(event.dpid) + COLORS['RESET']
        protocol = COLORS['GREY'] + protocol + COLORS['RESET']

        log.info(
            f"{COLORS['WHITE']}[SWITCH:{COLORS['GREEN']}{switch}{COLORS['WHITE']}] "
            f"SRC:{COLORS['CYAN']}{source}{COLORS['WHITE']} "
            f"DST:{COLORS['LIGHT_GREEN']}{destination}{COLORS['WHITE']}{COLORS['RESET']} "
            f"PROTOCOL:{COLORS['GREY']}{protocol}{COLORS['WHITE']} "
        )
        
    def _handle_ConnectionUp(self, event):
        """
        Se ejecuta cuando un switch se conecta al controlador
        Si el switch es el que tiene las políticas de firewall, se instalan las reglas
        """

        # Esto es por si quisiera bloquear el trafico IPv6 en todos los switches
        # policy_ipv6 = of.ofp_flow_mod()
        # policy_ipv6.match.__setattr__(DATA_LINK_TYPE, pkt.ethernet.IPV6_TYPE)
        # event.connection.send(policy_ipv6)
        # log.info("IPv6 traffic blocked on %s", dpidToStr(event.dpid))

        self.print_routing_table(event.connection)

        if event.dpid == self.switch_id:
            self.set_policies(event)
            log.info("Firewall rules installed on %s", dpidToStr(event.dpid))

    def load_policies(self):
        """
        Carga las reglas del firewall desde el archivo JSON configurado.
        """
        try:
            with open(POLICIES_FILE) as archivo:
                datos = json.load(archivo)
                self.policies = datos.get("policies", [])
                self.switch_id = datos.get("switch", 1)
        except FileNotFoundError:
            log.error(f"No se encontró el archivo de políticas: {POLICIES_FILE}")
            self.policies = []
            self.switch_id = 1
        except Exception as e:
            log.error(f"Error al cargar las políticas: {e}")
            self.policies = []
            self.switch_id = 1

    def set_policies(self, event):
        """
        Establece las políticas de firewall en el evento, si no hay nw_proto o dl_type en la política, genera todas las variantes
        """

        # #Bloquea todo el tráfico IPv6 que no coincida con las políticas
        # policy_ipv6 = of.ofp_flow_mod()
        # policy_ipv6.match.__setattr__(DATA_LINK_TYPE, pkt.ethernet.IPV6_TYPE)
        # event.connection.send(policy_ipv6)

        for policy in self.policies:

            policy_variants = [policy]
            if TRANSPORT_PROTO not in policy:
                policy_variants = self._generate_variants(
                    policy_variants, TRANSPORT_PROTO, NW_PROTO.keys())

            if DATA_LINK_TYPE not in policy:
                policy_variants = self._generate_variants(
                    policy_variants, DATA_LINK_TYPE, DL_TYPE.keys())

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
        if field == DEST_PORT:
            return int(value)
        elif field == SOURCE_PORT:
            return int(value)
        elif field == TRANSPORT_PROTO:
            return NW_PROTO.get(value, None)
        elif field == DATA_LINK_SRC:
            return EthAddr(value)
        elif field == DATA_LINK_DEST:
            return EthAddr(value)
        elif field == SOURCE_IP:
            return IPAddr(value) if '.' in value else IPAddr6(value)
        elif field == DESTINATION_IP:
            return IPAddr(value) if '.' in value else IPAddr6(value)
        elif field == DATA_LINK_TYPE:
            return DL_TYPE.get(value, None)
        else:
            return None

    def _generate_variants(self, policies, field, values):
        """
        Si una politica no especifica un campo, genera variantes para
        todos los valores posibles (TCP, UDP, ICMP).
        """
        resultado = []
        for pol in policies:
            for val in values:
                nueva = pol.copy()
                nueva[field] = val
                resultado.append(nueva)
        return resultado


def launch():
    '''
    Lanza el firewall al iniciar el controlador
    '''
    core.registerNew(Firewall)
