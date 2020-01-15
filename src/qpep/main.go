package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"qpep/client"
	"qpep/server"
	"qpep/shared"
)

func main() {
	clientFlag := flag.Bool("client", false, "a bool")
	ackElicitingFlag := flag.Int("acks", 10, "Number of acks to bundle")
	ackDecimationFlag := flag.Int("decimate", 4, "Denominator of Ack Decimation Ratio")
	gatewayFlag := flag.String("gateway", "198.18.0.254", "IP address of gateway running qpep")
	flag.Parse()
	shared.QuicConfiguration.AckElicitingPacketsBeforeAck = *ackElicitingFlag
	shared.QuicConfiguration.AckDecimationDenominator = *ackDecimationFlag
	client.ClientConfiguration.GatewayHost = *gatewayFlag

	if *clientFlag {
		fmt.Println("Running Client")
		go client.RunClient()
	} else {
		go server.RunServer()
	}
	interruptListener := make(chan os.Signal)
	signal.Notify(interruptListener, os.Interrupt)
	<-interruptListener
	log.Println("Exiting...")
	os.Exit(1)
}
