FROM ubuntu:16.04
RUN echo "deb [trusted=yes] http://packages.net4sat.org/opensand xenial stable" | tee /etc/apt/sources.list.d/opensand.list
RUN apt-get update
RUN apt-get install -y netcat
RUN apt-get install -y iputils-ping
RUN apt-get install -y net-tools
RUN apt-get install -y iproute2
RUN apt-get install -y qupzilla ca-certificates
RUN apt-get install -y iperf3
RUN apt-get install -y python3
RUN apt-get install -y openvpn
RUN apt-get install -y wget
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:vmkononenko/uperf
RUN apt-get update && apt-get install uperf
RUN apt-get install -y apt-transport-https
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 379CE192D401AB61
RUN echo "deb https://ookla.bintray.com/debian xenial main" | tee  /etc/apt/sources.list.d/speedtest.list
RUN apt-get update && apt-get install -y speedtest
RUN update-ca-certificates
RUN apt-get install -y curl
RUN curl -sL https://deb.nodesource.com/setup_11.x  | bash -
RUN apt-get -y install nodejs
RUN export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=True; npm install hiper -g
COPY client.ovpn /root/client.ovpn
COPY speedtest.py /tmp/speedtest.py
COPY launch_firefox.sh /tmp/launch_firefox.sh
RUN chmod +x /tmp/launch_firefox.sh
CMD exec tail -f /dev/null