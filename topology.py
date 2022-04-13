#!/usr/bin/env python
import argparse

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.node import Host
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def myNetwork(mac):

    net = Mininet( topo=None,
                   build=False,
                   ipBase='10.0.0.0/8',
                   autoSetMacs=mac) # setting autoSetMacs value according to the provided command line argument

    info( '*** Adding controller\n' )
    c0=net.addController(name='c0',
                      controller=RemoteController,
                      protocol='tcp',
                      ip='127.0.0.1',
                      port=6653)

    info( '*** Add switches\n')
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch)
#    s2 = net.addSwitch('s2', cls=OVSKernelSwitch)
#    s3 = net.addSwitch('s3', cls=OVSKernelSwitch)
#    s4 = net.addSwitch('s4', cls=OVSKernelSwitch)
#    s5 = net.addSwitch('s5', cls=OVSKernelSwitch)
#    s6 = net.addSwitch('s6', cls=OVSKernelSwitch)

    info( '*** Add hosts\n')
    h1 = net.addHost('h1', cls=Host, ip='10.0.0.1', defaultRoute=None)
    h2 = net.addHost('h2', cls=Host, ip='10.0.0.2', defaultRoute=None)
    h3 = net.addHost('h3', cls=Host, ip='10.0.0.3', defaultRoute=None)
    h4 = net.addHost('h4', cls=Host, ip='10.0.0.4', defaultRoute=None)
    h5 = net.addHost('h5', cls=Host, ip='10.0.0.5', defaultRoute=None)
    h6 = net.addHost('h6', cls=Host, ip='10.0.0.6', defaultRoute=None)
#    h7 = net.addHost('h7', cls=Host, ip='10.0.0.7', defaultRoute=None)
#    h8 = net.addHost('h8', cls=Host, ip='10.0.0.8', defaultRoute=None)

    info( '*** Add links\n')
#    net.addLink(s1, s2)
#    net.addLink(s1, s3)
#    net.addLink(s1, s4)
#    net.addLink(s2, s5)
#    net.addLink(s2, s6)
    net.addLink(s1, h1)
    net.addLink(s1, h2)
    net.addLink(s1, h3)
    net.addLink(s1, h4)
    net.addLink(s1, h5)
    net.addLink(s1, h6)
#    net.addLink(s6, h7)
#    net.addLink(s6, h8)

    info( '*** Starting network\n')
    net.build()
    info( '*** Starting controllers\n')
    for controller in net.controllers:
        controller.start()

    info( '*** Starting switches\n')
    net.get('s1').start([c0])
#    net.get('s2').start([c0])
#    net.get('s3').start([c0])
#    net.get('s4').start([c0])
#    net.get('s5').start([c0])
#    net.get('s6').start([c0])

    info( '*** Post configure switches and hosts\n')

    CLI(net)
    net.stop()

if __name__ == '__main__':

    # parser for command line arguments
    parser = argparse.ArgumentParser(description='Mid Level API to create custom topology')
    parser.add_argument('--mac', action='store_true') # setting mac to True
    parser.set_defaults(mac=False) # default value for mac is False
    args = parser.parse_args() # parsing the arguments

    # creating the custom topology
    setLogLevel('info')
    myNetwork(args.mac) # calling the function with command line arguments
