from ControllerMonitor import *

start_time = None
end_time = None
pkt_in_sniff = None
last_time_pkt_in = None
topology_match = False
fail = False
target_links = None
total_packets = 0
count_packets = 0
total_lldp = 0
count_lldp = 0

controller_monitor = ControllerMonitor('java','10.3.3.106', 'admin', 'b1vbx11')
