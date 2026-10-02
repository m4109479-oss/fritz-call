import asyncio
import logging

from app.eventbus import EVENT_BUS

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.connections = []
        self.loop = None
        self.send_lock = asyncio.Lock()

    async def connect(self, websocket):
        await websocket.accept()
        self.connections.append(websocket)
        self.loop = asyncio.get_running_loop()

    def disconnect(self, websocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def _send(self, websocket, event):
        try:
            await asyncio.wait_for(websocket.send_json(event), timeout=5)
        except Exception:
            self.disconnect(websocket)
            try:
                await asyncio.wait_for(websocket.close(), timeout=1)
            except Exception:
                pass

    async def send_event(self, event):
        # Serialize events, but do not let one client block delivery to the rest.
        async with self.send_lock:
            await asyncio.gather(*(self._send(ws, event) for ws in self.connections.copy()))

    def handle_event(self, event):
        if self.loop and self.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self.send_event(dict(event)), self.loop)
            future.add_done_callback(self._log_failure)

    @staticmethod
    def _log_failure(future):
        if not future.cancelled() and future.exception():
            logger.warning("WebSocket-Ereignis konnte nicht gesendet werden")


WEBSOCKET_MANAGER = WebSocketManager()
EVENT_BUS.subscribe(WEBSOCKET_MANAGER.handle_event)
