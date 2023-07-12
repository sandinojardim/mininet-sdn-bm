import subprocess
import random, time
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from arguments_parser import parser
from setup_dhcp import setup
from mininet.node import Host
from host_links_onoff import get_host_size, get_link_size, get_target_link



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
                if args.links:
                    link = net.addLink(neighbor_switch, switch)
                    #print(link)
                    #link.intf2.config(up=False)  # Set the second interface of the link to down
                    interface_name = link.intf2.name  # Get the name of the second interface
                    additional_links.append(interface_name)
                    subprocess.run(['ifconfig', interface_name, 'down'])  # Set the interface to a down state

    
    c0 = net.addController('c0', controller=RemoteController, ip=controller_data[0], port=controller_data[1])
    
    return clients, servers, switches, additional_links


if __name__ == '__main__':

    input_param, args = parser('workload')
    print(input_param)
    topology, num_sw = generate_topology(input_param[0],input_param[1])
    client_links = []
    server_links = []
    cl, srv, sw, additional_links = generate_network(topology, num_sw, client_links, server_links,input_param[2])

    net.start()

    with open('output/link_length.txt','w') as f:
        f.write(f'{len(net.links)-(len(client_links)+len(server_links))}')
    
    if not args.links and not args.hosts:
        CLI(net)
    
    #start_traffic(cl, srv)
    #time.sleep(10)

    if args.links:
        sum_times_on, sum_times_off = 0,0
        for i in range(0,10):
            start_time = time.time()
            num_links_to_bring_up = args.links_to_add  # Adjust this number as per your requirement
            existent_links = get_target_link()
            intf2_links = random.sample(additional_links, num_links_to_bring_up)
            for link in intf2_links:
                subprocess.run(['ifconfig', link, 'up'])
                
            while get_link_size(args.controller_name,args.controller_ip, args.rest_port) != existent_links+(num_links_to_bring_up*2):
                continue
            end_time = time.time()
            sum_times_on += (end_time - start_time)
        
            print(f'link on time_{i} = {end_time - start_time}')

            start_time = time.time()
            for link in intf2_links:
                subprocess.run(['ifconfig', link, 'down'])
            while get_link_size(args.controller_name,args.controller_ip, args.rest_port) != existent_links:
                continue
            end_time = time.time()
            sum_times_off += (end_time - start_time)
            print(f'link off time_{i} = {end_time - start_time}')
            time.sleep(random.randint(1,10))
        print(f'link on avg time = {sum_times_on/10}')
        print(f'link off  avgtime = {sum_times_off/10}')
        #CLI(net)
        

    if args.hosts:
        for i in range(0,10):
            additional_hosts = []
            num_hosts_to_add = args.hosts_to_add  # Number of additional hosts to add
            switches_to_attach = [1,2,3,4,5,6]  # List of switches to attach the hosts to
            attached_hosts = []  # List to store the attached host tuples (switch, port)
            sum_times_on, sum_times_off = 0,0
            tuples = []
            for j in range(num_hosts_to_add):
                switch_index = random.choice(switches_to_attach)  # Choose a random switch to attach the host
                switch = net.switches[switch_index - 1]
                host = net.addHost(f'h{j}')
                additional_hosts.append(host)
                switch_port = len(switch.ports)  # Find the next available port on the switch
                link = net.addLink(host, switch, port1=0, port2=switch_port)
                interface_name = link.intf1.name  # Get the name of the host's interface connected to the switch
                switch.attach(f's{switch_index}-eth{switch_port}')
                attached_hosts.append((switch_index, switch_port))  # Store the switch and port tuple
                if j == 0:
                    start_time = time.time()
                tuples.append([switch_index,switch_port]) # this is only for floodlight
                
            
            setup(args.controller_name,args.controller_ip,args.rest_port,tuples)
            for host in additional_hosts:
                host.cmd('dhclient &')    
            while get_host_size(args.controller_name,args.controller_ip, args.rest_port) != num_hosts_to_add:
                continue
            end_time = time.time()
            sum_times_on += (end_time - start_time)
            print(f'host on time_{i} = {end_time - start_time}')

            start_time = time.time()
            for switch_index, switch_port in attached_hosts:
                switch = net.switches[switch_index - 1]
                switch.detach(f's{switch_index}-eth{switch_port}')
            while get_host_size(args.controller_name,args.controller_ip, args.rest_port) != 0:
                continue
            end_time = time.time()
            sum_times_off += (end_time - start_time)
            print(f'host off time_{i} = {end_time - start_time}')
            time.sleep(random.randint(1,10))
        print(f'link on avg time = {sum_times_on/10}')
        print(f'link off  avgtime = {sum_times_off/10}')
        #CLI(net)    
    
    net.stop()
    subprocess.run(['mn', '-c'])