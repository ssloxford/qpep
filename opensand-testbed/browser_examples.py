import argparse
import ipaddress
from testbeds import BasicTestbed, LeoTestbed
from scenarios import QPEPScenario, PEPsalScenario, PlainScenario, OpenVPNScenario


def validate_ip(addr):
    if addr != "linux":
        try:
            ipaddress.IPv4Network(addr)
        except ValueError:
            raise argparse.ArgumentTypeError("%s is not a valid IPv4 address for your XServer" % addr)
        return addr
    else:
        return ''

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('xhost',
                        help='The host IP address of an accessible XServer. '
                             'Note: this must be accessible from within the docker testbed '
                             '(so localhost or 127.0.0.1 will not work).',
                        type=validate_ip)
    parser.add_argument('--display',
                        help='The display number of an accessible XServer (default: 0)',
                        default=0, type=int)
    parser.add_argument('--scenario',
                        help='The PEP scenario you wish to evaluate (default: plain)',
                        default='plain',
                        choices=['plain', 'qpep', 'pepsal_distributed', 'pepsal_integrated', 'open_vpn']
                        )
    parser.add_argument('--orbit',
                        help='The orbit you want to simulate the satellite location delay for (default: GEO)',
                        default='GEO',
                        choices=['GEO','LEO']
                        )
    parser.add_argument('--wireshark',
                        help='Add this flag to launch a wireshark instance on the simulated satellite.',
                        default=False,
                        action='store_true')
    args = parser.parse_args()
    # First define our OpenSAND testbed environment
    testbed = None
    if args.orbit == 'GEO':
        testbed = BasicTestbed(host_ip=args.xhost, display_number=args.display)
    else:
        testbed = LeoTestbed(host_ip=args.xhost, display_number=args.display)

    # Next set the scenario
    scenario_dict = {
        "plain": PlainScenario(name="Plain", testbed=testbed, benchmarks=[]),
        "qpep": QPEPScenario(name="QPEP", testbed=testbed, benchmarks=[]),
        "pepsal_distributed": PEPsalScenario(name="Distributed PEPsal", testbed=testbed, gateway=True, benchmarks=[]),
        "pepsal_integrated": PEPsalScenario(name="Integrated PEPsal", testbed=testbed, benchmarks=[]),
        "open_vpn": OpenVPNScenario(name="OpenVPN", testbed=testbed, benchmarks=[])
    }
    scenario = scenario_dict[args.scenario]

    # Launch the testbed and deploy the PEP/VPN if relevant
    scenario.deploy_scenario()

    # Open applications in the network
    testbed.launch_web_browser()
    if args.wireshark:
        testbed.launch_wireshark()