from statistics import mean

from loguru import logger
from abc import ABC, abstractmethod
import docker
import json
import re

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
        for item in list(self.results.items()):
            print(item[0], ": ",
                  round(item[1]["sent_bps"]/1000000,3), "/",
                  round(item[1]["received_bps"]/1000000, 3))

class IperfBenchmark(Benchmark):
    def __init__(self, file_sizes):
        self.file_sizes = file_sizes
        super().__init__(name="IPerf")

    def run(self):
        for file_size in self.file_sizes:
            self.results["iperf_" + str(round(file_size/1000000, 3)) + "mb"] = self.run_iperf_test(file_size)

    def run_iperf_test(self, transfer_bytes):
        logger.debug("Starting iperf server")
        docker_client = docker.from_env()
        gateway_workstation = docker_client.containers.get("ws-gw")
        gateway_workstation.exec_run("pkill -9 iperf3")
        gateway_workstation.exec_run("iperf3 -s", detach=True)
        logger.debug("Starting iperf client")
        terminal_workstation = docker_client.containers.get("ws-st")
        exit_code, output = terminal_workstation.exec_run("iperf3 -c 172.22.0.9 -R --json -n " + str(transfer_bytes))
        json_string = output.decode('unicode_escape').rstrip('\n').replace('Linux\n', 'Linux') # there's an error in iperf3's json output here
        test_result = json.loads(json_string)
        if "error - control socket has closed unexpectedly" in json_string:
            logger.warning("IPerf connect socket lost, download failed")
            return {
                "sent_bytes": 0,
                "sent_bps": 0,
                "received_bytes": 0,
                "received_bps": 0
            }
        try:
            logger.debug("Iperf Result: " + str(test_result["end"]["sum_sent"]["bits_per_second"]) +
                           "/" + str(test_result["end"]["sum_received"]["bits_per_second"]))
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

class SitespeedBenchmark(Benchmark):
    def __init__(self, hosts=alexa_top_20):
        self.hosts = hosts
        super().__init__(name="SiteSpeed")
        self.results = []

    def run(self):
        logger.debug("Launching SiteSpeed.io Tests")
        docker_client = docker.from_env()
        terminal_workstation = docker_client.containers.get("sitespeed")

        #Connect sitespeed container to satellite network
        terminal_workstation.exec_run("ip route del default")
        terminal_workstation.exec_run("ip route add default via 172.21.0.4")

        host_string = ''
        for host in self.hosts:
            host_string = host + " "
            host_result = terminal_workstation.exec_run('/usr/src/app/bin/browsertime.js -n 1 --headless --video false --visualElements false ' + str(host_string))
            matches = re.findall('Load: ([0-9.]+)([ms])', str(host_result))
            if len(matches) == 0:
                logger.error("No browsertime measurement for ", host_string)
                print(host_result)
            for match in matches:
                # if the connection measures in milliseconds we take as is, otherwise convert
                if match[1] == 'm':
                    self.results.append(float(match[0]))
                elif match[1] == 's':
                    self.results.append(float(match[0])*1000)
                logger.debug("Browsertime: " + str(host_string) + " " + str(match[0]) + str(match[1]))

    def print_results(self):
        print("Mean page load time: ", mean(self.results))
        print("Load time measurements: ", self.results)

class SpeedtestBenchmark(Benchmark):
    def __init__(self, server_id=13658):
        self.server_id = server_id
        super().__init__(name="SpeedTest")

    def run(self):
        logger.debug("Launching Speedtest CLI")
        docker_client = docker.from_env()
        terminal_workstation = docker_client.containers.get("ws-st")
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