FROM ubuntu:16.04
RUN echo "deb [trusted=yes] http://packages.net4sat.org/opensand xenial stable" | tee /etc/apt/sources.list.d/opensand.list
RUN apt-get update
RUN apt-get install -y netcat
RUN apt-get install -y iputils-ping
RUN apt-get install -y net-tools
RUN apt-get install -y iproute2
RUN apt-get install -y iperf3
RUN apt-get install -y wget
ENTRYPOINT ip route del default && ip route add default via 172.22.0.3 && bash && exec tail -f /dev/null