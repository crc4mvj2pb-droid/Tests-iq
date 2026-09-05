// All sound is synthesized at runtime via the WebAudio API. No external
// audio assets are used, which keeps the game license-clean and instant to load.

export class SoundEngine {
  private ctx: AudioContext | null = null;
  private engineOsc: OscillatorNode | null = null;
  private engineGain: GainNode | null = null;
  private masterGain: GainNode | null = null;
  enabled = true;

  private ensure() {
    if (!this.ctx) {
      this.ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.value = 0.5;
      this.masterGain.connect(this.ctx.destination);
    }
    if (this.ctx.state === 'suspended') void this.ctx.resume();
    return this.ctx;
  }

  startEngine() {
    if (!this.enabled) return;
    const ctx = this.ensure();
    if (this.engineOsc) return;
    this.engineOsc = ctx.createOscillator();
    this.engineOsc.type = 'sawtooth';
    this.engineGain = ctx.createGain();
    this.engineGain.gain.value = 0.0001;
    this.engineOsc.connect(this.engineGain);
    this.engineGain.connect(this.masterGain!);
    this.engineOsc.frequency.value = 60;
    this.engineOsc.start();
  }

  updateEngine(speed: number, throttle: boolean) {
    if (!this.enabled || !this.engineOsc || !this.engineGain || !this.ctx) return;
    const target = throttle ? 70 + Math.min(speed * 10, 220) : 40 + Math.min(speed * 6, 120);
    this.engineOsc.frequency.setTargetAtTime(target, this.ctx.currentTime, 0.08);
    this.engineGain.gain.setTargetAtTime(throttle ? 0.06 : 0.03, this.ctx.currentTime, 0.1);
  }

  stopEngine() {
    if (this.engineOsc) {
      try {
        this.engineOsc.stop();
      } catch {
        /* already stopped */
      }
      this.engineOsc.disconnect();
      this.engineOsc = null;
    }
  }

  private blip(freq: number, duration: number, type: OscillatorType = 'sine', gain = 0.25) {
    if (!this.enabled) return;
    const ctx = this.ensure();
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    g.gain.value = gain;
    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
    osc.connect(g);
    g.connect(this.masterGain!);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  }

  flip() {
    this.blip(520, 0.18, 'triangle', 0.2);
  }

  perfectLanding() {
    this.blip(880, 0.12, 'sine', 0.3);
    setTimeout(() => this.blip(1320, 0.15, 'sine', 0.25), 70);
  }

  landing() {
    this.blip(180, 0.1, 'square', 0.15);
  }

  crash() {
    if (!this.enabled) return;
    const ctx = this.ensure();
    const bufferSize = ctx.sampleRate * 0.35;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / bufferSize);
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;
    const g = ctx.createGain();
    g.gain.value = 0.4;
    noise.connect(g);
    g.connect(this.masterGain!);
    noise.start();
  }

  checkpoint() {
    this.blip(740, 0.1, 'sine', 0.2);
  }

  countdownBeep(final: boolean) {
    this.blip(final ? 880 : 440, 0.15, 'square', 0.2);
  }

  victory() {
    [523, 659, 784, 1046].forEach((f, i) => setTimeout(() => this.blip(f, 0.25, 'triangle', 0.25), i * 110));
  }
}

export const sound = new SoundEngine();
