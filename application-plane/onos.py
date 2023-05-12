import requests
import time
from scapy.all import *
from scapy.layers.l2 import Ether
from scapy.layers.inet import TCP, ICMP
from scapy.contrib.openflow import OFPTFeaturesRequest, OFPTFeaturesReply, OFPTPacketIn



CONTROLLER_IP = 'localhost'
CONTROLLER_MAC = '02:42:ac:11:00:02'
REST_PORT = '8181'
QUERY_INTERVAL = 3

def get_topology():
    url = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/topology'
    headers = {'Accept': 'application/json'}
    response = requests.get(url, headers=headers,auth=('onos','rocks'))
    response_data = response.json()
    print(response_data)
    # Extract the topology information from the response
    topology = response_data['devices']
    return topology

def compare_topology(topology, len_topology):
    # Check if the topology matches the deployed topology
    if topology == len_topology:
        return True
    else:
        return False

def calculate_topology_discovery_time(start_time, end_time):
    topology_discovery_time = end_time - start_time
    return topology_discovery_time

# Record the time for the first LLDP packet received at the controller
start_time = None

def is_ofpt_features_reply(packet):
    global start_time
    while packet.payload:
        x = packet.payload
        if 'OFPTFeaturesReply' in x.summary():
            start_time = time.time()
            return True
        packet = x
    return False


def RFC8456_net_topology_discovery_time(len_topology):
    # Record the time for the first discovery message received at the controller
    print("Waiting for the first LLDP packet...")
    #print(f"ether dst {CONTROLLER_IP}")
    res = sniff(iface='docker0',filter='tcp and dst port 6633',stop_filter=is_ofpt_features_reply)
    #res.summary()

    # Query the controller every t=3 seconds to obtain the discovered network topology information
    consecutive_failures = 0
    while True:
        topology = get_topology()

        # Compare the discovered topology information with the deployed topology information
        topology_match = compare_topology(topology, len_topology)
        if topology_match:
            # Record the time for the last discovery message sent to the controller
            end_time = time.time()
            print(f'End time: {end_time}')
            break
        else:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print('Topology discovery failed')
                break

        time.sleep(QUERY_INTERVAL)

    # Calculate the topology discovery time
    if topology_match:
        topology_discovery_time = calculate_topology_discovery_time(start_time, end_time)
        print(f'Topology discovery time: {topology_discovery_time} seconds')

if __name__ == '__main__':
    RFC8456_net_topology_discovery_time(9)