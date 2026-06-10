from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Union, Dict, Any, Optional
import requests
import os
import json
import time
import asyncio
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
import os

load_dotenv()

app = FastAPI(
    title="MedGemma API Wrapper (Multimodal)",
    description="API for accessing Google MedGemma 1.5 4B deployed on Baseten. Supports Text, Vision (Base64/URL images) and Streaming.",
    version="2.0.0"
)

# Servir Frontend si existe
if os.path.exists("static"):
    app.mount("/app", StaticFiles(directory="static", html=True), name="static")

BASETEN_API_KEY = os.getenv("BASETEN_API_KEY")
BASETEN_MODEL_ID = os.getenv("BASETEN_MODEL_ID")

# --- Schemas Multimodales ---
class TextContent(BaseModel):
    type: str = "text"
    text: str

class ImageUrl(BaseModel):
    url: str

class ImageContent(BaseModel):
    type: str = "image_url"
    image_url: ImageUrl

# El contenido puede ser un simple string (solo texto) o una lista mezclada de texto e imagenes
ContentType = Union[str, List[Union[TextContent, ImageContent]]]

class Message(BaseModel):
    role: str = Field(..., description="Role of the sender (system, user, assistant)")
    content: ContentType = Field(..., description="Message content. Can be a string or a list of text/image objects.")

class ChatRequest(BaseModel):
    messages: List[Message]
    max_tokens: int = 1024
    temperature: float = 0.7

class ChatResponse(BaseModel):
    generated_text: str

# --- Endpoints ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the MedGemma Multimodal API Wrapper. Go to /docs to view the interactive UI."}

@app.post("/chat", response_model=ChatResponse)
async def generate_chat(request: ChatRequest):
    """Respuesta normal para todo tipo de mensajes (Texto e Imágenes). Espera a que termine de procesar."""
    if not BASETEN_API_KEY or not BASETEN_MODEL_ID or BASETEN_MODEL_ID == "YOUR_MODEL_ID_HERE":
        raise HTTPException(status_code=500, detail="Baseten API Key or Model ID not configured. Please set them in the .env file.")

    url = f"https://model-{BASETEN_MODEL_ID}.api.baseten.co/environments/production/predict"
    headers = {"Authorization": f"Api-Key {BASETEN_API_KEY}", "Content-Type": "application/json"}
    
    # Preparamos el payload exactamente como vLLM lo espera
    payload = {
        "messages": [msg.model_dump() for msg in request.messages], 
        "max_tokens": request.max_tokens, 
        "temperature": request.temperature
    }

    max_retries = 30 # Hasta 5 minutos de espera
    retry_delay = 10 # Segundos
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return ChatResponse(generated_text=data["choices"][0]["message"]["content"])
            else:
                return ChatResponse(generated_text=str(data))
        except Exception as e:
            error_details = response.text if 'response' in locals() else str(e)
            # Si el error menciona que el modelo está despertando o hay error de servidor, reintentamos
            if "Model is unhealthy" in error_details or response.status_code in [500, 502, 503, 504]:
                if attempt < max_retries - 1:
                    print(f"Cold Start detectado. Esperando {retry_delay}s... (Intento {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
            # Si es un error distinto o se acabaron los intentos, lanzamos la excepcion
            raise HTTPException(status_code=500, detail=f"Baseten Error: {error_details}")

@app.post("/chat/stream")
async def generate_chat_stream(request: ChatRequest):
    """Respuesta con Streaming para mensajes de texto e imágenes. Manda los tokens palabra por palabra."""
    if not BASETEN_API_KEY or not BASETEN_MODEL_ID or BASETEN_MODEL_ID == "YOUR_MODEL_ID_HERE":
        raise HTTPException(status_code=500, detail="Baseten API Key or Model ID not configured.")

    url = f"https://model-{BASETEN_MODEL_ID}.api.baseten.co/environments/production/predict"
    headers = {"Authorization": f"Api-Key {BASETEN_API_KEY}", "Content-Type": "application/json"}
    
    payload = {
        "messages": [msg.model_dump() for msg in request.messages], 
        "max_tokens": request.max_tokens, 
        "temperature": request.temperature,
        "stream": True
    }

    def event_stream():
        max_retries = 30
        retry_delay = 10
        
        for attempt in range(max_retries):
            try:
                with requests.post(url, headers=headers, json=payload, stream=True) as response:
                    # Chequear si hay error de Cold Start
                    if response.status_code in [500, 502, 503, 504] or not response.ok:
                        error_details = response.text
                        if "Model is unhealthy" in error_details or response.status_code >= 500:
                            if attempt < max_retries - 1:
                                print(f"Cold Start detectado en Stream. Esperando {retry_delay}s... (Intento {attempt + 1}/{max_retries})")
                                time.sleep(retry_delay)
                                continue
                    
                    response.raise_for_status()
                    # Si llego aca, el modelo esta sano
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode("utf-8")
                            if decoded_line.startswith("data: "):
                                json_str = decoded_line.replace("data: ", "")
                                if json_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(json_str)
                                    if "choices" in chunk and len(chunk["choices"]) > 0:
                                        delta = chunk["choices"][0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    pass
                    return # Salimos de la funcion si el stream termino con exito
            except Exception as e:
                # Si falló la conexión completamente, reintenta
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                yield f"\\n\\n[Error: {str(e)}]"
                return

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
