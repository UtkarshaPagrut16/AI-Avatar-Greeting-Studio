/* =========================================================================
   voice.js - Plays the generated speech file and measures its loudness.

   Uses the Web Audio API to build this small "audio graph":

        <audio> element ──► MediaElementSource ──┬──► Analyser ──► speakers
                                                 └──► MediaStreamDestination
                                                        (audio track for recording)

   * The Analyser tells the avatar how loud the voice is (mouth movement).
   * The MediaStreamDestination gives recorder.js a real audio TRACK that it
     can combine with the canvas video track. Just playing an <audio> tag
     next to a canvas would NOT put sound into the recording.
   ========================================================================= */

class VoicePlayer {
  constructor(audioElement) {
    this.audio = audioElement;
    this.ctx = null;          // AudioContext, created on the first click
    this.analyser = null;
    this.recordDestination = null;
    this.samples = null;
    this.hasAudio = false;
  }

  /** Build the audio graph once. Must be called after a user click (browser rule). */
  ensureGraph() {
    if (this.ctx) return true;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return false;
    this.ctx = new AudioCtx();
    const source = this.ctx.createMediaElementSource(this.audio);  // allowed only once per element
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 1024;
    this.samples = new Float32Array(this.analyser.fftSize);
    this.recordDestination = this.ctx.createMediaStreamDestination();
    source.connect(this.analyser);
    this.analyser.connect(this.ctx.destination);   // so we can hear it
    source.connect(this.recordDestination);        // so it can be recorded
    return true;
  }

  /** Load a new speech file and wait until its length is known. */
  load(url) {
    return new Promise((resolve, reject) => {
      const onReady = () => { cleanup(); this.hasAudio = true; resolve(this.audio.duration); };
      const onError = () => { cleanup(); this.hasAudio = false; reject(new Error("The browser could not load the speech file.")); };
      const cleanup = () => {
        this.audio.removeEventListener("loadedmetadata", onReady);
        this.audio.removeEventListener("error", onError);
      };
      this.audio.addEventListener("loadedmetadata", onReady);
      this.audio.addEventListener("error", onError);
      this.audio.src = url;
      this.audio.load();
    });
  }

  async play() {
    if (!this.hasAudio) throw new Error("Create the voice first.");
    this.ensureGraph();
    if (this.ctx && this.ctx.state === "suspended") await this.ctx.resume();
    await this.audio.play();
  }

  pause() { this.audio.pause(); }

  stop() {
    this.audio.pause();
    if (this.hasAudio) this.audio.currentTime = 0;
  }

  async replay() {
    this.stop();
    await this.play();
  }

  get isPlaying() { return !this.audio.paused && !this.audio.ended; }
  get duration() { return Number.isFinite(this.audio.duration) ? this.audio.duration : 0; }

  /** Current loudness 0..1 (root-mean-square of the waveform). */
  level() {
    if (!this.analyser || !this.isPlaying) return 0;
    this.analyser.getFloatTimeDomainData(this.samples);
    let sum = 0;
    for (let i = 0; i < this.samples.length; i++) sum += this.samples[i] * this.samples[i];
    const rms = Math.sqrt(sum / this.samples.length);
    return Math.max(0, Math.min(1, (rms - 0.012) / 0.16));   // ignore silence, scale speech
  }

  /** The audio track that recorder.js adds to the video. */
  recordingTrack() {
    if (!this.ensureGraph()) return null;
    return this.recordDestination.stream.getAudioTracks()[0] || null;
  }
}

window.VoicePlayer = VoicePlayer;
