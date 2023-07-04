import requests

CONTROLLER_IP = 'localhost'
REST_PORT = '8181'

url = f'http://{CONTROLLER_IP}:{REST_PORT}/onos/v1/topology'
headers = {'Accept': 'application/json'}
response = requests.get(url, headers=headers,auth=('onos','rocks'))
response_data = response.json()
topology = response_data['devices']
links = response_data['links']

print(f'Topo = {topology} | Links = {links}')