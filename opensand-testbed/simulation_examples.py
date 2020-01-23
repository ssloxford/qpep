import sys
import copy
import time
from statistics import mean
from loguru import logger
from testbeds import BasicTestbed, LeoTestbed
from scenarios import QPEPScenario, OpenVPNScenario, PEPsalScenario, PlainScenario, QPEPAckScenario, QPEPCongestionScenario
from benchmarks import IperfBenchmark, SitespeedBenchmark

def ack_bundling_test_scenario():
    testbed = BasicTestbed(host_ip=HOST_IP)
    benchmarks = [SitespeedBenchmark(hosts=["https://www.bbc.co.uk"], iterations=3)]
    qpep_ack_scenario = QPEPAckScenario(name='QPEP Ack Bundling Test', testbed=testbed, benchmarks=benchmarks)
    qpep_ack_scenario.deploy_scenario()
    scenario_results = []
    for i in range(1, 20):
        qpep_ack_scenario.deploy_scenario(testbed_up=True, ack_level=i)
        qpep_ack_scenario.benchmarks = copy.deepcopy(benchmarks)
        qpep_ack_scenario.run_benchmarks(deployed=True)
        for benchmark in qpep_ack_scenario.benchmarks:
            print("Results for PLT ACK Decimation " + str(i))
            print(benchmark.results)
            scenario_results.extend(benchmark.results)
    print("PLT ACK DECIMATION DONE", scenario_results)

def congestion_window_test_scenario():
    testbed = BasicTestbed(host_ip=HOST_IP)
    benchmarks = [SitespeedBenchmark(hosts=["https://www.bbc.co.uk"], iterations=3)]
    qpep_congestion_scenario = QPEPCongestionScenario(name='QPEP Congestion Window Test', testbed=testbed, benchmarks=benchmarks)
    qpep_congestion_scenario.deploy_scenario()
    scenario_results = []
    for i in range(1, 50):
        qpep_congestion_scenario.deploy_scenario(testbed_up=True, congestion_window=i)
        qpep_congestion_scenario.benchmarks = copy.deepcopy(benchmarks)
        qpep_congestion_scenario.run_benchmarks(deployed=True)
        for benchmark in qpep_congestion_scenario.benchmarks:
            print("Results for Congestion Window Test " + str(i))
            print(benchmark.results)
            scenario_results.extend(benchmark.results)
            print("Current overall results: ", scenario_results)
    print("Congestion Test DECIMATION DONE", scenario_results)


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
    scenarios = [pepsal_scenario, qpep_scenario, plain_scenario, distributed_pepsal_scenario]
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
    attenuation_levels = [i*0.5 for i in range(9,11)]
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
            at_up_measurements = []
            at_down_measurements = []
            testbed.start_testbed()
            testbed.connect_terminal_workstation()
            testbed.set_downlink_attenuation(attenuation_value=attenuation_level)
            testbed.run_attenuation_scenario()
            scenario.deploy_scenario(testbed_up=True)
            for i in range(0, 5):
                scenario.benchmarks = copy.deepcopy(benchmarks)
                scenario.run_benchmarks(deployed=True)
                iperf_scenario_results = scenario.benchmarks[0].results
                for key in iperf_scenario_results:
                    at_up_measurements.append(iperf_scenario_results[key]["sent_bps"])
                    at_down_measurements.append(iperf_scenario_results[key]["received_bps"])
                logger.debug(scenario.name + "(" + str(attenuation_level) + ")")
                print("Current AT Up Results " + str(attenuation_level) + "# " +str(i) + ":" + str(at_up_measurements))
                print("Current AT Down Results " + str(attenuation_level) + "# " +str(i) + ":"  + str(at_down_measurements))
            scenario_up.append(mean(at_up_measurements))
            scenario_down.append(mean(at_down_measurements))
            print("Overall Results UP: ", str(scenario_up))
            print("Overall Results DOWN: ", str(scenario_down))
            testbed.stop_testbed()
            time.sleep(1)
        logger.success("Attenuation Test Complete")
        print(scenario_up)
        print(scenario_down)


def attenuation_test_pepsal_scenario():
    testbed = BasicTestbed(host_ip=HOST_IP)
    attenuation_levels = [i*0.5 for i in range(6,11)]
    benchmarks = [SitespeedBenchmark(hosts=["https://www.bbc.co.uk"], iterations=5)]
    pepsal_scenario = PEPsalScenario(name="PEPsal Attenuation  ", testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    distributed_pepsal_scenario = PEPsalScenario(name="Distributed Attenuation  ", gateway=True, testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    scenarios = [pepsal_scenario, distributed_pepsal_scenario]
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
    scenarios = [distributed_pepsal_scenario, qpep_scenario, vpn_scenario, plain_scenario, pepsal_scenario]
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
    scenarios = [plain_scenario, pepsal_scenario, distributed_pepsal_scenario, qpep_scenario, vpn_scenario]
    for scenario in scenarios:
        logger.debug("Running PLT test scenario " + str(scenario.name))
        scenario.deploy_scenario()
        scenario.run_benchmarks(deployed=True)
        for benchmark in scenario.benchmarks:
            print("Results for PLT " + str(scenario.name))
            print(benchmark.results)


HOST_IP = "192.168.0.4" # Set this to the IP address of an X Server (Display #0)
if __name__ == '__main__':
    logger.remove()
    #logger.add(sys.stderr, level="SUCCESS")
    logger.add(sys.stderr, level="DEBUG")

    # Run Iperf Goodput Tests
    iperf_test_scenario()

    # Run PLT Alexa Top 20 Test
    plt_test_scenario()

    # Run Attenuation Tests
    # First look at Iperf over attenuation
    attenuation_test_iperf_scenario()
    attenuation_test_iperf_distributed_scenario() # some pepsal configurations requires a slightly different boot order

    # Next look at attenuation page load times
    attenuation_test_plt_scenario()
    attenuation_test_pepsal_scenario() # pepsal network configurations requires a slightly different boot order

    # Next look at LEO delay
    leo_testbed = LeoTestbed(host_ip=HOST_IP)
    plt_test_scenario(leo_testbed)

    #Next look at ACK decimation
    ack_bundling_test_scenario()

    #And inital congestion window variation
    congestion_window_test_scenario()