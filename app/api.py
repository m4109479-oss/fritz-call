from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from app.config import load_config
from app.export_info import get_export_modified_at
from app.runtime_status import RUNTIME_STATUS
from app.state import CALL_MANAGER
from app.websocket_manager import WEBSOCKET_MANAGER

app = FastAPI(title="Fritz-Call API", version="1.1")


@app.get("/status")
def status():
    runtime = RUNTIME_STATUS.snapshot()
    return {
        "online": runtime["fritz_connected"],
        **runtime,
        "calls": CALL_MANAGER.get_current(),
        "export_modified_at": get_export_modified_at(load_config()["customer"]["csv_file"]),
    }


@app.get("/history")
def history():
    calls = CALL_MANAGER.get_history()
    return {"count": len(calls), "calls": calls}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await WEBSOCKET_MANAGER.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        WEBSOCKET_MANAGER.disconnect(websocket)


app.mount("/", StaticFiles(directory="web", html=True), name="web")
