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

// --- Condições externas (clima + cotações via scraping) ---
async function refreshExternal() {
  try {
    const [wRes, mRes, nRes] = await Promise.allSettled([
      fetch('/scraping/weather'),
      fetch('/scraping/market'),
      fetch('/scraping/news'),
    ]);

    const wEl = document.getElementById('weather-content');
    if (wRes.status === 'fulfilled' && wRes.value.ok) {
      const w = await wRes.value.json();
      wEl.innerHTML = '';
      const line = document.createElement('div');
      line.className = 'weather-line';
      const temp = document.createElement('span');
      temp.className = 'temp';
      temp.textContent = `${Math.round(w.temperature_c ?? 0)}°C`;
      line.appendChild(temp);
      line.appendChild(document.createTextNode(
        `${w.weather_description || ''} — ${w.location || ''} | vento ${Math.round(w.wind_kmh || 0)} km/h`
      ));
      wEl.appendChild(line);
    } else {
      wEl.innerHTML = '<span class="muted">Indisponível.</span>';
    }

    const mEl = document.getElementById('market-content');
    if (mRes.status === 'fulfilled' && mRes.value.ok) {
      const m = await mRes.value.json();
      mEl.innerHTML = '';
      (m.quotes || []).slice(0, 5).forEach(q => {
        const row = document.createElement('div');
        row.className = 'quote-line';

        const name = document.createElement('span');
        name.textContent = q.product;

        const val = document.createElement('span');
        const variation = q.variation_pct;
        const price = q.price_brl;
        const priceStr = typeof price === 'number' ? price.toFixed(2) : '?';

        // Constrói via DOM (não usar innerHTML em dados externos)
        const priceText = document.createTextNode(`R$ ${priceStr}/${q.unit || ''} `);
        val.appendChild(priceText);

        if (typeof variation === 'number') {
          const varSpan = document.createElement('span');
          varSpan.className = variation >= 0 ? 'var-up' : 'var-down';
          varSpan.textContent = `(${variation >= 0 ? '+' : ''}${variation.toFixed(1)}%)`;
          val.appendChild(varSpan);
        }

        row.appendChild(name);
        row.appendChild(val);
        mEl.appendChild(row);
      });
      if (!mEl.children.length) {
        mEl.innerHTML = '<span class="muted">Sem cotações.</span>';
      }
    } else {
      mEl.innerHTML = '<span class="muted">Indisponível.</span>';
    }
    const nEl = document.getElementById('news-content');
    if (nEl) {
      if (nRes.status === 'fulfilled' && nRes.value.ok) {
        const n = await nRes.value.json();
        nEl.innerHTML = '';
        (n.headlines || []).slice(0, 3).forEach(h => {
          const row = document.createElement('div');
          row.className = 'news-line';

          const date = document.createElement('span');
          date.className = 'news-date';
          date.textContent = h.date || '';

          const title = document.createElement('span');
          title.textContent = h.title || '';

          row.appendChild(date);
          row.appendChild(title);
          nEl.appendChild(row);
        });
        if (!nEl.children.length) {
          nEl.innerHTML = '<span class="muted">Sem manchetes.</span>';
        }
      } else {
        nEl.innerHTML = '<span class="muted">Indisponível.</span>';
      }
    }
  } catch (_) {
    document.getElementById('weather-content').innerHTML = '<span class="muted">Erro de rede.</span>';
    document.getElementById('market-content').innerHTML = '<span class="muted">Erro de rede.</span>';
  }
}

refreshExternal();
setInterval(refreshExternal, 5 * 60 * 1000); // 5 minutos
