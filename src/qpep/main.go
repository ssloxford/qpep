package main

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"qpep/client"
	"qpep/server"
	"qpep/shared"
)

func main() {
	client.ClientConfiguration.GatewayHost = shared.QuicConfiguration.GatewayIP

	if shared.QuicConfiguration.ClientFlag {
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
