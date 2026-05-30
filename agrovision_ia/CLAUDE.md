# CLAUDE.md — AgroVision AI (Atividade 2 concluída)

> Documento mestre. Documentação detalhada de processo vive em `orgprompts/`.

## Onde estão as coisas

```
orgprompts/
├── CLAUDE.md                              # Mestre v3
├── CONTEXT_PART1_ARCHITECTURE.md          # Diagnóstico arquitetural (R1–R10)
├── CONTEXT_PART2_SECURITY.md              # Auditoria de segurança (RS-01–RS-15)
├── CONTEXT_PART3_CODE_QUALITY.md          # Antes/Depois das 15 refatorações
├── CONTEXT_PART4_SCRAPING.md              # Camada de scraping
├── PROMPTS_PART3.md                       # Prompts agrupados (Parte 3)
└── PROMPTS_PART4.md                       # Prompts agrupados (Parte 4)
```

## Visão Geral

O **AgroVision AI** é um sistema de monitoramento por visão computacional. Combina **YOLO** (detecção visual), **Ollama** (LLM local) e uma camada de **agente** em Python sobre **FastAPI**. A câmera é uma fonte pública (HLS/m3u8 da Caltrans) escolhida de um pool configurável — webcam local como fallback.

A **camada de web scraping** (implementada na Atividade 2) enriquece o contexto do agente com dados públicos externos: clima via Open-Meteo, cotações agro via CEPEA/Notícias Agrícolas e manchetes via Embrapa.

**Regra mental:**
> YOLO prediz objetos. Ollama escreve texto. Agente decide como o Ollama deve raciocinar com os dados do projeto. Scraping traz contexto externo para tornar a análise mais rica.

## Stack

| Camada | Tecnologia | Versão |
|---|---|---|
| Web framework | FastAPI | 0.115.0 |
| Servidor ASGI | Uvicorn | 0.30.6 |
| Visão computacional | OpenCV | 4.10.0.84 |
| Modelo de detecção | YOLOv8n (Ultralytics) | 8.3.0 |
| Template engine | Jinja2 | 3.1.4 |
| Banco de dados | SQLite (nativo Python) | — |
| Cliente HTTP | httpx | 0.27.0 |
| Scraping HTML | beautifulsoup4 + lxml | ≥4.12 / ≥5.0 |
| Carga de `.env` | python-dotenv | ≥1.0.0 |
| LLM local | Ollama (`llama3`) | qualquer recente |
| Linguagem | Python | 3.11.x |

## Como executar

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Garantir Ollama
ollama list
ollama pull llama3
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:11434/api/tags
# Se não responder: em outro terminal -> ollama serve

python -m uvicorn app:app --reload
# http://127.0.0.1:8000
```

## Endpoints

### Operacionais
| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Dashboard HTML |
| GET | `/health` | Status |
| GET | `/events` | Últimos 50 eventos |

### Câmera
| Método | Rota | Descrição |
|---|---|---|
| GET | `/frame` | Snapshot JPEG |
| GET | `/video_feed` | MJPEG live |
| GET | `/stream` | Alias |
| GET | `/camera/status` | Estado |
| GET | `/cameras` | Pool + ativa |

### IA / Agente
| Método | Rota | Descrição |
|---|---|---|
| POST | `/chat` | Pergunta — resposta completa |
| POST | `/chat/stream` | Pergunta — resposta NDJSON streaming |
| GET | `/agent/status` | Perfil + preview do contexto enriquecido |
| GET | `/ollama/status` | Saúde do Ollama |

### Scraping
| Método | Rota | Descrição |
|---|---|---|
| GET | `/scraping/status` | Estado (enabled, sources, cache stats) |
| GET | `/scraping/weather` | Clima atual (Open-Meteo) |
| GET | `/scraping/market` | Cotações agro (CEPEA/Notícias Agrícolas) |
| GET | `/scraping/news` | Manchetes agro (Embrapa/MAPA) |
| POST | `/scraping/refresh` | Força refresh — `?source=weather\|market\|news` |

## Atividade 2 — Status final

| Parte | Status |
|---|---|
| Parte 1 — Revisão de Arquitetura | Documentada em `orgprompts/CONTEXT_PART1_ARCHITECTURE.md` |
| Parte 2 — Revisão de Segurança | Documentada em `orgprompts/CONTEXT_PART2_SECURITY.md` |
| Parte 3 — Refatorações (A→E) | Concluída e commitada |
| Parte 4 — Scraping (4.A→4.H) | Concluída e commitada |

## Cuidados Éticos

**Câmera:**
- Apenas câmeras públicas oficiais (Caltrans) ou privadas com autorização.
- Agente nunca identifica pessoas, faz reconhecimento facial ou perfilamento.

**Scraping:**
- Apenas fontes públicas e gratuitas — sem login, sem paywall.
- User-Agent identificável (`AgroVisionAI-Educational/1.0`) — nunca finge ser browser.
- Cache obrigatório (TTL configurável): Open-Meteo 10min, CEPEA 1h, Embrapa 30min.
- Rate limit por fonte (`SCRAPING_MIN_INTERVAL=30s`).
- robots.txt verificado para cada fonte antes de implementar.
- Crédito às fontes exibido no painel:
  - **Open-Meteo** (CC BY 4.0)
  - **CEPEA/ESALQ-USP via Notícias Agrícolas**
  - **Embrapa/MAPA**
- Dados externos injetados no agente DENTRO de delimitadores `=== INÍCIO/FIM ===` (mitigação P4-R2).
- Títulos de notícias truncados em 120 chars (defesa adicional contra prompt injection).
- Frontend usa `textContent`/`createElement` para dados externos — nunca `innerHTML` (mitigação P4-R3).
- `POST /scraping/refresh` aceita apenas `Literal["weather","market","news"]` — bloqueia SSRF (mitigação P4-R6).
