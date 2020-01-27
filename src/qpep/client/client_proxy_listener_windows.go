package client

// +build windows

/*NOTE: QPEP technically sort of can run locally as a windows executable but it is much more complicated to configure
The appropriate network routes. IP address information is not maintained either since windows sockets are very tricky.*/
import (
	"fmt"
	"net"
)

type ClientProxyListener struct {
	base net.Listener
}

func (listener *ClientProxyListener) Accept() (net.Conn, error) {
	return listener.AcceptTProxy()
}

func (listener *ClientProxyListener) AcceptTProxy() (*net.TCPConn, error) {
	tcpConn, err := listener.base.(*net.TCPListener).AcceptTCP()

	if err != nil {
		return nil, err
	}
	return tcpConn, nil
	//return &ProxyConn{TCPConn: tcpConn}, nil
}

func (listener *ClientProxyListener) Addr() net.Addr {
	return listener.base.Addr()
}

func (listener *ClientProxyListener) Close() error {
	return listener.base.Close()
}

func NewClientProxyListener(network string, laddr *net.TCPAddr) (net.Listener, error) {
	//Open basic TCP listener
	listener, err := net.ListenTCP(network, laddr)
	if err != nil {
		return nil, err
	}

	//Find associated file descriptor for listener to set socket options on
	fileDescriptorSource, err := listener.File()
	if err != nil {
		return nil, &net.OpError{Op: "ClientListener", Net: network, Source: nil, Addr: laddr, Err: fmt.Errorf("get file descriptor: %s", err)}
	}
	defer fileDescriptorSource.Close()

	//return a derived TCP listener object with TCProxy support
	return &ClientProxyListener{base: listener}, nil
}
