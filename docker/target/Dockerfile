FROM ubuntu:18.04
RUN apt-get update --fix-missing
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install wireshark
RUN apt-get install -y iptables iproute2 wget netcat iputils-ping
