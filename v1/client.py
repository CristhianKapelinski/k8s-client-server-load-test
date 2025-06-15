# client.py
import socket
import time
import os

SERVER_IP = os.environ.get("SERVER_IP", "localhost") # IP do serviço Kubernetes
SERVER_PORT = int(os.environ.get("SERVER_PORT", 8080))
MESSAGE = os.environ.get("MESSAGE", "Hello from client!")
CLIENT_ID = os.environ.get("CLIENT_ID", "default_client")

def connect_and_send():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_IP, SERVER_PORT))
        print(f"[{CLIENT_ID}] Connected to {SERVER_IP}:{SERVER_PORT}")

        full_message = f"{MESSAGE} (from {CLIENT_ID})"
        client.send(full_message.encode('utf-8'))
        
        response = client.recv(1024)
        print(f"[{CLIENT_ID}] Received from server: {response.decode('utf-8').strip()}")
        client.close()
        return True
    except ConnectionRefusedError:
        print(f"[{CLIENT_ID}] Connection refused by {SERVER_IP}:{SERVER_PORT}. Server might not be ready.")
        return False
    except Exception as e:
        print(f"[{CLIENT_ID}] An error occurred: {e}")
        return False

if __name__ == "__main__":
    # Tenta conectar várias vezes caso o servidor ainda não esteja pronto
    max_retries = 10
    retry_delay = 5 # seconds
    for i in range(max_retries):
        print(f"[{CLIENT_ID}] Attempt {i+1}/{max_retries} to connect...")
        if connect_and_send():
            break
        time.sleep(retry_delay)
    else:
        print(f"[{CLIENT_ID}] Failed to connect to server after {max_retries} attempts.")