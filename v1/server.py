# server.py
import socket
import threading
import os

PORT = int(os.environ.get("PORT", 8080))
HOST = '0.0.0.0'

def handle_client(client_socket, addr):
    print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            print(f"[*] Received from {addr[0]}:{addr[1]}: {data.decode('utf-8').strip()}")
            client_socket.sendall(data) # Echo back the received data
    except Exception as e:
        print(f"[-] Error handling client {addr[0]}:{addr[1]}: {e}")
    finally:
        print(f"[*] Client {addr[0]}:{addr[1]} disconnected")
        client_socket.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[*] Listening on {HOST}:{PORT}")

    while True:
        client_socket, addr = server.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_handler.start()

if __name__ == "__main__":
    main()