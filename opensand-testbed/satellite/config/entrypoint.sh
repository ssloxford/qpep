#!/bin/bash
service dbus start
service avahi-daemon start
opensand_interfaces
sand-collector -b
sand-daemon
xvfb-run sand-manager -i