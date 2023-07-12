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
            response = requests.get(url, headers=headers, auth=auth)
            if response.status_code == 200:
                data = response.json()
                if 'node' in data['nodes']:
                    nodes = data['nodes']['node']
                    link_count = 0
                    host_count = 0
                    for node in nodes:
                        node_connectors = node.get('node-connector', [])
                        for connector in node_connectors:
                            state = connector.get('flow-node-inventory:state', {})
                            link_down = state.get('link-down', False)
                            if not link_down:
                                link_count += 1
                        if node_connectors and node.get('node-type') == 'OF':
                            host_count += 1
                    return link_count #odl adds one local link for each sw
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