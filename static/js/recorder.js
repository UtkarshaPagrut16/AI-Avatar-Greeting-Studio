/* =========================================================================
   recorder.js - Records the animated canvas + the voice into one WebM video.

   Steps (all inside the browser, nothing is uploaded to the internet):
     1. canvas.captureStream(30)          -> a VIDEO track (30 frames/second)
     2. voice.recordingTrack()            -> an AUDIO track (from Web Audio)
     3. new MediaStream([video, audio])   -> one combined stream
     4. new MediaRecorder(stream, {mimeType: "video/webm;codecs=vp9,opus"})
     5. start recording, wave for a moment, play the voice, wait for "ended"
     6. stop -> collect the chunks -> Blob -> downloadable .webm file

   Success is reported ONLY from the recorder's "stop" event, after all data
   has arrived and the file is checked to be non-empty.
   ========================================================================= */

const LEAD_IN_MS = 900;     // avatar waves before speaking
const TAIL_MS = 1300;       // avatar waves goodbye after speaking
const FPS = 30;

class RecorderError extends Error {
  constructor(message, code = "error") {
    super(message);
    this.code = code;       // "error" or "cancelled"
  }
}

class GreetingRecorder {
  constructor(canvas, voice, avatar) {
    this.canvas = canvas;
    this.voice = voice;
    this.avatar = avatar;
    this.cancelFn = null;
  }

  /** Can this browser record? Returns {ok, reason}. */
  static checkSupport(canvas) {
    if (typeof window.MediaRecorder === "undefined") {
      return { ok: false, reason: "This browser does not support MediaRecorder. Please use Chrome or Edge." };
    }
    if (!canvas || typeof canvas.captureStream !== "function") {
      return { ok: false, reason: "This browser cannot capture the canvas. Please use Chrome or Edge." };
    }
    if (!(window.AudioContext || window.webkitAudioContext)) {
      return { ok: false, reason: "This browser does not support the Web Audio API." };
    }
    if (!GreetingRecorder.pickMimeType()) {
      return { ok: false, reason: "This browser cannot record WebM video with audio." };
    }
    return { ok: true, reason: "" };
  }

  /** Pick the first WebM format (video + audio codecs) the browser supports. */
  static pickMimeType() {
    const options = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"];
    return options.find((type) => window.MediaRecorder && MediaRecorder.isTypeSupported(type)) || "";
  }

  get isRecording() { return this.cancelFn !== null; }

  cancel() { if (this.cancelFn) this.cancelFn(); }

  /**
   * Record the greeting. Resolves with {blob, mimeType, seconds}.
   * onProgress(fraction 0..1, text) is called about 5 times per second.
   */
  async record(onProgress = () => {}) {
    const support = GreetingRecorder.checkSupport(this.canvas);
    if (!support.ok) throw new RecorderError(support.reason);
    if (!this.voice.hasAudio || !this.voice.duration) throw new RecorderError("Create the voice before recording.");

    this.voice.stop();
    this.voice.ensureGraph();
    if (this.voice.ctx.state === "suspended") await this.voice.ctx.resume();

    const audioTrack = this.voice.recordingTrack();
    if (!audioTrack) throw new RecorderError("Could not get an audio track for the recording.");
    const canvasStream = this.canvas.captureStream(FPS);
    const videoTrack = canvasStream.getVideoTracks()[0];
    if (!videoTrack) throw new RecorderError("Could not capture the avatar animation.");

    const mimeType = GreetingRecorder.pickMimeType();
    const combined = new MediaStream([videoTrack, audioTrack]);
    let recorder;
    try {
      recorder = new MediaRecorder(combined, { mimeType, videoBitsPerSecond: 3_000_000, audioBitsPerSecond: 128_000 });
    } catch (err) {
      videoTrack.stop();
      throw new RecorderError("The browser refused to start recording: " + err.message);
    }

    const totalMs = LEAD_IN_MS + this.voice.duration * 1000 + TAIL_MS;
    const chunks = [];
    const startedAt = performance.now();

    return new Promise((resolve, reject) => {
      let finished = false;
      let ticker = null, guard = null, leadTimer = null, tailTimer = null;
      const audio = this.voice.audio;

      const cleanup = () => {
        clearInterval(ticker); clearTimeout(guard); clearTimeout(leadTimer); clearTimeout(tailTimer);
        audio.removeEventListener("ended", onEnded);
        audio.removeEventListener("error", onAudioError);
        videoTrack.stop();               // stop capturing the canvas (audio track is reused)
        this.avatar.setSpeaking(false);
        this.cancelFn = null;
      };

      const fail = (message, code = "error") => {
        if (finished) return;
        finished = true;
        this.voice.stop();
        try { if (recorder.state !== "inactive") recorder.stop(); } catch (_) { /* ignore */ }
        cleanup();
        reject(new RecorderError(message, code));
      };

      const onEnded = () => {
        this.avatar.setSpeaking(false);
        this.avatar.wave(TAIL_MS);
        onProgress(0.97, "Saying goodbye...");
        tailTimer = setTimeout(() => { if (recorder.state === "recording") recorder.stop(); }, TAIL_MS);
      };
      const onAudioError = () => fail("The voice stopped because of a playback error.");

      recorder.ondataavailable = (event) => { if (event.data && event.data.size > 0) chunks.push(event.data); };
      recorder.onerror = (event) => fail("Recording error: " + ((event.error && event.error.message) || "unknown"));
      recorder.onstop = () => {
        if (finished) return;                // already failed or cancelled
        finished = true;
        cleanup();
        const blob = new Blob(chunks, { type: "video/webm" });
        if (blob.size < 2000) {
          reject(new RecorderError("The recording came out empty. Please try again and keep this tab visible."));
          return;
        }
        onProgress(1, "Finished");
        resolve({ blob, mimeType, seconds: (performance.now() - startedAt) / 1000 });
      };

      audio.addEventListener("ended", onEnded);
      audio.addEventListener("error", onAudioError);
      this.cancelFn = () => fail("Recording cancelled.", "cancelled");

      try {
        recorder.start(250);                 // deliver data every 250 ms
      } catch (err) {
        fail("Could not start recording: " + err.message);
        return;
      }
      this.avatar.wave(LEAD_IN_MS + 400);
      onProgress(0.01, "Recording intro...");

      leadTimer = setTimeout(async () => {
        if (finished) return;
        try {
          await this.voice.play();
          this.avatar.setSpeaking(true);
        } catch (err) {
          fail("Could not play the voice for recording: " + err.message);
        }
      }, LEAD_IN_MS);

      ticker = setInterval(() => {
        const fraction = Math.min(0.96, (performance.now() - startedAt) / totalMs);
        onProgress(fraction, this.voice.isPlaying ? "Recording - avatar is speaking..." : "Recording...");
      }, 200);

      // Safety net: never record forever if "ended" is missed.
      guard = setTimeout(() => fail("Recording took longer than expected and was stopped."), totalMs + 15000);
    });
  }
}

window.GreetingRecorder = GreetingRecorder;
window.RecorderError = RecorderError;
