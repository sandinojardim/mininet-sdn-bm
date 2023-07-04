import requests

CONTROLLER_IP = 'localhost'
REST_PORT = '8181'

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
            print(f'Links = {len(nodes)} | {(links-len(nodes))}')#odl adds one local link for each sw
        else:
            print('nothing')
    else:
        print(f"Error: {response.status_code} - {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")