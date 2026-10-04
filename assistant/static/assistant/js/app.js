(function () {
  const cfg = window.MM_CONFIG;

  const els = {
    statusText: document.getElementById("mm-status-text"),
    date: document.getElementById("mm-date"),
    time: document.getElementById("mm-time"),

    cpuPct: document.getElementById("mm-cpu-pct"),
    cpuBar: document.getElementById("mm-cpu-bar"),
    ramLabel: document.getElementById("mm-ram-label"),
    ramBar: document.getElementById("mm-ram-bar"),
    cpuBox: document.getElementById("mm-cpu-box"),
    memBox: document.getElementById("mm-mem-box"),
    diskBox: document.getElementById("mm-disk-box"),
    refreshStats: document.getElementById("mm-refresh-stats"),

    weatherTemp: document.getElementById("mm-weather-temp"),
    weatherIcon: document.getElementById("mm-weather-icon"),
    weatherCity: document.getElementById("mm-weather-city"),
    weatherDesc: document.getElementById("mm-weather-desc"),
    weatherHumidity: document.getElementById("mm-weather-humidity"),
    weatherWind: document.getElementById("mm-weather-wind"),
    weatherFeels: document.getElementById("mm-weather-feels"),
    refreshWeather: document.getElementById("mm-refresh-weather"),

    knowledgePanel: document.getElementById("mm-knowledge-panel"),
    knowledgeImage: document.getElementById("mm-knowledge-image"),
    knowledgeTitle: document.getElementById("mm-knowledge-title"),

    model3dPanel: document.getElementById("mm-model3d-panel"),
    model3dFrame: document.getElementById("mm-model3d-frame"),
    model3dTitle: document.getElementById("mm-model3d-title"),

    messages: document.getElementById("mm-messages"),
    chatForm: document.getElementById("mm-chat-form"),
    chatInput: document.getElementById("mm-chat-input"),
    micInline: document.getElementById("mm-mic-inline"),
    micMain: document.getElementById("mm-mic-main"),
  };

  let knowledgeTimer = null;

  // ---------------------------------------------------------------
  // Clock
  // ---------------------------------------------------------------
  function tickClock() {
    const now = new Date();
    els.date.textContent = now.toLocaleDateString(undefined, {
      year: "numeric", month: "long", day: "numeric",
    });
    els.time.textContent = now.toLocaleTimeString();
  }
  tickClock();
  setInterval(tickClock, 1000);

  // ---------------------------------------------------------------
  // System stats
  // ---------------------------------------------------------------
  function renderStats(data) {
    els.cpuPct.textContent = data.cpu_percent.toFixed(0) + "%";
    els.cpuBar.style.width = data.cpu_percent + "%";
    els.ramLabel.textContent = `${data.ram_used_gb} GB`;
    els.ramBar.style.width = data.ram_percent + "%";
    els.cpuBox.textContent = data.cpu_percent.toFixed(0) + "%";
    els.memBox.textContent = data.ram_percent.toFixed(0) + "%";
    els.diskBox.innerHTML = `${data.disk_used_gb}/${data.disk_total_gb}<br>GB`;
  }

  function fetchStats() {
    fetch(cfg.statsUrl).then((r) => r.json()).then(renderStats).catch(() => {});
  }

  // ---------------------------------------------------------------
  // Weather
  // ---------------------------------------------------------------
  const WEATHER_ICONS = {
    clear: "☀", cloud: "☁", rain: "🌧", drizzle: "🌦", storm: "⛈",
    snow: "❄", mist: "🌫", fog: "🌫", overcast: "☁",
  };

  function pickIcon(description) {
    const d = (description || "").toLowerCase();
    for (const key in WEATHER_ICONS) {
      if (d.includes(key)) return WEATHER_ICONS[key];
    }
    return "☁";
  }

  function renderWeather(data) {
    els.weatherTemp.textContent = `${data.temp_c}°C`;
    els.weatherIcon.textContent = pickIcon(data.description);
    els.weatherCity.textContent = `${data.city}${data.country ? ", " + data.country : ""}`;
    els.weatherDesc.textContent = data.description;
    els.weatherHumidity.textContent = `${data.humidity}%`;
    els.weatherWind.textContent = `${data.wind_ms} m/s`;
    els.weatherFeels.textContent = `${data.feels_like_c}°C`;
  }

  function fetchWeather(city) {
    const url = city ? `${cfg.weatherUrl}?city=${encodeURIComponent(city)}` : cfg.weatherUrl;
    fetch(url).then((r) => r.json()).then(renderWeather).catch(() => {});
  }

  // ---------------------------------------------------------------
  // Knowledge visual panel (swaps in over the idle canvas animation)
  // ---------------------------------------------------------------
  function showKnowledge(visual) {
    if (!visual || !visual.data) return;

    if (visual.type === "model3d") {
      const { title, embed_url } = visual.data;
      if (!embed_url) return;
      clearTimeout(knowledgeTimer);
      els.model3dTitle.textContent = title;
      els.model3dFrame.src = embed_url;
      els.model3dPanel.hidden = false;
      els.knowledgePanel.hidden = true;
      window.MindMeshGraph && window.MindMeshGraph.pause();
      // 3D models stay up longer than a static image since people like
      // to rotate/zoom them — no auto-hide timer here, click to dismiss.
      return;
    }

    if (visual.type === "knowledge") {
      const { title, image } = visual.data;
      if (!image) return; // nothing to show visually; canvas stays as-is
      clearTimeout(knowledgeTimer);
      els.knowledgeTitle.textContent = title;
      els.knowledgeImage.src = image;
      els.knowledgePanel.hidden = false;
      els.model3dPanel.hidden = true;
      window.MindMeshGraph && window.MindMeshGraph.pause();
      knowledgeTimer = setTimeout(hideKnowledge, 15000);
    }
  }

  function hideKnowledge() {
    els.knowledgePanel.hidden = true;
    els.model3dPanel.hidden = true;
    els.model3dFrame.src = "about:blank"; // stop the iframe running in the background
    window.MindMeshGraph && window.MindMeshGraph.resume();
  }

  els.knowledgePanel.addEventListener("click", hideKnowledge);
  // The 3D panel itself is meant to be dragged/zoomed, so only its title
  // acts as a "close" affordance rather than the whole surface.
  els.model3dTitle.addEventListener("click", hideKnowledge);
  els.model3dTitle.style.cursor = "pointer";

  // ---------------------------------------------------------------
  // Conversation
  // ---------------------------------------------------------------
  function appendMessage(role, text) {
    const wrap = document.createElement("div");
    wrap.className = `mm-msg mm-msg-${role}`;
    if (role === "assistant") {
      const avatar = document.createElement("span");
      avatar.className = "mm-msg-avatar";
      avatar.textContent = "AI";
      wrap.appendChild(avatar);
    }
    const bubble = document.createElement("div");
    bubble.className = "mm-msg-bubble";
    bubble.textContent = text;
    wrap.appendChild(bubble);
    els.messages.appendChild(wrap);
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  function setStatus(text) {
    els.statusText.textContent = text;
  }

  function sendMessage(text) {
    text = (text || "").trim();
    if (!text) return;

    appendMessage("user", text);
    els.chatInput.value = "";
    setStatus("THINKING…");

    fetch(cfg.chatUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": cfg.csrfToken,
      },
      body: JSON.stringify({ message: text }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          appendMessage("assistant", "Something went wrong: " + data.error);
          return;
        }
        appendMessage("assistant", data.reply);
        window.MindMeshSpeech && window.MindMeshSpeech.speak(data.reply);

        if (data.visual) {
          if (data.visual.type === "knowledge" || data.visual.type === "model3d") {
            showKnowledge(data.visual);
          }
          if (data.visual.type === "stats") renderStats(data.visual.data);
          if (data.visual.type === "weather") renderWeather(data.visual.data);
        }
      })
      .catch(() => {
        appendMessage("assistant", "I couldn't reach the server just now — please try again.");
      })
      .finally(() => setStatus("LISTENING FOR WAKE WORD"));
  }

  els.chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage(els.chatInput.value);
  });

  // ---------------------------------------------------------------
  // Mic buttons (inline + main footer button both do the same thing)
  // ---------------------------------------------------------------
  function handleMicClick() {
    if (!window.MindMeshSpeech || !window.MindMeshSpeech.supported()) {
      alert("Speech recognition isn't supported in this browser. Try Chrome or Edge, or just type your question.");
      return;
    }
    window.MindMeshSpeech.start(
      (text) => {
        els.chatInput.value = text;
        sendMessage(text);
      },
      (state) => {
        if (state === "listening") {
          setStatus("LISTENING…");
          els.micMain.classList.add("listening");
        } else {
          setStatus("LISTENING FOR WAKE WORD");
          els.micMain.classList.remove("listening");
        }
      }
    );
  }

  els.micMain.addEventListener("click", handleMicClick);
  els.micInline.addEventListener("click", handleMicClick);

  // ---------------------------------------------------------------
  // Refresh buttons
  // ---------------------------------------------------------------
  els.refreshStats.addEventListener("click", fetchStats);
  els.refreshWeather.addEventListener("click", () => fetchWeather());

  // ---------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------
  fetchStats();
  fetchWeather(cfg && cfg.defaultCity);
  setInterval(fetchStats, 5000);
  setInterval(() => fetchWeather(), 10 * 60 * 1000);
})();
