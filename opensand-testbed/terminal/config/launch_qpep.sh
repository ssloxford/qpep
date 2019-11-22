sysctl -w net.ipv4.ip_forward=1
iptables -t mangle -N DIVERT
iptables -t mangle -A PREROUTING -m socket -j DIVERT
iptables -t mangle -A DIVERT -j MARK --set-mark 1
iptables -t mangle -A DIVERT -j ACCEPT
ip rule add fwmark 1 lookup 100
ip route add local 0.0.0.0/0 dev lo table 100
iptables -t mangle -A PREROUTING -i eth0 -p tcp -j TPROXY --tproxy-mark 0x1/0x1 --on-port 8080
iptables -t nat -A POSTROUTING -j MASQUERADE
go run /root/go/src/qpep/main.go