package shared

import (
	"flag"
)

type QuicConfig struct {
	AckElicitingPacketsBeforeAck int
	AckDecimationDenominator     int
	InitialCongestionWindowPackets int
	MultiStream bool
	VarAckDelay float64
	MaxAckDelay int //in miliseconds, used to determine if decimating
	MinReceivedBeforeAckDecimation int
	ClientFlag bool
	GatewayIP string
}

var ( 
	QuicConfiguration QuicConfig
)

func init() {
	ackElicitingFlag := flag.Int("acks", 10, "Number of acks to bundle")
	ackDecimationFlag := flag.Int("decimate", 4, "Denominator of Ack Decimation Ratio")
	congestionWindowFlag := flag.Int("congestion", 4, "Number of QUIC packets for initial congestion window")
	multiStreamFlag := flag.Bool("multistream", true, "Enable multiplexed QUIC streams inside a single session")
	maxAckDelayFlag := flag.Int("ackDelay", 25, "Maximum number of miliseconds to hold back an ack for decimation")
	varAckDelayFlag := flag.Float64("varAckDelay", 0.25, "Variable number of miliseconds to hold back an ack for decimation, as multiple of RTT")
	minReceivedBeforeAckDecimationFlag := flag.Int("minBeforeDecimation", 100, "Minimum number of packets before initiating ack decimation")
	clientFlag := flag.Bool("client", false, "a bool")
	gatewayFlag := flag.String("gateway", "198.18.0.254", "IP address of gateway running qpep")

	flag.Parse()
	QuicConfiguration = QuicConfig{
		AckElicitingPacketsBeforeAck: *ackElicitingFlag,
		AckDecimationDenominator: *ackDecimationFlag, 
		InitialCongestionWindowPackets: *congestionWindowFlag,
		MultiStream: *multiStreamFlag, 
		MaxAckDelay: *maxAckDelayFlag, 
		VarAckDelay: *varAckDelayFlag, 
		MinReceivedBeforeAckDecimation: *minReceivedBeforeAckDecimationFlag,
		ClientFlag: *clientFlag,
		GatewayIP: *gatewayFlag,
	}
}