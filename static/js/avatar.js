/* =========================================================================
   avatar.js - The original 2D cartoon avatar, drawn with the Canvas API.

   Nothing here is AI. It is ordinary drawing code that runs ~60 times per
   second (requestAnimationFrame). Each frame we:
     1. update timers (blinking, head bob, waving, particles)
     2. read the current loudness of the voice (0..1) to open the mouth
     3. draw background -> avatar -> greeting card -> disclosure text

   Lip-sync note: the mouth follows the LOUDNESS of the real audio
   (amplitude-based). It is NOT phoneme-level lip-sync, so mouth shapes
   do not match individual sounds like "o" or "m" exactly.
   ========================================================================= */

const AVATAR_THEMES = {
  Birthday:        { bg: ["#efe6ff", "#ffe3f1"], accent: "#ff6fae", particle: "confetti", headline: "Happy Birthday" },
  Anniversary:     { bg: ["#ffe6f0", "#efe7ff"], accent: "#ef5b8f", particle: "hearts",   headline: "Happy Anniversary" },
  Congratulations: { bg: ["#ece6ff", "#fff1d2"], accent: "#f2a516", particle: "confetti", headline: "Congratulations" },
  "Thank You":     { bg: ["#e3f1ff", "#efe8ff"], accent: "#4d9cf0", particle: "sparkles", headline: "Thank You" },
  Welcome:         { bg: ["#ddf4ff", "#efe9ff"], accent: "#3fb6c9", particle: "bubbles",  headline: "Welcome" },
  Festival:        { bg: ["#fff0d9", "#efe4ff"], accent: "#f08a24", particle: "lights",   headline: "Happy Festival" },
  Custom:          { bg: ["#efe9ff", "#e2f0ff"], accent: "#7c5cff", particle: "sparkles", headline: "Best Wishes" },
};

// Target face settings for each expression. The avatar smoothly moves
// toward these numbers, so changes look natural instead of jumping.
const EXPRESSIONS = {
  happy:     { browRaise: 0,  browTilt: 0,    smile: 1.0, eyeOpen: 1.0,  eyeSize: 1.0,  mouthO: 0 },
  excited:   { browRaise: 10, browTilt: -0.1, smile: 1.4, eyeOpen: 1.1,  eyeSize: 1.12, mouthO: 0 },
  calm:      { browRaise: -2, browTilt: 0,    smile: 0.6, eyeOpen: 0.72, eyeSize: 1.0,  mouthO: 0 },
  warm:      { browRaise: 4,  browTilt: 0.28, smile: 0.85, eyeOpen: 0.88, eyeSize: 1.0, mouthO: 0 },
  surprised: { browRaise: 16, browTilt: 0,    smile: 0.2, eyeOpen: 1.25, eyeSize: 1.2,  mouthO: 1 },
};

// Which expression "Auto" chooses for each tone.
const TONE_EXPRESSION = { Friendly: "happy", Formal: "calm", Funny: "excited", Heartfelt: "warm" };

const AVATAR_LOOKS = {
  skin:  ["#f6c7a1", "#e0a57c", "#b97a53", "#8d5a3b"],
  hair:  ["#3b2a4f", "#1f1a24", "#7a4a2b", "#c4703c"],
  shirt: ["#7c5cff", "#4d9cf0", "#ef5b8f", "#2fb38f"],
};

class AvatarRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.W = canvas.width;   // 960 - drawing size (the recorded video size)
    this.H = canvas.height;  // 540
    this.levelSource = () => 0;   // function returning voice loudness 0..1
    this.speaking = false;
    this.expressionName = "happy";
    this.face = { ...EXPRESSIONS.happy };
    this.look = { skin: AVATAR_LOOKS.skin[0], hair: AVATAR_LOOKS.hair[0], shirt: AVATAR_LOOKS.shirt[0] };
    this.mouthOpen = 0;
    this.blink = 0;                  // 0 = eyes open, 1 = closed
    this.nextBlinkAt = performance.now() + 1500;
    this.gaze = { x: 0, y: 0, tx: 0, ty: 0, next: 0 };
    this.waveUntil = 0;
    this.armLift = 0;
    this.caption = { headline: "Happy Birthday", name: "Your friend", from: "", source: "" };
    this.setTheme("Birthday");
    this.lastTime = performance.now();
    this.running = false;
  }

  /* ---------------- public methods used by app.js / recorder.js -------- */
  start() {
    if (this.running) return;
    this.running = true;
    const loop = (now) => {
      if (!this.running) return;
      this.update(now);
      this.draw(now);
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  setLevelSource(fn) { this.levelSource = fn; }
  setSpeaking(isSpeaking) { this.speaking = isSpeaking; }
  setExpression(name) { if (EXPRESSIONS[name]) this.expressionName = name; }
  setLook(part, color) { if (part in this.look) this.look[part] = color; }
  wave(ms = 1500) { this.waveUntil = performance.now() + ms; }

  setTheme(occasion) {
    this.theme = AVATAR_THEMES[occasion] || AVATAR_THEMES.Custom;
    this.particles = this.makeParticles(this.theme.particle, 34);
  }

  setCaption({ headline, name, from, source }) {
    this.caption = { headline: headline || this.theme.headline, name: name || "", from: from || "", source: source || "" };
  }

  /* ---------------- animation state ----------------------------------- */
  update(now) {
    const dt = Math.min(0.05, (now - this.lastTime) / 1000);
    this.lastTime = now;

    // Ease every face value toward the chosen expression.
    const target = EXPRESSIONS[this.expressionName];
    for (const key of Object.keys(this.face)) {
      this.face[key] += (target[key] - this.face[key]) * Math.min(1, dt * 6);
    }

    // Blinking: close quickly, open again, then wait 2-5 seconds.
    if (now >= this.nextBlinkAt) {
      const t = (now - this.nextBlinkAt) / 140;  // one blink = 2 x 140 ms
      this.blink = t < 1 ? t : t < 2 ? 2 - t : 0;
      if (t >= 2) this.nextBlinkAt = now + 2000 + Math.random() * 3000;
    }

    // Eyes look around a little now and then.
    if (now > this.gaze.next) {
      this.gaze.tx = (Math.random() - 0.5) * 6;
      this.gaze.ty = (Math.random() - 0.5) * 3;
      this.gaze.next = now + 1200 + Math.random() * 2500;
    }
    this.gaze.x += (this.gaze.tx - this.gaze.x) * dt * 5;
    this.gaze.y += (this.gaze.ty - this.gaze.y) * dt * 5;

    // Mouth: amplitude-based approximation of lip movement.
    let targetMouth = 0;
    if (this.speaking) {
      const level = Math.max(0, Math.min(1, this.levelSource() || 0));
      targetMouth = Math.pow(level, 0.8);
    }
    const speed = targetMouth > this.mouthOpen ? 0.55 : 0.28;   // open fast, close slower
    this.mouthOpen += (targetMouth - this.mouthOpen) * speed;

    // Raise the arm while waving.
    const waving = now < this.waveUntil;
    this.armLift += ((waving ? 1 : 0) - this.armLift) * Math.min(1, dt * 7);

    for (const p of this.particles) {
      p.y += p.vy * dt;
      p.x += Math.sin(now / 1000 * p.sway + p.phase) * 12 * dt;
      p.rot += p.vr * dt;
      if (p.vy > 0 && p.y > this.H + 20) { p.y = -20; p.x = Math.random() * this.W; }
      if (p.vy < 0 && p.y < -20) { p.y = this.H + 20; p.x = Math.random() * this.W; }
    }
  }

  makeParticles(kind, count) {
    const colors = ["#ff6fae", "#7c5cff", "#4d9cf0", "#ffc43d", "#2fc6a5", "#b388ff"];
    const list = [];
    for (let i = 0; i < count; i++) {
      const rising = kind === "bubbles" || kind === "hearts" || kind === "lights";
      list.push({
        kind, x: Math.random() * this.W, y: Math.random() * this.H,
        vy: (rising ? -1 : 1) * (14 + Math.random() * 26),
        size: 4 + Math.random() * 7, rot: Math.random() * 6.28, vr: (Math.random() - 0.5) * 3,
        sway: 0.5 + Math.random(), phase: Math.random() * 6.28,
        color: colors[i % colors.length], alpha: 0.35 + Math.random() * 0.45,
      });
    }
    return list;
  }

  /* ---------------- drawing ------------------------------------------- */
  draw(now) {
    const { ctx, W, H } = this;
    const t = now / 1000;

    // Background gradient + soft decorative circles.
    const grad = ctx.createLinearGradient(0, 0, W, H);
    grad.addColorStop(0, this.theme.bg[0]);
    grad.addColorStop(1, this.theme.bg[1]);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "rgba(255,255,255,0.45)";
    this.circle(120, 90, 70); this.circle(860, 470, 110); this.circle(520, 40, 36);
    this.drawParticles();

    // Floor shadow, then the avatar with a gentle idle bob.
    const bob = Math.sin(t * 2.1) * 4 + (this.speaking ? Math.sin(t * 9) * 1.5 * this.mouthOpen : 0);
    const tilt = Math.sin(t * 0.9) * 0.025 + (this.expressionName === "warm" ? 0.05 : 0);
    ctx.fillStyle = "rgba(80, 50, 140, 0.12)";
    ctx.beginPath(); ctx.ellipse(300, 520, 170, 22, 0, 0, Math.PI * 2); ctx.fill();
    this.drawAvatar(300, 240 + bob, tilt, t);

    this.drawCard(t);
    this.drawDisclosure();
  }

  circle(x, y, r) { const c = this.ctx; c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fill(); }

  drawParticles() {
    const c = this.ctx;
    for (const p of this.particles) {
      c.save();
      c.globalAlpha = p.alpha;
      c.translate(p.x, p.y);
      c.rotate(p.rot);
      c.fillStyle = p.color;
      if (p.kind === "confetti") {
        c.fillRect(-p.size / 2, -p.size, p.size, p.size * 2);
      } else if (p.kind === "hearts") {
        this.heart(0, 0, p.size * 1.6, "#ff7eb0");
      } else if (p.kind === "bubbles") {
        c.strokeStyle = "rgba(77,156,240,0.7)"; c.lineWidth = 2;
        c.beginPath(); c.arc(0, 0, p.size * 1.4, 0, Math.PI * 2); c.stroke();
      } else if (p.kind === "lights") {
        c.fillStyle = "#ffcf5a"; c.shadowColor = "#ffb12b"; c.shadowBlur = 14;
        c.beginPath(); c.arc(0, 0, p.size * 0.8, 0, Math.PI * 2); c.fill();
      } else { // sparkles: four-point star
        c.beginPath();
        const s = p.size * 1.3;
        c.moveTo(0, -s); c.lineTo(s * 0.25, -s * 0.25); c.lineTo(s, 0); c.lineTo(s * 0.25, s * 0.25);
        c.lineTo(0, s); c.lineTo(-s * 0.25, s * 0.25); c.lineTo(-s, 0); c.lineTo(-s * 0.25, -s * 0.25);
        c.closePath(); c.fill();
      }
      c.restore();
    }
  }

  heart(x, y, s, color) {
    const c = this.ctx;
    c.fillStyle = color;
    c.beginPath();
    c.moveTo(x, y + s * 0.3);
    c.bezierCurveTo(x - s, y - s * 0.4, x - s * 0.4, y - s, x, y - s * 0.35);
    c.bezierCurveTo(x + s * 0.4, y - s, x + s, y - s * 0.4, x, y + s * 0.3);
    c.fill();
  }

  drawAvatar(cx, cy, tilt, t) {
    const c = this.ctx;
    const f = this.face;
    const { skin, hair, shirt } = this.look;

    // ---- body (does not tilt with the head) ----
    const breathe = Math.sin(t * 1.6) * 2;
    c.fillStyle = shirt;
    c.beginPath();
    c.moveTo(cx - 175, 540);
    c.bezierCurveTo(cx - 170, cy + 175 - breathe, cx - 110, cy + 150, cx - 40, cy + 145);
    c.lineTo(cx + 40, cy + 145);
    c.bezierCurveTo(cx + 110, cy + 150, cx + 170, cy + 175 - breathe, cx + 175, 540);
    c.closePath();
    c.fill();
    // collar
    c.fillStyle = "rgba(255,255,255,0.85)";
    c.beginPath(); c.moveTo(cx - 42, cy + 145); c.lineTo(cx, cy + 195); c.lineTo(cx + 42, cy + 145); c.closePath(); c.fill();
    // neck
    c.fillStyle = this.shade(skin, -18);
    c.fillRect(cx - 30, cy + 95, 60, 55);
    c.beginPath(); c.moveTo(cx - 30, cy + 140); c.lineTo(cx, cy + 172); c.lineTo(cx + 30, cy + 140); c.fill();

    this.drawArm(cx, cy, t);

    // ---- head (tilts slightly) ----
    c.save();
    c.translate(cx, cy);
    c.rotate(tilt);

    c.fillStyle = hair;                                     // back hair
    c.beginPath(); c.ellipse(0, -8, 132, 140, 0, 0, Math.PI * 2); c.fill();
    c.beginPath(); c.roundRect(-132, -10, 264, 95, 40); c.fill();

    c.fillStyle = skin;                                     // ears
    c.beginPath(); c.ellipse(-112, 12, 16, 24, 0, 0, Math.PI * 2); c.fill();
    c.beginPath(); c.ellipse(112, 12, 16, 24, 0, 0, Math.PI * 2); c.fill();
    c.beginPath(); c.ellipse(0, 6, 110, 124, 0, 0, Math.PI * 2); c.fill();   // face

    c.fillStyle = hair;                                     // fringe / bangs
    c.beginPath();
    c.moveTo(-118, 0);
    c.bezierCurveTo(-132, -178, 132, -182, 118, -5);   // high enough to cover the top of the head
    c.bezierCurveTo(95, -55, 55, -70, 20, -62);
    c.bezierCurveTo(-5, -40, -60, -40, -80, -60);
    c.bezierCurveTo(-95, -40, -110, -25, -118, 0);
    c.fill();

    c.fillStyle = "rgba(255,120,150,0.30)";                 // cheeks
    c.beginPath(); c.ellipse(-62, 48, 20, 12, 0, 0, Math.PI * 2); c.fill();
    c.beginPath(); c.ellipse(62, 48, 20, 12, 0, 0, Math.PI * 2); c.fill();

    this.drawEyes(f);
    this.drawBrows(f, hair);

    c.strokeStyle = this.shade(skin, -45);                  // nose
    c.lineWidth = 3; c.lineCap = "round";
    c.beginPath(); c.moveTo(-4, 28); c.quadraticCurveTo(4, 36, -2, 40); c.stroke();

    this.drawMouth(f);
    c.restore();
  }

  drawEyes(f) {
    const c = this.ctx;
    const open = Math.max(0.05, f.eyeOpen * (1 - this.blink));
    for (const side of [-1, 1]) {
      const ex = side * 44, ey = 8;
      const rx = 19 * f.eyeSize, ry = 23 * f.eyeSize * Math.min(open, 1.2);
      if (open < 0.18) {                                     // closed eye = curved line
        c.strokeStyle = "#2b1f3a"; c.lineWidth = 4;
        c.beginPath(); c.moveTo(ex - rx, ey); c.quadraticCurveTo(ex, ey + 8, ex + rx, ey); c.stroke();
        continue;
      }
      c.fillStyle = "#ffffff";
      c.beginPath(); c.ellipse(ex, ey, rx, ry, 0, 0, Math.PI * 2); c.fill();
      c.save();
      c.beginPath(); c.ellipse(ex, ey, rx, ry, 0, 0, Math.PI * 2); c.clip();
      const gx = ex + this.gaze.x, gy = ey + this.gaze.y + 2;
      c.fillStyle = "#5b45b0"; c.beginPath(); c.arc(gx, gy, 13 * f.eyeSize, 0, Math.PI * 2); c.fill();
      c.fillStyle = "#1d1430"; c.beginPath(); c.arc(gx, gy, 6.5 * f.eyeSize, 0, Math.PI * 2); c.fill();
      c.fillStyle = "#ffffff"; c.beginPath(); c.arc(gx + 4, gy - 5, 3.5, 0, Math.PI * 2); c.fill();
      c.restore();
      c.strokeStyle = "#2b1f3a"; c.lineWidth = 3;          // upper lash line
      c.beginPath(); c.ellipse(ex, ey, rx, ry, 0, Math.PI * 1.08, Math.PI * 1.92); c.stroke();
    }
  }

  drawBrows(f, hair) {
    const c = this.ctx;
    c.strokeStyle = this.shade(hair, -10);
    c.lineWidth = 7; c.lineCap = "round";
    const lift = f.browRaise + (this.speaking ? this.mouthOpen * 4 : 0);
    for (const side of [-1, 1]) {
      const inner = -40 - lift + f.browTilt * -22;   // tilt > 0 raises inner ends (caring look)
      const outer = -34 - lift + f.browTilt * 10;
      c.beginPath();
      c.moveTo(side * 22, inner);
      c.quadraticCurveTo(side * 44, Math.min(inner, outer) - 8, side * 64, outer);
      c.stroke();
    }
  }

  drawMouth(f) {
    const c = this.ctx;
    const my = 72;
    const open = Math.max(this.mouthOpen, f.mouthO * 0.45);
    if (open < 0.06) {                                     // closed smile
      const w = 30 + f.smile * 10, curve = 6 + f.smile * 12;
      c.strokeStyle = "#8a2d4b"; c.lineWidth = 5; c.lineCap = "round";
      c.beginPath(); c.moveTo(-w, my - 4); c.quadraticCurveTo(0, my - 4 + curve * 1.6, w, my - 4); c.stroke();
      return;
    }
    const w = 28 + f.smile * 8 - open * 6;
    const h = 8 + open * 40;
    c.fillStyle = "#6b1f3c";
    c.beginPath();
    c.moveTo(-w, my - 6);
    c.quadraticCurveTo(0, my - 6 - 4 + f.smile * 3, w, my - 6);          // upper lip
    c.quadraticCurveTo(w * 0.9, my - 6 + h, 0, my - 6 + h);               // lower right
    c.quadraticCurveTo(-w * 0.9, my - 6 + h, -w, my - 6);                 // lower left
    c.fill();
    c.save();
    c.clip();
    if (open > 0.22) {                                                     // teeth
      c.fillStyle = "#fffdf8";
      c.fillRect(-w * 0.7, my - 9, w * 1.4, 7 + open * 3);
    }
    c.fillStyle = "#ef7b9a";                                               // tongue
    c.beginPath(); c.ellipse(0, my - 6 + h, w * 0.6, h * 0.42, 0, 0, Math.PI * 2); c.fill();
    c.restore();
  }

  drawArm(cx, cy, t) {
    if (this.armLift < 0.02) return;
    const c = this.ctx;
    const lift = this.armLift;
    const shoulderX = cx + 120, shoulderY = cy + 190;
    const swing = Math.sin(t * 10) * 0.35 * lift;
    const handX = shoulderX + 70 + Math.sin(swing) * 30;
    const handY = shoulderY - 170 * lift + 30;
    c.strokeStyle = this.look.shirt; c.lineWidth = 34; c.lineCap = "round";
    c.beginPath(); c.moveTo(shoulderX, shoulderY); c.quadraticCurveTo(shoulderX + 70, shoulderY - 40, handX, handY + 30); c.stroke();
    c.save();
    c.translate(handX, handY);
    c.rotate(swing);
    c.fillStyle = this.look.skin;
    c.beginPath(); c.ellipse(0, 0, 24, 27, 0, 0, Math.PI * 2); c.fill();
    for (let i = 0; i < 4; i++) {
      c.beginPath(); c.ellipse(-15 + i * 10, -27, 5.5, 13, 0, 0, Math.PI * 2); c.fill();
    }
    c.beginPath(); c.ellipse(24, -2, 6, 12, -0.8, 0, Math.PI * 2); c.fill();   // thumb
    c.restore();
  }

  drawCard(t) {
    const c = this.ctx;
    const x = 540, y = 110, w = 380, h = 300;
    c.save();
    c.shadowColor = "rgba(90, 60, 160, 0.18)"; c.shadowBlur = 24; c.shadowOffsetY = 8;
    c.fillStyle = "rgba(255,255,255,0.86)";
    c.beginPath(); c.roundRect(x, y, w, h, 26); c.fill();
    c.restore();

    c.textAlign = "center";
    const mid = x + w / 2;
    c.fillStyle = this.theme.accent;
    this.fitText(this.caption.headline, mid, y + 70, w - 40, 40, "700");

    const nameGrad = c.createLinearGradient(x, 0, x + w, 0);
    nameGrad.addColorStop(0, "#6a4cf0"); nameGrad.addColorStop(1, "#4d9cf0");
    c.fillStyle = nameGrad;
    this.fitText(this.caption.name, mid, y + 145, w - 40, 58, "800");

    if (this.caption.from) {
      c.fillStyle = "#6f6890";
      this.fitText(`with love from ${this.caption.from}`, mid, y + 192, w - 50, 22, "500");
    }

    // Speaking indicator: five bars that follow the voice loudness.
    const level = this.speaking ? this.mouthOpen : 0;
    for (let i = 0; i < 5; i++) {
      const wobble = this.speaking ? (Math.sin(t * 12 + i * 1.3) + 1) / 2 : 0;
      const barH = 8 + level * 42 * (0.5 + wobble * 0.5);
      c.fillStyle = this.speaking ? this.theme.accent : "#d6cdf3";
      c.beginPath(); c.roundRect(mid - 50 + i * 22, y + 255 - barH / 2, 12, barH, 6); c.fill();
    }
    c.fillStyle = this.speaking ? this.theme.accent : "#a59cc6";
    c.font = "600 15px 'Segoe UI', system-ui, sans-serif";
    c.fillText(this.speaking ? "speaking..." : "", mid, y + 292);
  }

  drawDisclosure() {
    const c = this.ctx;
    const text = "Animated, computer-generated avatar - not a real person" +
      (this.caption.source ? `  |  ${this.caption.source}` : "");
    c.font = "500 14px 'Segoe UI', system-ui, sans-serif";
    const width = c.measureText(text).width + 24;
    c.fillStyle = "rgba(255,255,255,0.75)";
    c.beginPath(); c.roundRect(14, this.H - 38, width, 26, 13); c.fill();
    c.fillStyle = "#5a4f80"; c.textAlign = "left";
    c.fillText(text, 26, this.H - 20);
  }

  /** Draw text, shrinking the font until it fits the given width. */
  fitText(text, x, y, maxWidth, size, weight) {
    const c = this.ctx;
    let s = size;
    do {
      c.font = `${weight} ${s}px 'Segoe UI', system-ui, sans-serif`;
      s -= 2;
    } while (c.measureText(text).width > maxWidth && s > 12);
    c.fillText(text, x, y);
  }

  /** Make a hex colour lighter (+) or darker (-). */
  shade(hex, amount) {
    const n = parseInt(hex.slice(1), 16);
    const clamp = (v) => Math.max(0, Math.min(255, v));
    const r = clamp((n >> 16) + amount), g = clamp(((n >> 8) & 255) + amount), b = clamp((n & 255) + amount);
    return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
  }
}

window.AvatarRenderer = AvatarRenderer;
window.AVATAR_LOOKS = AVATAR_LOOKS;
window.TONE_EXPRESSION = TONE_EXPRESSION;
