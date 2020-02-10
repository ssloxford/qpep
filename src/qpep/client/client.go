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
	"time"
)

var (
	proxyListener       net.Listener
	ClientConfiguration = ClientConfig{ListenHost: "0.0.0.0", ListenPort: 8080,
		GatewayHost: "198.18.0.254", GatewayPort: 4242,
		QuicStreamTimeout: 2, MultiStream: shared.QuicConfiguration.MultiStream,
		ConnectionRetries: 3,
		IdleTimeout:       time.Duration(300) * time.Second}
	quicSession             quic.Session
	QuicClientConfiguration = quic.Config{
		IdleTimeout:        time.Duration(300) * time.Second,
		MaxIncomingStreams: 40000,
	}
)

type ClientConfig struct {
	ListenHost        string
	ListenPort        int
	GatewayHost       string
	GatewayPort       int
	QuicStreamTimeout int
	MultiStream       bool
	IdleTimeout       time.Duration
	ConnectionRetries int
}

func RunClient() {
	log.Println("Starting TCP-QPEP Tunnel Listener")
	log.Printf("Binding to TCP %s:%d", ClientConfiguration.ListenHost, ClientConfiguration.ListenPort)
	var err error
	proxyListener, err = NewClientProxyListener("tcp", &net.TCPAddr{IP: net.ParseIP(ClientConfiguration.ListenHost),
		Port: ClientConfiguration.ListenPort})
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
	var quicStream quic.Stream = nil
	// if we allow for multiple streams in a session, lets try and open on the existing session
	if ClientConfiguration.MultiStream {
		//if we have already opened a quic session, lets check if we've expired our stream
		if quicSession != nil {
			var err error
			log.Printf("Trying to open on existing session")
			quicStream, err = quicSession.OpenStream()
			// if we weren't able to open a quicStream on that session (usually inactivity timeout), we can try to open a new session
			if err != nil {
				log.Printf("Unable to open new stream on existing QUIC session: %s\n")
				quicStream = nil
			} else {
				log.Printf("Opened a new stream: %d", quicStream.StreamID())
			}
		}
	}
	// if we haven't opened a stream from multistream, we can open one with a new session
	if quicStream == nil {
		// open a new quicSession (with all the TLS jazz)
		var err error
		quicSession, err = openQuicSession()
		// if we were unable to open a quic session, drop the TCP connection with RST
		if err != nil {
			return
		}

		//Open a stream to send data on this new session
		quicStream, err = quicSession.OpenStreamSync(context.Background())
		// if we cannot open a stream on this session, send a TCP RST and let the client decide to try again
		if err != nil {
			log.Printf("Unable to open QUIC stream: %s\n", err)
			return
		}
	}
	defer quicStream.Close()

	//We want to wait for both the upstream and downstream to finish so we'll set a wait group for the threads
	var streamWait sync.WaitGroup
	streamWait.Add(2)

	//Set our custom header to the QUIC session so the server can generate the correct TCP handshake on the other side
	sessionHeader := shared.QpepHeader{SourceAddr: tcpConn.RemoteAddr().(*net.TCPAddr), DestAddr: tcpConn.LocalAddr().(*net.TCPAddr)}
	quicStream.Write(sessionHeader.ToBytes())
	log.Printf("Sent QUIC header to server")

	streamQUICtoTCP := func(dst *net.TCPConn, src quic.Stream) {
		_, err := io.Copy(dst, src)
		dst.SetLinger(3)
		dst.Close()
		//src.CancelRead(1)
		//src.Close()
		if err != nil {
			log.Printf("Error on Copy %s", err)
		}
		streamWait.Done()
	}

	streamTCPtoQUIC := func(dst quic.Stream, src *net.TCPConn) {
		_, err := io.Copy(dst, src)
		src.SetLinger(3)
		src.Close()
		//src.CloseWrite()
		//dst.CancelWrite(1)
		//dst.Close()
		if err != nil {
			log.Printf("Error on Copy %s", err)
		}
		streamWait.Done()
	}

	//Proxy all stream content from quic to TCP and from TCP to quic
	go streamTCPtoQUIC(quicStream, tcpConn.(*net.TCPConn))
	go streamQUICtoTCP(tcpConn.(*net.TCPConn), quicStream)

	//we exit (and close the TCP connection) once both streams are done copying
	streamWait.Wait()
	quicStream.Close()
	log.Printf("Done sending data on %d", quicStream.StreamID())
}

func openQuicSession() (quic.Session, error) {
	var err error
	var session quic.Session
	tlsConf := &tls.Config{InsecureSkipVerify: true, NextProtos: []string{"qpep-demo"}}
	gatewayPath := ClientConfiguration.GatewayHost + ":" + strconv.Itoa(ClientConfiguration.GatewayPort)
	quicClientConfig := QuicClientConfiguration
	for i := 0; i < ClientConfiguration.ConnectionRetries; i++ {
		session, err = quic.DialAddr(gatewayPath, tlsConf, &quicClientConfig)
		if err == nil {
			return session, nil
		} else {
			log.Printf("Failed to Open QUIC Session: %s\n    Retrying...\n", err)
		}
	}

	log.Printf("Max Retries Exceeded. Unable to Open QUIC Session: %s\n", err)
	return nil, err
}

func openQuicStream(session quic.Session) (quic.Stream, error) {

	stream, err := session.OpenStreamSync(context.Background())
	if err != nil {

		//If the current tunnel has timed out, open a new tunnel for traffic
		if err.Error() == "NO_ERROR: No recent network activity" {
			quicSession, err = openQuicSession()
			stream, err = quicSession.OpenStreamSync(context.Background())
		} else {
			log.Printf("Error opening quic stream: %s", err)
			return nil, err
		}
	}

	return stream, nil
}
