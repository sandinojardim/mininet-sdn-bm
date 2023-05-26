import requests
import subprocess, signal
import time, datetime
from arguments_parser import parser
from scapy.all import *
from scapy.contrib.openflow import OFPTPacketIn, OFPTPacketOut

start_time = None
pkt_in_sniff = None
last_time_pkt_in = None
topology_match = False
fail = False

def last_ofpt_packet_in(packet):
    global last_time_pkt_in
    if 'OFPTPacketIn' in packet.summary():
        last_time_pkt_in = time.time()
        #print(last_time_pkt_in)
        if topology_match or fail:
            return True
        else:
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
        return topology
    elif controller == 'floodlight':
        url = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/core/controller/switches/json'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                switches = response.json()
                return len(switches)
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
                    return len(nodes)
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



def is_ofpt_packet_out(packet):
    global start_time
    #print(packet.summary())
    if 'OFPTPacketOut' in packet.summary():
        start_time = time.time()
        #print(packet[TCP].seq,datetime.fromtimestamp(start_time).strftime("%H:%M:%S,%f")[:-3])
        return True
    else:
        return False

def start_pkt_in_sniff():
    global pkt_in_sniff
    pkt_in_sniff = sniff(iface=args.iface, filter=f'tcp and dst port {args.controller_port}', stop_filter=last_ofpt_packet_in)


def stop_pkt_in_sniff():
    global pkt_in_sniff
    if pkt_in_sniff:
        pkt_in_sniff.join(timeout=2)  # Wait for the sniffing thread to finish gracefully


def RFC8456_net_topology_discovery_time(len_topology,controller,ctrl_ip, rest_port):
    global topology_match, fail
    QUERY_INTERVAL = args.query_interval
    pkt_in_sniff_thread = threading.Thread(target=start_pkt_in_sniff)  # Initialize pkt_in_sniff_thread here

    print("Waiting for the first OFPTPacketOut message...")
    sniff(iface=f'{args.iface}',filter=f'tcp and src port {args.controller_port}',stop_filter=is_ofpt_packet_out)
    
    pkt_in_sniff_thread.start()


    #print(' Start sniffing Packet-In messages after the first sniff ends')
    # Query the controller every t=3 seconds to obtain the discovered network topology information
    consecutive_failures = 0
    while True:
        topology = get_topology(controller,ctrl_ip, rest_port)
        #print(' Compare the discovered topology information with the deployed topology information')
        topology_match = compare_topology(topology, len_topology)
        if topology_match:
            #print("MATCH!")
            pkt_in_sniff_thread.join()
            # Record the time for the last discovery message sent to the controller
            end_time = last_time_pkt_in
            break
            #with open('output/last_ofpt_packet_in_'+args.controller_name+'.txt', 'r') as f:
            #    print("Recording last OPFT_PacketIN")
            #    lines = f.readlines()
            #    end_time = float(lines[-1].strip())
            #    print(datetime.fromtimestamp(end_time).strftime("%H:%M:%S,%f")[:-3])
            #    break
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
        topology_discovery_time = calculate_topology_discovery_time(start_time, end_time)
        with open('output/topo_disc_'+controller+'.txt', 'a') as f:
            f.write(f"{topology_discovery_time}\n")

if __name__ == '__main__':

    # Parse the command line arguments
    args = parser('topology')

    with open('output/topo_disc_'+args.controller_name+'.txt', 'w') as f:
        pass

    RFC8456_net_topology_discovery_time(args.target_length,
                                        args.controller_name,
                                        args.controller_ip,
                                        args.rest_port)