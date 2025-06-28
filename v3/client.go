// client.go
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
	defaultMessagePrefix     = "Hello from client!"
	defaultMessagesPerClient = 1
	defaultConcurrentClients = 1
	maxRetries               = 3
	retryDelay               = 5 * time.Second
)

// LogData struct to match the JSON output format expected by process_logs.py
type LogData struct {
	ClientFullID         string   `json:"client_full_id"`
	ServerIP             string   `json:"server_ip"`
	ServerPort           int      `json:"server_port"`
	MessagesSent         int      `json:"messages_sent"`
	MessagesReceived     int      `json:"messages_received"`
	ConnectionSuccess    bool     `json:"connection_success"`
	TotalLatencyMs       float64  `json:"total_latency_ms"`
	Errors               []string `json:"errors"`
	AverageLatencyMs     float64  `json:"average_latency_ms"` // Calculated before marshaling
}

/**
 * @brief Establishes a TCP connection to a server and sends multiple messages, logging results and errors.
 *
 * This function attempts to connect to a specified TCP server using the provided IP address and port.
 * For each message to be sent, it constructs a message string with a prefix and client identifier,
 * sends it to the server, and waits for a response. It measures the round-trip latency for each message,
 * tracks the number of messages sent and received, and logs any errors encountered during the process.
 * The function also maintains connection status and computes average latency. All results are output
 * via the outputLogData function.
 *
 * @param clientInstanceID        Unique integer identifier for the client instance.
 * @param serverIP                IP address of the server to connect to.
 * @param serverPort              Port number of the server to connect to.
 * @param clientIDBase            Base string for the client identifier.
 * @param messagePrefix           Prefix to use for each message sent.
 * @param numMessagesPerClient    Number of messages to send from this client.
 * @param wg                      Pointer to a sync.WaitGroup for concurrency synchronization.
 */
func connectAndSend(clientInstanceID int, serverIP string, serverPort int, clientIDBase string, messagePrefix string, numMessagesPerClient int, wg *sync.WaitGroup) {
	defer wg.Done()

	clientFullID := fmt.Sprintf("%s-%d", clientIDBase, clientInstanceID)
	logData := LogData{
		ClientFullID:      clientFullID,
		ServerIP:          serverIP,
		ServerPort:        serverPort,
		MessagesSent:      0,
		MessagesReceived:  0,
		ConnectionSuccess: false,
		TotalLatencyMs:    0,
		Errors:            []string{},
	}

	conn, err := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", serverIP, serverPort), 10*time.Second) // 10-second dial timeout
	if err != nil {
		logData.Errors = append(logData.Errors, fmt.Sprintf("Connection failed: %v", err))
		outputLogData(logData)
		return
	}
	defer conn.Close()
	logData.ConnectionSuccess = true

	// Set a deadline for reads and writes
	conn.SetDeadline(time.Now().Add(60 * time.Second)) // Overall deadline for the connection

	for i := 0; i < numMessagesPerClient; i++ {
		fullMessage := fmt.Sprintf("%s (from %s - msg %d)", messagePrefix, clientFullID, i+1)
		
		start := time.Now()
		_, err := conn.Write([]byte(fullMessage))
		if err != nil {
			logData.Errors = append(logData.Errors, fmt.Sprintf("Error sending message %d: %v", i+1, err))
			break // Stop sending messages if write fails
		}
		logData.MessagesSent++

		buffer := make([]byte, 1024)
		
		bytesRead, err := conn.Read(buffer) // Line 78 in previous version
		if err != nil {
			if err == io.EOF {
				logData.Errors = append(logData.Errors, "Server closed connection prematurely.")
			} else {
				logData.Errors = append(logData.Errors, fmt.Sprintf("Error receiving response for message %d: %v", i+1, err))
			}
			break // Stop if read fails
		}
		
		// Fix for "responseContent declared and not used":
		// If you don't need to use the `responseContent` string directly in further logic,
		// you can use the blank identifier `_` to discard it but satisfy the compiler that
		// the operation (string conversion) was performed.
		_ = string(buffer[:bytesRead]) // This explicitly uses bytesRead and discards the string value
		
		end := time.Now()
		latencyMs := float64(end.Sub(start).Nanoseconds()) / 1e6
		logData.TotalLatencyMs += latencyMs
		logData.MessagesReceived++

	}

	if logData.MessagesReceived > 0 {
		logData.AverageLatencyMs = logData.TotalLatencyMs / float64(logData.MessagesReceived)
	} else {
		logData.AverageLatencyMs = 0
	}
	outputLogData(logData)
}

func outputLogData(data LogData) {
	jsonData, err := json.Marshal(data)
	if err != nil {
		log.Printf("Error marshaling log data: %v", err)
		return
	}
	fmt.Println(string(jsonData)) // Output to stdout for redirection by run_tests.sh
}

func main() {
	serverIP := os.Getenv("SERVER_IP")
	if serverIP == "" {
		serverIP = defaultServerIP
	}

	serverPortStr := os.Getenv("SERVER_PORT")
	serverPort := defaultServerPort
	if serverPortStr != "" {
		p, err := strconv.Atoi(serverPortStr)
		if err != nil {
			log.Printf("Warning: Invalid SERVER_PORT environment variable '%s'. Using default port %d. Error: %v", serverPortStr, defaultServerPort, err)
		} else {
			serverPort = p
		}
	}

	clientIDBase := os.Getenv("CLIENT_ID")
	if clientIDBase == "" {
		clientIDBase = "default_client_pod"
	}

	numMessagesPerClientStr := os.Getenv("NUM_MESSAGES_PER_CLIENT")
	numMessagesPerClient := defaultMessagesPerClient
	if numMessagesPerClientStr != "" {
		m, err := strconv.Atoi(numMessagesPerClientStr)
		if err != nil {
			log.Printf("Warning: Invalid NUM_MESSAGES_PER_CLIENT environment variable '%s'. Using default %d. Error: %v", numMessagesPerClientStr, defaultMessagesPerClient, err)
		} else {
			numMessagesPerClient = m
		}
	}

	numConcurrentClientsStr := os.Getenv("NUM_CONCURRENT_CLIENTS")
	numConcurrentClients := defaultConcurrentClients
	if numConcurrentClientsStr != "" {
		c, err := strconv.Atoi(numConcurrentClientsStr)
		if err != nil {
			log.Printf("Warning: Invalid NUM_CONCURRENT_CLIENTS environment variable '%s'. Using default %d. Error: %v", numConcurrentClientsStr, defaultConcurrentClients, err)
		} else {
			numConcurrentClients = c
		}
	}

	log.Printf("[%s] Starting %d concurrent client tasks, each sending %d messages.", clientIDBase, numConcurrentClients, numMessagesPerClient)

	// Fix for "wg declared and not used": Removed 'var wg sync.WaitGroup' here (line 170 in your context)
	// because currentAttemptWG is used instead.

	connectedAtLeastOnce := false

	for attempt := 1; attempt <= maxRetries; attempt++ {
		currentAttemptWG := sync.WaitGroup{} // Use a new WaitGroup for each attempt

		for i := 0; i < numConcurrentClients; i++ {
			currentAttemptWG.Add(1)
			go connectAndSend(i, serverIP, serverPort, clientIDBase, defaultMessagePrefix, numMessagesPerClient, &currentAttemptWG)
		}
		currentAttemptWG.Wait() // Wait for all goroutines in this attempt to finish
		
		connectedAtLeastOnce = true 
		break // Exit retry loop after first attempt
	}

	if !connectedAtLeastOnce {
		log.Printf("[%s] Failed to run client tasks after %d attempts.", clientIDBase, maxRetries)
	}

	log.Printf("[%s] All client tasks completed.", clientIDBase)
}