import subprocess
import os
from loguru import logger
import nclib
import docker

def launch_qpep():
    docker_client = docker.from_env()
    logger.info("Starting Client Side of QPEP Proxy")
    terminal_container = docker_client.containers.get("terminal")
    terminal_container.exec_run("bash /opensand_config/launch_qpep.sh", detach=True)
    logger.info("Starting Gateway Side of QPEP Proxy")
    gateway_container = docker_client.containers.get("gateway")
    gateway_container.exec_run("bash /opensand_config/launch_qpep.sh", detach=True)


def start_testbed(host_ip, display_number):
    logger.info("Shutting Down Previous Testbeds")
    subprocess.call(["docker-compose", "down"])
    my_env = {**os.environ, 'DISPLAY': str(host_ip) + ":" + str(display_number)}
    logger.info("Starting Testbed Containers")
    subprocess.call(["docker-compose", "up", "-d"], env=my_env)

    logger.info("Starting Opensand Platform")
    opensand_launched = False
    while not opensand_launched:
        try:
            nc = nclib.Netcat(('localhost', 5656), verbose=False)
            nc.recv_until(b'help')
            nc.recv()
            nc.send(b'status\n')
            response = nc.recv()
            opensand_launched = ('SAT' in str(response)) and ('GW0' in str(response)) and ('ST1' in str(response))
        except nclib.errors.NetcatError:
            continue

    logger.info("Launching Opensand Simulation")
    nc.send(b'start\n')
    simulation_running = False
    while not simulation_running:
        nc.send(b'status\n')
        response = str(nc.recv())
        simulation_running = response.count('RUNNING') > 3

    logger.info("Connecting User Terminal to Satellite Spot Beam")
    docker_client = docker.from_env()
    terminal_container = docker_client.containers.get("terminal")
    terminal_container.exec_run("/sbin/ip route delete default")
    terminal_container.exec_run("/sbin/ip route add default via 172.22.0.3")

def connect_terminal_workstation(host_ip):
    logger.info("Starting User Workstation")
    docker_client = docker.from_env()
    workstation_container = docker_client.containers.get("ws-st")
    logger.info("Adding External Route to Docker Host for GUI Services")
    workstation_container.exec_run("ip route add " + str(host_ip) + " via 172.25.0.1 dev eth1")
    logger.info("Connecting User Workstation to Satellite Router")
    workstation_container.exec_run("ip route del default")
    workstation_container.exec_run("ip route add default via 172.21.0.4")

def launch_web_browser():
    logger.info("Launching Web Browser on User Workstation")
    docker_client = docker.from_env()
    workstation_container = docker_client.containers.get("ws-st")
    workstation_container.exec_run("qupzilla", detach=True)

def launch_wireshark():
    logger.info("Starting Wireshark on Satellite Endpoint")
    docker_client = docker.from_env()
    satellite_container = docker_client.containers.get("satellite")
    satellite_container.exec_run("wireshark", detach=True)

if __name__ == '__main__':
    start_testbed("192.168.0.5", 0)
    connect_terminal_workstation("192.168.0.5")
    launch_qpep()
    launch_wireshark()
    launch_web_browser()
