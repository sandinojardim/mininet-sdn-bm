import requests
import time
from arguments_parser import parser
from global_variables import *
from scapy.all import *
from scapy.contrib.openflow3 import OFPTPacketIn, OFPTPacketOut, OpenFlow3
from scapy.contrib.lldp import LLDPDU




def get_target_link():
    with open('output/link_length.txt','r') as f:
        lines = f.readlines()
        value = int(lines[-1].strip())
    return value

def is_ofpt_packet_out(packet):
    global start_time, total_packets, total_lldp, count_packets, count_lldp
    total_packets += len(packet)
    count_packets += 1
    if 'OFPTPacketOut' in packet.summary():
        start_time = time.time()
        controller_monitor.start() #starts cpu/mem monitoring
        if(packet.getlayer(LLDPDU)):
            total_lldp += len(packet)
            count_lldp +=1
        return True
    else:
        return False

def last_ofpt_packet_in(packet):
    global last_time_pkt_in, total_packets, total_lldp, count_packets, count_lldp
    total_packets += len(packet)
    count_packets += 1
    if topology_match or fail:
        controller_monitor.stop() #stop cpu/mem monitoring
        return True
    else:
        if 'OFPTPacketIn' in packet.summary():
            last_time_pkt_in = time.time()
            if(packet.getlayer(LLDPDU)):
                total_lldp += len(packet)
                count_lldp +=1
        return False


def get_link_size(controller,CONTROLLER_IP, REST_PORT):
    if controller == 'onos':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/topology'
        headers = {'Accept': 'application/json'}
        response = requests.get(url, headers=headers,auth=('onos','rocks'))
        response_data = response.json()
        links = response_data['links']
        return links
    elif controller == 'floodlight':
        url2 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/topology/links/json'
        try:
            response2 = requests.get(url2)
            if response2.status_code == 200:
                links = response2.json()
                return len(links)*2
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
    elif controller == 'odl':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/restconf/operational/opendaylight-inventory:nodes'
        headers = {
            'Accept': 'application/json',
        }
        auth = ('admin', 'admin')
        try:
            response = requests.get(url,headers=headers,auth=auth)
            if response.status_code == 200:
                data = response.json()
                if 'node' in data['nodes']:
                    nodes = data['nodes']['node']
                    links = sum(len(node.get('node-connector', [])) for node in nodes)
                    return (links-len(nodes))/2 #odl adds one local link for each sw
                else:
                    return 0
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

def get_host_size(controller,CONTROLLER_IP, REST_PORT):
    if controller == 'onos':
        url2 = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/hosts'
        headers = {'Accept': 'application/json'}
        response2 = requests.get(url2, headers=headers,auth=('onos','rocks'))
        host_Data = response2.json()
        hosts = len(host_Data['hosts'])
        return hosts
    elif controller == 'floodlight':
        url3 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/device/'
        try:
            response3 = requests.get(url3)
            if response3.status_code == 200:
                hosts = response3.json()
                host_count = sum(1 for h in hosts['devices'] if len(h['attachmentPoint']) == 1)
                return host_count
            else:
                print(f"Error: {response3.status_code} - {response3.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
    elif controller == 'odl':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/restconf/operational/opendaylight-inventory:nodes'
        headers = {
            'Accept': 'application/json',
        }
        auth = ('admin', 'admin')
        try:
            response = requests.get(url,headers=headers,auth=auth)
            if response.status_code == 200:
                data = response.json()
                if 'node' in data['nodes']:
                    nodes = data['nodes']['node']
                    links = sum(len(node.get('node-connector', [])) for node in nodes)
                    return (links-len(nodes))#odl adds one local link for each sw
                else:
                    return 0
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")


def compare_topology(topology, len_topology):
    # Check if the topology matches the deployed topology
    if topology == len_topology:
        return True
    else:
        return False

def calculate_topology_discovery_time(start_time, end_time):
    topology_discovery_time = end_time - start_time
    return topology_discovery_time


def start_pkt_in_sniff():
    global pkt_in_sniff
    pkt_in_sniff = sniff(iface=args.iface, filter=f'tcp and dst port {args.controller_port}', stop_filter=last_ofpt_packet_in)


def stop_pkt_in_sniff():
    global pkt_in_sniff
    if pkt_in_sniff:
        pkt_in_sniff.join(timeout=2)  # Wait for the sniffing thread to finish gracefully


def RFC8456_net_topology_discovery_time(len_topology,controller,ctrl_ip, rest_port):
    global topology_match, fail, target_links, end_time, total_packets, count_lldp
    QUERY_INTERVAL = args.query_interval
    pkt_in_sniff_thread = threading.Thread(target=start_pkt_in_sniff)  # Initialize pkt_in_sniff_thread here

    print("Waiting for the first OFPTPacketOut message...")
    sniff(iface=f'{args.iface}',filter=f'tcp and src port {args.controller_port}',stop_filter=is_ofpt_packet_out)
    
    pkt_in_sniff_thread.start()


    #print(' Start sniffing Packet-In messages after the first sniff ends')
    # Query the controller every t=3 seconds to obtain the discovered network topology information
    consecutive_failures, consec_link_failures = 0,0
    while True:
        topology, links = get_topology(controller,ctrl_ip, rest_port)
        print(topology,links)
        if compare_topology(topology, len_topology):
            if end_time == None:
                # Record the time for the last discovery message sent to the controller
                end_time = last_time_pkt_in
            if args.no_links:
                topology_match = True
                pkt_in_sniff_thread.join()
                end_time_links = 0
                break
            else:
                if target_links == None:
                    target_links = get_target_link()
                if links == (target_links*2):
                    topology_match = True
                    pkt_in_sniff_thread.join()
                    end_time_links = last_time_pkt_in
                    break
                else:
                    consec_link_failures +=1
                    if consec_link_failures >= args.consec_link_failures:
                        topology_match = False
                        with open('output/topo_disc_'+controller+'.txt', 'a') as f:
                            f.write(f"{args.consec_failures * args.query_interval},{args.consec_failures * args.query_interval},{total_lldp},{count_lldp},{total_packets},{count_packets}\n")
                        break
        else:
            consecutive_failures += 1
            if consecutive_failures >= args.consec_failures:
                fail = True
                with open('output/topo_disc_'+controller+'.txt', 'a') as f:
                    f.write(f"{args.consec_failures * args.query_interval},{args.consec_failures * args.query_interval},{total_lldp},{count_lldp},{total_packets},{count_packets}\n")
                break

        time.sleep(QUERY_INTERVAL)

    # Calculate the topology discovery time
    if topology_match:
        # Collect the measurements from each controller monitor
        cpu_usage = controller_monitor.cpu_usage
        memory_usage = controller_monitor.memory_usage

        # Calculate average CPU and memory usage for each controller
        avg_cpu = sum(cpu_usage) / len(cpu_usage)
        avg_memory = sum(memory_usage) / len(memory_usage)
        print('CPU: ',cpu_usage)
        print('Memory: ',memory_usage)
        print('Avg_CPU: ',avg_cpu)
        print('Avg_Memory: ',avg_memory)
        print('total packets: ',total_packets)
        topology_discovery_time = calculate_topology_discovery_time(start_time, end_time)
        with open('output/topo_disc_'+controller+'.txt', 'a') as f:
            if args.no_links:
                f.write(f"{topology_discovery_time},{topology_discovery_time},{total_lldp},{count_lldp},{total_packets},{count_packets}\n")
            else:
                f.write(f"{topology_discovery_time},{end_time_links-start_time},{total_lldp},{count_lldp},{total_packets},{count_packets}\n")

if __name__ == '__main__':

    # Parse the command line arguments
    args = parser('topology')

    with open('output/topo_disc_'+args.controller_name+'.txt', 'w') as f:
        pass

    RFC8456_net_topology_discovery_time(args.target_length,
                                        args.controller_name,
                                        args.controller_ip,
                                        args.rest_port)