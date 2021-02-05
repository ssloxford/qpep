FROM pavja2/qpep:terminal
# RUN echo "deb [trusted=yes] http://packages.net4sat.org/opensand xenial oldstable" | tee /etc/apt/sources.list.d/opensand.list
# RUN apt-get update
# RUN apt-get install -y opensand pepsal
# RUN apt-get install -y net-tools
# RUN apt-get install -y iputils-ping
# RUN apt-get install -y netcat
# RUN apt-get install -y software-properties-common
# RUN add-apt-repository ppa:longsleep/golang-backports
# RUN apt-get update && apt-get install -y golang-go iptables
# EXPOSE 3141
# EXPOSE 5358
# EXPOSE 5926
COPY config/term.conf /etc/opensand/daemon.conf
COPY config/entrypoint.sh /tmp/entrypoint.sh
RUN chmod +x /tmp/entrypoint.sh
COPY pepsal /usr/bin/pepsal
ENTRYPOINT /bin/bash /tmp/entrypoint.sh