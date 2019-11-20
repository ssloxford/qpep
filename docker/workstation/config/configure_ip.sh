sysctl -w net.ipv4.ip_forward=1
ip r del default
ip r add default via 198.18.1.254 dev eth1
ip route add 192.168.0.5 via 172.25.0.1 dev eth0