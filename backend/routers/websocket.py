"""
WebSocket Endpoint for Real-Time Dashboard Telemetry (Section 2 & 7):
Streams 1 Hz updates of voltages, powers, currents, position, speed, controller actions,
and safety supervisor clip events.
"""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services.simulation_service import SimulationService

ws_router = APIRouter(tags=["WebSocket"])

@ws_router.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await websocket.accept()
    sim = SimulationService()
    queue = asyncio.Queue(maxsize=10)
    sim.subscribers.append(queue)

    try:
        # Immediately send current state on connect
        if sim.latest_signals:
            import json
            await websocket.send_text(json.dumps(sim.latest_signals))

        while True:
            # Wait for next 1s aggregated broadcast
            msg = await queue.get()
            await websocket.send_text(msg)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if queue in sim.subscribers:
            sim.subscribers.remove(queue)
