import requests
import subprocess, signal
import time, datetime
from arguments_parser import parser
from global_variables import *
from scapy.all import *
from scapy.contrib.openflow import OFPTPacketIn, OFPTPacketOut


def get_target_link():
    with open('output/link_length.txt','r') as f:
        lines = f.readlines()
        value = int(lines[-1].strip())
    return value

def is_ofpt_packet_out(packet):
    global start_time, total_packets
    total_packets += 1
    if 'OFPTPacketOut' in packet.summary():
        start_time = time.time()
        #print(packet[TCP].seq,datetime.fromtimestamp(start_time).strftime("%H:%M:%S,%f")[:-3])
        return True
    else:
        return False

def last_ofpt_packet_in(packet):
    global last_time_pkt_in, total_packets
    total_packets += 1
    if topology_match or fail:
        return True
    else:
        if 'OFPTPacketIn' in packet.summary():
            last_time_pkt_in = time.time()
        return False
    #with open('output/last_ofpt_packet_in_'+args.controller_name+'.txt', 'a') as f:
    #    f.write(f"{last_time_pkt_in}\n")

def run_ofpt_packet_in_record(controller_name, controller_port, iface):
    cmd = ['python3', 'ofpt_packetin_record.py', iface, controller_name, controller_port]
    print(cmd)
    return subprocess.Popen(cmd,stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def get_topology(controller,CONTROLLER_IP, REST_PORT):
    if controller == 'onos':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/topology'
        headers = {'Accept': 'application/json'}
        response = requests.get(url, headers=headers,auth=('onos','rocks'))
        response_data = response.json()
        #print(response_data)
        # Extract the topology information from the response
        topology = response_data['devices']
        links = response_data['links']
        return topology, links
    elif controller == 'floodlight':
        url1 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/core/controller/switches/json'
        url2 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/core/controller/links/json'
        try:
            response1 = requests.get(url1)
            response2 = requests.get(url2)
            if response1.status_code == 200:
                switches = response1.json()
                links = response2.json()
                return len(switches), len(links)
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
                    return len(nodes), (links-len(nodes))#odl adds one local link for each sw
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
    global topology_match, fail, target_links, end_time, total_packets
    QUERY_INTERVAL = args.query_interval
    pkt_in_sniff_thread = threading.Thread(target=start_pkt_in_sniff)  # Initialize pkt_in_sniff_thread here

    print("Waiting for the first OFPTPacketOut message...")
    sniff(iface=f'{args.iface}',filter=f'tcp and src port {args.controller_port}',stop_filter=is_ofpt_packet_out)
    
    pkt_in_sniff_thread.start()


    #print(' Start sniffing Packet-In messages after the first sniff ends')
    # Query the controller every t=3 seconds to obtain the discovered network topology information
    consecutive_failures = 0
    while True:
        topology, links = get_topology(controller,ctrl_ip, rest_port)
        print(topology,links)
        #print(' Compare the discovered topology information with the deployed topology information')
        if compare_topology(topology, len_topology):
            if end_time == None:
                # Record the time for the last discovery message sent to the controller
                end_time = last_time_pkt_in
            if target_links == None:
                target_links = get_target_link()
            if links == (target_links*2):
                topology_match = True
                pkt_in_sniff_thread.join()
                end_time_links = last_time_pkt_in
                break
            else:
                topology_match = False
        else:
            consecutive_failures += 1
            if consecutive_failures >= args.consec_failures:
                fail = True
                with open('output/topo_disc_'+controller+'.txt', 'a') as f:
                    f.write("-1.0\n") #flag for script stop
                break

        time.sleep(QUERY_INTERVAL)

    # Calculate the topology discovery time
    if topology_match:
        print('total packets: ',total_packets)
        topology_discovery_time = calculate_topology_discovery_time(start_time, end_time)
        with open('output/topo_disc_'+controller+'.txt', 'a') as f:
            f.write(f"{topology_discovery_time},{end_time_links-start_time}\n")

if __name__ == '__main__':

    # Parse the command line arguments
    args = parser('topology')

    with open('output/topo_disc_'+args.controller_name+'.txt', 'w') as f:
        pass

    RFC8456_net_topology_discovery_time(args.target_length,
                                        args.controller_name,
                                        args.controller_ip,
                                        args.rest_port)