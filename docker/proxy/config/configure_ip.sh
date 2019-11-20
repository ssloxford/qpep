ip r del default
ip r add default via 198.18.0.254 dev eth0
sysctl -w net.ipv4.ip_forward=1
iptables -t mangle -N DIVERT
iptables -t mangle -A PREROUTING -m socket -j DIVERT
iptables -t mangle -A DIVERT -j MARK --set-mark 1
iptables -t mangle -A DIVERT -j ACCEPT
ip rule add fwmark 1 lookup 100
ip route add local 0.0.0.0/0 dev lo table 100
iptables -t mangle -A PREROUTING -i eth1 -p tcp -j TPROXY --tproxy-mark 0x1/0x1 --on-port 8080
iptables -t nat -A POSTROUTING -j MASQUERADE