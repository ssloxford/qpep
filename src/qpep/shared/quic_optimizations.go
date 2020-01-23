package shared

type QuicConfig struct {
	AckElicitingPacketsBeforeAck int
	AckDecimationDenominator     int
	InitialCongestionWindowPackets int
}

var QuicConfiguration = QuicConfig{AckElicitingPacketsBeforeAck: 20, AckDecimationDenominator: 4, InitialCongestionWindowPackets: 10}
