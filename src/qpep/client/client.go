package client

import (
	"crypto/tls"
	"github.com/lucas-clemente/quic-go"
	"golang.org/x/net/context"
	"io"
	"log"
	"net"
	"os"
	"os/signal"
	"qpep/shared"
	"strconv"
	"sync"
)

var (
	proxyListener net.Listener
	clientConfig  = ClientConfig{ListenHost: "0.0.0.0", ListenPort: 8080,
		GatewayHost: "198.18.0.254", GatewayPort: 4242,
		QuicStreamTimeout: 2}
)

type ClientConfig struct {
	ListenHost        string
	ListenPort        int
	GatewayHost       string
	GatewayPort       int
	QuicStreamTimeout int
}

func RunClient() {
	log.Println("Starting TCP-QPEP Tunnel Listener")
	log.Printf("Binding to TCP %s:%d", clientConfig.ListenHost, clientConfig.ListenPort)
	var err error
	proxyListener, err = NewClientProxyListener("tcp", &net.TCPAddr{IP: net.ParseIP(clientConfig.ListenHost),
		Port: clientConfig.ListenPort})
	if err != nil {
		log.Fatalf("Encountered error when binding client proxy listener: %s", err)
	}
	defer proxyListener.Close()

	go ListenTCPConn()

	interruptListener := make(chan os.Signal)
	signal.Notify(interruptListener, os.Interrupt)
	<-interruptListener
	log.Println("Exiting...")
	os.Exit(1)
}

func ListenTCPConn() {
	for {
		conn, err := proxyListener.Accept()
		if err != nil {
			if netErr, ok := err.(net.Error); ok && netErr.Temporary() {
				log.Printf("Temporary error when accepting connection: %s", netErr)
			}
			log.Fatalf("Unrecoverable error while accepting connection: %s", err)
			return
		}

		go handleTCPConn(conn)
	}

}

func handleTCPConn(tcpConn net.Conn) {
	log.Printf("Accepting TCP connection from %s with destination of %s", tcpConn.RemoteAddr().String(), tcpConn.LocalAddr().String())
	defer tcpConn.Close()

	quicStream, err := openQuicStream()
	if err != nil {
		log.Fatalf("Unable to open quic stream: %s", err)
		return
	}
	//give the stream some time to setup
	var streamWait sync.WaitGroup
	streamWait.Add(clientConfig.QuicStreamTimeout)
	sessionHeader := shared.QpepHeader{SourceAddr: tcpConn.RemoteAddr().(*net.TCPAddr), DestAddr: tcpConn.LocalAddr().(*net.TCPAddr)}

	//Send header addressing information for the stream (new quic stream for each TCP connection?)

	streamConn := func(dst io.Writer, src io.Reader) {
		io.Copy(dst, src)
		streamWait.Done()
	}

	quicStream.Write(sessionHeader.ToBytes())
	//Proxy all stream content from quic to TCP and from TCP to quic
	go streamConn(quicStream, tcpConn)
	go streamConn(tcpConn, quicStream)

	streamWait.Wait()
}

func openQuicStream() (quic.Stream, error) {
	tlsConf := &tls.Config{InsecureSkipVerify: true, NextProtos: []string{"qpep-demo"}}
	gatewayPath := clientConfig.GatewayHost + ":" + strconv.Itoa(clientConfig.GatewayPort)
	session, err := quic.DialAddr(gatewayPath, tlsConf, nil)
	if err != nil {
		log.Printf("Error opening tls session: %s", err)
		return nil, err
	}

	stream, err := session.OpenStreamSync(context.Background())
	if err != nil {
		log.Printf("Error opening quic stream: %s", err)
		return nil, err
	}

	return stream, nil
}
