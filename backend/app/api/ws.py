from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any
from backend.app.core.event_bus import event_bus
import asyncio

router = APIRouter(prefix="/ws", tags=["websocket"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
                
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# We need to subscribe to the event_bus when the app starts.
_is_subscribed = False

def _subscribe_if_needed():
    global _is_subscribed
    if not _is_subscribed:
        import asyncio
        event_bus.set_main_loop(asyncio.get_running_loop())
        
        async def on_event(msg):
            # The event_bus passes an IntrusionEvent, FaceRecognitionResult, or similar object/dict.
            if hasattr(msg, "model_dump"):
                data = msg.model_dump()
            elif hasattr(msg, "__dict__"):
                data = dict(msg.__dict__)
            else:
                data = msg
            await manager.broadcast({
                "type": "NEW_EVENT",
                "payload": data
            })
            
        async def on_alert(msg):
            data = msg.model_dump() if hasattr(msg, "model_dump") else (dict(msg.__dict__) if hasattr(msg, "__dict__") else msg)
            await manager.broadcast({
                "type": "NEW_ALERT",
                "payload": data
            })
            
        async def on_alert_update(msg):
            data = msg.model_dump() if hasattr(msg, "model_dump") else (dict(msg.__dict__) if hasattr(msg, "__dict__") else msg)
            await manager.broadcast({
                "type": "ALERT_UPDATED",
                "payload": data
            })
            
        async def on_anpr(msg):
            data = msg.model_dump() if hasattr(msg, "model_dump") else (dict(msg.__dict__) if hasattr(msg, "__dict__") else msg)
            await manager.broadcast({
                "type": "NEW_ANPR",
                "payload": data
            })
        async def on_camera_status(msg):
            data = msg.model_dump() if hasattr(msg, "model_dump") else (dict(msg.__dict__) if hasattr(msg, "__dict__") else msg)
            await manager.broadcast({
                "type": "NEW_CAMERA_STATUS",
                "payload": data
            })
            
        event_bus.subscribe("events.intrusion", on_event)
        event_bus.subscribe("events.behavior", on_event)
        event_bus.subscribe("events.face_recognition", on_event)
        event_bus.subscribe("alerts.new", on_alert)
        event_bus.subscribe("alerts.updated", on_alert_update)
        event_bus.subscribe("events.anpr", on_anpr)
        event_bus.subscribe("camera.status", on_camera_status)
        _is_subscribed = True

@router.websocket("/events")
async def websocket_endpoint(websocket: WebSocket):
    _subscribe_if_needed()
    await manager.connect(websocket)
    try:
        while True:
            # We don't really expect messages from the client yet,
            # but we need to receive to detect disconnects.
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
