package client

import "net"

type ProxyConn struct {
	*net.TCPConn
}
