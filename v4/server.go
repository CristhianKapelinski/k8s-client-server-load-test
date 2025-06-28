// server.go (Otimizado para Mínimos Logs)
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
	defer conn.Close()

	// LOG REMOVIDO: Aceitação de conexão. Descomente apenas para depuração.
	// addr := conn.RemoteAddr().String()
	// log.Printf("[*] Accepted connection from %s", addr)

	buffer := make([]byte, 1024)
	for {
		n, err := conn.Read(buffer)
		if err != nil {
			// Mantemos o log de erro, mas removemos o log de desconexão normal (io.EOF)
			if err != io.EOF {
				log.Printf("[-] Error reading from client: %v", err)
			}
			break
		}

		// LOG REMOVIDO: Mensagem recebida. Este era o log mais custoso.
		// message := string(buffer[:n])
		// log.Printf("[*] Received from %s: %s", addr, message)

		// Echo back
		_, err = conn.Write(buffer[:n])
		if err != nil {
			log.Printf("[-] Error writing to client: %v", err)
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
			// O log de aviso na inicialização é mantido, pois não afeta a performance do teste.
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

	// Mantemos o log de inicialização para confirmar que o servidor está no ar.
	log.Printf("[*] Serving on %s", listener.Addr().String())

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("[-] Error accepting connection: %v", err)
			continue
		}
		go handleClient(conn)
	}
}