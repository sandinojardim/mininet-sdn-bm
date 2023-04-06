from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch

def mininet_topo():
    # create a Mininet network
    net = Mininet(controller=RemoteController, switch=OVSSwitch)

    # add switches
    s1 = net.addSwitch('s1', protocols='OpenFlow10')

    # add hosts
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    h3 = net.addHost('h3')

    # add links
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)

    # add remote controller
    c0 = net.addController('c0', controller=RemoteController, ip='172.17.0.2', port=6633)

    # start the network
    net.start()

    # run the CLI
    CLI(net)

    net.pingAll()

    # stop the network
    net.stop()

if __name__ == '__main__':
    # set log level
    setLogLevel('info')

    # create Mininet topology
    mininet_topo()
