from loguru import logger
import docker
import sys
import copy
import pprint
from testbeds import BasicTestbed
from scenarios import QPEPScenario, OpenVPNScenario, PEPsalScenario, PlainScenario
from benchmarks import IperfBenchmark, SitespeedBenchmark

HOST_IP = "10.21.205.121"

def ack_bundling_test():
    test_results = {}
    start_testbed(HOST_IP, 0)
    connect_terminal_workstation(HOST_IP)
    configure_qpep()
    docker_client = docker.from_env()
    terminal_container = docker_client.containers.get("terminal")
    gateway_workstation = docker_client.containers.get("ws-gw")
    for i in range(0, 100, 5):
        terminal_container.exec_run("go run /root/go/src/qpep/main.go -client -gateway 172.22.0.9 -acks " + str(i), detach=True)
        gateway_workstation.exec_run("go run /root/go/src/qpep/main.go -acks " + str(i), detach=True)
        results = run_iperf_test()
        print(i, "ACKS: ",round(results['sent_bps']/1000000, 3),"/",round(results['received_bps']/1000000, 3))
        #print(results)
        test_results[str(i)] = {
            "sent_bps": results['sent_bps'],
            "received_bps": results['received_bps']
        }
        terminal_container.exec_run("pkill -9 main")
        gateway_workstation.exec_run("pkill -9 main")
    print(test_results)

def ack_decimation_test():
    test_results = {}
    start_testbed(HOST_IP, 0)
    connect_terminal_workstation(HOST_IP)
    configure_qpep()
    docker_client = docker.from_env()
    terminal_container = docker_client.containers.get("terminal")
    gateway_workstation = docker_client.containers.get("ws-gw")
    for i in range(0, 20):
        terminal_container.exec_run("go run /root/go/src/qpep/main.go -client -gateway 172.22.0.9 -decimate " + str(i), detach=True)
        gateway_workstation.exec_run("go run /root/go/src/qpep/main.go -decimate " + str(i), detach=True)
        iperf_results = run_iperf_test()
        speedtest_results = run_speedtest_test()
        print(i, "ACKS: ",round(iperf_results['sent_bps']/1000000, 3),"/",
              round(iperf_results['received_bps']/1000000, 3), "(iperf)\n",
              round(speedtest_results['sent_bps']/1000000, 3), "/", round(speedtest_results['received_bps']/1000000, 3))
        #print(results)
        test_results[str(i)] = {
            "iperf": iperf_results,
            "speedtest": speedtest_results
        }
        terminal_container.exec_run("pkill -9 main")
        gateway_workstation.exec_run("pkill -9 main")
    print(test_results)

def summarize_test_result(results):
    for item in list(results.items()):
        print(item[0], ": ", round(item[1]["sent_bps"]/1000000,3), "/", round(item[1]["received_bps"]/1000000, 3))

def attenuation_test_scenario():
    testbed = BasicTestbed(host_ip=HOST_IP)
    attenuation_levels = [i for i in range(0,5)]
    # test a 10kb transfer
    iperf_file_sizes = [100000]
    benchmarks = [IperfBenchmark(file_sizes=iperf_file_sizes)]

    # test with pepsal vs qpep vs plain
    pepsal_scenario = PEPsalScenario(name="PEPsal Attenuation  ", testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    qpep_scenario = QPEPScenario(name="QPEP Attenuation  ", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    plain_scenario = PlainScenario(name="Plain Attenuation  ", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    scenarios = [plain_scenario, pepsal_scenario, qpep_scenario]
    results = {}
    for scenario in scenarios:
        for attenuation_level in attenuation_levels:
            scenario.deploy_scenario()
            scenario.name = scenario.name[:-1] + str(attenuation_level)
            logger.debug("Running attenuation scenario for attenuation="+str(attenuation_level))
            scenario.testbed.set_downlink_attenuation(attenuation_level)
            scenario.testbed.run_attenuation_scenario()
            scenario.run_benchmarks(deployed=True)
            scenario.print_results()
    logger.success("Attenuation Test Complete")
    pprint.pprint(results)
if __name__ == '__main__':
    logger.remove()
    #logger.add(sys.stderr, level="SUCCESS")
    #logger.add(sys.stderr, level="DEBUG")
    attenuation_test_scenario()

    #testbed = BasicTestbed(host_ip=HOST_IP)
    #testbed.start_testbed()
    #testbed.set_downlink_attenuation(5)
    #testbed.run_attenuation_scenario()

    # iperf_file_sizes = ([10**i for i in range(3,9)] + [int((10**i)/2) for i in range(3,9)])
    # iperf_file_sizes.sort()
    # benchmarks = [IperfBenchmark(file_sizes=iperf_file_sizes)]
    # plain_scenario = PlainScenario(name="Plain", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    # vpn_scenario = OpenVPNScenario(name="OpenVPN", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    # pepsal_scenario = PEPsalScenario(name="PEPSal", testbed=testbed, benchmarks=copy.deepcopy(benchmarks), terminal=True, gateway=False)
    # qpep_scenario = QPEPScenario(name="QPEP", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    # #plain_scenario.deploy_scenario()
    # #testbed.connect_sitespeed_workstation()
    # #pepsal_scenario.deploy_scenario()
    # scenarios = [plain_scenario, pepsal_scenario, qpep_scenario, vpn_scenario]
    # for scenario in scenarios:
    #     scenario.run_benchmarks()
    #     scenario.print_results()
    # #qpep_scenario.deploy_scenario()
    # #scenarios = [qpep_scenario]
    # #for scenario in scenarios:
    # #    scenario.run_benchmarks()
    # #    scenario.print_results()
    # #for scenario in scenarios:
    # #    scenario.print_results()
    #
    # #start_testbed("10.21.205.226", 0)
    # #connect_terminal_workstation("10.21.205.226")
    # #10000, 100000, 1000000, 10000000
    # #result = benchmark_with_iperf(pepsal=False, qpep=False, ovpn=False, plain=True, file_sizes=[10000])
    # #summarize_test_result(result)
    # #ack_decimation_test()
    # #print(benchmark_with_speedtest(qpep=True))
