from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from app.state import CALL_MANAGER
from app.websocket_manager import WEBSOCKET_MANAGER


app = FastAPI(
    title="Fritz-Call API",
    version="1.0"
)


@app.get("/status")
def status():

    current = CALL_MANAGER.get_current()

    return {
        "online": True,
        "calls": list(current.values())
    }



@app.get("/history")
def history():

    calls = CALL_MANAGER.get_history()

    return {
        "count": len(calls),
        "calls": calls
    }



@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket
):

    await WEBSOCKET_MANAGER.connect(
        websocket
    )

    try:

        while True:

            await websocket.receive_text()

    except WebSocketDisconnect:

        WEBSOCKET_MANAGER.disconnect(
            websocket
        )



app.mount(
    "/",
    StaticFiles(
        directory="web",
        html=True
    ),
    name="web"
)
