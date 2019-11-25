import subprocess
import os
from loguru import logger
import nclib
import docker
import json
import time

def launch_qpep():
    docker_client = docker.from_env()
    logger.debug("Starting Client Side of QPEP Proxy")
    terminal_container = docker_client.containers.get("terminal")
    terminal_container.exec_run("bash /opensand_config/launch_qpep.sh", detach=True)
    logger.debug("Starting Gateway Side of QPEP Proxy")
    gateway_container = docker_client.containers.get("gateway")
    gateway_container.exec_run("bash /opensand_config/launch_qpep.sh", detach=True)


def start_testbed(host_ip, display_number):
    logger.debug("Shutting Down Previous Testbeds")
    subprocess.call(["docker-compose", "down"])
    my_env = {**os.environ, 'DISPLAY': str(host_ip) + ":" + str(display_number)}
    logger.debug("Starting Testbed Containers")
    subprocess.call(["docker-compose", "up", "-d"], env=my_env)

    logger.debug("Starting Opensand Platform")
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

    time.sleep(1) # it often takes a little while for Opensand to identify all hosts
    logger.debug("Launching Opensand Simulation")
    nc.send(b'start\n')
    simulation_running = False
    while not simulation_running:
        nc.send(b'status\n')
        response = str(nc.recv())
        simulation_running = response.count('RUNNING') > 3

    logger.debug("Connecting User Terminal to Satellite Spot Beam")
    docker_client = docker.from_env()
    terminal_container = docker_client.containers.get("terminal")
    terminal_container.exec_run("/sbin/ip route delete default")
    terminal_container.exec_run("/sbin/ip route add default via 172.22.0.3")
    logger.success("OpeSAND Testbed Running")

def connect_terminal_workstation(host_ip):
    logger.debug("Starting User Workstation")
    docker_client = docker.from_env()
    workstation_container = docker_client.containers.get("ws-st")
    logger.debug("Adding External Route to Docker Host for GUI Services")
    workstation_container.exec_run("ip route add " + str(host_ip) + " via 172.25.0.1 dev eth1")
    logger.debug("Connecting User Workstation to Satellite Router")
    workstation_container.exec_run("ip route del default")
    workstation_container.exec_run("ip route add default via 172.21.0.4")
    logger.success("Client Workstation Connected to Satellite Network")

def launch_web_browser():
    logger.debug("Launching Web Browser on User Workstation")
    docker_client = docker.from_env()
    workstation_container = docker_client.containers.get("ws-st")
    workstation_container.exec_run("qupzilla", detach=True)

def launch_wireshark():
    logger.debug("Starting Wireshark on Satellite Endpoint")
    docker_client = docker.from_env()
    satellite_container = docker_client.containers.get("satellite")
    satellite_container.exec_run("wireshark", detach=True)

def launch_pepsal(gateway=False, terminal=True):
    logger.debug("Starting PEPSal on Gateway Endpoint")
    docker_client = docker.from_env()
    if terminal:
        terminal_client = docker_client.containers.get("terminal")
        terminal_client.exec_run("bash /opensand_config/launch_pepsal.sh")
    if gateway:
        gateway_client = docker_client.containers.get("gateway")
        gateway_client.exec_run("bash /opensand_config/launch_pepsal.sh")

def run_iperf_test():
    logger.debug("Starting iperf server")
    docker_client = docker.from_env()
    gateway_workstation = docker_client.containers.get("ws-gw")
    gateway_workstation.exec_run("iperf3 -s", detach=True)
    logger.debug("Starting iperf client")
    terminal_workstation = docker_client.containers.get("ws-st")
    exit_code, output = terminal_workstation.exec_run("iperf3 -c 172.22.0.9 --json")
    json_string = output.decode('unicode_escape').rstrip('\n').replace('Linux\n', 'Linux') # there's an error in iperf3's json output here
    results = json.loads(json_string)
    return {
        "sent_bytes": results["end"]["sum_sent"]["bytes"],
        "sent_bps": results["end"]["sum_sent"]["bits_per_second"],
        "received_bytes": results["end"]["sum_received"]["bytes"],
        "received_bps": results["end"]["sum_received"]["bits_per_second"],
    }

def run_speedtest_test():
    logger.debug("Launching Speedtest CLI")
    docker_client = docker.from_env()
    terminal_workstation = docker_client.containers.get("ws-st")
    speedtest_results = terminal_workstation.exec_run('python3 /tmp/speedtest.py --json --server 838')
    json_string = speedtest_results.output.decode('unicode_escape').rstrip('\n')
    json_data = json.loads(json_string)
    return {
        "sent_bytes": json_data["bytes_sent"],
        "received_bytes": json_data["bytes_received"],
        "sent_bps": json_data["upload"],
        "received_bps": json_data["download"]
    }

def launch_vpn():
    logger.debug("Launching OpenVPN on User Workstation")
    docker_client = docker.from_env()
    terminal_workstation = docker_client.containers.get("ws-st")
    ovpn_results = terminal_workstation.exec_run("openvpn --config /root/client.ovpn --daemon")
    time.sleep(20) # it takes a while for OVPN to esablish a connection over satellite, so we can just wait to be sure (otherwise we have to configure with systemd)

def benchmark_with_iperf(pepsal=False, plain=False, qpep=False, ovpn=False):
    results = {}
    #plain test
    if plain:
        logger.debug("Launching plain satellite network iperf3 test")
        start_testbed("10.21.205.226", 0)
        connect_terminal_workstation("10.21.205.226")
        results["plain"] = run_iperf_test()

    if ovpn:
        #note for some reason this hangs unless you run the iperf commands manually within docker
        logger.debug("Launching openvpn satellite network iperf3 test")
        start_testbed("10.21.205.226", 0)
        connect_terminal_workstation("10.21.205.226")
        launch_vpn()
        results["ovpn"] = run_iperf_test()

    #pepsal test
    if pepsal:
        logger.debug("Launching unencrypted PEPSAL network iperf3 test")
        start_testbed("10.21.205.226", 0)
        connect_terminal_workstation("10.21.205.226")
        launch_pepsal(gateway=True, terminal=True)
        results["pepsal"] = run_iperf_test()

    #qpep test
    if qpep:
        logger.debug("Launching encrypted QPEP network iperf3 test")
        start_testbed("10.21.205.226", 0)
        connect_terminal_workstation("10.21.205.226")
        launch_qpep()
        results["qpep"] = run_iperf_test()

    return results

def benchmark_with_speedtest(pepsal=False, plain=False, qpep=False, ovpn=False):
    results = {}
    if plain:
        start_testbed("10.21.205.226", 0)
        connect_terminal_workstation("10.21.205.226")
        results["plain"] = run_speedtest_test()

    if ovpn:
        start_testbed("10.21.205.226", 0)
        connect_terminal_workstation("10.21.205.226")
        launch_vpn()
        results["ovpn"] = run_speedtest_test()


    if pepsal:
        start_testbed("10.21.205.226", 0)
        connect_terminal_workstation("10.21.205.226")
        launch_pepsal(gateway=True, terminal=True)
        results["pepsal"] = run_speedtest_test()
    if qpep:
        start_testbed("10.21.205.226", 0)
        connect_terminal_workstation("10.21.205.226")
        launch_qpep()
        results["qpep"] = run_speedtest_test()

    return results

if __name__ == '__main__':
    #start_testbed("10.21.205.226", 0)
    #connect_terminal_workstation("10.21.205.226")
    print(benchmark_with_iperf(pepsal=True, ovpn=True, qpep=True, plain=True))
    print(benchmark_with_speedtest(ovpn=True, pepsal=True, qpep=True, plain=True))
