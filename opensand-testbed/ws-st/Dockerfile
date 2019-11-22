FROM ubuntu:16.04
RUN echo "deb [trusted=yes] http://packages.net4sat.org/opensand xenial stable" | tee /etc/apt/sources.list.d/opensand.list
RUN apt-get update
RUN apt-get install -y netcat
RUN apt-get install -y iputils-ping
RUN apt-get install -y net-tools
RUN apt-get install -y iproute2
RUN apt-get update && apt-get install -y qupzilla ca-certificates
RUN update-ca-certificates
COPY launch_firefox.sh /tmp/launch_firefox.sh
RUN chmod +x /tmp/launch_firefox.sh
CMD exec tail -f /dev/null