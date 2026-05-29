# CONTEXT.md — AgroVision AI (Atividade 2)

> Contexto vivo de alto nível. Para detalhes de cada parte, consulte os arquivos `CONTEXT_PARTn_*.md` dentro de `orgprompts/`.

## 1. Onde estamos hoje

A Atividade 1 está **concluída**. O projeto entrou na **Atividade 2** — revisão crítica do código gerado por IA, hardening de segurança, refatorações estruturais e implementação de uma camada de web scraping.

**Estado da Atividade 1 (validado):**
- Pool de câmeras públicas Caltrans com fallback resiliente ✅
- Streaming de resposta no chat (NDJSON) ✅
- Warmup do Ollama no startup ✅
- CSS/JS extraídos de `templates/index.html` ✅
- Rotas de observabilidade `/ollama/status`, `/cameras` ✅
- `.gitignore` ainda **não foi criado** — vira primeira tarefa da Sessão A.

**Estado da Atividade 2 (em execução):**
- Documentação planejada e revisada com o projeto real em mãos ✅
- Prompts por sessão preparados em `orgprompts/` ✅
- Próxima ação: rodar a **Sessão A da Parte 3** no Claude Code.

## 2. Estrutura da Atividade 2

| Parte | Foco | Doc detalhado | Prompts |
|---|---|---|---|
| 1 | Revisão de Arquitetura | `orgprompts/CONTEXT_PART1_ARCHITECTURE.md` | (sem prompts — só análise/relatório) |
| 2 | Revisão de Segurança | `orgprompts/CONTEXT_PART2_SECURITY.md` | (sem prompts — só análise/relatório) |
| 3 | Refatoração do Código IA | `orgprompts/CONTEXT_PART3_CODE_QUALITY.md` | `orgprompts/PROMPTS_PART3.md` + individuais |
| 4 | Camada de Web Scraping | `orgprompts/CONTEXT_PART4_SCRAPING.md` | `orgprompts/PROMPTS_PART4.md` + individuais |

## 3. Sessões da Parte 3 (refatoração)

| Sessão | Foco | Arquivo individual de prompt |
|---|---|---|
| A | Higiene básica (`.gitignore`, índice SQL, `with`, `Field`+`Literal`, multipart) | `orgprompts/SESSAO_A_higiene.md` |
| B | Logging estruturado + thread protegida | `orgprompts/SESSAO_B_logging.md` |
| C | Refatorações estruturais (MJPEG, ChatSession, ObjectDetector, agent.ask) | `orgprompts/SESSAO_C_estrutural.md` |
| D | Anti-prompt-injection (system prompt + delimitadores) | `orgprompts/SESSAO_D_injection.md` |
| E | Cosméticas opcionais | `orgprompts/SESSAO_E_cosmetica.md` |

## 4. Etapas da Parte 4 (scraping)

| Etapa | Foco | Arquivo individual de prompt |
|---|---|---|
| 4.A | Infraestrutura (cache, rate limiter, ScrapingService) | `orgprompts/ETAPA_4A_infraestrutura.md` |
| 4.B | Weather — Open-Meteo (JSON) | `orgprompts/ETAPA_4B_weather.md` |
| 4.C | Market — CEPEA/Notícias Agrícolas (HTML) | `orgprompts/ETAPA_4C_market.md` |
| 4.D | Integração com agente | `orgprompts/ETAPA_4D_integracao.md` |
| 4.E | Validação do background refresh | `orgprompts/ETAPA_4E_refresh.md` |
| 4.F | Frontend (card de condições externas) | `orgprompts/ETAPA_4F_frontend.md` |
| 4.G | News (opcional) | `orgprompts/ETAPA_4G_news.md` |
| 4.H | Hardening final + checklist | `orgprompts/ETAPA_4H_hardening.md` |

## 5. Como trabalhar com cada prompt

1. Abra o arquivo individual da sessão/etapa atual (ex: `orgprompts/SESSAO_A_higiene.md`).
2. No Claude Code, com o projeto aberto, **cole o conteúdo inteiro** do arquivo como mensagem.
3. O Claude Code lerá os `@CLAUDE.md` e `@orgprompts/CONTEXT_PARTn_*.md` referenciados no preâmbulo do prompt.
4. Após executar, **rode os comandos de validação** que estão no FIM do mesmo arquivo.
5. Se tudo OK, commit no git e parta para o próximo arquivo.
6. Se algo falhar, traga o erro de volta pra revisão antes de prosseguir.

## 6. Decisões macro

| Decisão | Por quê |
|---|---|
| Manter `llama3` como modelo padrão | Já validado em sala, `llama3.2:3b` continua suportado via `.env`. |
| Manter pool Caltrans | Fontes públicas legais e disponíveis. |
| Open-Meteo (JSON) + CEPEA/Notícias Agrícolas (HTML) | Atende o requisito explícito de "web scraping" + cumpre o objetivo agro. |
| Cache em arquivo separado `scraping_cache.db` | Isolamento + permite resetar cache sem afetar eventos. |
| Manter SQLite | Suficiente para o escopo da disciplina. |
| **Não** adicionar autenticação | Documentar como dívida técnica (RS-02 no `CONTEXT_PART2_SECURITY.md`). |
| Substituir `print()` por `logging` | Sessão B. |
| Refatoração antes do scraping | Para o scraping crescer em cima de base limpa. |

## 7. Comandos comuns

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app:app --reload

# Smoke test
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/camera/status
curl http://127.0.0.1:8000/agent/status
curl http://127.0.0.1:8000/ollama/status
curl http://127.0.0.1:8000/scraping/status        # após Etapa 4.A
```

## 8. Log de sessões (Atividade 2)

### Pré-sessão — Planejamento concluído
- **Feito:** análise prévia do projeto, criação dos 6 documentos de contexto, prompts divididos por sessão/etapa.
- **Decisões:** ordem Parte 3 → Parte 4. Open-Meteo + CEPEA confirmados como fontes. `.gitignore` é primeiro item da Sessão A.
- **Próximos passos:** rodar `orgprompts/SESSAO_A_higiene.md` no Claude Code.

### Sessão A — 2026-05-29
- **Feito:** RS-01 (`.gitignore` criado), R5 (índice `idx_event_time` em `events`), R6 (`with sqlite3.connect` em todas as funções de `event_repository.py`), RS-06 (`Field(min_length=1, max_length=4000)` em `ChatRequest.message`), RS-07 (`Literal["user","assistant","system"]` + `Field(max_length=4000)` em `ChatMessage`), RS-14 (`python-multipart` removido de `requirements.txt`).
- **Validação:** aguardando smoke tests do usuário (`/health`, `/events`, `/camera/status`, índice no SQLite, rejeição 422 em msg >4000 chars).
- **Pendências:** validar e fazer commit `"Atividade 2 - Sessão A: higiene básica"` → partir para Sessão B.

### Sessão B — `[data]`
- **Feito:**
- **Validação:**
- **Pendências:**

### Sessão C — `[data]`
- **Feito:**
- **Validação:**
- **Pendências:**

### Sessão D — `[data]`
- **Feito:**
- **Validação:**
- **Pendências:**

### Sessão E — `[data]` (opcional)
- **Feito:**
- **Validação:**
- **Pendências:**

### Etapa 4.A — `[data]`
- **Feito:**
- **Validação:**
- **Pendências:**

### Etapa 4.B — `[data]`
- **Feito:**
- **Validação:**
- **Pendências:**

### Etapa 4.C — `[data]`
- **Feito:**
- **Validação:**
- **Pendências:**

### Etapa 4.D — `[data]`
- **Feito:**
- **Validação:**
- **Pendências:**

### Etapa 4.E — `[data]`
- **Feito:**
- **Validação:**
- **Pendências:**

### Etapa 4.F — `[data]`
- **Feito:**
- **Validação:**
- **Pendências:**

### Etapa 4.G — `[data]` (opcional)
- **Feito:**
- **Validação:**
- **Pendências:**

### Etapa 4.H — `[data]`
- **Feito:**
- **Validação:**
- **Pendências:**

## 9. Cuidados éticos (lembrete)

- Câmeras: apenas Caltrans (públicas) ou privadas com autorização.
- Agente nunca identifica pessoas.
- Scraping: User-Agent identificável, cache obrigatório, fontes confiáveis.
- Crédito às fontes deve aparecer no painel.
