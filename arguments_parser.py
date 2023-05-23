import argparse

def parser(program):
    if program == 'topology-script':
        parser = argparse.ArgumentParser(description='RFC8456 SDN Benchmarking - Topology Discovery - Script.')
        
        parser.add_argument('controller_ip', help='Controller IP address', default='localhost')
        parser.add_argument('controller_port', help='Controller port number',default=6653)
        parser.add_argument('controller_name', help='Controller name')
        parser.add_argument('rest_port', help='REST API port number',default=8181)
        parser.add_argument('target_length', help='Target Topology Length',type=int)
        parser.add_argument('iface', help='Interface to listen',default='lo')
        parser.add_argument('--topology', choices=['3-tier', 'star', 'mesh', 'leaf-spine'], help='Topology type')
        parser.add_argument('--num-cores', type=int, help='Number of core switches (for 3-tier topology)')
        parser.add_argument('--num-aggs', type=int, help='Number of aggregation switches (for 3-tier topology)')
        parser.add_argument('--num-access', type=int, help='Number of access switches (for 3-tier topology)')
        parser.add_argument('--num-switches', type=int, help='Number of switches (for star/mesh topology)')
        parser.add_argument('--hub-switch', type=int, help='Hub switch index (for star topology)')
        parser.add_argument('--num-leafs', type=int, help='Number of leaf switches (for leaf-spine topology)')
        parser.add_argument('--num-spines', type=int, help='Number of spine switches (for leaf-spine topology)')
        args = parser.parse_args()
        return args
    elif program == 'workload':
        parser = argparse.ArgumentParser(description='Workload Generator for SDN-BM experiments')
        parser.add_argument('controller_ip', help='Controller IP address', default='localhost')
        parser.add_argument('controller_port', help='Controller port number',default=6653)
        parser.add_argument('--topology', choices=['3-tier', 'star', 'mesh', 'leaf-spine'], help='Topology type')
        parser.add_argument('--num-cores', type=int, help='Number of core switches (for 3-tier topology)')
        parser.add_argument('--num-aggs', type=int, help='Number of aggregation switches (for 3-tier topology)')
        parser.add_argument('--num-access', type=int, help='Number of access switches (for 3-tier topology)')
        parser.add_argument('--num-switches', type=int, help='Number of switches (for star/mesh topology)')
        parser.add_argument('--hub-switch', type=int, help='Hub switch index (for star topology)')
        parser.add_argument('--num-leafs', type=int, help='Number of leaf switches (for leaf-spine topology)')
        parser.add_argument('--num-spines', type=int, help='Number of spine switches (for leaf-spine topology)')
        args = parser.parse_args()

        topology_type = args.topology
        if topology_type == '3-tier':
            num_cores = args.num_cores
            num_aggs = args.num_aggs
            num_access = args.num_access
            return [topology_type, [num_cores, num_aggs, num_access],[args.controller_ip,args.controller_port]]
        elif topology_type == 'star':
            num_switches = args.num_switches
            hub_switch = args.hub_switch
            return [topology_type, [num_switches, hub_switch],[args.controller_ip,args.controller_port]]
        elif topology_type == 'mesh':
            num_switches = args.num_switches
            return [topology_type, [num_switches],[args.controller_ip,args.controller_port]]
        elif topology_type == 'leaf-spine':
            num_leafs = args.num_leafs
            num_spines = args.num_spines
            return [topology_type, [num_leafs, num_spines],[args.controller_ip,args.controller_port]]
    elif program == 'topology':
        parser = argparse.ArgumentParser(description='RFC8456 SDN Benchmarking - Topology Discovery.')
        
        parser.add_argument('controller_ip', help='Controller IP address', default='localhost')
        parser.add_argument('controller_port', help='Controller port number',default=6653)
        parser.add_argument('controller_name', help='Controller name')
        parser.add_argument('rest_port', help='REST API port number',default=8181)
        parser.add_argument('target_length', help='Target Topology Length',type=int)
        parser.add_argument('iface', help='Interface to listen',default='lo')
        return parser.parse_args()