from mininet.topo import Topo

MAX_HOSTS = 4


class MyTopo(Topo):
    def __init__(self, _switches=3):
        # Initialize topology
        Topo.__init__(self)

        _switches = _switches if _switches > 0 else 1

        # --- ETAPA 1: Declarar hosts ---
        # Se crean 4 hosts con MACs fijas
        hosts = [self.addHost(f'h{i}', mac=f"00:00:00:00:00:{i}")
                 for i in range(1, MAX_HOSTS + 1)]
        
        # --- ETAPA 2: Declarar switches ---
        # Se crea una cantidad variable de switches conectados en cadena
        switches = [self.addSwitch(
            f's{i}', failMode='standalone') for i in range(1, _switches + 1)]

        # --- ETAPA 3: Conectar hosts y switches ---
        # Conectar h1 y h2 al primer switch
        self.addLink(hosts[0], switches[0])
        self.addLink(hosts[1], switches[0])
        # Conectar h3 y h4 al último switch
        self.addLink(hosts[2], switches[-1])
        self.addLink(hosts[3], switches[-1])

        # Conectar los switches en cadena (lineales)
        [
            self.addLink(switches[i], switches[i + 1])
            for i in range(len(switches) - 1)
        ]

        """
        h1             h3
         \             /
          s1--s2--...--sn
         /             \  
        h2             h4
        """


topos = {'customTopo': (lambda switches: MyTopo(_switches=switches))}
