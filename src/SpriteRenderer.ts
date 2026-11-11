import { maskPath } from "./assets.ts";
import { decodeSourceDepth, fitMaskTexture, legacyDepthEncoding, maskIndex } from "./atlas.ts";
import { nightAmount, project } from "./model.ts";
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
    this.ready = Promise.all(
      (data.maskBundle ? ["depth"] : ["depth", "water"]).map(async (name) => {
        const image = new Image();
        image.src = maskPath(data, name);
        await image.decode();
        const pixels = readMask(image, this.maskWidth, this.maskHeight);
        if (name === "depth") this.depth = pixels;
        if (name === "water" || data.maskBundle) this.water = pixels;
      }),
    ).then(() => {});
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
    this.visible = { cars: 0, boats: 0, planes: 0, occluded: 0 };
    if (night > 0.01) {
      ctx.globalCompositeOperation = "screen";
      for (const w of this.data.windows) {
        if (w.seed > 62) continue;
        const p = this.point(w.p, v);
        if (p.x < 0 || p.x > v.width || p.y < 0 || p.y > v.height) continue;
        if (!this.isVisible(w.p)) continue;
        ctx.fillStyle = `rgba(255,${185 + (w.seed % 50)},${95 + (w.seed % 65)},${night * (0.12 + (w.seed % 7) * 0.015)})`;
        const ww = Math.max(1.2, unit * 0.8),
          hh = Math.max(1.6, unit * 1.4);
        ctx.fillRect(p.x - ww / 2, p.y - hh / 2, ww, hh);
      }
      for (const lamp of this.data.lamps) {
        if (!this.isVisible(lamp)) continue;
        const p = this.point(lamp, v),
          r = Math.max(3, unit * 4);
        const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r);
        g.addColorStop(0, `rgba(255,218,133,${night * 0.8})`);
        g.addColorStop(0.25, `rgba(255,196,104,${night * 0.28})`);
        g.addColorStop(1, "rgba(255,196,104,0)");
        ctx.fillStyle = g;
        ctx.fillRect(p.x - r, p.y - r, r * 2, r * 2);
      }
      ctx.globalCompositeOperation = "source-over";
    }
    const poses = frame.poses
      .slice()
      .sort(
        (a, b) =>
          project(a.point, this.data.projection).depth -
          project(b.point, this.data.projection).depth,
      );
    for (const pose of poses) {
      if (!this.isVisible(pose.point, pose.kind === "plane")) {
        this.visible.occluded++;
        continue;
      }
      const p = this.point(pose.point, v);
      if (
        p.x < -100 ||
        p.x > v.width + 100 ||
        p.y < -100 ||
        p.y > v.height + 100
      )
        continue;
      if (pose.kind === "ferry" || pose.kind === "cargo") {
        if (pose.moving) {
          const wakeScale = this.data.kind === "bay" ? 28 : 1,
            len =
              (pose.kind === "cargo" ? 65 : 33) *
              (this.data.transportScale ?? 1);
          for (const side of [-1, 1]) {
            ctx.beginPath();
            let drawing = false;
            for (let j = 8; j < 70; j += 3) {
              const wobble =
                1 + Math.sin(j * 0.25 - frame.clock.transportTime * 3) * 0.1;
              const wp = pose.point.map(
                (value, i) =>
                  value -
                  pose.direction[i] * (len * 0.5 + j * wakeScale) +
                  (i === 0
                    ? -pose.direction[1]
                    : i === 1
                      ? pose.direction[0]
                      : 0) *
                    j *
                    wakeScale *
                    0.16 *
                    side *
                    wobble,
              ) as Point3;
              const sp = this.point(wp, v);
              if (this.isWater(wp)) {
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
      }
      if (pose.kind === "car") this.visible.cars++;
      else if (pose.kind === "plane") this.visible.planes++;
      else this.visible.boats++;
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
