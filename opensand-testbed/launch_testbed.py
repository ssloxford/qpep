from statistics import mean

from loguru import logger
import docker
import sys
import copy
import pprint
import time
from testbeds import BasicTestbed, LeoTestbed
from scenarios import QPEPScenario, OpenVPNScenario, PEPsalScenario, PlainScenario
from benchmarks import IperfBenchmark, SitespeedBenchmark

HOST_IP = "10.21.204.246"

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

def attenuation_test_iperf_scenario():
    testbed = BasicTestbed(host_ip=HOST_IP)
    attenuation_levels = [i*0.5 for i in range(0,11)]
    # test a 10mb transfer
    iperf_file_sizes = [10000000]
    benchmarks = [IperfBenchmark(file_sizes=iperf_file_sizes, reset_on_run=True)]
    # test with pepsal vs qpep vs plain
    pepsal_scenario = PEPsalScenario(name="PEPsal Attenuation  ", testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    distributed_pepsal_scenario = PEPsalScenario(name="Distributed PEPsal Attenuation  ", gateway=True, terminal=True, testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    qpep_scenario = QPEPScenario(name="QPEP Attenuation  ", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    plain_scenario = PlainScenario(name="Plain Attenuation  ", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    scenarios = [distributed_pepsal_scenario]
    for scenario in scenarios:
        up_results = []
        down_results = []
        scenario.deploy_scenario()
        for attenuation_level in attenuation_levels:
            at_up_measurements = []
            at_down_measurements = []
            for i in range(0, 5):
                scenario.benchmarks = copy.deepcopy(benchmarks)
                logger.debug("Running attenuation scenario test #" +str(i) +" for attenuation="+str(attenuation_level))
                scenario.testbed.set_downlink_attenuation(attenuation_level)
                scenario.testbed.run_attenuation_scenario()
                scenario.run_benchmarks(deployed=True)

                for benchmark in scenario.benchmarks:
                    for key in benchmark.results:
                        at_up_measurements.append(benchmark.results[key]["sent_bps"])
                        at_down_measurements.append(benchmark.results[key]["received_bps"])
                        logger.debug("Attenuation Result: " + str(attenuation_level) +" --- " + str(benchmark.results[key]["sent_bps"]) + "/" + str(benchmark.results[key]["received_bps"]))

            # after running 5 sample tests, add their mean to our reported average
            up_results.append(mean(at_up_measurements))
            down_results.append(mean(at_down_measurements))
            print("Current Up: ", up_results)
            print("Current Down: ", down_results)
        print(scenario.name, "Results: ")
        print("    Down:", down_results)
        print("    Up:", up_results)
    logger.success("Attenuation Test Complete")


def attenuation_test_iperf_distributed_scenario():
    testbed = BasicTestbed(host_ip=HOST_IP)
    attenuation_levels = [i*0.5 for i in range(0,11)]
    # test a 10mb transfer
    iperf_file_sizes = [10000000]
    benchmarks = [IperfBenchmark(file_sizes=iperf_file_sizes, reset_on_run=True)]
    # test with pepsal vs qpep vs plain
    distributed_pepsal_scenario = PEPsalScenario(name="Distributed PEPsal Attenuation  ", gateway=True, terminal=True, testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    scenarios = [distributed_pepsal_scenario]
    for scenario in scenarios:
        scenario_up = []
        scenario_down = []
        for attenuation_level in attenuation_levels:
            testbed.start_testbed()
            testbed.connect_terminal_workstation()
            testbed.set_downlink_attenuation(attenuation_value=attenuation_level)
            testbed.run_attenuation_scenario()
            scenario.deploy_scenario(testbed_up=True)
            scenario.benchmarks = copy.deepcopy(benchmarks)
            scenario.run_benchmarks(deployed=True)
            iperf_scenario_results = scenario.benchmarks[0].results
            for key in iperf_scenario_results:
                scenario_up.append(iperf_scenario_results[key]["sent_bps"])
                scenario_down.append(iperf_scenario_results[key]["received_bps"])
                logger.debug(scenario.name + "(" + str(attenuation_level) + ")")
            print("Current Up Results " + str(scenario_up))
            print("Current Down Results " + str(scenario_down))
            testbed.stop_testbed()
            time.sleep(1)
    logger.success("Attenuation Test Complete")


def attenuation_test_pepsal_scenario():
    testbed = BasicTestbed(host_ip=HOST_IP)
    attenuation_levels = [i*0.5 for i in range(6,11)]
    benchmarks = [SitespeedBenchmark(hosts=["https://www.bbc.co.uk"], iterations=5)]
    pepsal_scenario = PEPsalScenario(name="PEPsal Attenuation  ", testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    distributed_pepsal_scenario = PEPsalScenario(name="Distributed Attenuation  ", gateway=True, testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    scenarios = [distributed_pepsal_scenario]
    for scenario in scenarios:
        scenario_results = []
        scenario_errors = []
        for attenuation_level in attenuation_levels:
            testbed.start_testbed()
            testbed.connect_terminal_workstation()
            testbed.set_downlink_attenuation(attenuation_value=attenuation_level)
            testbed.run_attenuation_scenario()
            scenario.deploy_scenario(testbed_up=True)
            scenario.benchmarks = copy.deepcopy(benchmarks)
            scenario.run_benchmarks(deployed=True)
            for benchmark in scenario.benchmarks:
                if len(benchmark.results) > 0:
                    scenario_results.append(mean(benchmark.results))
                scenario_errors.append(benchmark.errors)
            logger.debug("Current results: " + str(scenario_results))
            logger.debug("Current errors: " + str(scenario_errors))
            testbed.stop_testbed()
            time.sleep(1)
        print(scenario.name, " Results: ")
        print("    PLT: ", scenario_results)
        print("    ERR: ", scenario_errors)

def attenuation_test_plt_scenario():
    testbed = BasicTestbed(host_ip=HOST_IP)
    attenuation_levels = [i*0.5 for i in range(0,11)]
    benchmarks = [SitespeedBenchmark(hosts=["https://www.bbc.co.uk"], iterations=5)]

    # test with pepsal vs qpep vs plain
    # NB - due to the networking requirements of PEPsal, a special testbed launch order is required in attenuation_test_pepsal_scenario to allow access to web content
    qpep_scenario = QPEPScenario(name="QPEP Attenuation  ", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    plain_scenario = PlainScenario(name="Plain Attenuation  ", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    vpn_scenario = OpenVPNScenario(name="OpenVPN", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    scenarios = [plain_scenario, qpep_scenario, vpn_scenario]
    for scenario in scenarios:
        scenario_results = []
        scenario_errors = []
        scenario.deploy_scenario()
        for attenuation_level in attenuation_levels:
            scenario.benchmarks = copy.deepcopy(benchmarks)
            logger.debug("Running attenuation scenario test for attenuation="+str(attenuation_level))
            scenario.testbed.set_downlink_attenuation(attenuation_level)
            scenario.testbed.run_attenuation_scenario()
            scenario.testbed.connect_terminal_workstation()
            scenario.run_benchmarks(deployed=True)
            for benchmark in scenario.benchmarks:
                if len(benchmark.results) > 0:
                    scenario_results.append(mean(benchmark.results))
                scenario_errors.append(benchmark.errors)
        print(scenario.name, "Results: ")
        print("    PLT: ", scenario_results)
        print("    ERR: ", scenario_errors)
    logger.success("Attenuation PLT Test Complete")

def iperf_test_scenario():
    testbed = BasicTestbed(host_ip=HOST_IP)
    # from 500k to 9.5 mb in 250mb steps
    iperf_file_sizes = [(i/4)*1000000 for i in range(1, 40)]
    iperf_file_sizes.sort()
    logger.debug("Running Iperf Test Scenario with file sizes: " + str(iperf_file_sizes))
    benchmarks = [IperfBenchmark(file_sizes=iperf_file_sizes)]
    plain_scenario = PlainScenario(name="Plain", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    vpn_scenario = OpenVPNScenario(name="OpenVPN", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    pepsal_scenario = PEPsalScenario(name="PEPSal", testbed=testbed, benchmarks=copy.deepcopy(benchmarks), terminal=True, gateway=False)
    distributed_pepsal_scenario = PEPsalScenario(name="Distributed Attenuation", gateway=True, terminal=True, testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    qpep_scenario = QPEPScenario(name="QPEP", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    scenarios = [distributed_pepsal_scenario]
    for scenario in scenarios:
        logger.debug("Running iperf test scenario " + str(scenario.name))
        iperf_scenario_results = {}
        scenario.run_benchmarks()
        for benchmark in scenario.benchmarks:
            iperf_scenario_results = benchmark.results
            print(iperf_scenario_results)
        up_speeds = []
        down_speeds = []
        for key in iperf_scenario_results:
            up_speeds.append(iperf_scenario_results[key]["sent_bps"])
            down_speeds.append(iperf_scenario_results[key]["received_bps"])
        print(scenario.name)
        print("    Up: ", up_speeds)
        print("  Down:", down_speeds)

def plt_test_scenario(testbed=None):
    if testbed is None:
        testbed = BasicTestbed(host_ip=HOST_IP)
    benchmarks = [SitespeedBenchmark()]
    plain_scenario = PlainScenario(name="Plain", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    vpn_scenario = OpenVPNScenario(name="OpenVPN", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    pepsal_scenario = PEPsalScenario(name="PEPSal", testbed=testbed, benchmarks=copy.deepcopy(benchmarks), terminal=True, gateway=False)
    distributed_pepsal_scenario = PEPsalScenario(name="Distributed PEPsal  ",terminal=True, gateway=True, testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    qpep_scenario = QPEPScenario(name="QPEP", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    scenarios = [vpn_scenario]
    for scenario in scenarios:
        logger.debug("Running PLT test scenario " + str(scenario.name))
        scenario.deploy_scenario()
        scenario.run_benchmarks(deployed=True)
        for benchmark in scenario.benchmarks:
            print("Results for PLT " + str(scenario.name))
            print(benchmark.results)

if __name__ == '__main__':
    logger.remove()
    #logger.add(sys.stderr, level="SUCCESS")
    logger.add(sys.stderr, level="DEBUG")

    # Run Iperf Goodput Tests
    #iperf_test_scenario()

    # Run PLT Alexa Top 20 Test
    #plt_test_scenario()

    # Run Attenuation Tests
    # First look at Iperf over attenuation
    #attenuation_test_iperf_scenario()
    attenuation_test_iperf_distributed_scenario()

    # Next look at attenuation page load times
    #attenuation_test_plt_scenario()
    #attenuation_test_pepsal_scenario() # pepsal network configurations requires a slightly different boot order since PEPsal intercepts docker controller traffic

    # Next look at LEO delay
    #leo_testbed = LeoTestbed(host_ip=HOST_IP)
    #plt_test_scenario(leo_testbed)

    #iperf_test_scenario()
    #attenuation_test_plt_scenario()
    #attenuation_test_scenario()
    #iperf_test_scenario()

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
