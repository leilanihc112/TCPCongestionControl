# TCP Congestion Control
TCP Congestion Control algorithms with mininet

Algorithms:
  * Reno
  * Cubic
  * Westwood
  * H-TCP

Make sure to install the following packages before running: 
`sudo apt-get install gnuplot`
`sudo apt-get install iperf3`

Run the following before running any tests to ensure no other processes are running in mininet:
`sudo mn -c`

To run all tests together:
`sudo python dumbbell_topology.py`
