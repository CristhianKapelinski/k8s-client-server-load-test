# client.py
import asyncio
import time
import os
import json # For structured logging

SERVER_IP = os.environ.get("SERVER_IP", "localhost")
SERVER_PORT = int(os.environ.get("SERVER_PORT", 8080))
MESSAGE_PREFIX = os.environ.get("MESSAGE_PREFIX", "Hello from client!")
CLIENT_ID_BASE = os.environ.get("CLIENT_ID", "default_client_pod")
NUM_MESSAGES_PER_CLIENT = int(os.environ.get("NUM_MESSAGES_PER_CLIENT", 1))
NUM_CONCURRENT_CLIENTS = int(os.environ.get("NUM_CONCURRENT_CLIENTS", 1))

async def connect_and_send(client_instance_id):
    client_full_id = f"{CLIENT_ID_BASE}-{client_instance_id}"
    log_data = {
        "client_full_id": client_full_id,
        "server_ip": SERVER_IP,
        "server_port": SERVER_PORT,
        "messages_sent": 0,
        "messages_received": 0,
        "connection_success": False,
        "total_latency_ms": 0,
        "errors": []
    }

    try:
        reader, writer = await asyncio.open_connection(SERVER_IP, SERVER_PORT)
        log_data["connection_success"] = True
        # print(f"[{client_full_id}] Connected to {SERVER_IP}:{SERVER_PORT}")

        for i in range(NUM_MESSAGES_PER_CLIENT):
            full_message = f"{MESSAGE_PREFIX} (from {client_full_id} - msg {i+1})"
            
            start_time = time.perf_counter()
            writer.write(full_message.encode('utf-8'))
            await writer.drain()
            log_data["messages_sent"] += 1

            response = await reader.read(1024)
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            log_data["total_latency_ms"] += latency_ms
            log_data["messages_received"] += 1

            # print(f"[{client_full_id}] Sent: '{full_message}', Received: '{response.decode('utf-8').strip()}' Latency: {latency_ms:.2f}ms")

    except ConnectionRefusedError:
        error_msg = f"Connection refused by {SERVER_IP}:{SERVER_PORT}. Server might not be ready."
        log_data["errors"].append(error_msg)
        # print(f"[{client_full_id}] {error_msg}")
    except asyncio.TimeoutError:
        error_msg = f"Connection timeout to {SERVER_IP}:{SERVER_PORT}."
        log_data["errors"].append(error_msg)
        # print(f"[{client_full_id}] {error_msg}")
    except Exception as e:
        error_msg = f"An error occurred: {e}"
        log_data["errors"].append(error_msg)
        # print(f"[{client_full_id}] {error_msg}")
    finally:
        if 'writer' in locals() and not writer.is_closing():
            writer.close()
            await writer.wait_closed()
        
        # Log results for this client instance
        if log_data["messages_received"] > 0:
            log_data["average_latency_ms"] = log_data["total_latency_ms"] / log_data["messages_received"]
        else:
            log_data["average_latency_ms"] = 0
        
        # Output structured log for later parsing
        print(json.dumps(log_data))

async def main():
    tasks = []
    print(f"[{CLIENT_ID_BASE}] Starting {NUM_CONCURRENT_CLIENTS} concurrent client tasks, each sending {NUM_MESSAGES_PER_CLIENT} messages.")
    for i in range(NUM_CONCURRENT_CLIENTS):
        tasks.append(connect_and_send(i))
    
    # Run all client tasks concurrently
    await asyncio.gather(*tasks)
    print(f"[{CLIENT_ID_BASE}] All client tasks completed.")

if __name__ == "__main__":
    # Tenta conectar várias vezes caso o servidor ainda não esteja pronto
    max_retries = 3 # Reduced retries, asyncio connect handles some retry implicitly
    retry_delay = 5 # seconds
    
    connected_at_least_once = False
    for i in range(max_retries):
        try:
            asyncio.run(main())
            connected_at_least_once = True
            break
        except Exception as e:
            print(f"[{CLIENT_ID_BASE}] Attempt {i+1}/{max_retries} failed: {e}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
    
    if not connected_at_least_once:
        print(f"[{CLIENT_ID_BASE}] Failed to run client tasks after {max_retries} attempts.")