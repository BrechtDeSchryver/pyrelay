from fastapi import FastAPI, Request, UploadFile, File, Form , Body
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.exceptions import HTTPException
from Config.lifespan import lifespan
from Networking.PacketHelper import createPacket
import json
import uvicorn

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    """
    A root endpoint that returns the API content.
    """
    content = """
    <body>
    <h1>NOX API</h1>
    <p>This is the NOX API</p>
    </body>
    """
    return HTMLResponse(content=content)

@app.get("/client/data/")
async def get_client_data(data: dict = Body(...)):
    """
    Endpoint to get a client's data by their GUID.
    """
    guid = data.get("guid")
    if not guid:
        raise HTTPException(status_code=400, detail="GUID is required")

    client_data = app.clientMan.getClientData(guid)
    if client_data:
        return client_data
    else:
        raise HTTPException(status_code=404, detail="Client not found")

@app.post("/login/")
async def login(account: dict = Body(...)):
    """
    Endpoint to log in a client.
    """
    try:
        app.clientMan.addClient(account)
        return {"status": "success", "message": "Client added successfully."}
    except Exception as e:
        raise #HTTPException(status_code=400, detail=str(e))

@app.post("/logout/")
async def logout(data: dict = Body(...)):
    """
    Endpoint to log out a client by their GUID.
    """
    guid = data.get("guid")
    if not guid:
        raise HTTPException(status_code=400, detail="GUID is required")

    if app.clientMan.removeClient(guid):
        return {"status": "success", "message": "Client removed successfully."}
    else:
        raise HTTPException(status_code=404, detail="Client not found")

@app.post("/trade/")
async def dupe(data: dict = Body(...)):
    """
    Endpoint to log out a client by their GUID.
    """
    guid = data.get("guid")
    reciever = data.get("reciever")
    if not guid or not reciever:
        raise HTTPException(status_code=400, detail="DATA WRONG")
    packet = createPacket("REQUESTTRADE")
    packet.name = reciever
    if app.clientMan.sendPacket(guid,packet):
        return {"status": "success", "message": "Trade Request was send."}
    else:
        raise HTTPException(status_code=404)

@app.post("/vault/")
async def dupe(data: dict = Body(...)):
    """
    Endpoint to log out a client by their GUID.
    """
    guid = data.get("guid")
    if not guid:
        raise HTTPException(status_code=400, detail="DATA WRONG")

    if app.clientMan.letClientEnterVault(guid):
        return {"status": "success", "message": "Vault was entered."}
    else:
        raise HTTPException(status_code=404)

@app.post("/dupe/")
async def dupe(data: dict = Body(...)):
    """
    Endpoint to log out a client by their GUID.
    """
    guid = data.get("guid")
    if not guid:
        raise HTTPException(status_code=400, detail="GUID is required")

    if app.clientMan.removeClient(guid):
        return {"status": "success", "message": "Client removed successfully."}
    else:
        raise HTTPException(status_code=404, detail="Client not found")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)