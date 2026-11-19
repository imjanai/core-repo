export class DrawingViewer {
  constructor(canvas, { select, place, isPlacing }) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.select = select;
    this.place = place;
    this.isPlacing = isPlacing;
    this.symbols = [];
    this.lines = new Path2D();
    this.bounds = null;
    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.selected = null;
    this.drag = null;
    new ResizeObserver(() => {
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.round(canvas.clientWidth * ratio);
      canvas.height = Math.round(canvas.clientHeight * ratio);
      if (!this.fitted) this.fit();
      else this.draw();
    }).observe(canvas);
    canvas.addEventListener("wheel", event => {
      event.preventDefault();
      this.zoom(event.deltaY < 0 ? 1.18 : 1 / 1.18, event.offsetX, event.offsetY);
    }, { passive: false });
    canvas.addEventListener("pointerdown", event => {
      if (!event.isPrimary || event.button !== 0) return;
      canvas.setPointerCapture(event.pointerId);
      this.drag = { x: event.offsetX, y: event.offsetY, left: this.offsetX, top: this.offsetY };
    });
    canvas.addEventListener("pointermove", event => {
      if (!this.drag || !event.isPrimary) return;
      this.offsetX = this.drag.left + event.offsetX - this.drag.x;
      this.offsetY = this.drag.top + event.offsetY - this.drag.y;
      this.draw();
    });
    canvas.addEventListener("pointercancel", () => { this.drag = null; });
    canvas.addEventListener("pointerup", event => {
      if (!this.drag || !event.isPrimary) return;
      const distance = Math.hypot(event.offsetX - this.drag.x, event.offsetY - this.drag.y);
      this.drag = null;
      if (distance > 5) return;
      const x = (event.offsetX - this.offsetX) / this.scale;
      const y = (this.offsetY - event.offsetY) / this.scale;
      if (this.isPlacing()) {
        this.place(x, y);
        return;
      }
      let nearest = null;
      let best = 14 / this.scale;
      for (const symbol of this.symbols) {
        const separation = Math.hypot(symbol.x - x, symbol.y - y);
        if (separation < best) {
          nearest = symbol.id;
          best = separation;
        }
      }
      if (nearest) this.select(nearest);
    });
  }

  load(paths) {
    this.lines = new Path2D();
    this.bounds = { left: Infinity, right: -Infinity, bottom: Infinity, top: -Infinity };
    for (const path of paths) {
      for (const [index, [x, y]] of path.entries()) {
        if (index === 0) this.lines.moveTo(x, -y);
        else this.lines.lineTo(x, -y);
        this.bounds.left = Math.min(this.bounds.left, x);
        this.bounds.right = Math.max(this.bounds.right, x);
        this.bounds.bottom = Math.min(this.bounds.bottom, y);
        this.bounds.top = Math.max(this.bounds.top, y);
      }
    }
    this.fitted = false;
    this.fit();
  }

  fit() {
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;
    if (!width || !height) return;
    const bounds = { ...this.bounds };
    let { left = Infinity, right = -Infinity, bottom = Infinity, top = -Infinity } = bounds;
    for (const { x, y } of this.symbols) {
      left = Math.min(left, x);
      right = Math.max(right, x);
      bottom = Math.min(bottom, y);
      top = Math.max(top, y);
    }
    if (!Number.isFinite(left)) [left, right, bottom, top] = [-1000, 1000, -1000, 1000];
    this.scale = Math.min((width - 50) / Math.max(100, right - left), (height - 50) / Math.max(100, top - bottom));
    this.fitScale = this.scale;
    this.offsetX = width / 2 - (left + right) / 2 * this.scale;
    this.offsetY = height / 2 + (bottom + top) / 2 * this.scale;
    this.fitted = true;
    this.draw();
  }

  zoom(factor, x = this.canvas.clientWidth / 2, y = this.canvas.clientHeight / 2) {
    const next = Math.max(this.fitScale / 8, Math.min(this.fitScale * 100, this.scale * factor));
    const ratio = next / this.scale;
    this.offsetX = x - (x - this.offsetX) * ratio;
    this.offsetY = y - (y - this.offsetY) * ratio;
    this.scale = next;
    this.draw();
  }

  draw() {
    const ctx = this.context;
    const ratio = window.devicePixelRatio || 1;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.setTransform(ratio * this.scale, 0, 0, ratio * this.scale, ratio * this.offsetX, ratio * this.offsetY);
    ctx.strokeStyle = "#9dbdc2";
    ctx.lineWidth = 1 / this.scale;
    ctx.stroke(this.lines);
    for (const symbol of this.symbols) {
      const selected = symbol.id === this.selected;
      ctx.beginPath();
      ctx.arc(symbol.x, -symbol.y, (selected ? 8 : 5) / this.scale, 0, Math.PI * 2);
      ctx.fillStyle = selected ? "#ffc77a" : "#55ddb0";
      ctx.fill();
      ctx.strokeStyle = "#142b32";
      ctx.lineWidth = 1.5 / this.scale;
      ctx.stroke();
    }
  }
}
