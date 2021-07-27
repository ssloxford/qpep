from statistics import mean

from loguru import logger
from abc import ABC, abstractmethod
import docker
import json
import time
import re

import os
from dotenv import load_dotenv
load_dotenv()

alexa_top_20 = [
    "https://www.google.com",
    "https://www.youtube.com",
    "https://www.tmall.com",
    "https://www.facebook.com",
    "https://www.baidu.com",
    "https://www.qq.com",
    "https://www.sohu.com",
    "https://www.taobao.com",
    "https://www.360.cn",
    "https://www.jd.com",
    "https://www.yahoo.com",
    "https://www.amazon.com",
    "https://www.wikipedia.org",
    "https://www.weibo.com",
    "https://www.sina.com.cn",
    "https://www.reddit.com",
    "https://www.live.com",
    "https://www.netflix.com",
    "https://www.okezone.com",
    "https://www.vk.com"
]

class Benchmark(ABC):
    def __init__(self, name=""):
        self.results = {}
        self.name = name

    @abstractmethod
    def run(self):
        pass

    def print_results(self):
        print(self.results)

class IperfBenchmark(Benchmark):
    def __init__(self, file_sizes, reset_on_run=True, iterations=1):
        self.file_sizes = file_sizes
        self.reset_on_run = reset_on_run
        self.iterations = iterations
        super().__init__(name="IPerf")

    def run(self):
        docker_client = docker.from_env()
        terminal_workstation = docker_client.containers.get(os.getenv("WS_ST_CONTAINER_NAME"))
        terminal_workstation.exec_run("wget http://1.1.1.1") #use this to warm up vpns/peps
        for i in range(0, self.iterations):
            for file_size in self.file_sizes:
                test_results = self.run_iperf_test(file_size, self.reset_on_run)
                result_name = "iperf_" + str(round(file_size/1000000, 3)) + "mb"
                if result_name not in self.results.keys():
                    self.results[result_name] = {}
                    for key in test_results.keys():
                        self.results[result_name][key] = [test_results[key]]
                else:
                    for key in test_results.keys():
                        self.results[result_name][key].append(test_results[key])
            print("Interim Results (Iter:", i+1, " of ", self.iterations, "):", self.results)

    def run_iperf_test(self, transfer_bytes, reset_on_run, with_timeout=True, timeout=600):
        logger.debug("Starting iperf server")
        docker_client = docker.from_env()
        gateway_workstation = docker_client.containers.get(os.getenv('WS_GW_CONTAINER_NAME'))
        if reset_on_run:
            gateway_workstation.exec_run("pkill -9 iperf3")
            time.sleep(1)
        gateway_workstation.exec_run("iperf3 -s", detach=True)
        logger.debug("Starting iperf client")
        terminal_workstation = docker_client.containers.get(os.getenv("WS_ST_CONTAINER_NAME"))
        if reset_on_run:
            terminal_workstation.exec_run("pkill -9 iperf3")
            time.sleep(1)
        if with_timeout:
            exit_code, output = terminal_workstation.exec_run("/usr/bin/timeout --signal=SIGINT " + str(timeout) +" /usr/bin/iperf3 --no-delay -c "  + str(os.getenv("GW_NETWORK_HEAD"))+ ".0.9 -R --json -n " + str(transfer_bytes))
        else:
            exit_code, output = terminal_workstation.exec_run("iperf3 --no-delay -c "  + str(os.getenv("GW_NETWORK_HEAD"))+ ".0.9 -R --json -n " + str(transfer_bytes))
        json_string = output.decode('unicode_escape').rstrip('\n').replace('Linux\n', 'Linux') # there's an error in iperf3's json output here
        try:
            test_result = json.loads(json_string)
        except:
            json_string = "error - control socket has closed unexpectedly"
        if "error - control socket has closed unexpectedly" in json_string:
            logger.debug("IPerf connect socket lost, download failed")
            return {
                "sent_bytes": 0,
                "sent_bps": 0,
                "received_bytes": 0,
                "received_bps": 0
            }
        try:
            logger.debug("Iperf Result: " + str(test_result["end"]["sum_sent"]["bits_per_second"]/1000000) +
                           "/" + str(test_result["end"]["sum_received"]["bits_per_second"]/1000000))
        except:
            logger.error("Unable to parse iperf result")
            print(json_string)
            return {
                "sent_bytes": 0,
                "sent_bps": 0,
                "received_bytes": 0,
                "received_bps": 0
            }
        return {
            "sent_bytes": test_result["end"]["sum_sent"]["bytes"],
            "sent_bps": test_result["end"]["sum_sent"]["bits_per_second"],
            "received_bytes": test_result["end"]["sum_received"]["bytes"],
            "received_bps": test_result["end"]["sum_received"]["bits_per_second"],
        }
    
    def print_results(self):
        print("Full Results: ")
        print(self.results)
        print("~"*25)
        print("Average Speeds: ")
        for result_key in self.results.keys():
            print(result_key, "sent_bps:", mean(self.results[result_key]["sent_bps"]) / 1000000)
            print(result_key, "received_bps:", mean(self.results[result_key]["received_bps"])/ 1000000)
 

class SitespeedBenchmark(Benchmark):
    def __init__(self, hosts=alexa_top_20, iterations=1, average_only=False, scenario=None, sub_iterations=1):
        self.hosts = hosts
        self.iterations = iterations
        self.average_only = average_only
        super().__init__(name="SiteSpeed")
        self.results = {}
        self.errors = 0
        self.scenario = scenario
        self.sub_iterations = sub_iterations

    def run(self):
        logger.debug("Launching SiteSpeed.io Tests")
        docker_client = docker.from_env()
        #terminal_workstation = docker_client.containers.get(os.getenv("SITESPEED_CONTAINER_NAME"))
        #terminal_workstation.exec_run("ip route del default")
        #terminal_workstation.exec_run("ip route add default via " + str(os.getenv("ST_NETWORK_HEAD"))+".0.4")
        
        host_string = ''
        for i in range(0, self.iterations):
            terminal_workstation = docker_client.containers.get(os.getenv("WS_ST_CONTAINER_NAME"))
            #Connect sitespeed container to satellite network
            terminal_workstation.exec_run("ip route del default")
            terminal_workstation.exec_run("ip route add default via " + str(os.getenv("ST_NETWORK_HEAD"))+".0.4")
            terminal_workstation.exec_run("wget http://1.1.1.1") #use this to warm up vpns/peps
            for host in self.hosts:
                host_string = host + " "
                host_result = terminal_workstation.exec_run('/usr/bin/browsertime -n ' + str(self.sub_iterations) +' --headless --xvfb --browser firefox --cacheClearRaw  --firefox.geckodriverPath /usr/bin/geckodriver --firefox.preference network.dns.disableIPv6:true --video=false --visualMetrics=false --visualElements=false ' + str(host_string))
                matches = re.findall('Load: ([0-9.]+)([ms])', str(host_result))
                if self.sub_iterations > 1:
                    matches = matches[:-1] # the last match is the average load time, which we don't want mixing up our stats
                for match in matches:
                        # if the connection measures in milliseconds we take as is, otherwise convert
                    if match[1] == 'm':
                        host_val = float(match[0])
                    elif match[1] == 's':
                        host_val = float(match[0]) * 1000
                    if host not in self.results.keys():
                            self.results[host] = [host_val]
                    else:
                            self.results[host].append(host_val)
                if len(matches) == 0:
                    logger.warning("No browsertime measurement for " + str(host_string))
                    print(host_result)
                else:
                    logger.debug("Browsertime: " + str(host_string) + " " + str(match[0]) + str(match[1]))
                #count failed connections for host
                error_matches = re.findall('UrlLoadError', str(host_result))
                self.errors = self.errors + len(error_matches)
                logger.debug("Browsertime Error Count: " + str(len(error_matches)) + " " + host)
                print("Interim Results: ","(", self.name,")", self.results)
            if i != self.iterations - 1:  
                self.scenario.deploy_scenario()

    def print_results(self):
        print(self.results)

        #print("Mean page load time: ", mean(self.results))
        #print("Load time measurements: ", self.results)
        print("Failed load count: ", self.errors)

class SpeedtestBenchmark(Benchmark):
    def __init__(self, server_id=13658):
        self.server_id = server_id
        super().__init__(name="SpeedTest")

    def run(self):
        logger.debug("Launching Speedtest CLI")
        docker_client = docker.from_env()
        terminal_workstation = docker_client.containers.get(os.getenv("WS_ST_CONTAINER_NAME"))
        speedtest_results = terminal_workstation.exec_run('python3 /tmp/speedtest.py --json --server ' + str(self.server_id))
        json_string = speedtest_results.output.decode('unicode_escape').rstrip('\n')
        json_data = json.loads(json_string)
        logger.success("Speedtest Complete" + str(json_data["upload"]) + "/" + str(json_data["download"]))
        return {
            "sent_bytes": json_data["bytes_sent"],
            "received_bytes": json_data["bytes_received"],
            "sent_bps": json_data["upload"],
            "received_bps": json_data["download"]
        }