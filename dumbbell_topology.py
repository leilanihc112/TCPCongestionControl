#!/usr/bin/env python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Node
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.util import quietRun, dumpNodeConnections
from mininet.cli import CLI
import os
import subprocess
import time
from os import path

class Dumbbell_Topology(Topo):
	# Dumbbell topology for mininet

	def build(self, delay=2):
		""" 
		For all calculations, we assume 12000 bits/packet and 1500-byte packets
		"""

		# Backbone Router 1
		s1 = self.addSwitch('s1')
		# Backbone Router 2
		s2 = self.addSwitch('s2')
		# Access Router 1
		s3 = self.addSwitch('s3')
		# Access Router 2
		s4 = self.addSwitch('s4')
		
		"""
		The backbone routers can transmit at 984Mbps (82p/ms).
		Bandwidth of 984Mbps.
		"""
		# Bandwidth is in Mbps, delay is in ms, and max queue size is in packets
		# Connect Backbone Router 1 to Backbone Router 2
		self.addLink(s1, s2, bw=984, delay='{0}ms'.format(delay))
		
		"""
		The access routers can transmit/receive at 252Mbps (21p/ms).
		Bandwidth of 252Mbps and a delay of 0ms.
		Max queue size = 20% * bandwidth * delay.
		"""
		# Bandwidth is in Mbps, delay is in ms, and max queue size is in packets
		# Connect Access Router 1 to Backbone Router 1
		self.addLink(s1, s3, bw=252, delay='0ms', max_queue_size=21*delay*0.2)
		# Connect Access Router 2 to Backbone Router 2
		self.addLink(s2, s4, bw=252, delay='0ms', max_queue_size=21*delay*0.2)
		
		# Source 1
		h1 = self.addHost('h1')
		# Source 2
		h2 = self.addHost('h2')
		# Receiver 1
		h3 = self.addHost('h3')
		# Receiver 2
		h4 = self.addHost('h4')
		
		"""
		The hosts can transmit/receive at 960Mbps (80p/ms).
		Delay of 0ms.
		"""
		# Bandwidth is in Mbps, delay is in ms, and max queue size is in packets
		# Connect Source 1 to Access Router 1
		self.addLink(h1, s3, bw=960, delay='0ms')
		# Connect Source 2 to Access Router 1
		self.addLink(h2, s3, bw=960, delay='0ms')
		# Connect Receiver 1 to Access Router 2
		self.addLink(h3, s4, bw=960, delay='0ms')
		# Connect Receiver 2 to Access Router 2
		self.addLink(h4, s4, bw=960, delay='0ms')

	
def run_tests(delay):
	print("DELAY {0}".format(delay))
	topo = Dumbbell_Topology(delay)
	net = Mininet(topo=topo, link=TCLink)
	net.start()
	
	print("Dumping host connections")
	dumpNodeConnections(net.hosts)
	
	print("Testing network connectivity")
	h1, h3 = net.get('h1', 'h3')
	h2, h4 = net.get('h2', 'h4')
	
	for i in range(1, 10):
		net.pingFull(hosts=(h1, h3))
	
	for i in range(1, 10):
		net.pingFull(hosts=(h3, h1))
		
	for i in range(1, 10):
		net.pingFull(hosts=(h2, h4))
	
	for i in range(1, 10):
		net.pingFull(hosts=(h4, h2))
		
	print("Testing bandwidth between h1 and h3..")
	net.iperf(hosts=(h1, h3), fmt='m', seconds=10, port=5001)
	
	print("Testing bandwidth between h2 and h4")
	net.iperf(hosts=(h2, h4), fmt='m', seconds=10, port=5001)
	
	print("Stopping test...")
	net.stop()

	
def run_tcp_tests_cwnd(algorithm, delay):
	topo = Dumbbell_Topology(delay)
	net = Mininet(topo=topo, link=TCLink)
	net.start()
	
	print("Dumping host connections")
	dumpNodeConnections(net.hosts)
	
	#CLI(net)
	
	h1, h2, h3, h4 = net.getNodeByName('h1', 'h2', 'h3', 'h4')
	host_addr = dict({'h1': h1.IP(), 'h2': h2.IP(), 'h3': h3.IP(), 'h4': h4.IP()})
	print('Host addresses: {0}'.format(host_addr))
	
	if (path.exists('results/cwnd_{0}_{1}_{2}'.format(algorithm, h1, delay))):
		os.remove('results/cwnd_{0}_{1}_{2}'.format(algorithm, h1, delay))
	if (path.exists('results/cwnd_{0}_{1}_{2}'.format(algorithm, h2, delay))):
		os.remove('results/cwnd_{0}_{1}_{2}'.format(algorithm, h2, delay))

        h1_timeout = 500
        stagger_time = 62
        h2_timeout = 438

	# run iperf
	popens = dict()
	print('Starting iperf server h3')
	popens[h3] = h3.popen('iperf3 -s -p 5566 -1', shell=True)
	print('Starting iperf server h4')
	popens[h4] = h4.popen('iperf3 -s -p 5566 -1', shell=True)
	time.sleep(5)
	
	print('Starting iperf client h1')
	popens[h1] = h1.popen('nohup iperf3 -c {0} -p 5566 -t {1} -C {2} -i 1 > results/cwnd_{3}_{4}_{5}'.format(h3.IP(), h1_timeout, algorithm, algorithm, h1, delay), shell=True)
	
        print('{0} delay for client h2'.format(stagger_time))
	for i in range(stagger_time,0,-1):
		time.sleep(1)
		print(i)

	print('Starting iperf client h2')
	popens[h2] = h2.popen('nohup iperf3 -c {0} -p 5566 -t {1} -C {2} -i 1 > results/cwnd_{3}_{4}_{5}'.format(h4.IP(), h2_timeout, algorithm, algorithm, h2, delay), shell=True)

	print("Waiting for clients to finish...")
	
	popens[h2].communicate()
        popens[h1].communicate()
	popens[h3].terminate()
	popens[h4].terminate()
	
	print("Stopping test")
	net.stop()
	
	print("Processing data")
	gather_data(algorithm, delay, True, stagger_time)
	plot_iperf(algorithm, delay, True, h1_timeout)


def run_tcp_tests_fairness(algorithm, delay):
	topo = Dumbbell_Topology(delay)
	net = Mininet(topo=topo)
	net.start()
	
	print("Dumping host connections")
	dumpNodeConnections(net.hosts)
	#CLI(net)
	
	h1, h2, h3, h4 = net.getNodeByName('h1', 'h2', 'h3', 'h4')
	host_addr = dict({'h1': h1.IP(), 'h2': h2.IP(), 'h3': h3.IP(), 'h4': h4.IP()})
	print('Host addresses: {0}'.format(host_addr))
	
	if (path.exists('results/fair_{0}_{1}_{2}'.format(algorithm, h3, delay))):
		os.remove('results/fair_{0}_{1}_{2}'.format(algorithm, h3, delay))
	if (path.exists('results/fair_{0}_{1}_{2}'.format(algorithm, h4, delay))):
		os.remove('results/fair_{0}_{1}_{2}'.format(algorithm, h4, delay))
	
        h1_timeout = 500

	# run iperf
	popens = dict()
	print('Starting iperf server h3')
	popens[h3] = h3.popen('iperf3 -s -p 5566 -i 1 -1 > results/fair_{0}_{1}_{2}'.format(algorithm, h3, delay), shell=True)
	print('Starting iperf server h4')
	popens[h4] = h4.popen('iperf3 -s -p 5566 -i 1 -1 > results/fair_{0}_{1}_{2}'.format(algorithm, h4, delay), shell=True)
	time.sleep(5)
	
	print('Starting iperf client h1')
	popens[h1] = h1.popen('iperf3 -c {0} -p 5566 -t {1} -C {2}'.format(h3.IP(), h1_timeout, algorithm), shell=True)
	print('Starting iperf client h2')
	popens[h2] = h2.popen('iperf3 -c {0} -p 5566 -t {1} -C {2}'.format(h4.IP(), h1_timeout, algorithm), shell=True)
	
	print("Waiting for clients to finish...")
		
	popens[h1].communicate()
        popens[h2].communicate()
	popens[h3].terminate()
	popens[h4].terminate()
	
	print("Stopping test")
	net.stop()
	
	print("Processing data")
	gather_data(algorithm, delay, False, h1_timeout)
	plot_iperf(algorithm, delay, False, h1_timeout)
	

def gather_data(algorithm, delay, cwnd, timeout2):
	
	if cwnd == True:
		if (path.exists("results/{0}_h1_{1}_cwnd_new".format(algorithm, delay))):
			os.remove("results/{0}_h1_{1}_cwnd_new".format(algorithm, delay))
		if (path.exists("results/{0}_h2_{1}_cwnd_new".format(algorithm, delay))):
			os.remove("results/{0}_h2_{1}_cwnd_new".format(algorithm, delay))
		print("Creating the files for IPERF to plot the CWND graph")
		subprocess.Popen("cat results/cwnd_{0}_h1_{1} | grep sec | head -n -2 | tr - \" \" | awk '{{if ($12 == \"KBytes\")print $4, int($11*1000)/(1500); else if ($12 == \"MBytes\")print $4, int($11*1000000)/(1500); else print($11)/(1500);}}'> results/{2}_h1_{3}_cwnd_new".format(algorithm,delay,algorithm,delay), shell=True)
		subprocess.Popen("cat results/cwnd_{0}_h2_{1} | grep sec | head -n -2 | tr - \" \" | awk '{{if ($12 == \"KBytes\")print {2}+$4, int($11*1000)/(1500); else if ($12 == \"MBytes\")print {2}+$4, int($11*1000000)/(1500); else print {2}+$4, ($11)/(1500);}}' > results/{3}_h2_{4}_cwnd_new".format(algorithm,delay,timeout2,algorithm,delay), shell=True)
		print("Done") 
	else:
		if (path.exists("results/{0}_h3_{1}_fair_new".format(algorithm, delay))):
			os.remove("results/{0}_h3_{1}_fair_new".format(algorithm, delay))
		if (path.exists("results/{0}_h4_{1}_fair_new".format(algorithm, delay))):
			os.remove("results/{0}_h4_{1}_fair_new".format(algorithm, delay))
		print("Creating the files for IPERF to plot the TCP fairness graph")
		subprocess.Popen("cat results/fair_{0}_h3_{1} | grep sec | head -n -2 | tr - \" \" | awk '{{print $4, $8}}' > results/{2}_h3_{3}_fair_new".format(algorithm,delay,algorithm,delay), shell=True)
                subprocess.Popen("cat results/fair_{0}_h4_{1} | grep sec | head -n -2 | tr - \" \" | awk '{{print $4, $8}}' > results/{2}_h4_{3}_fair_new".format(algorithm,delay,algorithm,delay), shell=True)
		print("Done") 


def plot_iperf(algorithm, delay, cwnd, timeout):
	if cwnd == True:		
		if (path.exists("results/{0}_{1}_cwnd.png".format(algorithm, delay))):
			os.remove("results/{0}_{1}_cwnd.png".format(algorithm, delay))
		print("Creating the plots for IPERF for the CWND graph")
		plot1 = subprocess.Popen(["gnuplot"], stdin=subprocess.PIPE)
                plot1.stdin.write("plot \"results/{0}_h1_{1}_cwnd_new\" title \"TCP Flow 1\" with linespoints, \"results/{0}_h2_{1}_cwnd_new\" title \"TCP Flow 2\" with linespoints\n".format(algorithm, delay))
		plot1.stdin.write("set xrange[1:{0}]\n".format(timeout))
		plot1.stdin.write("set xtics 1,{0},{1}\n".format(int(timeout/10),timeout))
		plot1.stdin.write("set title \"Change in cwnd (packets) vs Time (1s units) for two TCP flows (rtt = {0} ms) using {1}\"\n".format(delay*2, algorithm.upper()))
		plot1.stdin.write("set xlabel \"Time (seconds)\"\n")
		plot1.stdin.write("set ylabel \"Congestion Window (packets)\"\n")
		plot1.stdin.write("set terminal png\n")
		plot1.stdin.write("set output \"results/{0}_{1}_cwnd.png\"\n".format(algorithm, delay))
		plot1.stdin.write("replot\n")
		plot1.stdin.write("exit\n")
                plot1.communicate()
	else:
		if (path.exists("results/{0}_{1}_fair.png".format(algorithm, delay))):
			os.remove("results/{0}_{1}_fair.png".format(algorithm, delay))
		print("Creating the plots for IPERF for the TCP fairness graph")
		plot1 = subprocess.Popen(["gnuplot"], stdin=subprocess.PIPE)
		plot1.stdin.write("plot \"results/{0}_h3_{1}_fair_new\" title \"TCP Flow 1\" with linespoints, \"results/{0}_h4_{1}_fair_new\" title \"TCP Flow 2\" with linespoints\n".format(algorithm, delay))

		plot1.stdin.write("set xrange[1:{0}]\n".format(timeout))
		plot1.stdin.write("set xtics 1,{0},{1}\n".format(int(timeout/10),timeout))
		plot1.stdin.write("set title \"Change in Throughput (Mbps) vs Time (1s units) for two TCP flows (rtt = {0} ms) using {1}\"\n".format(delay*2, algorithm.upper()))
		plot1.stdin.write("set xlabel \"Time (seconds)\"\n")
		plot1.stdin.write("set ylabel \"Throughput (Mbps)\"\n")
		plot1.stdin.write("set terminal png\n")
		plot1.stdin.write("set output \"results/{0}_{1}_fair.png\"\n".format(algorithm, delay))
		plot1.stdin.write("replot\n")
		plot1.stdin.write("exit\n")
                plot1.communicate()

def clean_topology():
    print("Cleaning mininet")
    clean1 = subprocess.Popen("sudo mn -c", shell=True)
    clean1.communicate()
    clean2 = subprocess.Popen("sudo pkill -9 iperf", shell=True)
    clean2.communicate()


if __name__ == '__main__':
	delay = [21, 81, 162]
	algorithm = ['cubic', 'reno', 'westwood', 'vegas']

	setLogLevel('info')
	
	#for y in delay:
	#	run_tests(y)
	
	clean_topology()
	
	for x in algorithm:
		for y in delay:
			print("CWND for {0} {1}".format(x, y))
			run_tcp_tests_cwnd(x, y)
			clean_topology()
			print("TCP Fairness for {0} {1}".format(x, y))
			run_tcp_tests_fairness(x, y)
			clean_topology()
