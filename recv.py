import asyncio
import websockets

class MessageReceiver:
    async def receive_message(self):
        async with websockets.connect("ws://localhost:8765") as websocket:
            while True:
                message = await websocket.recv()
                print(f"Received message: {message}")

# Example usage
async def main():
    receiver = MessageReceiver()
    await receiver.receive_message()

asyncio.run(main())
