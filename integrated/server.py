# server.py
import asyncio
import os

PORT = int(os.environ.get("PORT", 8080))
HOST = '0.0.0.0'

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")
    try:
        while True:
            data = await reader.read(1024)
            if not data:
                break
            message = data.decode('utf-8').strip()
            print(f"[*] Received from {addr[0]}:{addr[1]}: {message}")
            writer.write(data) # Echo back the received data
            await writer.drain() # Ensure the data is sent
    except ConnectionResetError:
        print(f"[-] Client {addr[0]}:{addr[1]} forcibly closed connection.")
    except Exception as e:
        print(f"[-] Error handling client {addr[0]}:{addr[1]}: {e}")
    finally:
        print(f"[*] Client {addr[0]}:{addr[1]} disconnected")
        writer.close()
        await writer.wait_closed() # Ensure the writer is closed

async def main():
    server = await asyncio.start_server(
        handle_client, HOST, PORT)

    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f"[*] Serving on {addrs}")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())