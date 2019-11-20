FROM ubuntu:18.04
RUN apt-get update --fix-missing
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:longsleep/golang-backports
RUN apt-get update --fix-missing
RUN apt-get install -y iptables iproute2 wget golang-go git netcat
#ENV GOPATH /root/goproxy
#RUN go get -u github.com/go-delve/delve/cmd/dlv
COPY docker/proxy/config/configure_ip.sh /root/configure_ip.sh
#COPY goproxy/ /root/goproxy
#RUN go build -gcflags "all=-N -l" -o /goproxy /root/goproxy/goproxy.go
ENTRYPOINT /bin/bash /root/configure_ip.sh; bash
#CMD /root/goproxy/bin/dlv --listen=:40000 --headless=true --api-version=2 exec /goproxy