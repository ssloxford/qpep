sysctl -w net.ipv4.ip_forward=1
ip r add 192.18.1.0/24 via 198.18.0.2
iptables -t nat -A POSTROUTING -j MASQUERADE