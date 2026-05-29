// --- Atualização periódica da tabela de eventos ---
async function refreshEvents() {
  try {
    const res = await fetch('/events');
    if (!res.ok) return;
    const events = await res.json();
    const tbody = document.getElementById('events-body');

    if (!events.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="no-events">Nenhum evento registrado ainda.</td></tr>';
      return;
    }

    const labelClass = {
      person: 'label-person', car: 'label-car',
      truck: 'label-truck', bus: 'label-bus', motorcycle: 'label-motorcycle'
    };

    tbody.innerHTML = events.slice(0, 20).map(e => `
      <tr>
        <td>${e.event_time}</td>
        <td><span class="label-badge ${labelClass[e.label] || ''}">${e.label}</span></td>
        <td class="conf">${Math.round(e.confidence * 100)}%</td>
        <td><a href="${e.image_path}" target="_blank" style="color:#60a5fa;font-size:.75rem;">ver</a></td>
      </tr>
    `).join('');
  } catch (_) {}
}

setInterval(refreshEvents, 10000);

// --- Chat ---
const form = document.getElementById('chat-form');
const input = document.getElementById('chat-input');
const btn = document.getElementById('chat-btn');
const messages = document.getElementById('chat-messages');

function appendMsg(text, type) {
  const div = document.createElement('div');
  div.className = `msg msg-${type}`;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

// Lê resposta em streaming de /chat/stream (uma linha JSON por chunk)
async function streamAnswer(question, onChunk, onDone, onError) {
  try {
    const res = await fetch('/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: question }),
    });
    if (!res.ok || !res.body) throw new Error('Falha na conexão');
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let nl;
      while ((nl = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, nl).trim();
        buffer = buffer.slice(nl + 1);
        if (!line) continue;
        try {
          const obj = JSON.parse(line);
          if (obj.error) { onError(obj.error); return; }
          if (obj.done)  { onDone(); return; }
          if (obj.chunk) onChunk(obj.chunk);
        } catch (_) { /* ignora linhas malformadas */ }
      }
    }
    onDone();
  } catch (e) {
    onError(e.message || 'Erro de rede');
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const question = input.value.trim();
  if (!question) return;

  appendMsg(question, 'user');
  input.value = '';
  btn.disabled = true;
  btn.textContent = 'Aguarde...';

  const botDiv = document.createElement('div');
  botDiv.className = 'msg msg-bot';
  messages.appendChild(botDiv);
  messages.scrollTop = messages.scrollHeight;

  await streamAnswer(
    question,
    (chunk) => {
      botDiv.textContent += chunk;
      messages.scrollTop = messages.scrollHeight;
    },
    () => {
      btn.disabled = false;
      btn.textContent = 'Enviar';
      input.focus();
    },
    (errMsg) => {
      botDiv.className = 'msg msg-error';
      botDiv.textContent = errMsg;
      btn.disabled = false;
      btn.textContent = 'Enviar';
      input.focus();
    }
  );
});

// --- Verifica saúde da API ---
async function checkHealth() {
  try {
    const res = await fetch('/health');
    const badge = document.getElementById('status-badge');
    badge.textContent = res.ok ? '● ONLINE' : '● OFFLINE';
    badge.style.background = res.ok ? '#22c55e' : '#ef4444';
  } catch (_) {
    document.getElementById('status-badge').textContent = '● OFFLINE';
    document.getElementById('status-badge').style.background = '#ef4444';
  }
}

refreshEvents();   // carga inicial em vez do render do Jinja
checkHealth();
setInterval(checkHealth, 30000);
