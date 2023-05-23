import csv, time, argparse
import subprocess
import os
from email_sender import send_email_with_attachment
from arguments_parser import parser


# Check if the file exists
if not os.path.isfile('output/topology_output.txt'):
    # Create the file
    with open('output/topology_output.txt', 'w') as f:
        pass

def run_topology_discovery(controller_name, controller_ip, controller_port, rest_port, target_length, iface):
    cmd = ['python3', 'application-plane/topology.py', controller_ip, controller_port, controller_name, rest_port, str(target_length),iface]
    return subprocess.Popen(cmd,stdout=subprocess.PIPE)

def run_workload_simulation(topology_type, topology_parameters):
    if topology_type == 'leaf-spine':
        cmd = ['python3', 'workload.py','--topology',topology_type, '--num-leafs', f'{topology_parameters[0]}', '--num-spines', f'{topology_parameters[1]}']
        return subprocess.Popen(cmd,stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def write_to_csv(filename, data):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['num_nodes', 'avg_tdt'])
        writer.writerows(data)

if __name__ == '__main__':
    args = parser('topology-script')
    
    data = []
    running = True
    while running:
        tdt_sum = 0
        i = 10
        target_length = i + (i * 2)
        print('Running for topo_lenght = {}'.format(target_length))
        for j in range(1, 11):
            print('running topology.py')
            topology_proc = run_topology_discovery(args.controller_name,args.controller_ip,args.controller_port,args.rest_port,(i + i * 2),args.iface)
            time.sleep(5)
            print('running workload.py')
            run_simulation_proc = run_workload_simulation(args.topology, [i, i * 2])

            # Wait for topology.py to finish execution
            topology_proc.wait()  # Wait for topology.py to finish
            print('finished topology.py')
            # Send EOF to the run_simulation subprocess
            #run_simulation_proc.stdin.write(b'\x04')  # Send CTRL-D / EOF
            run_simulation_proc.stdin.flush()
            run_simulation_proc.communicate()  # Wait for run_simulation to finish and capture output


            # Wait for the subprocess to finish
            run_simulation_proc.wait()
            print('finished workload.py')

            # Read the last line of the output file generated by topology.py
            with open('output/topo_disc_'+args.controller_name+'.txt', 'r') as f:
                lines = f.readlines()
                topology_discovery_time = float(lines[-1].strip())
                if topology_discovery_time > 0.0:
                    tdt_sum += topology_discovery_time
                else:
                    running = False

            # Append the topology discovery time to the topology_output.txt file
            #with open('topology_output.txt', 'a') as f:
            #    f.write(f"{topology_discovery_time}\n")

        avg_tdt = tdt_sum / 10
        data.append([target_length, avg_tdt])
        i = i*2

    write_to_csv('output/'+args.controller_name+'_average_topology_discovery_time.csv', data)
    send_email_with_attachment(f'({args.controller_name}) Task completed', 'Experiment finished successfully', 'output/'+args.controller_name+'_average_topology_discovery_time.csv')

