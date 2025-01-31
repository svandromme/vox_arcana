from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
import json
import random
import os
from openai import AsyncOpenAI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

openai_client = AsyncOpenAI()

app = FastAPI()

# Configurer CORS pour permettre les requêtes depuis d'autres domaines
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ou spécifie une liste de domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stockage des sessions en mémoire
sessions = {}

def generate_session_id():
    """Génère un ID unique de 6 chiffres qui n'est pas encore utilisé."""
    while True:
        session_id = str(random.randint(100000, 999999))  # Génère un nombre entre 100000 et 999999
        if session_id not in sessions:  # Vérifie qu'il n'est pas déjà pris
            return session_id

@app.post("/sessions")
def create_session(language: str = "english"):
    """Crée une nouvelle session avec un ID unique."""
    session_id = generate_session_id()
    sessions[session_id] = {"session_infos": {"language": language}, "connected_clients": []}
    return {"session_id": session_id}


@app.websocket("/ws/{session_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, username: str):
    """Gère la connexion WebSocket et l'envoi de messages en temps réel."""
    if session_id not in sessions:
        await websocket.close(code=1003)  # Ferme la connexion avec un code d'erreur
        return

    username = generate_pseudonym(username, sessions[session_id]["session_infos"]["language"])

    # Accepter la connexion
    await websocket.accept()
    sessions[session_id]["connected_clients"].append({"websocket": websocket,"client_infos":{"username": username}})
    print("Un client s'est connecté")
    emit_message(session_id, generate_login_message(username, sessions[session_id]["session_infos"]["language"]))

    try:
        while True:
            # Attendre un message du client
            message = await websocket.receive_text()
            await handle_message(session_id, message)
    except WebSocketDisconnect:
        disconnect(session_id, websocket)


async def disconnect(session_id: str, websocket):
    for client in sessions[session_id]["connected_clients"]:
        if client["websocket"] == websocket:
            sessions[session_id]["connected_clients"].remove(client)
            break
    print(f"{client["client_infos"]["username"]} s'est déconnecté.")

    if not sessions[session_id]["connected_clients"]:  # Vérifie si la liste est vide
        del sessions[session_id]  # Supprime la session
        print(f"Session {session_id} supprimée car plus aucun utilisateur connecté.")


async def handle_message(session_id: str, message: str):
    """Gère la réception et la diffusion des messages."""
    try:
        data = json.loads(message)
        username = data["username"]
        text = data["message"]

        emit_message(session_id, f"{username}: {text}")

    except json.JSONDecodeError:
        print("Erreur : Message mal formé reçu")


async def emit_message(session_id:str, message: str):
    for client in sessions[session_id]["connected_clients"]:
            await client["websocket"].send_text(message)


async def generate_pseudonym(username: str, language: str = "english"):
    prompt = f"Generate a humorous fantasy-themed pseudonym for a user. The pseudonym must follow the format: '{username} the [descriptor]'. The descriptor should be a funny, quirky, or unexpected fantasy-related title. Avoid generic terms—favor creative, playful, and slightly absurd choices. Answer in {language}"
    pseudonym = call_openai(prompt)
    return pseudonym


async def generate_login_message(username: str, language: str = "english"):
    prompt = f"Generate a single humorous message in {language} announcing that a user has joined a session. The message should include the placeholder [{username}] for the user's name. It should be playful, witty, and evoke a sense of adventure or fun. Example: \"{username} has entered the realm. Brace yourselves for adventure!\""
    message = call_openai(prompt)
    return message


async def call_openai(prompt: str):
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.7
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return {"error": f"OpenAI API error: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)