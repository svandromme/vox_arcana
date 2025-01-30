from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
import json
from fastapi.middleware.cors import CORSMiddleware
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ou spécifie une liste de domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = {}


@app.post("/sessions")
def create_session():
    session_id = str(uuid.uuid4())  # Génère un ID unique
    sessions[session_id] = {"connected_clients" : []}
    return {"session_id": session_id}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    if session_id not in sessions:
        await websocket.close(code=1003)  # Ferme la connexion avec un code d'erreur
        return
    # Accepter la connexion
    await websocket.accept()
    # Ajouter le client à la liste des connectés
    sessions[session_id]["connected_clients"].append(websocket)
    try:
        while True:
            # Attendre un message du client
            message = await websocket.receive_text()
            print(f"Message reçu : {message}")
            # Répondre à tous les clients connectés
            for client in sessions[session_id]["connected_clients"]:
                await client.send_text(f"Message reçu: {message}")
    except WebSocketDisconnect:
        # Supprimer le client de la liste lors de la déconnexion
        sessions[session_id]["connected_clients"].remove(websocket)
        print("Un client s'est déconnecté")


async def handle_message(message: str, session_id: str):
    data = json.loads(message)
    username = data["username"]
    message = data["message"]
    for client in sessions[session_id]["connected_clients"]:
        await client.send_text(f"{username}: {message}")