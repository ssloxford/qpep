package shared

import (
	"encoding/binary"
	"io"
	"net"
)

const QPEP_PREAMBLE_LENGTH = 2

type QpepHeader struct {
	SourceAddr *net.TCPAddr
	DestAddr   *net.TCPAddr
}

func (header QpepHeader) ToBytes() []byte {
	var byteOutput []byte

	sourceType := getNetworkTypeFromAddr(header.SourceAddr)
	destType := getNetworkTypeFromAddr(header.DestAddr)
	byteOutput = append(byteOutput, sourceType)
	byteOutput = append(byteOutput, destType)

	byteOutput = append(byteOutput, ipToBytes(header.SourceAddr.IP, sourceType)...)
	byteOutput = append(byteOutput, portToBytes(header.SourceAddr.Port)...)

	byteOutput = append(byteOutput, ipToBytes(header.DestAddr.IP, destType)...)
	byteOutput = append(byteOutput, portToBytes(header.DestAddr.Port)...)

	return byteOutput
}

func GetQpepHeader(stream io.Reader) (QpepHeader, error) {
	header := QpepHeader{}
	preamble := make([]byte, QPEP_PREAMBLE_LENGTH)
	_, err := stream.Read(preamble)
	if err != nil {
		return header, err
	}

	var sourceIpEnd int
	if preamble[0] == 0x04 {
		sourceIpEnd = net.IPv4len
	} else {
		sourceIpEnd = net.IPv6len
	}

	sourcePortEnd := sourceIpEnd + 2

	var destIpEnd int
	if preamble[1] == 0x04 {
		destIpEnd = sourcePortEnd + net.IPv4len
	} else {
		destIpEnd = sourcePortEnd + net.IPv6len
	}
	destPortEnd := destIpEnd + 2

	byteInput := make([]byte, destPortEnd)
	_, err = stream.Read(byteInput)
	if err != nil {
		return header, err
	}
	srcIPAddr := net.IP(byteInput[0:sourceIpEnd])
	srcPort := int(binary.LittleEndian.Uint16(byteInput[sourceIpEnd:sourcePortEnd]))

	destIPAddr := net.IP(byteInput[sourcePortEnd:destIpEnd])
	destPort := int(binary.LittleEndian.Uint16(byteInput[destIpEnd:destPortEnd]))

	srcAddr := &net.TCPAddr{IP: srcIPAddr, Port: srcPort}
	dstAddr := &net.TCPAddr{IP: destIPAddr, Port: destPort}
	return QpepHeader{SourceAddr: srcAddr, DestAddr: dstAddr}, nil
}

func QpepHeaderFromBytes(byteInput []byte) QpepHeader {
	var sourceIpEnd int
	if byteInput[0] == 0x04 {
		sourceIpEnd = QPEP_PREAMBLE_LENGTH * +net.IPv4len
	} else {
		sourceIpEnd = QPEP_PREAMBLE_LENGTH + net.IPv6len
	}
	sourcePortEnd := sourceIpEnd + 2

	var destIpEnd int
	if byteInput[1] == 0x04 {
		destIpEnd = sourcePortEnd + net.IPv4len
	} else {
		destIpEnd = sourcePortEnd + net.IPv6len
	}
	destPortEnd := destIpEnd + 2

	srcIPAddr := net.IP(byteInput[QPEP_PREAMBLE_LENGTH:sourceIpEnd])
	srcPort := int(binary.LittleEndian.Uint16(byteInput[sourceIpEnd:sourcePortEnd]))

	destIPAddr := net.IP(byteInput[sourcePortEnd:destIpEnd])
	destPort := int(binary.LittleEndian.Uint16(byteInput[destIpEnd:destPortEnd]))

	srcAddr := &net.TCPAddr{IP: srcIPAddr, Port: srcPort}
	dstAddr := &net.TCPAddr{IP: destIPAddr, Port: destPort}
	return QpepHeader{SourceAddr: srcAddr, DestAddr: dstAddr}
}

func ipToBytes(addr net.IP, addrType byte) []byte {
	if addrType == 0x04 {
		return addr.To4()
	} else {
		return addr.To16()
	}
}

func portToBytes(port int) []byte {
	result := make([]byte, 2)
	binary.LittleEndian.PutUint16(result, uint16(port))
	return result
}

func GetHeaderLength(preamble []byte) int {
	headerLength := QPEP_PREAMBLE_LENGTH
	if preamble[0] == 0x04 {
		headerLength += net.IPv4len
	} else {
		headerLength += net.IPv6len
	}

	if preamble[1] == 0x04 {
		headerLength += net.IPv4len
	} else {
		headerLength += net.IPv6len
	}

	//add four bytes for TCP port numbers
	headerLength += 4
	return headerLength
}

func getNetworkTypeFromAddr(addr *net.TCPAddr) byte {
	if addr.IP.To4() != nil {
		return 0x04
	} else if addr.IP.To16() != nil {
		return 0x06
	} else {
		//TODO: Catch errors like this
		return 0x00
	}
}
