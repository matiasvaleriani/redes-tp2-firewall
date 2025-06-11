from mininet.topo import Topo

MAX_HOSTS = 4


class MyTopo(Topo):
    def __init__(self, _switches=3):
        # Initialize topology
        Topo.__init__(self)

        _switches = _switches if _switches > 0 else 1

        hosts = [self.addHost(f'h{i}', mac=f"00:00:00:00:00:{i}")
                 for i in range(1, MAX_HOSTS + 1)]
        switches = [self.addSwitch(
            f's{i}', failMode='standalone') for i in range(1, _switches + 1)]

        self.addLink(hosts[0], switches[0])
        self.addLink(hosts[1], switches[0])
        self.addLink(hosts[2], switches[-1])
        self.addLink(hosts[3], switches[-1])

        [
            self.addLink(switches[i], switches[i + 1])
            for i in range(len(switches) - 1)
        ]


topos = {'customTopo': (lambda switches: MyTopo(_switches=switches))}
