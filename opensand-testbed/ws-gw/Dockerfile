FROM pavja2/qpep:ws-gw
# RUN echo "deb [trusted=yes] http://packages.net4sat.org/opensand xenial oldstable" | tee /etc/apt/sources.list.d/opensand.list
# RUN apt-get update
# RUN apt-get install -y netcat
# RUN apt-get install -y iputils-ping
# RUN apt-get install -y net-tools
# RUN apt-get install -y iproute2
# RUN apt-get install -y iperf3
# RUN apt-get install -y wget
# RUN apt-get install -y software-properties-common
# RUN add-apt-repository ppa:longsleep/golang-backports
# RUN add-apt-repository ppa:vmkononenko/uperf
# RUN apt-get update && apt-get install -y golang-go iptables
# RUN apt-get install uperf
ENTRYPOINT ip route del default && ip route add default via 172.12.0.3 && bash && exec tail -f /dev/null
