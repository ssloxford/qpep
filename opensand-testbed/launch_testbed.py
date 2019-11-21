import subprocess
import os
import time
import nclib

host_ip = "10.21.204.73"
my_env = {**os.environ, 'DISPLAY': '10.21.204.73:0'}
subprocess.call(["docker-compose", "down"])
subprocess.call(["docker-compose", "up", "-d"], env=my_env)
os_launched = False
while not os_launched:
    try:
        nc = nclib.Netcat(('localhost', 5656), verbose=False)
        nc.recv_until(b'help')
        nc.recv()
        nc.send(b'status\n')
        response = nc.recv()
        os_launched = ('SAT' in str(response)) and ('GW0' in str(response)) and ('ST1' in str(response))
    except nclib.errors.NetcatError:
        continue
nc.send(b'start\n')
simulation_launched = False
while not simulation_launched:
    nc.send(b'status\n')
    response = str(nc.recv())
    simulation_launched = response.count('RUNNING') > 3
print("Simulation Running")
os.system('docker-compose exec -T terminal /sbin/ip route delete default')
os.system('docker-compose exec -T terminal /sbin/ip route add default via 172.22.0.3')
#print("starting firefox")
print("starting workstation")
os.system("docker-compose exec -T ws-st /sbin/ip route add " + host_ip +" via 172.25.0.1 dev eth1")
#print("route added")
os.system("docker-compose exec -T ws-st /sbin/ip route del default")
os.system("docker-compose exec -T ws-st /sbin/ip route add default via 172.21.0.4")
#print("new default")
os.system("docker-compose exec -T ws-st /usr/bin/qupzilla")

#print("opening wireshark")
#os.system("docker-compose exec -T satellite /usr/bin/wireshark")



#os.system("docker-compose run -T ws-st /sbin/ip route del default && /sbin/ip route add default via 172.21.0.4")
#subprocess.call(["docker-compose", "run", "-d", "ws-st", "firefox"], env=my_env)
#os.system("docker-compose exec -T ws-st /sbin/ip route del default && /sbin/ip route add default via 172.21.0.4")
print("done")