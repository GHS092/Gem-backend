# MedGemma API Wrapper (Multimodal)

Este proyecto levanta una API local (con FastAPI) que actúa como puente seguro hacia tu modelo `MedGemma-4B` alojado en Baseten.

## Capacidades Activadas
1. **Chat de Texto Normal**
2. **Historial de Conversación** (Memoria enviando múltiples mensajes)
3. **Visión Multimodal** (Soporte para radiografías e imágenes médicas en Base64 o URL)
4. **Streaming** (Respuestas en tiempo real)

## Instalación y Ejecución

1. Crea o verifica tu archivo `.env` en esta carpeta:
```ini
BASETEN_API_KEY=tu_api_key_aqui
BASETEN_MODEL_ID=tu_model_id_aqui
```

2. Instala dependencias e inicia el servidor:
```bash
pip install -r requirements.txt
python main.py
```

3. Abre `http://localhost:8000/docs` en tu navegador para ver la interfaz interactiva.

## Ejemplos de Integración para tu Plataforma

### Ejemplo 1: Pregunta Médica Simple (Solo Texto)
```javascript
const response = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        messages: [
            { role: "system", content: "Eres un oncólogo experto." },
            { role: "user", content: "¿Cuáles son los síntomas del melanoma?" }
        ]
    })
});
const data = await response.json();
console.log(data.generated_text);
```

### Ejemplo 2: Analizar una Radiografía (Multimodal / Visión)
Puedes enviar imágenes directamente codificadas en Base64 o mediante una URL pública.

```javascript
// Asegúrate de tener la imagen en formato Base64 (ej: "data:image/jpeg;base64,/9j/4AAQSkZJRgABA...")
const imageBase64 = "data:image/jpeg;base64,tu_string_base64_aqui";

const payload = {
    messages: [
        {
            role: "user",
            content: [
                { type: "text", text: "Por favor, analiza esta radiografía de tórax y dime si hay consolidación." },
                { type: "image_url", image_url: { url: imageBase64 } }
            ]
        }
    ],
    max_tokens: 1024,
    temperature: 0.2
};

const response = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
});

const data = await response.json();
console.log(data.generated_text);
```

### Ejemplo 3: Usando Streaming
Llama a `http://localhost:8000/chat/stream` usando Server-Sent Events (SSE) o procesando la respuesta HTTP por partes para mostrar el texto letra por letra.
