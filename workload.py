import subprocess
import random, time
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from arguments_parser import parser


net = Mininet(controller=RemoteController, switch=OVSSwitch)

def generate_topology(topology_type, topology_parameters):
    if topology_type == 'star':
        num_switches, hub_switch = topology_parameters
        connections = [[] for _ in range(num_switches)]
        for i in range(1, num_switches+1):
            if i != hub_switch:
                connections[i-1].append(hub_switch)
                
        return connections, num_switches
    elif topology_type == 'mesh':
        num_switches = topology_parameters[0]
        return [[j+1 for j in range(num_switches) if j!= i] for i in range(num_switches)], num_switches
    elif topology_type == 'leaf-spine':
        num_leafs, num_spines = topology_parameters
        connections = [[] for _ in range(num_leafs)]
        start = num_leafs
        for i in range(num_leafs):
            for j in range(num_spines):
                connections[i].append(start+j+1)
        return connections, (num_leafs+num_spines)
    elif topology_type == '3-tier':
        num_cores, num_aggs, num_access = topology_parameters
        connections = [[] for i in range(num_cores+num_aggs)]
        # Connect core switches horizontally and to all aggregation switches
        for i in range(num_cores):
            if i+1 < num_cores:
                connections[i].append(i+2)
            for j in range(num_aggs):
                connections[i].append(j+num_cores+1)
                
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
                
        if num_access % 2 == 1:
            connections[start+i].append(num_cores+num_aggs+num_access)
        return connections, (num_cores+num_aggs+num_access)


def start_traffic(clients, servers):
    def on_finished(result, node):
        print(f"{node.name} finished with exit code {result}")
        # Do something else when the command finishes, e.g., stop the simulation
    port = random.randint(3000,8000)
    for srv in servers:
        srv.cmd('nc -lk {} > logserver.txt &'.format(port))
        srv.cmd('tcpdump -w {}.pcap &'.format(srv.name))

    for host in clients:
        server = random.choice(servers)
        cmd = 'sourcesonoff -v -t -d {} --port-number {} --doff-type=weibull --don-min=10 --don-max=1000 --doff-min=1s --doff-max=2s --random-seed {} --turn 3 >> log_{}.txt'.format(server.IP(),port,random.randrange(1000),host.name)
        host.cmd('echo {} > log_{}.txt'.format(time.strftime("%H%M%S.%f")[:-3],host.name))
        host.sendCmd(cmd, printPid=True, callback=lambda result: on_finished(result, host))

    # Wait for the traffic to finish
    for host in clients:
        host.waitOutput()
        host.cmd('echo {} >> log_{}.txt'.format(time.strftime("%H%M%S.%f")[:-3],host.name))



def generate_network(topology, num_switches, client_links, server_links, controller_data):
    switches = []
    for i in range(num_switches):
        switch = net.addSwitch('s{}'.format(i+1), protocols=['OpenFlow13'])
        switches.append(switch)
    
    clients = []
    for i in range(len(client_links)):
        host = net.addHost('cl{}'.format(i+1))
        clients.append(host)
        switch_index, port_number = client_links[i]
        switch = switches[switch_index - 1]
        net.addLink(host, switch, port1=0, port2=port_number)
    
    servers = []
    for i in range(len(server_links)):
        host = net.addHost('srv{}'.format(i+1))
        servers.append(host)
        switch_index, port_number = server_links[i]
        switch = switches[switch_index - 1]
        net.addLink(host, switch, port1=0, port2=port_number)
    additional_links = []
    for i, neighbors in enumerate(topology):
        switch = switches[i]
        for neighbor in neighbors:
            if neighbor <= num_switches:
                neighbor_switch = switches[neighbor - 1]
                net.addLink(switch, neighbor_switch)
                link = net.addLink(neighbor_switch, switch)
                #print(link)
                #link.intf2.config(up=False)  # Set the second interface of the link to down
                interface_name = link.intf2.name  # Get the name of the second interface
                additional_links.append(interface_name)
                subprocess.run(['ifconfig', interface_name, 'down'])  # Set the interface to a down state

    
    c0 = net.addController('c0', controller=RemoteController, ip=controller_data[0], port=controller_data[1])
    
    return clients, servers, additional_links


if __name__ == '__main__':

    input_param = parser('workload')
    print(input_param)
    topology, num_sw = generate_topology(input_param[0],input_param[1])
    client_links = [[1,1],[2,1]]
    server_links = [[3,1],[3,2]]
    cl, srv, additional_links = generate_network(topology, num_sw, client_links, server_links,input_param[2])

    net.start()
    with open('output/link_length.txt','w') as f:
        f.write(f'{len(net.links)-(len(client_links)+len(server_links))}')
    CLI(net)
    #start_traffic(cl, srv)
    #time.sleep(10)

    # num_links_to_bring_up = 3  # Adjust this number as per your requirement
    # intf2_links = random.sample(additional_links, num_links_to_bring_up)
    # for link in intf2_links:
    #     print(link)
    #     subprocess.run(['ifconfig', link, 'up'])
    additional_hosts = []
    num_hosts_to_add = 2  # Number of additional hosts to add
    switches_to_attach = [1, 2]  # List of switches to attach the hosts to
    for i in range(num_hosts_to_add):
        switch_index = random.choice(switches_to_attach)  # Choose a random switch to attach the host
        switch = net.switches[switch_index - 1]
        host = net.addHost(f'h{i}')
        additional_hosts.append(host)
        switch_port = len(switch.ports)  # Find the next available port on the switch
        link = net.addLink(host, switch, port1=0, port2=switch_port)
        interface_name = link.intf1.name  # Get the name of the host's interface connected to the switch
        host.setIP('10.0.0.{}/8'.format(i+len(client_links)+len(server_links)+1), intf=interface_name)  # Assign an IP address to the host
    CLI(net)
    net.stop()
    subprocess.run(['mn', '-c'])