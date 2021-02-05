import fileinput
import os
from dotenv import load_dotenv
load_dotenv()

def configure_gateway_container():
    base_path = 'gateway/config/'
    conf_file = base_path + 'gw.conf'
    change_line(conf_file, 22, 'emu_ipv4 = ' + str(os.getenv("EMU_NETWORK_HEAD")) + ".0.3/24")
    change_line(conf_file, 25, 'lan_ipv4 = ' + str(os.getenv("GW_NETWORK_HEAD")) + ".0.3/24")
    change_line(conf_file, 29, 'lan_ipv6 = ' + str(os.getenv("GW_IP6_HEAD")) + ":6602:102::1/64")

    pespal_file = base_path + 'launch_pepsal.sh'
    change_line(pespal_file, 5, 
    '/sbin/iptables -A POSTROUTING -t nat -s ' + str(os.getenv('ST_NETWORK_HEAD')) + '.0.0/24 -o eth0 -j MASQUERADE --random')

def configure_proxy_st_container():
    base_path = 'proxy-st/'
    
    ovpn_file = base_path + "client.ovpn"
    change_line(ovpn_file, 6, 'remote '+ str(os.getenv("GW_NETWORK_HEAD"))+'.0.10 1194 udp')
    
    firefox_file = base_path + 'launch_firefox.sh'
    change_line(firefox_file, 4, 'ip route add default via ' + str(os.getenv('ST_NETWORK_HEAD')) + '.0.4')
    change_line(firefox_file, 5, 'ip route add 192.168.0.5 via ' + str(os.getenv('GUI_NETWORK_HEAD')) + '.0.1 dev eth1')

def configure_satellite_container():
    base_path = 'satellite/config/'
    conf_file = base_path + 'sat.conf'
    change_line(conf_file, 17, 'emu_ipv4 = ' + str(os.getenv("EMU_NETWORK_HEAD")) + '.0.2/24')

def configure_terminal_container():
    base_path = 'terminal/config/'
    conf_file = base_path + 'term.conf'
    change_line(conf_file, 18, 'emu_ipv4 = ' + str(os.getenv("EMU_NETWORK_HEAD")) + '.0.4/24')
    change_line(conf_file, 20, 'lan_ipv4 = ' + str(os.getenv("ST_NETWORK_HEAD")) + '.0.4/24')
    change_line(conf_file, 21, 'lan_ipv6 = ' + str(os.getenv("ST_IP6_HEAD")) + ':6602:102::1/64')

def configure_ws_ovpn_container():
    base_path = 'ws-ovpn/'
    env_file = base_path + "ovpn_env.sh"
    change_line(env_file,24, 'declare -x OVPN_SERVER_URL=udp://' + str(os.getenv('GW_NETWORK_HEAD')) +'.0.10')


def configure_ws_st_container():
    base_path = 'ws-st/'
    ovpn_file = base_path + 'client.ovpn'
    change_line(ovpn_file, 6, 'remote '+ str(os.getenv("GW_NETWORK_HEAD"))+'.0.10 1194 udp')
    firefox_file = base_path + 'launch_firefox.sh'
    change_line(firefox_file, 4, 'ip route add default via ' + str(os.getenv('ST_NETWORK_HEAD')) + '.0.4')
    change_line(firefox_file, 5, 'ip route add 192.168.0.5 via ' + str(os.getenv('GUI_NETWORK_HEAD')) + '.0.1 dev eth1')


def configure_ws_gw_container():
    base_path = 'ws-gw/'
    docker_file = base_path + 'Dockerfile'
    change_line(docker_file, 15, 
    'ENTRYPOINT ip route del default && ip route add default via ' + str(os.getenv('GW_NETWORK_HEAD'))+'.0.3 && bash && exec tail -f /dev/null')


def change_line(filename, line_number, line_text):
    with open(filename, "r") as file:
        lines = file.readlines()
    lines[line_number-1] = line_text + '\n'
    with open(filename, "w") as file:
        file.writelines(lines)

def replace_string(original_string, replacement, filename):
    with fileinput.FileInput(filename, inplace=True) as file:
        for line in file:
            print(line.replace(text_to_search, replacement_text), end='')

if __name__ == '__main__':
    configure_gateway_container()
    configure_proxy_st_container()
    configure_satellite_container()
    configure_terminal_container()
    configure_ws_ovpn_container()
    configure_ws_st_container()
    configure_ws_gw_container()