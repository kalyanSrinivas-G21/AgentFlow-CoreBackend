# backend/scripts/test_ws.py
import asyncio
import websockets
import json
import sys

async def listen(project_id, token):
    uri = f"ws://localhost:8000/ws/projects/{project_id}?token={token}"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to project {project_id}. Listening for live Agent events...")
            print("-" * 50)
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                event_type = data.get('event_type', 'UNKNOWN')
                payload = data.get('payload', {})
                print(f"⚡ [EVENT]: {event_type}")
                print(f"   [DATA]: {json.dumps(payload, indent=2)}")
                print("-" * 50)
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ Connection closed abruptly: {e}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_ws.py <project_id> <token>")
        print("Example: python test_ws.py 123e4567-e89b-12d3-a456-426614174000 supersecret-demo-token")
        sys.exit(1)
    
    try:
        asyncio.run(listen(sys.argv[1], sys.argv[2]))
    except KeyboardInterrupt:
        print("\nExiting listener...")