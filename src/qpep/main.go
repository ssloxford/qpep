package main

import (
	"log"
	"os"
	"os/signal"
	"qpep/client"
	"qpep/server"
)

func main() {
	go client.RunClient()
	go server.RunServer()
	interruptListener := make(chan os.Signal)
	signal.Notify(interruptListener, os.Interrupt)
	<-interruptListener
	log.Println("Exiting...")
	os.Exit(1)
}
