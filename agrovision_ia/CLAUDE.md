# CLAUDE.md — AgroVision AI (Atividade 2 ativa)

> Documento mestre. Em caso de dúvidas de contexto, abra `CONTEXT.md` (estado vivo) e a pasta `orgprompts/` (todos os contextos detalhados + prompts por sessão).

## Onde estão as coisas

Este projeto está em **fase 2** (Atividade 2 — revisão de arquitetura, segurança, refatoração e implementação de camada de web scraping). Toda a documentação detalhada vive em `orgprompts/`:

```
orgprompts/
├── CLAUDE.md                              # Mestre v3 — leia este primeiro
├── CONTEXT.md                             # Contexto vivo geral + roadmap
├── CONTEXT_PART1_ARCHITECTURE.md          # Diagnóstico arquitetural (R1–R10)
├── CONTEXT_PART2_SECURITY.md              # Auditoria de segurança (RS-01–RS-15)
├── CONTEXT_PART3_CODE_QUALITY.md          # Antes/Depois das 15 refatorações
├── CONTEXT_PART4_SCRAPING.md              # Camada de scraping (Open-Meteo + CEPEA)
├── PROMPTS_PART3.md                       # Prompts agrupados (Parte 3)
└── PROMPTS_PART4.md                       # Prompts agrupados (Parte 4)
```

**Regra para o Claude Code:** sempre que receber um prompt de sessão (`Sessão A`, `Sessão B`, etc.), abra os 2 documentos indicados no preâmbulo do próprio prompt — geralmente `orgprompts/CLAUDE.md` (mestre v3) + o `CONTEXT_PARTn_*.md` da parte correspondente.

## Visão Geral

O **AgroVision AI** é um sistema de monitoramento por visão computacional. Combina **YOLO** (detecção visual), **Ollama** (LLM local) e uma camada de **agente** em Python sobre **FastAPI**. A câmera é uma fonte pública (HLS/m3u8 da Caltrans) escolhida aleatoriamente de um pool — webcam local serve apenas como fallback.

Na Atividade 2 o sistema ganha uma **camada de web scraping** (clima via Open-Meteo + cotações agro via CEPEA/Notícias Agrícolas) que enriquece o contexto do agente.

**Regra mental:**
> YOLO prediz objetos. Ollama escreve texto. Agente decide como o Ollama deve raciocinar com os dados do projeto. Scraping traz contexto externo para tornar a análise mais rica.

## Stack atual

| Camada | Tecnologia | Versão |
|---|---|---|
| Web framework | FastAPI | 0.115.0 |
| Servidor ASGI | Uvicorn | 0.30.6 |
| Visão computacional | OpenCV | 4.10.0.84 |
| Modelo de detecção | YOLOv8n (Ultralytics) | 8.3.0 |
| Template engine | Jinja2 | 3.1.4 |
| Banco de dados | SQLite (nativo Python) | — |
| Cliente HTTP | httpx | 0.27.0 |
| Scraping HTML (a adicionar na 4.A) | beautifulsoup4 + lxml | ≥4.12 / ≥5.0 |
| Carga de `.env` | python-dotenv | ≥1.0.0 |
| LLM local | Ollama (`llama3`) | qualquer recente |
| Linguagem | Python | 3.11.x |

> Para a stack completa, schema de banco, lista de endpoints e variáveis de ambiente atualizadas, ver **orgprompts/CLAUDE.md**.

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

Rotas para validação rápida:
- `/health`, `/camera/status`, `/cameras`
- `/ollama/status`, `/agent/status`, `/events`
- `/scraping/status` (após a Etapa 4.A)
- `/scraping/weather`, `/scraping/market` (após 4.B e 4.C)

## Ordem de trabalho da Atividade 2

Execução por sessões/etapas, na ordem:

1. **Parte 3 — Refatoração** (`orgprompts/PROMPTS_PART3.md`)
   - Sessão A → Higiene básica
   - Sessão B → Logging e robustez
   - Sessão C → Refatorações estruturais
   - Sessão D → Defesa contra prompt injection
   - Sessão E → Cosméticas (opcional)

2. **Parte 4 — Camada de Web Scraping** (`orgprompts/PROMPTS_PART4.md`)
   - 4.A → Infraestrutura
   - 4.B → Weather (Open-Meteo)
   - 4.C → Market (CEPEA/Notícias Agrícolas)
   - 4.D → Integração com agente
   - 4.E → Background refresh (validação)
   - 4.F → Frontend (card)
   - 4.G → News (opcional)
   - 4.H → Hardening final

Cada sessão tem seu próprio bloco de validação que **deve** ser executado antes de partir pra próxima.

## Cuidados Éticos

- Apenas câmeras públicas oficiais (Caltrans) ou privadas com autorização.
- Agente **nunca** identifica pessoas, faz reconhecimento facial ou perfilamento.
- Scraping: apenas fontes públicas e gratuitas (Open-Meteo, CEPEA via Notícias Agrícolas). User-Agent identificável. Cache obrigatório.
- Crédito às fontes exibido no painel (Open-Meteo CC BY 4.0, CEPEA/ESALQ-USP).
