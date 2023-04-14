import matplotlib.pyplot as plt
from scapy.all import rdpcap

# Load the pcap file
packets = rdpcap("./h2.pcap")

# Extract the timestamp and packet size from each packet
timestamps = []
sizes = []
for packet in packets:
    timestamps.append(packet.time)
    sizes.append(len(packet))

# Calculate the time elapsed between packets
times = [timestamps[i+1]-timestamps[i] for i in range(len(timestamps)-1)]

# Calculate the throughput in bytes per second
throughput = [sizes[i+1]/times[i] for i in range(len(times))]

# Plot the throughput data
plt.plot(timestamps[1:], throughput)
plt.xlabel("Time")
plt.ylabel("Throughput (bytes/s)")
#plt.show()
plt.savefig('throughput.png')
