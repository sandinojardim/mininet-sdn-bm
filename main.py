from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch, RemoteController
from mininet.link import TCLink

def generate_topology(topology_type, topology_parameters):
    if topology_type == 'star':
        num_switches, hub_switch = topology_parameters
        connections = [[] for _ in range(num_switches)]
        for i in range(1, num_switches+1):
            if i != hub_switch:
                connections[i-1].append(hub_switch)
                #connections[hub_switch-1].append(i) #if bidirectional links
        return connections
    elif topology_type == 'mesh':
        num_switches = topology_parameters[0]
        return [[j+1 for j in range(num_switches) if j!= i] for i in range(num_switches)]
    elif topology_type == 'leaf-spine':
        num_leafs, num_spines = topology_parameters
        connections = [[] for _ in range(num_leafs)]
        start = num_leafs
        for i in range(num_leafs):
            for j in range(num_spines):
                connections[i].append(start+j+1)
        return connections
    elif topology_type == '3-tier':
        num_cores, num_aggs, num_access = topology_parameters
        connections = [[] for i in range(num_cores+num_aggs)]
        # Connect core switches horizontally and to all aggregation switches
        for i in range(num_cores):
            if i+1 < num_cores:
                connections[i].append(i+2)
            for j in range(num_aggs):
                connections[i].append(j+num_cores+1)
                #connections[j+num_cores].append(i) #if bidirectional
        # Connect aggregation switches horizontally and to half of the access switches
        start = num_cores
        for i in range(num_aggs):
            if i+1 < num_aggs:
                connections[start+i].append(start+i+2)
            for j in range(num_access//2):
                if (start+i)-num_cores < num_aggs//2:
                    connections[start+i].append(start+num_aggs+j+1)
                else:
                    connections[start+i].append(start+num_aggs+(num_access//2)+j+1)
                #connections[start+j].append(i+num_cores) #if bidirectional
        if num_access % 2 == 1:
            connections[start+i].append(num_cores+num_aggs+num_access)
        return connections

def generate_network(num_hosts, topology, host_links):
    net = Mininet(controller=RemoteController, switch=OVSSwitch)
    
    
    #net.addController('c0', ip='127.0.0.1', port=6633)

    switches = []
    for i in range(len(topology)):
        switch = net.addSwitch('s{}'.format(i+1),protocols='OpenFlow13')
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
    """ for i in range(1,len(topology)+1):
        for j in topology[i-1]:
            net.addLink(f's{i}',f's{j}') """
    
    c0 = net.addController('c0', controller=RemoteController, ip='172.17.0.2', port=6633)
    
    net.start()
    CLI(net)
    
    net.pingAll()
    net.stop()

if __name__ == '__main__':
    topology = generate_topology('3-tier',[1,4,8]) #[[2, 6], [1, 3], [2, 4], [3, 5], [4, 6], [1, 5]]
    host_links = [[1, 1], [6, 1]]
    num_hosts = len(host_links)
    generate_network(num_hosts, topology, host_links)

