from dataclasses import dataclass
from collections import Counter
from typing import Iterator

from services.config import AGENT_EVENT_LIMIT
from services.event_repository import list_events
import services.ollama_client as ollama_client

MAX_HISTORY_MESSAGES = 8


@dataclass(frozen=True)
class AgentProfile:
    name: str
    role: str
    goal: str


AGENT_PROFILE = AgentProfile(
    name="Agente AgroVision",
    role="triagem operacional de eventos",
    goal="Analisar detecções recentes, explicar riscos e sugerir a próxima ação.",
)


def _build_system_prompt() -> str:
    return (
        f"Você é o {AGENT_PROFILE.name}, um agente de {AGENT_PROFILE.role}. "
        f"Objetivo: {AGENT_PROFILE.goal} "
        "Trate os dados como monitoramento operacional autorizado de ambiente real. "
        "Responda em português do Brasil, de forma direta e útil. "
        "Use os eventos fornecidos como fonte principal. "
        "Não invente dados que não aparecem no contexto. "
        "Não tente identificar pessoas; fale apenas sobre eventos, riscos e próximas ações. "
        "Quando fizer sentido, organize a resposta em: Leitura, Risco e Recomendação."
    )


def build_event_context(events: list) -> str:
    if not events:
        return "Contexto operacional: nenhum evento detectado ainda."

    label_counts = Counter(e["label"] for e in events)
    most_recent = events[0]
    avg_conf = sum(e["confidence"] for e in events) / len(events)
    dist = ", ".join(f"{lbl}: {cnt}" for lbl, cnt in label_counts.most_common())

    lines = [
        "Contexto operacional para o agente:",
        f"- Eventos considerados: {len(events)}",
        f"- Evento mais recente: {most_recent['label']} em {most_recent['event_time']}",
        f"- Distribuição recente: {dist}",
        f"- Confiança média: {avg_conf:.2f}",
        "Eventos recentes:",
    ]
    for i, e in enumerate(events[:10], 1):
        lines.append(
            f"  #{i} | {e['event_time']} | {e['label']} | conf={e['confidence']:.2f}"
        )
    return "\n".join(lines)


def normalize_history(history: list) -> list:
    normalized = []
    for msg in history:
        if isinstance(msg, dict) and msg.get("role") in ("user", "assistant"):
            normalized.append({"role": msg["role"], "content": msg["content"]})
        elif hasattr(msg, "role") and msg.role in ("user", "assistant"):
            normalized.append({"role": msg.role, "content": msg.content})
    return normalized[-MAX_HISTORY_MESSAGES:]


def build_agent_messages(question: str, history: list, events: list) -> list:
    return [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "system", "content": build_event_context(events)},
        *normalize_history(history),
        {"role": "user", "content": question},
    ]


def ask(question: str, history: list | None = None) -> str:
    events = list_events(AGENT_EVENT_LIMIT)
    messages = build_agent_messages(question, history or [], events)
    return ollama_client.chat(messages)


def ask_stream(question: str, history: list | None = None) -> Iterator[str]:
    events = list_events(AGENT_EVENT_LIMIT)
    messages = build_agent_messages(question, history or [], events)
    return ollama_client.chat_stream(messages)


def get_status() -> dict:
    events = list_events(AGENT_EVENT_LIMIT)
    return {
        "name": AGENT_PROFILE.name,
        "role": AGENT_PROFILE.role,
        "goal": AGENT_PROFILE.goal,
        "events_in_context": len(events),
        "context_preview": build_event_context(events),
    }
