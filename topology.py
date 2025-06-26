from mininet.topo import Topo

CANTIDAD_HOSTS = 4


class MyTopo(Topo):
    def __init__(self, _switches=3):
        Topo.__init__(self)

        _switches = _switches if _switches > 0 else 1
        
        # crear hosts h1 h2 h3 h4
        hosts = [self.addHost(f'h{i}', mac=f"00:00:00:00:00:{i}")
                 for i in range(1, CANTIDAD_HOSTS + 1)]        
        
        # se hacen N switches
        switches = [self.addSwitch(
            f's{i}', failMode='standalone') for i in range(1, _switches + 1)]
        
        # conectar s1-h1, s1-h2
        self.addLink(hosts[0], switches[0])
        self.addLink(hosts[1], switches[0])
        
        # conectar sN-h3, sN-h4
        self.addLink(hosts[2], switches[-1])
        self.addLink(hosts[3], switches[-1])

        # conectar switches en linea recta
        [
            self.addLink(switches[i], switches[i + 1])
            for i in range(len(switches) - 1)
        ]


topos = {'customTopo': (lambda switches: MyTopo(_switches=switches))}
