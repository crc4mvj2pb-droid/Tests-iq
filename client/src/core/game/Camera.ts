export class Camera {
  x = 0;
  y = 0;
  zoom = 1;
  shake = 0;
  private shakeSeed = Math.random() * 1000;

  follow(targetX: number, targetY: number, speedFactorX: number, dt: number) {
    const leadX = targetX + Math.min(220, speedFactorX * 0.18);
    this.x += (leadX - this.x) * Math.min(1, dt * 4.5);
    this.y += (targetY - 40 - this.y) * Math.min(1, dt * 3.5);
    if (this.shake > 0) this.shake = Math.max(0, this.shake - dt * 3.2);
  }

  addShake(amount: number) {
    this.shake = Math.min(1, this.shake + amount);
  }

  applyTransform(ctx: CanvasRenderingContext2D, width: number, height: number) {
    let sx = 0;
    let sy = 0;
    if (this.shake > 0) {
      this.shakeSeed += 1;
      sx = Math.sin(this.shakeSeed * 12.9) * this.shake * 14;
      sy = Math.cos(this.shakeSeed * 7.3) * this.shake * 14;
    }
    ctx.translate(width / 2 + sx, height / 2 + sy);
    ctx.scale(this.zoom, this.zoom);
    ctx.translate(-this.x, -this.y);
  }
}
