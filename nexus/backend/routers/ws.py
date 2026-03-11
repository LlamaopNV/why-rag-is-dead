from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.event_bus import event_bus

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(session_id: str, ws: WebSocket):
    await event_bus.connect(session_id, ws)
    try:
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await event_bus.disconnect(session_id, ws)
