# TP N2: Software-Defined Networks

## Ejecucion

Para instalar pox:

```
make install-pox
```

Para ejecutar el controlador de pox:

```
make pox
```

Para ejecutar la topologia de mininet:

```
make mininet
```

## Casos de prueba
La topologia que planteamos segun el enunciado es de 3 switches con 2 hosts en cada extremo de la cadena de switches.
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
## Caso de prueba 1: se deben descartar todos los mensajes cuyo puerto destino sea 80.

Podemos probar tanto con

```
mininet> hX curl hY
```

o usando iperf:
```
mininet> hX iperf -s -p 80&
mininet> hY iperf -c hX -p 80
```

Con UDP:

```
mininet> hX iperf -u -s -p 80&
mininet> hY iperf -u -c hX -p 80
```

## Caso de prueba 2: se deben descartar todos los mensajes que provengan del host 1, tengan como puerto destino el 5001, y estén utilizando el protocolo UDP.

```
mininet> hX iperf -u -s -p 5001&
mininet> h1 iperf -u -c hX -p 5001
```

## Caso de prueba 3: se deben elegir dos hosts cualesquiera y los mismos no deben poder comunicarse de ninguna forma.

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

Al reves tampoco podria existir comunicacion:

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

# Para ver las reglas instaladas en los switches

Podés inspeccionar las reglas de flujo (flow table) instaladas en cada switch usando el siguiente comando desde una terminal de Linux:

```
sudo ovs-ofctl dump-flows s1
```