from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

app = FastAPI()

# Liste pour suivre les utilisateurs connectés
connected_clients: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Accepter la connexion
    await websocket.accept()
    # Ajouter le client à la liste des connectés
    connected_clients.append(websocket)
    try:
        while True:
            # Attendre un message du client
            message = await websocket.receive_text()
            print(f"Message reçu : {message}")
            # Répondre à tous les clients connectés
            for client in connected_clients:
                await client.send_text(f"Message reçu: {message}")
    except WebSocketDisconnect:
        # Supprimer le client de la liste lors de la déconnexion
        connected_clients.remove(websocket)
        print("Un client s'est déconnecté")

