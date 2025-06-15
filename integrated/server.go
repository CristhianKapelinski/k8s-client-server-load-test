// server.go
package main

import (
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"strconv"
)

const (
	defaultPort = 8080
)

func handleClient(conn net.Conn) {
	defer conn.Close() // Ensure the connection is closed when the function exits

	addr := conn.RemoteAddr().String()
	log.Printf("[*] Accepted connection from %s", addr)

	buffer := make([]byte, 1024)
	for {
		// Read data from the client
		n, err := conn.Read(buffer)
		if err != nil {
			if err == io.EOF {
				log.Printf("[*] Client %s disconnected", addr)
			} else {
				log.Printf("[-] Error reading from client %s: %v", addr, err)
			}
			break
		}

		message := string(buffer[:n])
		log.Printf("[*] Received from %s: %s", addr, message)

		// Echo back the received data
		_, err = conn.Write(buffer[:n])
		if err != nil {
			log.Printf("[-] Error writing to client %s: %v", addr, err)
			break
		}
	}
}

func main() {
	portStr := os.Getenv("PORT")
	port := defaultPort
	if portStr != "" {
		p, err := strconv.Atoi(portStr)
		if err != nil {
			log.Printf("Warning: Invalid PORT environment variable '%s'. Using default port %d. Error: %v", portStr, defaultPort, err)
		} else {
			port = p
		}
	}

	listener, err := net.Listen("tcp", fmt.Sprintf("0.0.0.0:%d", port))
	if err != nil {
		log.Fatalf("Error listening: %v", err)
	}
	defer listener.Close()

	log.Printf("[*] Serving on %s", listener.Addr().String())

	for {
		// Wait for a client to connect
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("[-] Error accepting connection: %v", err)
			continue
		}

		// Handle the client connection in a new goroutine
		go handleClient(conn)
	}
}