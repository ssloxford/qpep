package server

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"encoding/pem"
	"github.com/lucas-clemente/quic-go"
	"golang.org/x/net/context"
	"io"
	"log"
	"math/big"
	"net"
	"os"
	"os/signal"
	"qpep/client"
	"qpep/shared"
	"strconv"
	"sync"
	"time"
)

var (
	serverConfig = ServerConfig{ListenHost: "0.0.0.0", ListenPort: 4242}
	quicListener quic.Listener
	quicSession  quic.Session
)

type ServerConfig struct {
	ListenHost string
	ListenPort int
}

func RunServer() {
	listenAddr := serverConfig.ListenHost + ":" + strconv.Itoa(serverConfig.ListenPort)
	log.Printf("Opening QPEP Server on: %s", listenAddr)
	var err error
	quicListener, err = quic.ListenAddr(listenAddr, generateTLSConfig(), &client.QuicClientConfiguration)
	if err != nil {
		log.Fatalf("Encountered error while binding QUIC listener: %s", err)
		return
	}
	defer quicListener.Close()

	go ListenQuicSession()

	interruptListener := make(chan os.Signal)
	signal.Notify(interruptListener, os.Interrupt)
	<-interruptListener
	log.Println("Exiting...")
	os.Exit(1)
}

func ListenQuicSession() {
	for {
		var err error
		quicSession, err = quicListener.Accept(context.Background())
		if err != nil {
			log.Printf("Unrecoverable error while accepting QUIC session: %s", err)
			return
		}
		go ListenQuicConn(quicSession)
	}
}

func ListenQuicConn(quicSession quic.Session) {
	for {
		stream, err := quicSession.AcceptStream(context.Background())
		if err != nil {
			if err.Error() != "NO_ERROR: No recent network activity" {
				log.Printf("Unrecoverable error while accepting QUIC stream: %s", err)
			}
			return
		}
		log.Printf("Opening QUIC StreamID: %d\n", stream.StreamID())

		go HandleQuicStream(stream)
	}
}

func HandleQuicStream(stream quic.Stream) {
	qpepHeader, err := shared.GetQpepHeader(stream)
	if err != nil {
		log.Printf("Unable to find QPEP header: %s", err)
		return
	}
	go handleTCPConn(stream, qpepHeader)
}

func handleTCPConn(stream quic.Stream, qpepHeader shared.QpepHeader) {
	log.Printf("Opening TCP Connection to %s\n", qpepHeader.DestAddr.String())
	tcpConn, err := net.DialTimeout("tcp", qpepHeader.DestAddr.String(), time.Duration(10)*time.Second)
	if err != nil {
		log.Printf("Unable to open TCP connection from QPEP stream: %s", err)
		return
	}
	log.Printf("Opened TCP Conn")

	var streamWait sync.WaitGroup
	streamWait.Add(2)
	streamQUICtoTCP := func(dst *net.TCPConn, src quic.Stream) {
		_, err = io.Copy(dst, src)
		dst.SetLinger(3)
		dst.Close()
		if err != nil {
			log.Printf("Error on Copy %s", err)
		}
		streamWait.Done()
	}
	streamTCPtoQUIC := func(dst quic.Stream, src *net.TCPConn) {
		_, err = io.Copy(dst, src)
		log.Printf("Finished Copying TCP Conn %s->%s", src.LocalAddr().String(), src.RemoteAddr().String())
		src.SetLinger(3)
		src.Close()
		if err != nil {
			log.Printf("Error on Copy %s", err)
		}
		streamWait.Done()
	}

	go streamQUICtoTCP(tcpConn.(*net.TCPConn), stream)
	go streamTCPtoQUIC(stream, tcpConn.(*net.TCPConn))

	//we exit (and close the TCP connection) once both streams are done copying
	streamWait.Wait()
	stream.CancelRead(0)
	stream.CancelWrite(0)
	log.Printf("Closing TCP Conn %s->%s", tcpConn.LocalAddr().String(), tcpConn.RemoteAddr().String())
}

func generateTLSConfig() *tls.Config {
	key, err := rsa.GenerateKey(rand.Reader, 1024)
	if err != nil {
		panic(err)
	}
	template := x509.Certificate{SerialNumber: big.NewInt(1)}
	certDER, err := x509.CreateCertificate(rand.Reader, &template, &template, &key.PublicKey, key)
	if err != nil {
		panic(err)
	}
	keyPEM := pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(key)})
	certPEM := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: certDER})

	tlsCert, err := tls.X509KeyPair(certPEM, keyPEM)
	if err != nil {
		panic(err)
	}
	return &tls.Config{
		Certificates: []tls.Certificate{tlsCert},
		NextProtos:   []string{"qpep-demo"},
	}
}
