#!/bin/bash
service dbus start
service avahi-daemon start
opensand_interfaces
sand-daemon -f