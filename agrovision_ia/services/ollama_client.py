import json
from typing import Iterator

import httpx

from services.config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_KEEP_ALIVE


def chat(messages: list) -> str:
    try:
        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            response = client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": OLLAMA_KEEP_ALIVE,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
    except httpx.ConnectError:
        raise RuntimeError(
            "Ollama não está respondendo. "
            "Certifique-se de que o serviço está ativo (ollama serve)."
        )
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Erro HTTP do Ollama: {e.response.status_code}")
    except Exception as e:
        raise RuntimeError(f"Erro ao comunicar com Ollama: {e}")


def chat_stream(messages: list) -> Iterator[str]:
    try:
        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            with client.stream(
                "POST",
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": True,
                    "keep_alive": OLLAMA_KEEP_ALIVE,
                },
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("done"):
                        break
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
    except httpx.ConnectError:
        raise RuntimeError(
            "Ollama não está respondendo. "
            "Certifique-se de que o serviço está ativo (ollama serve)."
        )
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Erro HTTP do Ollama: {e.response.status_code}")
    except Exception as e:
        raise RuntimeError(f"Erro ao comunicar com Ollama: {e}")


def warmup():
    """Envia uma requisição leve para pré-carregar o modelo em RAM."""
    try:
        with httpx.Client(timeout=60) as client:
            client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": "ping"}],
                    "stream": False,
                    "keep_alive": OLLAMA_KEEP_ALIVE,
                },
            )
        print("[ollama] Warmup concluído.")
    except Exception as e:
        print(f"[ollama] Warmup falhou silenciosamente: {e}")


def is_alive() -> dict:
    tags_url = OLLAMA_URL.replace("/api/chat", "/api/tags")
    try:
        with httpx.Client(timeout=3) as client:
            response = client.get(tags_url)
            response.raise_for_status()
            data = response.json()
            available_models = [m["name"] for m in data.get("models", [])]
            base = OLLAMA_MODEL.split(":")[0]
            model_loaded = any(m.split(":")[0] == base for m in available_models)
            return {
                "online": True,
                "model_loaded": model_loaded,
                "configured_model": OLLAMA_MODEL,
                "available_models": available_models,
            }
    except Exception:
        return {
            "online": False,
            "model_loaded": False,
            "configured_model": OLLAMA_MODEL,
            "available_models": [],
        }
