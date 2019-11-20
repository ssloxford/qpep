FROM ubuntu:18.04
RUN apt-get update --fix-missing
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:longsleep/golang-backports
RUN apt-get update --fix-missing
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install wireshark
RUN apt-get install -y iptables iproute2 wget golang-go
RUN apt-get install -y netcat
COPY docker/workstation/config/configure_ip.sh /root/configure_ip.sh
ENTRYPOINT /bin/bash /root/configure_ip.sh; bash