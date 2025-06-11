NSWITCHES := 3

install-pox:
	git clone http://github.com/noxrepo/pox && cd pox && git checkout origin/ichthyosaur

mininet:
	sudo mn -c  # Clean up first
	sudo mn --custom ./topology.py --topo customTopo,switches=${NSWITCHES} --arp --switch ovsk --controller remote

run-pox:
	python3 ./pox.py forwarding.l2_learning firewall


.PHONY: install-pox mininet run-pox
