package client

import (
	"fmt"
	"golang.org/x/sys/unix"
	"net"
	"syscall"
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

	//Make the port transparent so the gateway can see the real origin IP address (invisible proxy within satellite environment)
	if err = syscall.SetsockoptInt(int(fileDescriptorSource.Fd()), syscall.SOL_IP, syscall.IP_TRANSPARENT, 1); err != nil {
		return nil, &net.OpError{Op: "listen", Net: network, Source: nil, Addr: laddr, Err: fmt.Errorf("set socket option: IP_TRANSPARENT: %s", err)}
	}

	if err = syscall.SetsockoptInt(int(fileDescriptorSource.Fd()), syscall.SOL_TCP, unix.TCP_FASTOPEN, 1); err != nil {
		return nil, &net.OpError{Op: "listen", Net: network, Source: nil, Addr: laddr, Err: fmt.Errorf("set socket option: TCP_FASTOPEN: %s", err)}
	}

	//return a derived TCP listener object with TCProxy support
	return &ClientProxyListener{base: listener}, nil
}
