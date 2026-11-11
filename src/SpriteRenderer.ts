import { maskPath } from "./assets.ts";
import { decodeSourceDepth, fitMaskTexture, legacyDepthEncoding, maskIndex } from "./atlas.ts";
import { nightAmount, project, transportMagnification } from "./model.ts";
import type { Frame, Point3, SceneData } from "./types.ts";
export type ViewTransform = {
  left: number;
  top: number;
  scale: number;
  width: number;
  height: number;
  dpr: number;
};

function readMask(image: HTMLImageElement, width: number, height: number) {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  const read = (left: number, top: number, columns: number, rows: number) => {
    canvas.width = columns;
    canvas.height = rows;
    ctx.drawImage(image, left, top, columns, rows, 0, 0, columns, rows);
    return ctx.getImageData(0, 0, columns, rows).data;
  };
  const canvasLimit = 4096;
  if (width <= canvasLimit && height <= canvasLimit) return read(0, 0, width, height);

  const pixels = new Uint8ClampedArray(width * height * 4);
  for (let top = 0; top < height; top += canvasLimit) {
    for (let left = 0; left < width; left += canvasLimit) {
      const columns = Math.min(canvasLimit, width - left);
      const rows = Math.min(canvasLimit, height - top);
      const strip = read(left, top, columns, rows);
      for (let row = 0; row < rows; row++) {
        const start = row * columns * 4;
        pixels.set(strip.subarray(start, start + columns * 4), ((top + row) * width + left) * 4);
      }
    }
  }
  return pixels;
}

export class SpriteRenderer {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  data: SceneData;
  maskWidth: number;
  maskHeight: number;
  depth: Uint8ClampedArray | null = null;
  water: Uint8ClampedArray | null = null;
  ready: Promise<void>;
  private windowLights = new Map<number, { x: number; y: number }[]>();
  private lampLights: { x: number; y: number }[] = [];
  private lampGlow: HTMLCanvasElement;
  visible = { cars: 0, boats: 0, planes: 0, occluded: 0 };
  constructor(host: HTMLElement, data: SceneData) {
    this.data = data;
    [this.maskWidth, this.maskHeight] = data.maskSize ?? [
      data.width,
      data.height,
    ];
    this.canvas = document.createElement("canvas");
    this.canvas.className = "sprites";
    this.canvas.setAttribute("aria-hidden", "true");
    host.append(this.canvas);
    this.ctx = this.canvas.getContext("2d")!;
    this.lampGlow = document.createElement("canvas");
    this.lampGlow.width = this.lampGlow.height = 64;
    const glow = this.lampGlow.getContext("2d")!;
    const gradient = glow.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, "rgba(255,218,133,.8)");
    gradient.addColorStop(0.25, "rgba(255,196,104,.28)");
    gradient.addColorStop(1, "rgba(255,196,104,0)");
    glow.fillStyle = gradient;
    glow.fillRect(0, 0, 64, 64);
    this.ready = Promise.all(
      (data.maskBundle ? ["depth"] : ["depth", "water"]).map(async (name) => {
        const image = new Image();
        image.src = maskPath(data, name);
        await image.decode();
        const pixels = readMask(image, this.maskWidth, this.maskHeight);
        if (name === "depth") this.depth = pixels;
        if (name === "water" || data.maskBundle) this.water = pixels;
      }),
    ).then(() => {
      const visible = (p: Point3) => data.lightsPreFiltered || this.isVisible(p);
      for (const { p, seed } of data.windows) {
        if (seed > 62 || !visible(p)) continue;
        const group = this.windowLights.get(seed) ?? [];
        group.push(project(p, data.projection));
        this.windowLights.set(seed, group);
      }
      this.lampLights = data.lamps.filter(visible).map(p => project(p, data.projection));
    });
  }
  depthTexture(gl: WebGL2RenderingContext) {
    return fitMaskTexture(this.depth!, this.maskWidth, this.maskHeight, gl.getParameter(gl.MAX_TEXTURE_SIZE));
  }
  point(p: Point3, v: ViewTransform) {
    const q = project(p, this.data.projection);
    return {
      x: q.x * v.scale + v.left,
      y: q.y * v.scale + v.top,
      depth: q.depth,
      ix: q.x,
      iy: q.y,
    };
  }
  isVisible(p: Point3, plane = false) {
    const q = project(p, this.data.projection);
    const i = maskIndex(
      q.x,
      q.y,
      this.data.width,
      this.data.height,
      this.maskWidth,
      this.maskHeight,
    );
    if (i < 0) return false;
    if (plane || !this.depth) return true;
    let z = decodeSourceDepth(
      this.depth[i],
      this.depth[i + 1],
      this.data.depthEncoding ?? legacyDepthEncoding,
    );
    if (this.data.maskBundle) {
      const p = this.data.projection;
      const centre = (Math.floor(q.y / this.data.height * this.maskHeight) + .5)
        * this.data.height / this.maskHeight;
      z += (q.y - centre) * p.cosElevation / (p.scale * p.sinElevation);
    }
    return q.depth + 4.5 >= z;
  }
  isWater(p: Point3) {
    if (!this.water) return false;
    const q = project(p, this.data.projection);
    const i = maskIndex(
      q.x,
      q.y,
      this.data.width,
      this.data.height,
      this.maskWidth,
      this.maskHeight,
    );
    return i >= 0 && (this.data.maskBundle ? (this.water[i + 2] & 2) !== 0 : this.water[i] > 128);
  }
  draw(frame: Frame, v: ViewTransform, labels: boolean) {
    const c = this.canvas,
      ctx = this.ctx;
    if (
      c.width !== Math.round(v.width * v.dpr) ||
      c.height !== Math.round(v.height * v.dpr)
    ) {
      c.width = Math.round(v.width * v.dpr);
      c.height = Math.round(v.height * v.dpr);
    }
    ctx.setTransform(v.dpr, 0, 0, v.dpr, 0, 0);
    ctx.clearRect(0, 0, v.width, v.height);
    ctx.save();
    ctx.beginPath();
    ctx.rect(
      v.left,
      v.top,
      this.data.width * v.scale,
      this.data.height * v.scale,
    );
    ctx.clip();
    const night = nightAmount(frame.clock.hour),
      unit = this.data.projection.scale * v.scale;
    // At citywide zoom the minimum on-screen lamp size would saturate dense districts.
    const light = this.data.lightsPreFiltered ? night * Math.min(1, v.scale / 0.24) ** 1.65 : night;
    this.visible = { cars: 0, boats: 0, planes: 0, occluded: 0 };
    if (light > 0.01) {
      ctx.globalCompositeOperation = "screen";
      const ww = Math.max(1.2, unit * 0.8), hh = Math.max(1.6, unit * 1.4);
      for (const [seed, windows] of this.windowLights) {
        ctx.fillStyle = `rgba(255,${185 + (seed % 50)},${95 + (seed % 65)},${light * (0.12 + (seed % 7) * 0.015)})`;
        for (const window of windows) {
          const x = window.x * v.scale + v.left, y = window.y * v.scale + v.top;
          if (x < 0 || x > v.width || y < 0 || y > v.height) continue;
          ctx.fillRect(x - ww / 2, y - hh / 2, ww, hh);
        }
      }
      const r = Math.max(3, unit * 4);
      ctx.globalAlpha = light;
      for (const lamp of this.lampLights) {
        const x = lamp.x * v.scale + v.left, y = lamp.y * v.scale + v.top;
        if (x < -r || x > v.width + r || y < -r || y > v.height + r) continue;
        ctx.drawImage(this.lampGlow, x - r, y - r, r * 2, r * 2);
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
    }
    const wakes = [];
    for (const pose of frame.poses) {
      const p = this.point(pose.point, v);
      if (
        p.x < -100 ||
        p.x > v.width + 100 ||
        p.y < -100 ||
        p.y > v.height + 100
      )
        continue;
      if (!this.isVisible(pose.point, pose.kind === "plane")) {
        this.visible.occluded++;
        continue;
      }
      if (pose.kind === "car") this.visible.cars++;
      else if (pose.kind === "plane") this.visible.planes++;
      else {
        this.visible.boats++;
        if (pose.moving) wakes.push({ pose, depth: p.depth });
      }
    }
    wakes.sort((a, b) => a.depth - b.depth);
    const magnification = transportMagnification(this.data.transportScale ?? 1, unit, this.data.adaptiveTransport);
    const wakeScale = this.data.adaptiveTransport ? magnification * 28 / 38 : this.data.kind === "bay" ? 28 : 1;
    for (const { pose } of wakes) {
      const len = (pose.kind === "cargo" ? 65 : 33) * magnification;
      for (const side of [-1, 1]) {
        ctx.beginPath();
        let drawing = false;
        for (let j = 8; j < 70; j += 3) {
          const wobble = 1 + Math.sin(j * 0.25 - frame.clock.transportTime * 3) * 0.1;
          const distance = len * 0.5 + j * wakeScale;
          const spread = j * wakeScale * 0.16 * side * wobble;
          const [e, n, z] = pose.direction;
          const wp: Point3 = [
            pose.point[0] - e * distance - n * spread,
            pose.point[1] - n * distance + e * spread,
            pose.point[2] - z * distance,
          ];
          if (this.isWater(wp)) {
            const sp = this.point(wp, v);
            if (!drawing) ctx.moveTo(sp.x, sp.y);
            else ctx.lineTo(sp.x, sp.y);
            drawing = true;
          } else drawing = false;
        }
        ctx.strokeStyle = `rgba(205,234,228,${0.46 - night * 0.2})`;
        ctx.lineWidth = Math.max(0.6, unit * 0.5);
        ctx.stroke();
      }
    }
    if (labels) {
      for (const landmark of this.data.landmarks) {
        const p = this.point(landmark.p, v);
        ctx.font = '500 11px "Segoe UI", sans-serif';
        const width = ctx.measureText(landmark.name).width + 20;
        ctx.fillStyle = "rgba(14,27,35,.78)";
        ctx.beginPath();
        ctx.roundRect(p.x - width / 2, p.y - 27, width, 23, 4);
        ctx.fill();
        ctx.fillStyle = "#efefe5";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(landmark.name, p.x, p.y - 15.5);
        ctx.beginPath();
        ctx.arc(p.x, p.y, 2.4, 0, Math.PI * 2);
        ctx.fillStyle = "#f4b64c";
        ctx.fill();
      }
    }
    ctx.restore();
  }
  destroy() {
    this.canvas.remove();
  }
}
