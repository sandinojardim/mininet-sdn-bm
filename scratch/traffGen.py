#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Host, RemoteController
from mininet.link import TCLink
from mininet.cli import CLI

def run_sourcesonoff():
    h1, h2 = net.get('h1', 'h2')

    # configure h1 as the transmitter and h2 as the receiver
    tx_host, rx_host = h1.IP(), h2.IP()

    # create the sourcesonoff command
    cmd_cpt = 'tcpdump -i eth0 -w capture.pcap'

    h2.cmd(cmd_cpt)

    cmd = 'sourcesonoff --verbose --transmitter-udp -d {} --don-type=constant --don-max=61 --doff-type=constant --doff-max=312us'.format(rx_host)

    # start the sourcesonoff command on the transmitter host
    h1.cmd(cmd)

if __name__ == '__main__':
    net = Mininet(topo=None, link=TCLink, controller=RemoteController)

    # create two hosts
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')

    # create a link with 100Mbps and 10ms of delay
    net.addLink(h1, h2, bw=100, delay='10ms')

    # start the network
    net.start()

    # run sourcesonoff
    run_sourcesonoff()

    # start the CLI to interact with the network
    CLI(net)

    # stop the network
    net.stop()
