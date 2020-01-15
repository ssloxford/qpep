package shared

type QuicConfig struct {
	AckElicitingPacketsBeforeAck int
	AckDecimationDenominator     int
}

var QuicConfiguration = QuicConfig{AckElicitingPacketsBeforeAck: 20, AckDecimationDenominator: 4}
