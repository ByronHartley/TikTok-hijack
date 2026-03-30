#!/usr/bin/env python3
import asyncio
import websockets
import cv2
import numpy as np
import base64
from queue import Queue
import threading

frame_queue = Queue(maxsize=10)
connected_clients = {}

async def handle_client(websocket, path):
    target_id = path.split('/')[-1]
    connected_clients[target_id] = websocket
    
    try:
        async for message in websocket:
            # Decode base64 video frame
            img_data = base64.b64decode(message.split(',')[1])
            nparr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if not frame_queue.full():
                frame_queue.put(frame)
                
            # Forward to Flask stream endpoint
            print(f"[{target_id}] Frame received: {frame.shape}")
            
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if target_id in connected_clients:
            del connected_clients[target_id]

if __name__ == '__main__':
    start_server = websockets.serve(handle_client, "0.0.0.0", 8080)
    print("WebSocket server running on ws://0.0.0.0:8080")
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()