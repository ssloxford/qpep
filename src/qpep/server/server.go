package server

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/tls"
	"crypto/x509"
	"encoding/hex"
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
	streams      []quic.Stream
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
		//log.Printf("Opening QUIC StreamID: %d\n", stream.StreamID())

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
	defer stream.Close()
	log.Printf("Opening TCP Connection to %s\n", qpepHeader.DestAddr.String())
	tcpConn, err := net.DialTimeout("tcp", qpepHeader.DestAddr.String(), time.Duration(10)*time.Second)
	if err != nil {
		log.Printf("Unable to open TCP connection from QPEP stream: %s", err)
		return
	}

	//defer tcpConn.Close()
	var streamWait sync.WaitGroup
	streamWait.Add(2)
	//quicDataStream := bufio.NewReadWriter(bufio.NewReader(stream), bufio.NewWriter(stream))
	//tcpDataStream := bufio.NewReadWriter(bufio.NewReader(tcpConn), bufio.NewWriter(tcpConn))
	//This internal function just copies data from one stream to another until it's empty
	/*streamConn := func(dst io.WriteCloser, src io.ReadCloser, logger bool) {
		//fancyCopy(dst, src, streamWait)
		//copyBuf := make([]byte, 1000)
		_, err = io.Copy(dst, src)
		//fancyCopy(dst, src, streamWait)
		dst.Close()
		src.Close()
		if err != nil {
			log.Printf("Error on Copy %s", err)
		}
		streamWait.Done()
	}*/
	streamQUICtoTCP := func(dst *net.TCPConn, src quic.Stream) {
		//fancyCopy(dst, src, streamWait)
		//copyBuf := make([]byte, 1000)
		_, err = io.Copy(dst, src)
		//fancyCopy(dst, src, streamWait)
		dst.CloseWrite()
		src.CancelRead(1)
		src.Close()
		if err != nil {
			log.Printf("Error on Copy %s", err)
		}
		streamWait.Done()
	}
	streamTCPtoQUIC := func(dst quic.Stream, src *net.TCPConn) {
		//fancyCopy(dst, src, streamWait)
		//copyBuf := make([]byte, 1000)
		_, err = io.Copy(dst, src)
		//fancyCopy(dst, src, streamWait)
		src.CloseRead()
		dst.CancelWrite(1)
		dst.Close()
		if err != nil {
			log.Printf("Error on Copy %s", err)
		}
		streamWait.Done()
	}

	//log.Printf("STREAM %s", stream.StreamID())
	//Proxy all stream content from quic to TCP and from TCP to quic
	//go streamConn(stream, tcpConn, false)
	//go streamConn(tcpConn, stream, false)

	//go fancyCopy(stream, tcpConn, streamWait)
	//go fancyCopy(tcpConn, stream, streamWait)

	go streamQUICtoTCP(tcpConn.(*net.TCPConn), stream)
	go streamTCPtoQUIC(stream, tcpConn.(*net.TCPConn))

	//we exit (and close the TCP connection) once both streams are done copying
	streamWait.Wait()
	log.Printf("Closing TCP Conn %s->%s", tcpConn.LocalAddr().String(), tcpConn.RemoteAddr().String())
}

func fancyCopy(dst io.WriteCloser, src io.Reader, wg sync.WaitGroup) {
	recvBuf := make(chan []byte, 1000)
	var err error
	var copyWait sync.WaitGroup
	copyWait.Add(1)
	go func() {
		var n int
		buf := make([]byte, 10000)
		for {
			log.Printf("-----------------------------Read-------------------\n")
			if n, err = io.ReadFull(src, buf); err != nil {
				log.Printf("io.Read error %s\n", err.Error())
				copyWait.Done()
				return
			}
			log.Printf("-----------------------------Read %d bytes------done\n", n)
			recvBuf <- buf
			log.Printf("-----------------------------Sending channel------done\n", n)
		}
	}()
	go func() {
		for {
			buf := <-recvBuf
			var writeBytes int
			log.Printf("-----------------------------Write-------------------\n")
			writeBytes, err = dst.Write(buf)
			if err != nil {
				log.Printf("stream.Write failed: %s", err)
				copyWait.Done()
				return
			}
			log.Printf("-------------------------write Done, bytes: %d", writeBytes)
		}
	}()
	copyWait.Wait()
	log.Println("Done Streaming")
	//wg.Done()
}

func copyBuffer(dst io.Writer, src io.Reader, buf []byte, logger bool, streamId int) (written int64, err error) {
	// If the reader has a WriteTo method, use it to do the copy.
	// Avoids an allocation and a copy.
	if wt, ok := src.(io.WriterTo); ok {
		return wt.WriteTo(dst)
	}
	// Similarly, if the writer has a ReadFrom method, use it to do the copy.
	if rt, ok := dst.(io.ReaderFrom); ok {
		return rt.ReadFrom(src)
	}
	if buf == nil {
		size := 32 * 1024
		if l, ok := src.(*io.LimitedReader); ok && int64(size) > l.N {
			if l.N < 1 {
				size = 1
			} else {
				size = int(l.N)
			}
		}
		buf = make([]byte, size)
	}
	for {
		nr, er := src.Read(buf)
		if nr > 0 {
			if logger {
				log.Printf("Read %d from Buffer (Stream %d)", nr, streamId)
				log.Printf("Bytes are %s\n", hex.Dump(buf[0:nr]))
			}
			nw, ew := dst.Write(buf[0:nr])
			if logger {
				log.Printf("Written %d to Buffer", nw)
			}
			if nw > 0 {
				written += int64(nw)
			}
			if ew != nil {
				err = ew
				break
			}
			if nr != nw {
				err = io.ErrShortWrite
				break
			}
		}
		if er != nil {
			if er != io.EOF {
				err = er
			}
			break
		}
	}
	return written, err
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
