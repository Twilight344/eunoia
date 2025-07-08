import requests
import json

OLLAMA_URL = "http://34.131.29.49:11434/api/generate"
MODEL = "phi"

def stream_gemma_response(prompt: str):
    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": True
    }, stream=True)

    for line in response.iter_lines():
        if line:
            try:
                data = json.loads(line.decode('utf-8'))
                yield data.get("response", "")
            except:
                continue

