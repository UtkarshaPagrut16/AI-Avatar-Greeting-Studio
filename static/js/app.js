/* =========================================================================
   app.js - Connects the page to the Flask API and to the avatar/voice/recorder.

   Flow:  form -> POST /api/generate-script -> editable script
               -> POST /api/tts            -> speech .wav -> VoicePlayer
               -> GreetingRecorder.record() -> WebM Blob -> preview + download
               -> POST /api/videos          -> saved in local gallery
   ========================================================================= */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);

  // ---------------- shared state ----------------
  const state = {
    details: null,          // last form values sent to the server
    source: null,           // "llm" or "template"
    model: null,
    originalScript: "",     // text exactly as generated (to detect edits)
    voiceForScript: null,   // script text the current voice was made from
    voiceLanguage: null,
    status: null,
    recording: false,
    lastVideoUrl: null,
  };

  const avatar = new AvatarRenderer($("avatarCanvas"));
  const voice = new VoicePlayer($("voiceAudio"));
  const recorder = new GreetingRecorder($("avatarCanvas"), voice, avatar);
  avatar.setLevelSource(() => voice.level());
  avatar.start();

  // ---------------- small helpers ----------------
  function toast(message, type = "info", ms = 4500) {
    const el = document.createElement("div");
    el.className = `toast toast-${type}`;
    el.textContent = message;
    $("toastArea").appendChild(el);
    setTimeout(() => el.classList.add("hide"), ms);
    setTimeout(() => el.remove(), ms + 400);
  }

  function setBusy(button, busy, busyText) {
    if (busy) {
      button.dataset.label = button.innerHTML;
      button.innerHTML = `<span class="spinner"></span> ${busyText}`;
      button.disabled = true;
    } else if (button.dataset.label) {
      button.innerHTML = button.dataset.label;
      button.disabled = false;
    }
  }

  function setStep(n) {
    document.querySelectorAll(".step").forEach((el) => {
      const s = Number(el.dataset.step);
      el.classList.toggle("done", s < n);
      el.classList.toggle("active", s === n);
    });
  }

  async function api(url, options = {}) {
    let response;
    try {
      response = await fetch(url, options);
    } catch (err) {
      throw new Error("Cannot reach the app server. Is the black run_windows.bat window still open?");
    }
    let data = {};
    try { data = await response.json(); } catch (_) { /* not JSON */ }
    if (!response.ok || data.ok === false) {
      const error = new Error(data.error || `Server error (${response.status}).`);
      error.fields = data.fields;
      throw error;
    }
    return data;
  }

  const words = (text) => (text.trim() ? text.trim().split(/\s+/).length : 0);

  // ---------------- status chips ----------------
  async function loadStatus() {
    try {
      const s = await api("/api/status");
      state.status = s;
      const llm = $("chipLlm");
      if (s.llm.runner && s.llm.model_ready) {
        llm.textContent = `🤖 LLM ready: ${s.llm.model}`; llm.className = "chip chip-ok";
      } else if (s.llm.runner) {
        llm.textContent = `⚠ Model ${s.llm.model} not downloaded – template fallback`; llm.className = "chip chip-warn";
      } else {
        llm.textContent = "⚠ Ollama not running – template fallback"; llm.className = "chip chip-warn";
      }
      const vc = $("chipVoice");
      if (!s.tts.installed) { vc.textContent = "✖ Voice: pyttsx3 missing"; vc.className = "chip chip-bad"; }
      else if (s.tts.error) { vc.textContent = "✖ Voice engine error"; vc.className = "chip chip-bad"; vc.title = s.tts.error; }
      else { vc.textContent = `🔊 Voices: ${s.tts.voices.length}`; vc.className = "chip chip-ok";
             vc.title = s.tts.voices.map((v) => v.name).join("\n"); }
      const ff = $("chipFfmpeg");
      ff.textContent = s.ffmpeg ? "🎬 FFmpeg: MP4 available" : "FFmpeg: not installed (optional)";
      ff.className = s.ffmpeg ? "chip chip-ok" : "chip chip-muted";
      updateLanguageOptions();
    } catch (err) {
      $("chipLlm").textContent = "Server not reachable";
      $("chipLlm").className = "chip chip-bad";
    }
  }

  function updateLanguageOptions() {
    const langs = (state.status && state.status.tts && state.status.tts.languages) || {};
    const select = $("languageSelect");
    let hint = "";
    for (const option of select.options) {
      const ok = langs[option.value] !== false;
      option.disabled = !ok;
      option.textContent = option.textContent.replace(" – no voice installed", "") + (ok ? "" : " – no voice installed");
      if (!ok && option.value === "hi") hint = "Hindi needs a Hindi Windows voice. Use Hinglish instead.";
    }
    if (select.selectedOptions[0] && select.selectedOptions[0].disabled) select.value = "en";
    $("languageHint").textContent = hint;
  }

  // ---------------- step 1: form ----------------
  const form = $("greetingForm");

  function updateOccasionField() {
    const occasion = $("occasionSelect").value;
    const wrap = $("occasionNameWrap");
    const show = occasion === "Festival" || occasion === "Custom";
    wrap.classList.toggle("hidden", !show);
    $("occasionNameLabel").textContent = occasion === "Custom" ? "Describe the occasion *" : "Festival name";
    form.occasion_name.placeholder = occasion === "Custom" ? "e.g. Farewell, Graduation" : "e.g. Diwali, Eid, Christmas";
    avatar.setTheme(occasion);
    refreshCaption();
  }

  function readForm() {
    const data = Object.fromEntries(new FormData(form).entries());
    if (data.occasion !== "Festival" && data.occasion !== "Custom") data.occasion_name = "";
    return data;
  }

  function clearFieldErrors() {
    document.querySelectorAll(".field-error").forEach((el) => { el.textContent = ""; });
    form.querySelectorAll(".invalid").forEach((el) => el.classList.remove("invalid"));
  }

  function showFieldErrors(fields = {}) {
    for (const [name, message] of Object.entries(fields)) {
      const slot = document.querySelector(`.field-error[data-for="${name}"]`);
      if (slot) slot.textContent = message;
      if (form[name] && form[name].classList) form[name].classList.add("invalid");
    }
  }

  function quickValidate(data) {
    const errors = {};
    if (!data.recipient.trim()) errors.recipient = "Recipient name is required.";
    if (!data.sender.trim()) errors.sender = "Sender name is required.";
    if (data.occasion === "Custom" && !data.occasion_name.trim()) errors.occasion_name = "Please describe the occasion.";
    return errors;
  }

  function headlineFor(details) {
    if (!details) return "";
    const event = details.occasion_name;
    switch (details.occasion) {
      case "Festival": return event ? `Happy ${event}` : "Happy Festival";
      case "Custom": return event || "Best Wishes";
      default: return AVATAR_THEMES[details.occasion].headline;
    }
  }

  function refreshCaption() {
    const d = state.details || readForm();
    const sourceText = state.source === "llm" ? `Script: local AI (${state.model})`
      : state.source === "template" ? "Script: template (not AI)" : "";
    const edited = state.source && $("scriptBox").value.trim() !== state.originalScript.trim() ? ", edited" : "";
    avatar.setCaption({
      headline: headlineFor(d),
      name: (d.recipient || "").trim() || "Your friend",
      from: (d.sender || "").trim(),
      source: sourceText ? sourceText + edited : "",
    });
  }

  function applyAutoExpression() {
    const active = document.querySelector("#expressionRow .mini.active");
    if (active && active.dataset.expression === "auto") {
      const tone = (state.details || readForm()).tone;
      avatar.setExpression(TONE_EXPRESSION[tone] || "happy");
    }
  }

  async function generateScript() {
    clearFieldErrors();
    const data = readForm();
    const quick = quickValidate(data);
    if (Object.keys(quick).length) { showFieldErrors(quick); toast("Please fill in the required fields.", "error"); return; }

    const usingLLM = state.status && state.status.llm.model_ready;
    const buttons = [$("generateBtn"), $("regenerateBtn")];
    buttons.forEach((b) => setBusy(b, true, usingLLM ? "AI is writing..." : "Generating..."));
    $("scriptBox").classList.add("loading");
    try {
      const result = await api("/api/generate-script", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
      });
      state.details = data;
      state.source = result.source;
      state.model = result.model;
      state.originalScript = result.script;
      $("scriptBox").value = result.script;
      showSource(result);
      onScriptChanged();
      avatar.setTheme(data.occasion);
      applyAutoExpression();
      refreshCaption();
      setStep(2);
      $("regenerateBtn").disabled = false;
      toast(result.source === "llm" ? "Greeting written by the local AI model." :
        "LLM unavailable – template fallback used (not AI).", result.source === "llm" ? "success" : "warn");
    } catch (err) {
      showFieldErrors(err.fields);
      toast(err.message, "error", 7000);
    } finally {
      buttons.forEach((b) => setBusy(b, false));
      $("regenerateBtn").disabled = !state.source;
      $("scriptBox").classList.remove("loading");
      loadStatus();
    }
  }

  function showSource(result) {
    const badge = $("sourceBadge");
    badge.classList.remove("hidden", "badge-ai", "badge-template");
    if (result.source === "llm") {
      badge.textContent = `🤖 AI-generated · ${result.model}`;
      badge.classList.add("badge-ai");
    } else {
      badge.textContent = "📄 Template fallback – NOT AI";
      badge.classList.add("badge-template");
    }
    const notice = $("sourceNotice");
    notice.textContent = result.notice;
    notice.className = "notice " + (result.source === "llm" ? "notice-ai" : "notice-template");
  }

  // ---------------- step 2: script editing ----------------
  function onScriptChanged() {
    const text = $("scriptBox").value;
    const n = words(text);
    const seconds = Math.round(n / (165 / 60));
    $("wordCount").textContent = `${n} words · about ${seconds} s of speech`;
    const edited = state.source && text.trim() !== state.originalScript.trim();
    $("editedFlag").classList.toggle("hidden", !edited);
    $("voiceBtn").disabled = n === 0;
    if (state.voiceForScript !== null && text !== state.voiceForScript) {
      $("voiceInfo").textContent = "⚠ The script changed. Click “Create voice” again so speech matches the text.";
      $("voiceInfo").className = "voice-info warn";
      setRecordEnabled();
    }
    refreshCaption();
  }

  // ---------------- step 3: voice ----------------
  async function createVoice() {
    const script = $("scriptBox").value.trim();
    if (!script) { toast("The script is empty.", "error"); return; }
    voice.ensureGraph();        // created inside the click so the browser allows audio
    voice.stop();
    const language = (state.details || readForm()).language;
    setBusy($("voiceBtn"), true, "Creating voice...");
    try {
      const result = await api("/api/tts", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script, language }),
      });
      const duration = await voice.load(result.url);
      state.voiceForScript = $("scriptBox").value;
      state.voiceLanguage = language;
      $("voiceInfo").textContent = `🔊 Voice: ${result.voice_name} · ${duration.toFixed(1)} s (offline speech, pyttsx3)`;
      $("voiceInfo").className = "voice-info ok";
      ["playBtn", "pauseBtn", "stopBtn", "replayBtn"].forEach((id) => { $(id).disabled = false; });
      setStep(3);
      setRecordEnabled();
      toast("Voice created. Press ▶ Play to preview.", "success");
    } catch (err) {
      toast(err.message, "error", 8000);
    } finally {
      setBusy($("voiceBtn"), false);
    }
  }

  function voiceIsCurrent() {
    return voice.hasAudio && state.voiceForScript !== null && state.voiceForScript === $("scriptBox").value;
  }

  function setRecordEnabled() {
    $("recordBtn").disabled = state.recording || !voiceIsCurrent() || !$("consentBox").checked;
    $("recordBtn").title = !voiceIsCurrent() ? "Create the voice first"
      : !$("consentBox").checked ? "Tick the consent box first" : "";
  }

  // Avatar speaking state follows the REAL audio element events.
  const audioEl = $("voiceAudio");
  audioEl.addEventListener("play", () => { avatar.setSpeaking(true); $("speakingBadge").classList.remove("hidden"); });
  ["pause", "ended"].forEach((evt) => audioEl.addEventListener(evt, () => {
    avatar.setSpeaking(false); $("speakingBadge").classList.add("hidden");
    if (evt === "ended" && !state.recording) avatar.wave(1200);
  }));

  async function safePlay(action) {
    try { await action(); } catch (err) { toast("Could not play audio: " + err.message, "error"); }
  }

  // ---------------- step 4: record ----------------
  async function recordVideo() {
    if (!voiceIsCurrent()) { toast("Create the voice for the current script first.", "error"); return; }
    if (!$("consentBox").checked) { toast("Please tick the consent box first.", "error"); return; }
    const support = GreetingRecorder.checkSupport($("avatarCanvas"));
    if (!support.ok) { toast(support.reason, "error", 8000); return; }

    state.recording = true;
    setRecordEnabled();
    ["playBtn", "pauseBtn", "stopBtn", "replayBtn", "voiceBtn", "generateBtn", "regenerateBtn"]
      .forEach((id) => { $(id).disabled = true; });
    $("scriptBox").readOnly = true;
    $("cancelRecordBtn").classList.remove("hidden");
    $("recordProgress").classList.remove("hidden");
    $("resultBox").classList.add("hidden");
    $("recordStatus").className = "record-status";
    $("recordBtn").innerHTML = '<span class="rec-dot"></span> Recording...';

    try {
      const result = await recorder.record((fraction, text) => {
        $("recordBar").style.width = `${Math.round(fraction * 100)}%`;
        $("recordStatus").textContent = `${text} (${Math.round(fraction * 100)}%) – keep this tab open and visible.`;
      });
      showResult(result);
      setStep(4);
      await saveToGallery(result.blob);
    } catch (err) {
      const cancelled = err.code === "cancelled";
      $("recordStatus").textContent = cancelled ? "Recording cancelled. Nothing was saved." : "❌ " + err.message;
      $("recordStatus").className = "record-status " + (cancelled ? "" : "error");
      toast(err.message, cancelled ? "info" : "error", 7000);
    } finally {
      state.recording = false;
      $("recordBtn").innerHTML = "● Record greeting video";
      $("cancelRecordBtn").classList.add("hidden");
      $("recordProgress").classList.add("hidden");
      $("recordBar").style.width = "0%";
      $("scriptBox").readOnly = false;
      ["playBtn", "pauseBtn", "stopBtn", "replayBtn"].forEach((id) => { $(id).disabled = !voice.hasAudio; });
      $("voiceBtn").disabled = words($("scriptBox").value) === 0;
      $("generateBtn").disabled = false;
      $("regenerateBtn").disabled = !state.source;
      setRecordEnabled();
    }
  }

  function downloadName() {
    const d = state.details || readForm();
    const slug = (s) => (s || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "greeting";
    const now = new Date();
    const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}` +
      `-${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(2, "0")}`;
    return `greeting_${slug(d.recipient)}_${slug(d.occasion)}_${stamp}.webm`;
  }

  function showResult(result) {
    if (state.lastVideoUrl) URL.revokeObjectURL(state.lastVideoUrl);
    const url = URL.createObjectURL(result.blob);
    state.lastVideoUrl = url;
    const video = $("resultVideo");
    video.src = url;
    // MediaRecorder WebM files have no length in their header; this trick makes
    // the browser scan the file so the seek bar shows the correct duration.
    video.onloadedmetadata = () => {
      if (video.duration === Infinity) {
        video.currentTime = 1e101;
        video.ontimeupdate = () => { video.ontimeupdate = null; video.currentTime = 0; };
      }
    };
    const link = $("downloadLink");
    link.href = url;
    link.download = downloadName();
    $("resultInfo").textContent = `${(result.blob.size / 1024 / 1024).toFixed(2)} MB · ${result.mimeType} · ` +
      "contains the avatar animation and the voice. Plays in Chrome, Edge, Firefox or VLC.";
    $("resultBox").classList.remove("hidden");
    $("recordStatus").textContent = "✅ Recording finished successfully.";
    $("recordStatus").className = "record-status success";
    toast("Video recorded! You can play or download it now.", "success");
  }

  async function saveToGallery(blob) {
    const d = state.details || readForm();
    const body = new FormData();
    body.append("video", blob, "greeting.webm");
    body.append("label", `${d.occasion} for ${d.recipient}`.slice(0, 80));
    try {
      const res = await api("/api/videos", { method: "POST", body });
      const st = res.video.streams;
      let check = "";
      if (st) check = st.video && st.audio ? " FFprobe check: ✅ video + audio tracks found." : " FFprobe check: ⚠ a track is missing.";
      $("resultInfo").textContent += ` Saved to the gallery.${check}`;
      loadGallery();
    } catch (err) {
      $("resultInfo").textContent += " (Could not save a copy to the gallery: " + err.message + " – the download button still works.)";
    }
  }

  // ---------------- gallery ----------------
  async function loadGallery() {
    try {
      const res = await api("/api/videos");
      renderGallery(res.videos, res.ffmpeg);
    } catch (err) {
      $("gallery").innerHTML = `<p class="empty">Could not load the gallery: ${escapeHtml(err.message)}</p>`;
    }
  }

  function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function renderGallery(videos, ffmpeg) {
    const box = $("gallery");
    if (!videos.length) { box.innerHTML = '<p class="empty">No videos yet. Record your first greeting above!</p>'; return; }
    box.innerHTML = videos.map((v) => {
      const streams = v.streams ? (v.streams.video && v.streams.audio
        ? '<span class="tag tag-ok">✓ video + audio</span>' : '<span class="tag tag-warn">track missing</span>') : "";
      const mp4 = v.mp4_url ? `<a class="btn btn-light btn-small" href="${v.mp4_url}?download=1">⬇ MP4</a>`
        : ffmpeg ? `<button class="btn btn-light btn-small" data-mp4="${v.name}">Make MP4</button>` : "";
      return `<div class="gallery-item">
          <video src="${v.url}" controls preload="metadata"></video>
          <div class="gallery-meta"><strong>${escapeHtml(v.label)}</strong>
            <small>${escapeHtml(v.created)} · ${v.size_kb} KB</small>${streams}</div>
          <div class="btn-row">
            <a class="btn btn-primary btn-small" href="${v.url}?download=1">⬇ WebM</a>${mp4}
            <button class="btn btn-danger btn-small" data-delete="${v.name}">Delete</button>
          </div></div>`;
    }).join("");
  }

  $("gallery").addEventListener("click", async (event) => {
    const del = event.target.closest("[data-delete]");
    const mp4 = event.target.closest("[data-mp4]");
    if (del) {
      if (!confirm("Delete this video from the gallery?")) return;
      try { await api(`/api/videos/${encodeURIComponent(del.dataset.delete)}`, { method: "DELETE" }); loadGallery(); toast("Video deleted.", "info"); }
      catch (err) { toast(err.message, "error"); }
    }
    if (mp4) {
      setBusy(mp4, true, "Converting...");
      try { await api(`/api/videos/${encodeURIComponent(mp4.dataset.mp4)}/mp4`, { method: "POST" }); toast("MP4 copy created.", "success"); loadGallery(); }
      catch (err) { toast(err.message, "error", 7000); setBusy(mp4, false); }
    }
  });

  // ---------------- avatar customisation ----------------
  function buildSwatches() {
    const names = { skin: "Skin", hair: "Hair", shirt: "Shirt" };
    $("swatchGroups").innerHTML = Object.entries(AVATAR_LOOKS).map(([part, colors]) =>
      `<div class="swatch-group"><span>${names[part]}</span>${colors.map((c, i) =>
        `<button class="swatch${i === 0 ? " active" : ""}" style="background:${c}" data-part="${part}" data-color="${c}" aria-label="${names[part]} colour ${i + 1}"></button>`).join("")}</div>`).join("");
  }

  $("swatchGroups").addEventListener("click", (event) => {
    const sw = event.target.closest(".swatch");
    if (!sw) return;
    document.querySelectorAll(`.swatch[data-part="${sw.dataset.part}"]`).forEach((b) => b.classList.remove("active"));
    sw.classList.add("active");
    avatar.setLook(sw.dataset.part, sw.dataset.color);
  });

  $("expressionRow").addEventListener("click", (event) => {
    const btn = event.target.closest(".mini");
    if (!btn) return;
    document.querySelectorAll("#expressionRow .mini").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    if (btn.dataset.expression === "auto") applyAutoExpression();
    else avatar.setExpression(btn.dataset.expression);
  });

  // ---------------- wire up events ----------------
  form.addEventListener("submit", (e) => { e.preventDefault(); generateScript(); });
  $("regenerateBtn").addEventListener("click", generateScript);
  $("occasionSelect").addEventListener("change", updateOccasionField);
  form.addEventListener("input", (e) => {
    if (e.target.name === "message") $("messageCount").textContent = e.target.value.length;
    if (e.target.name === "recipient" || e.target.name === "sender") { if (!state.details) refreshCaption(); }
    if (e.target.name === "tone") applyAutoExpression();
  });
  form.addEventListener("change", (e) => { if (e.target.name === "tone") applyAutoExpression(); });
  $("scriptBox").addEventListener("input", onScriptChanged);
  $("voiceBtn").addEventListener("click", createVoice);
  $("playBtn").addEventListener("click", () => safePlay(() => voice.play()));
  $("pauseBtn").addEventListener("click", () => voice.pause());
  $("stopBtn").addEventListener("click", () => voice.stop());
  $("replayBtn").addEventListener("click", () => safePlay(() => voice.replay()));
  $("consentBox").addEventListener("change", setRecordEnabled);
  $("recordBtn").addEventListener("click", recordVideo);
  $("cancelRecordBtn").addEventListener("click", () => recorder.cancel());
  $("refreshGalleryBtn").addEventListener("click", loadGallery);

  buildSwatches();
  updateOccasionField();
  applyAutoExpression();
  loadStatus();
  loadGallery();

  // Exposed only for the automated browser check (tests/e2e) and debugging.
  window.greetingStudio = { state, avatar, voice, recorder };
})();
