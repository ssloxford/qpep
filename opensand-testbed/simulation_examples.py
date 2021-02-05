import sys
import copy
import time
from statistics import mean
import json
from loguru import logger
from testbeds import BasicTestbed, LeoTestbed
from scenarios import QPEPScenario, OpenVPNScenario, PEPsalScenario, PlainScenario, QPEPAckScenario, QPEPCongestionScenario
from benchmarks import IperfBenchmark, SitespeedBenchmark
import numpy
import os
from dotenv import load_dotenv
load_dotenv()

def ack_bundling_iperf_scenario():
    # Simulates ACK decimation ratios for different IPERF transfer sizes at different PLR rates
    # qpep-only scenario
    testbed = BasicTestbed(host_ip=HOST_IP)
    iperf_file_sizes=[1000000, 2000000, 5000000]
    plr_levels = [0, 1*pow(10,-7), 1*(pow(10, -4)), 1*(pow(10,-2))]
    benchmarks = [IperfBenchmark(file_sizes=iperf_file_sizes, reset_on_run=True, iterations=int(os.getenv("IPERF_ITERATIONS")))]
    ack_bundling_numbers = [ack for ack in range(1, 31, 1)]
    scenario = QPEPAckScenario(name='QPEP Ack Bundling Test', testbed=testbed, benchmarks=[])
    decimation_results = {}
    for ack_bundling_number in ack_bundling_numbers[int(os.getenv("ACK_BUNDLING_MIN")):int(os.getenv("ACK_BUNDLING_MAX"))]:
        scenario.deploy_scenario(ack_level=ack_bundling_number)
        if str(ack_bundling_number) not in decimation_results.keys():
            decimation_results[str(ack_bundling_number)] = {}
        for plr_level in plr_levels:
            plr_string = numpy.format_float_positional(plr_level, precision=7, trim='-')
            if plr_string not in decimation_results[str(ack_bundling_number)].keys():
                decimation_results[str(ack_bundling_number)][plr_string] = []
            
            scenario.testbed.set_plr_percentage(plr_string, st_out=False, gw_out=True)
            scenario.benchmarks = copy.deepcopy(benchmarks)
            scenario.run_benchmarks(deployed=True)
            
            for benchmark in scenario.benchmarks:
                decimation_results[str(ack_bundling_number)][plr_string].append(benchmark.results)
            
            logger.debug("Interim bundling results for PLR level " + str(plr_string) + " and ACK level " + str(ack_bundling_number) +":" + str(decimation_results))
    print("Final Ack Bundling Results for QPEP " + str(os.getenv("ACK_BUNDLING_MIN") + "-" + str(os.getenv("ACK_BUNDLING_MAX"))))
    print("*********************\n")
    print(decimation_results)
    print("\n*********************")

def iperf_test_scenario():
    # Simulates IPERF transfers at different file sizes

    testbed = BasicTestbed(host_ip=HOST_IP)
    # from 250k to 9.75 mb in 250kb steps
    # we add one modest "Warm up" sessions to start the connections for d_pepsal and qpep which have high first packet costs  but only
    # experience these costs once, when the customer starts the respective applications
    iperf_file_sizes = [25*1000, 50*1000, 100*1000, 150*1000]+[(i/4)*1000000 for i in range(1, 47)]
    iperf_file_sizes.sort()
    benchmarks = [IperfBenchmark(file_sizes=iperf_file_sizes[int(os.getenv("IPERF_MIN_SIZE_INDEX")):int(os.getenv("IPERF_MAX_SIZE_INDEX"))], iterations=int(os.getenv("IPERF_ITERATIONS")))]
    plain_scenario = PlainScenario(name="Plain", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    vpn_scenario = OpenVPNScenario(name="OpenVPN", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    pepsal_scenario = PEPsalScenario(name="PEPSal", testbed=testbed, benchmarks=copy.deepcopy(benchmarks), terminal=True, gateway=False)
    distributed_pepsal_scenario = PEPsalScenario(name="Distributed PEPsal", gateway=True, terminal=True, testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    qpep_scenario = QPEPScenario(name="QPEP", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    scenarios = [qpep_scenario, distributed_pepsal_scenario, vpn_scenario, plain_scenario, pepsal_scenario]
    for scenario in scenarios:
        if scenario.name == os.getenv("SCENARIO_NAME"):
            logger.debug("Running iperf test scenario " + str(scenario.name))
            iperf_scenario_results = {}
            scenario.run_benchmarks()
            for benchmark in scenario.benchmarks:
                logger.debug("Running Iperf Test Scenario (", str(scenario.name), ") with file sizes: " + str(benchmark.file_sizes))
                iperf_scenario_results = benchmark.results
                print(iperf_scenario_results)
            scenario.print_results()

def plt_test_scenario(testbed=None):
    if testbed is None:
        testbed = BasicTestbed(host_ip=HOST_IP, display_number=0)
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
    plain_scenario = PlainScenario(name="Plain", testbed=testbed, benchmarks=[])
    vpn_scenario = OpenVPNScenario(name="OpenVPN", testbed=testbed, benchmarks=[])
    pepsal_scenario = PEPsalScenario(name="PEPSal", testbed=testbed, benchmarks=[], terminal=True, gateway=False)
    distributed_pepsal_scenario = PEPsalScenario(name="Distributed PEPsal",terminal=True, gateway=True, testbed=testbed,benchmarks=[])
    qpep_scenario = QPEPScenario(name="QPEP", testbed=testbed, benchmarks=[])
    scenarios = [plain_scenario, pepsal_scenario, distributed_pepsal_scenario, qpep_scenario, vpn_scenario]
    for scenario in scenarios:
        if scenario.name == os.getenv("SCENARIO_NAME"):
            scenario.benchmarks = [SitespeedBenchmark(hosts=alexa_top_20[int(os.getenv("ALEXA_MIN")):int(os.getenv("ALEXA_MAX"))], scenario=scenario, iterations=int(os.getenv("PLT_ITERATIONS")), sub_iterations=int(os.getenv("PLT_SUB_ITERATIONS")))]
            logger.debug("Running PLT test scenario " + str(scenario.name))
            scenario.deploy_scenario()
            scenario.run_benchmarks(deployed=True)
            for benchmark in scenario.benchmarks:
                print("Results for PLT " + str(scenario.name))
                print(benchmark.results)
    for scenario in scenarios:
        if scenario.name == os.getenv("SCENARIO_NAME"):
            scenario.print_results()

def plr_plt_scenario():
    testbed = BasicTestbed(host_ip=HOST_IP)
    
    sites_to_check = ["https://www.nasa.gov"]
    plr_levels = list(numpy.unique(list(numpy.geomspace((1*pow(10, -7)), (1*pow(10,2)), num=20)) + list(numpy.geomspace((1*pow(10,-7)), (1*pow(10,2)), num=10))))
    
    plain_scenario = PlainScenario(name="Plain", testbed=testbed, benchmarks=[])
    vpn_scenario = OpenVPNScenario(name="OpenVPN", testbed=testbed, benchmarks=[])
    pepsal_scenario = PEPsalScenario(name="PEPSal", testbed=testbed, benchmarks=[], terminal=True, gateway=False)
    distributed_pepsal_scenario = PEPsalScenario(name="Distributed PEPsal",terminal=True, gateway=True, testbed=testbed,benchmarks=[])
    qpep_scenario = QPEPScenario(name="QPEP", testbed=testbed, benchmarks=[])
    scenarios = [plain_scenario, pepsal_scenario, distributed_pepsal_scenario, qpep_scenario, vpn_scenario]

    for scenario in scenarios:
        benchmarks = [SitespeedBenchmark(hosts=sites_to_check, scenario=scenario, iterations=1, sub_iterations=int(os.getenv("PLR_PLT_ITERATIONS")))]
        if scenario.name == os.getenv("SCENARIO_NAME"):
            logger.debug("Running PLR PLT scenario" + str(scenario.name))
            plr_scenario_results = {}
            for plr_level in plr_levels[int(os.getenv("PLR_MIN_INDEX")):int(os.getenv("PLR_MAX_INDEX"))]:
                plr_string = numpy.format_float_positional(plr_level, precision=7, trim='-')
                plr_scenario_results[str(plr_string)]=[]
                for j in range(0, int(os.getenv("PLR_META_ITERATIONS"))):
                    scenario.benchmarks = copy.deepcopy(benchmarks)
                    scenario.deploy_scenario()
                    scenario.testbed.set_plr_percentage(plr_string, st_out=False, gw_out=True)
                    logger.debug("Running PLR PLT for " + str(scenario.name) + " at " + str(plr_string) + " batch " + str(j) +" of " + str(os.getenv("PLR_META_ITERATIONS")))
                    scenario.run_benchmarks(deployed=True)
                    for benchmark in scenario.benchmarks:
                        plr_scenario_results[str(plr_string)].append(benchmark.results)
                logger.debug("Interim PLR/PLT Results (PLR: " + str(plr_string) + " meta_iteration: " + str(j) + "/" + str(int(os.getenv("PLR_META_ITERATIONS"))) + " Scenario: " + str(scenario.name) +"): " + str(plr_scenario_results) + "\n")
            print("Final PLR PLT results for " + str(scenario.name))
            print("***********************************************")
            print(plr_scenario_results)
            print('\n*********************************************')
    logger.success("PLR/PLT test complete")

def plr_test_scenario():
    testbed = BasicTestbed(host_ip=HOST_IP)
    iperf_file_sizes=[1000000, 2000000, 5000000, 1000000]
    # a balacned distribution across log scale of 20 points, plus key powers of ten, total length of 28 checkpoints from 10e-7 to 100
    plr_levels = list(numpy.unique(list(numpy.geomspace((1*pow(10, -7)), (1*pow(10,2)), num=20)) + list(numpy.geomspace((1*pow(10,-7)), (1*pow(10,2)), num=10))))

    benchmarks = [IperfBenchmark(file_sizes=iperf_file_sizes, reset_on_run=True, iterations=1)]
    # test with pepsal vs qpep vs plain
    pepsal_scenario = PEPsalScenario(name="PEPSal", testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    qpep_scenario = QPEPScenario(name="QPEP", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    plain_scenario = PlainScenario(name="Plain", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    vpn_scenario  = OpenVPNScenario(name="OpenVPN", testbed=testbed, benchmarks=copy.deepcopy(benchmarks))
    distributed_pepsal_scenario = PEPsalScenario(name="Distributed PEPsal", gateway=True, terminal=True, testbed=testbed,benchmarks=copy.deepcopy(benchmarks))
    scenarios = [qpep_scenario, plain_scenario, vpn_scenario, pepsal_scenario, distributed_pepsal_scenario]
    for scenario in scenarios:
        if scenario.name == os.getenv("SCENARIO_NAME"):
            logger.debug("Running packet loss rate scenario " + str(scenario.name))
            iperf_scenario_results = {}
            for plr_level in plr_levels[int(os.getenv("PLR_MIN_INDEX")):int(os.getenv("PLR_MAX_INDEX"))]:
                plr_string = numpy.format_float_positional(plr_level, precision=7, trim='-')
                iperf_scenario_results[str(plr_string)] = []
                for j in range(0, int(os.getenv("PLR_META_ITERATIONS"))):
                    logger.debug("Running PLR for " + str(scenario.name) +  " at " + str(plr_string) + " batch " + str(j) + " of " + str(os.getenv("PLR_META_ITERATIONS")))
                    scenario.deploy_scenario()
                    scenario.testbed.set_plr_percentage(plr_string, st_out=False, gw_out=True)
                    for i in range(0, int(os.getenv("IPERF_ITERATIONS"))):
                        scenario.benchmarks = copy.deepcopy(benchmarks)
                        scenario.run_benchmarks(deployed=True)
                        for benchmark in scenario.benchmarks:
                            iperf_scenario_results[str(plr_string)].append(benchmark.results)
                            # if the link breaks, we need to restart the ip routes
                            for key in benchmark.results.keys():
                                if(benchmark.results[key]["sent_bps"]) == 0:
                                    scenario.deploy_scenario()
                                    scenario.testbed.set_plr_percentage(plr_string, st_out=False, gw_out=True)
                                    logger.warning("Failed Iperf Run @ " + str(plr_string))
                                    break
                        logger.debug("Interim PLR Results (PLR: " + str(plr_string) + " sub_iter: " + str(i) + "/" + str(int(os.getenv("IPERF_ITERATIONS"))) + " Scenario: " + str(scenario.name) +"): " + str(iperf_scenario_results))
            print("Final PLR Results for ", scenario.name)
            print("*********************************")
            print(iperf_scenario_results)
            print("\n******************************")
    logger.success("PLR Test Complete")


HOST_IP = "192.168.0.15" # Set this to the IP address of an X Server (Display #0)
if __name__ == '__main__':
    # These functions draw on parameters from the .env file to determine which scenarios to run and which portions of the scenario. See the QPEP README for some advice on using .env to run simulations in parallel
    logger.remove()
    #logger.add(sys.stderr, level="SUCCESS")
    logger.add(sys.stderr, level="DEBUG")

    # Run Iperf Goodput Tests
    #iperf_test_scenario()

    # Run PLT Alexa Top 20 Test
    #plt_test_scenario()

    # Run PLR Tests
    # First look at Iperf over attenuation
    #plr_test_scenario()

    # Next look at PLR effect on page load times
    #plr_plt_scenario()

    # Next look at LEO delay
    #leo_testbed = LeoTestbed(host_ip=HOST_IP)
    #plt_test_scenario(leo_testbed)

    #Next look at ACK decimation
    ack_bundling_iperf_scenario()
