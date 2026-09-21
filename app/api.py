from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from app.config import load_config
from app.export_info import get_export_modified_at
from app.state import CALL_MANAGER
from app.websocket_manager import WEBSOCKET_MANAGER


app = FastAPI(
    title="Fritz-Call API",
    version="1.0"
)


@app.get("/status")
def status():

    current = CALL_MANAGER.get_current()

    csv_filename = load_config()["customer"]["csv_file"]

    return {
        "online": True,
        "calls": current,
        "export_modified_at": get_export_modified_at(
            csv_filename
        )
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
