import requests

CONTROLLER_IP = '10.3.3.106'
REST_PORT = '8181'

url = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/topology'
headers = {'Accept': 'application/json'}
response = requests.get(url, headers=headers,auth=('onos','rocks'))
response_data = response.json()
topology = response_data['devices']
links = response_data['links']
hosts = response_data['hosts']

print(f'Topo = {topology} | Links = {links} | Hosts = {hosts}')