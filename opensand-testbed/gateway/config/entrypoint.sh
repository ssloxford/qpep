#!/bin/bash
service dbus start
service avahi-daemon start
opensand_interfaces
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sand-daemon -f