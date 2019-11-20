package server

import (
	"bufio"
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
	"qpep/shared"
	"strconv"
)

var (
	serverConfig = ServerConfig{ListenHost: "0.0.0.0", ListenPort: 4242}
	quicListener quic.Listener
)

type ServerConfig struct {
	ListenHost string
	ListenPort int
}

func RunServer() {
	listenAddr := serverConfig.ListenHost + ":" + strconv.Itoa(serverConfig.ListenPort)
	log.Printf("Opening QPEP Server on: %s", listenAddr)
	var err error
	quicListener, err = quic.ListenAddr(listenAddr, generateTLSConfig(), nil)
	if err != nil {
		log.Fatalf("Encountered error while binding QUIC listener: %s", err)
		return
	}
	defer quicListener.Close()

	go ListenQuicConn()

	interruptListener := make(chan os.Signal)
	signal.Notify(interruptListener, os.Interrupt)
	<-interruptListener
	log.Println("Exiting...")
	os.Exit(1)
}

func ListenQuicConn() {
	for {
		quicSession, err := quicListener.Accept(context.Background())
		if err != nil {
			log.Fatalf("Unrecoverable error while accepting QUIC session: %s", err)
			return
		}

		stream, err := quicSession.AcceptStream(context.Background())
		if err != nil {
			log.Fatalf("Unrecoverable error while accepting QUIC stream: %s", err)
		}
		log.Printf("Opening QUIC StreamID: %d\n", stream.StreamID())

		go HandleQuicStream(stream)
	}
}

func HandleQuicStream(stream quic.Stream) {
	streamReader := bufio.NewReader(stream)
	headerLength, err := getQpepHeaderLength(streamReader)
	if err != nil {
		log.Fatalf("Unable to find QPEP header: %s", err)
		return
	}

	headerBytes := make([]byte, headerLength)
	readLength, err := streamReader.Read(headerBytes)
	if err != nil {
		log.Fatalf("Unable to read QPEP header. Only read %d bytes: %s", readLength, err)
		return
	}
	qpepHeader := shared.QpepHeaderFromBytes(headerBytes)
	log.Printf("Opening TCP Connection to %s\n", qpepHeader.DestAddr.String())
	tcpConn, err := net.Dial("tcp", qpepHeader.DestAddr.String())
	if err != nil {
		log.Fatalf("Unable to open TCP connection from QPEP stream: %s", err)
	}

	streamConn := func(dst io.WriteCloser, src io.Reader) {
		io.Copy(dst, src)
		dst.Close()
	}

	go streamConn(tcpConn, streamReader)
	go streamConn(stream, tcpConn)

}

func getQpepHeaderLength(streamReader *bufio.Reader) (int, error) {
	preambleBytes, err := streamReader.Peek(shared.QPEP_PREAMBLE_LENGTH)
	if err != nil {
		return 0, err
	}
	return shared.GetHeaderLength(preambleBytes), nil
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
