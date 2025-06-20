# redes-2025-1c-tp2

# POX Firewall

## Requisitos

-   Python 3.11
-   Mininet
-   Make (opcional)

## Ejecucion

Para ejecutar el controlador de pox

```
make run-pox

// o equivalente

python3 ./pox.py forwarding.l2_learning firewall
```

Para ejecutar la topologia de mininet

```
make mininet

// o equivalente

sudo mn -c  # Clean up first
sudo mn --custom ./topology.py --topo customTopo,switches=${NSWITCHES} --arp --switch ovsk --controller remote
```

## Casos de prueba

```
        h1           h3
         \          /
          s1--s2--s3
         /          \  
        h2           h4
```

### Pingall

```
mininet> pingall
```

## Se deben descartar todos los mensajes cuyo puerto destino sea 80.
### Primera regla

Podemos probar tanto con

```
mininet> hX curl hY

// o tambien

mininet> hX iperf -s -p 80&
mininet> hY iperf -c hX -p 80
```

### Segunda regla

```
mininet> hX iperf -u -s -p 80&
mininet> hY iperf -u -c hX -p 80
```

## Se deben descartar todos los mensajes que provengan del host 1, tengan como puerto destino el 5001, y estén utilizando el protocolo UDP.
### Tercera regla

```
mininet> hX iperf -u -s -p 5001&
mininet> h1 iperf -u -c hX -p 5001
```

## Se deben elegir dos hosts cualesquiera y los mismos no deben poder comunicarse de ninguna forma.
### Cuarta regla

h2 y h3 no deberian poder comunicarse por lo cual podemos probar con

```
// en UDP

mininet> h3 iperf -u -s -p 42069&
mininet> h2 iperf -u -c h3 -p 42069

// o en TCP

mininet> h3 iperf -u -s -p 42069&
mininet> h2 iperf -u -c h3 -p 42069

// o con ping

mininet> h2 ping h3
```

### Quinta regla

h2 y h3 no deberian poder comunicarse por lo cual podemos probar con

```
// en UDP

mininet> h2 iperf -u -s -p 42069&
mininet> h3 iperf -u -c h2 -p 42069

// o en TCP

mininet> h2 iperf -u -s -p 42069&
mininet> h3 iperf -u -c h2 -p 42069

// o con ping

mininet> h3 ping h2
```
