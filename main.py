from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch, RemoteController
from mininet.link import TCLink

def generate_network(num_hosts, topology, host_links):
    net = Mininet(controller=RemoteController, switch=OVSSwitch, link=TCLink)
    net.addController('c0', ip='127.0.0.1', port=6633)

    switches = []
    for i in range(len(topology)):
        switch = net.addSwitch('s{}'.format(i+1))
        switches.append(switch)

    for i in range(num_hosts):
        host = net.addHost('h{}'.format(i+1))
        switch_index, port_number = host_links[i]
        switch = switches[switch_index - 1]
        net.addLink(host, switch, port1=0, port2=port_number)

    for i, neighbors in enumerate(topology):
        switch = switches[i]
        for neighbor in neighbors:
            if neighbor <= len(topology):
                neighbor_switch = switches[neighbor - 1]
                net.addLink(switch, neighbor_switch)

    net.start()
    net.pingAll()
    net.stop()

if __name__ == '__main__':
    num_hosts = 4
    topology = [[2], [1, 3], [2], [2]]
    host_links = [[2, 1], [1,1], [3,1], [4, 1]]
    generate_network(num_hosts, topology, host_links)

