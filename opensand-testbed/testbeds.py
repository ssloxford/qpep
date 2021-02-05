import subprocess
import os
from loguru import logger
import nclib
import docker
import time
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
load_dotenv()

class BasicTestbed(object):
    def __init__(self, host_ip="192.168.1.199", display_number=0, linux=False):
        self.host_ip = host_ip
        self.display_number = display_number
        self.linux = linux

    def start_testbed(self):
        # First, shut down any old running testbeds
        logger.debug("Shutting Down Previous Testbeds")
        subprocess.call(["docker-compose", "down"], stderr=subprocess.DEVNULL)

        # The DISPLAY env variable points to an X server for showing OpenSAND UI
        my_env = {**os.environ, 'DISPLAY': str(self.host_ip) + ":" + str(self.display_number)}
        logger.debug("Starting Testbed Containers")

        # Start the docker containers
        subprocess.call(["docker-compose", "up", "-d"], env=my_env)

        # Wait for the opensand container to initialize then send a command to run the simulation
        logger.debug("Starting Opensand Platform")
        opensand_launched = False
        while not opensand_launched:
            try:
                nc = nclib.Netcat(('localhost', int(os.getenv('SAT_PORT_NUMBER'))), verbose=False)
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
            # wait for all three components (satellite, terminal and gateway) to start running
            simulation_running = response.count('RUNNING') > 3

        # now that the network is running, it is possible to add ip routes from user terminal through the network
        logger.debug("Connecting User Terminal to Satellite Spot Beam")
        docker_client = docker.from_env()
        terminal_container = docker_client.containers.get(os.getenv("ST_CONTAINER_NAME"))
        terminal_container.exec_run("/sbin/ip route delete default")
        terminal_container.exec_run("/sbin/ip route add default via " + str(os.getenv("GW_NETWORK_HEAD")) + ".0.3")
        logger.success("OpeSAND Testbed Running")

    def stop_testbed(self):
        logger.debug("Shutting Down Previous Testbeds")
        subprocess.call(["docker-compose", "down"])

    def connect_terminal_workstation(self):
        logger.debug("Starting User Workstation")
        docker_client = docker.from_env()
        workstation_container = docker_client.containers.get(os.getenv("WS_ST_CONTAINER_NAME"))
        logger.debug("Adding External Route to Docker Host for GUI Services")
        workstation_container.exec_run("ip route add " + str(self.host_ip) + " via " + str(os.getenv("GUI_NETWORK_HEAD"))+".0.1 dev eth1")
        logger.debug("Connecting User Workstation to Satellite Router")
        workstation_container.exec_run("ip route del default")
        workstation_container.exec_run("ip route add default via " + str(os.getenv("ST_NETWORK_HEAD"))+".0.4")
        logger.success("Client Workstation Connected to Satellite Network")

    def connect_sitespeed_workstation(self):
        logger.debug("Starting Sitespeed Workstation")
        docker_client = docker.from_env()
        sitespeed_container = docker_client.containers.get(os.getenv("SITESPEED_CONTAINER_NAME"))
        sitespeed_container.exec_run("ip route del default")
        sitespeed_container.exec_run("ip route add default via " + str(os.getenv("ST_NETWORK_HEAD"))+".0.4")
        logger.success("Sitespeed Workstation Connected to Satellite Network")

    def launch_wireshark(self):
        logger.debug("Starting Wireshark on Satellite Endpoint")
        docker_client = docker.from_env()
        satellite_container = docker_client.containers.get(os.getenv("SAT_CONTAINER_NAME"))
        satellite_container.exec_run("wireshark", detach=True)

    def launch_web_browser(self):
        logger.debug("Launching Web Browser on User Workstation")
        docker_client = docker.from_env()
        workstation_container = docker_client.containers.get(os.getenv("WS_ST_CONTAINER_NAME"))
        workstation_container.exec_run("qupzilla", detach=True)

    def set_downlink_attenuation(self, attenuation_value=0):
        logger.debug("Setting OpenSAND Downlink Attenuation to " + str(attenuation_value))
        gw_path = 'satellite/attenuation_scenario/gw0/plugins/ideal.conf'
        st_path = 'satellite/attenuation_scenario/st1/plugins/ideal.conf'
        gw_conf = ET.parse(gw_path)
        st_conf = ET.parse(st_path)
        xml_confs = [gw_conf.getroot(), st_conf.getroot()]
        for conf in xml_confs:
            attenuation_settings = conf.findall('ideal/ideal_attenuations/ideal_attenuation')
            for setting in attenuation_settings:
                if setting.attrib["link"] == "down":
                    setting.set("attenuation_value", str(attenuation_value))
        gw_conf.write(gw_path)
        st_conf.write(st_path)
        logger.debug("Updated Downlink Attenuations")
    
    def set_plr_percentage(self, plr_percentage, st_out=False, gw_out=True):
        logger.debug("Configuring Packet Loss Rate")
        docker_client = docker.from_env()
        containers_to_mod = []
        if st_out:
            logger.debug("Setting PLR for ST->GW at " + str(plr_percentage))
            containers_to_mod.append(docker_client.containers.get(os.getenv("ST_CONTAINER_NAME")))
        if gw_out:
            logger.debug("Setting PLR for GW->ST at " + str(plr_percentage))
            containers_to_mod.append(docker_client.containers.get(os.getenv("GW_CONTAINER_NAME")))
        for container in containers_to_mod:
            response = container.exec_run('/sbin/tc qdisc change dev opensand_tun root netem loss ' + str(plr_percentage) + "%", stderr=True, stdout=True)
            if "RTNETLINK" in str(response.output):
                container.exec_run('/sbin/tc qdisc add dev opensand_tun root netem loss ' + str(plr_percentage) + "%", stderr=True, stdout=True)
        logger.debug("Updated PLR to " + str(plr_percentage) + "%")

    def run_attenuation_scenario(self):
        logger.debug("Running Attenuation Scenario")
        # wait to connect to opensand
        opensand_launched = False
        nc = None
        while not opensand_launched:
            try:
                nc = nclib.Netcat(('localhost', int(os.getenv('SAT_PORT_NUMBER'))), verbose=False)
                nc.recv_until(b'help')
                nc.recv()
                opensand_launched = True
            except:
                continue
        logger.debug("Connected to NC Listener")
        # stop running scenarios if any
        nc.send(b'stop\n')
        nc.recv_until(b'OK', timeout=10)
        nc.recv()
        # opensand reports that the testbed has stopped a little before it actually has
        time.sleep(1)

        # load attenuation scenario
        nc.send(b'scenario attenuation_scenario\n')
        nc.recv_until(b'OK', timeout=10)
        nc.recv()

        # start new scenario
        nc.send(b'start\n')
        nc.recv_until(b'OK', timeout=10)
        logger.debug("Scenario Restarted")
        nc.recv()

        # ensure that the terminal modem is still connected
        docker_client = docker.from_env()
        terminal_container = docker_client.containers.get(os.getenv("ST_CONTAINER_NAME"))
        #terminal_container.exec_run("/sbin/ip route delete default")
        terminal_container.exec_run("/sbin/ip route add default via " + str(os.getenv("GW_NETWORK_HEAD"))+".0.3")

        logger.debug("Attenuation Scenario Launched")

class LeoTestbed(BasicTestbed):
    def start_testbed(self):
        # First, shut down any old running testbeds
        logger.debug("Shutting Down Previous Testbeds")
        subprocess.call(["docker-compose", "down"], stderr=subprocess.DEVNULL)

        # The DISPLAY env variable points to an X server for showing OpenSAND UI
        my_env = {**os.environ, 'DISPLAY': str(self.host_ip) + ":" + str(self.display_number)}
        logger.debug("Starting Testbed Containers")

        # Start the docker containers
        subprocess.call(["docker-compose", "up", "-d"], env=my_env)

        # Wait for the opensand container to initialize then send a command to run the simulation
        logger.debug("Starting Opensand Platform")
        opensand_launched = False
        while not opensand_launched:
            try:
                nc = nclib.Netcat(('localhost', int(os.getenv('SAT_PORT_NUMBER'))), verbose=False)
                nc.recv_until(b'help')
                nc.recv()
                nc.send(b'status\n')
                response = nc.recv()
                opensand_launched = ('SAT' in str(response)) and ('GW0' in str(response)) and ('ST1' in str(response))
            except nclib.errors.NetcatError:
                continue

        logger.debug("Loading Iridium Delay Simulation")
        nc.send(b'scenario delay_scenario\n')
        nc.recv_until(b'OK', timeout=10)
        nc.recv()
        time.sleep(1) # it often takes a little while for Opensand to identify all hosts
        logger.debug("Launching Opensand Simulation")
        nc.send(b'start\n')
        simulation_running = False
        while not simulation_running:
            nc.send(b'status\n')
            response = str(nc.recv())
            # wait for all three components (satellite, terminal and gateway) to start running
            simulation_running = response.count('RUNNING') > 3

        # now that the network is running, it is possible to add ip routes from user terminal through the network
        logger.debug("Connecting User Terminal to Satellite Spot Beam")
        docker_client = docker.from_env()
        terminal_container = docker_client.containers.get(os.getenv("ST_CONTAINER_NAME"))
        terminal_container.exec_run("/sbin/ip route delete default")
        terminal_container.exec_run("/sbin/ip route add default via " + str(os.getenv("GW_NETWORK_HEAD")) + ".0.3")
        logger.success("OpeSAND Testbed Running")
