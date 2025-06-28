// client.go (Otimizado para Mínimos Prints)
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"strconv"
	"sync"
	"time"
)

const (
	defaultServerIP          = "localhost"
	defaultServerPort        = 8080
	defaultMessagesPerClient = 1
	defaultConcurrentClients = 1
)

type LogData struct {
	ClientFullID      string   `json:"client_full_id"`
	ServerIP          string   `json:"server_ip"`
	ServerPort        int      `json:"server_port"`
	MessagesSent      int      `json:"messages_sent"`
	MessagesReceived  int      `json:"messages_received"`
	ConnectionSuccess bool     `json:"connection_success"`
	TotalLatencyMs    float64  `json:"total_latency_ms"`
	Errors            []string `json:"errors"`
	AverageLatencyMs  float64  `json:"average_latency_ms"`
}

func connectAndSend(clientInstanceID int, serverIP string, serverPort int, clientIDBase string, numMessagesPerClient int, wg *sync.WaitGroup) {
	defer wg.Done()

	clientFullID := fmt.Sprintf("%s-%d", clientIDBase, clientInstanceID)
	logData := LogData{
		ClientFullID:      clientFullID,
		ServerIP:          serverIP,
		ServerPort:        serverPort,
		Errors:            []string{},
	}

	conn, err := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", serverIP, serverPort), 10*time.Second)
	if err != nil {
		logData.Errors = append(logData.Errors, fmt.Sprintf("Connection failed: %v", err))
		outputLogData(logData) // ESSENCIAL: Envia o resultado mesmo em caso de falha de conexão
		return
	}
	defer conn.Close()
	logData.ConnectionSuccess = true

	conn.SetDeadline(time.Now().Add(60 * time.Second))

	for i := 0; i < numMessagesPerClient; i++ {
		fullMessage := fmt.Sprintf("msg %d from %s", i+1, clientFullID)
		
		start := time.Now()
		_, err := conn.Write([]byte(fullMessage))
		if err != nil {
			logData.Errors = append(logData.Errors, fmt.Sprintf("Error sending message: %v", err))
			break
		}
		logData.MessagesSent++

		buffer := make([]byte, 1024)
		_, err = conn.Read(buffer)
		if err != nil {
			if err != io.EOF {
				logData.Errors = append(logData.Errors, fmt.Sprintf("Error receiving response: %v", err))
			}
			break
		}
		
		end := time.Now()
		logData.TotalLatencyMs += float64(end.Sub(start).Nanoseconds()) / 1e6
		logData.MessagesReceived++
	}

	if logData.MessagesReceived > 0 {
		logData.AverageLatencyMs = logData.TotalLatencyMs / float64(logData.MessagesReceived)
	}
	outputLogData(logData) // ESSENCIAL: Envia o resultado final da tarefa
}

// ESSENCIAL: Esta função imprime os dados JSON para o stdout, que é lido pelo process_logs.py. Não remova.
func outputLogData(data LogData) {
	jsonData, err := json.Marshal(data)
	if err != nil {
		// Este log vai para stderr e só acontece se houver um erro de programação. Mantenha.
		log.Printf("Error marshaling log data: %v", err)
		return
	}
	fmt.Println(string(jsonData))
}

func main() {
	serverIP := os.Getenv("SERVER_IP")
	if serverIP == "" { serverIP = defaultServerIP }

	serverPort := defaultServerPort
	if p, err := strconv.Atoi(os.Getenv("SERVER_PORT")); err == nil { serverPort = p }

	clientIDBase := os.Getenv("CLIENT_ID")
	if clientIDBase == "" { clientIDBase = "default_client_pod" }

	numMessagesPerClient := defaultMessagesPerClient
	if m, err := strconv.Atoi(os.Getenv("NUM_MESSAGES_PER_CLIENT")); err == nil { numMessagesPerClient = m }

	numConcurrentClients := defaultConcurrentClients
	if c, err := strconv.Atoi(os.Getenv("NUM_CONCURRENT_CLIENTS")); err == nil { numConcurrentClients = c }

	// LOG REMOVIDO: Mensagem de início.
	// log.Printf("[%s] Starting %d concurrent client tasks, each sending %d messages.", clientIDBase, numConcurrentClients, numMessagesPerClient)

	var wg sync.WaitGroup
	for i := 0; i < numConcurrentClients; i++ {
		wg.Add(1)
		go connectAndSend(i, serverIP, serverPort, clientIDBase, numMessagesPerClient, &wg)
	}
	wg.Wait()

	// LOG REMOVIDO: Mensagem de fim.
	// log.Printf("[%s] All client tasks completed.", clientIDBase)
}