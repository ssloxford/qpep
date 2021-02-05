#!/usr/bin/env bash
echo "starting"
ip route del default
ip route add default via 172.11.0.4
ip route add 192.168.0.5 via 172.15.0.1 dev eth1
echo "done"