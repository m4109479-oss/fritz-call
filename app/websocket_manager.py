import asyncio

from app.eventbus import EVENT_BUS


class WebSocketManager:

    def __init__(self):

        self.connections = []
        self.loop = None


    async def connect(self, websocket):

        await websocket.accept()

        self.connections.append(
            websocket
        )

        self.loop = asyncio.get_running_loop()


    def disconnect(self, websocket):

        if websocket in self.connections:

            self.connections.remove(
                websocket
            )


    async def send_event(self, event):

        for websocket in self.connections.copy():

            try:

                await websocket.send_json(
                    event
                )

            except Exception:

                self.disconnect(
                    websocket
                )


    def handle_event(self, event):

        if self.loop:

            asyncio.run_coroutine_threadsafe(
                self.send_event(event),
                self.loop
            )


WEBSOCKET_MANAGER = WebSocketManager()


EVENT_BUS.subscribe(
    WEBSOCKET_MANAGER.handle_event
)
