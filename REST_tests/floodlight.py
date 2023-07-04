import requests

CONTROLLER_IP = '10.3.3.106'
REST_PORT = '8081'

url1 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/core/controller/switches/json'
url2 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/topology/links/json'
url3 = f'http://{CONTROLLER_IP}:{REST_PORT}/wm/topology/device/json'
try:
    response1 = requests.get(url1)
    response2 = requests.get(url2)
    response3 = requests.get(url3)
    if response1.status_code == 200:
        switches = response1.json()
        links = response2.json()
        hosts = response3.json()
        print(hosts)
        print(f'Topo = {len(switches)} | Links = {len(links)*2} | Hosts = {len(hosts)}')
    else:
        print(f"Error: {response1.status_code} - {response1.text}")
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")