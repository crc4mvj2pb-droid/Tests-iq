// Small synthesized sound effects — no external audio files to download or license.
export class AudioManager {
  private ctx: AudioContext | null = null;

  private ensure(): AudioContext {
    if (!this.ctx) this.ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    if (this.ctx.state === 'suspended') this.ctx.resume();
    return this.ctx;
  }

  unlock() {
    this.ensure();
  }

  private tone(freq: number, duration: number, type: OscillatorType, gainPeak: number, delay = 0, glideTo?: number) {
    const ctx = this.ensure();
    const t0 = ctx.currentTime + delay;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (glideTo) osc.frequency.exponentialRampToValueAtTime(Math.max(20, glideTo), t0 + duration);
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(gainPeak, t0 + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
    osc.connect(gain).connect(ctx.destination);
    osc.start(t0);
    osc.stop(t0 + duration + 0.05);
  }

  jump() {
    this.tone(340, 0.14, 'square', 0.08, 0, 520);
  }

  land() {
    this.tone(140, 0.12, 'sine', 0.1, 0, 70);
  }

  pickup() {
    this.tone(520, 0.08, 'triangle', 0.09, 0, 780);
    this.tone(780, 0.1, 'triangle', 0.07, 0.06);
  }

  useItem() {
    this.tone(300, 0.1, 'sine', 0.08, 0, 460);
  }

  fall() {
    this.tone(220, 0.4, 'sawtooth', 0.06, 0, 60);
  }

  hurt() {
    this.tone(120, 0.2, 'square', 0.1, 0, 50);
  }

  click() {
    this.tone(600, 0.05, 'square', 0.05);
  }

  summit() {
    [523, 659, 784, 1046].forEach((f, i) => this.tone(f, 0.35, 'triangle', 0.09, i * 0.12));
  }
}
