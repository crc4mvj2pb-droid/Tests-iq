interface Particle {
  x: number; y: number; vx: number; vy: number; life: number; maxLife: number; size: number; color: string;
}

export class ParticleSystem {
  private particles: Particle[] = [];

  spawnDust(x: number, y: number, dir: number, color: string, count = 4) {
    for (let i = 0; i < count; i++) {
      this.particles.push({
        x, y,
        vx: -dir * (1 + Math.random() * 2) + (Math.random() - 0.5),
        vy: -Math.random() * 1.5,
        life: 0.4 + Math.random() * 0.3,
        maxLife: 0.7,
        size: 3 + Math.random() * 3,
        color,
      });
    }
  }

  spawnSparks(x: number, y: number, color: string, count = 14) {
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2;
      const speed = 2 + Math.random() * 5;
      this.particles.push({
        x, y,
        vx: Math.cos(a) * speed,
        vy: Math.sin(a) * speed - 1,
        life: 0.5 + Math.random() * 0.4,
        maxLife: 0.9,
        size: 2 + Math.random() * 2.5,
        color,
      });
    }
  }

  spawnLanding(x: number, y: number, color: string) {
    for (let i = 0; i < 10; i++) {
      const a = Math.PI + Math.random() * Math.PI;
      const speed = 1 + Math.random() * 3;
      this.particles.push({
        x, y,
        vx: Math.cos(a) * speed,
        vy: Math.sin(a) * speed * 0.6,
        life: 0.4,
        maxLife: 0.5,
        size: 2 + Math.random() * 3,
        color,
      });
    }
  }

  update(dt: number) {
    for (const p of this.particles) {
      p.x += p.vx * dt * 60;
      p.y += p.vy * dt * 60;
      p.vy += dt * 9;
      p.life -= dt;
    }
    this.particles = this.particles.filter((p) => p.life > 0);
  }

  draw(ctx: CanvasRenderingContext2D) {
    for (const p of this.particles) {
      ctx.globalAlpha = Math.max(0, p.life / p.maxLife);
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
}
