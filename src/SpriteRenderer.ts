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

export class SpriteRenderer {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  data: SceneData;
  depth: Uint8ClampedArray | null = null;
  water: Uint8ClampedArray | null = null;
  ready: Promise<void>;
  visible = { cars: 0, boats: 0, planes: 0, occluded: 0 };
  constructor(host: HTMLElement, data: SceneData) {
    this.data = data;
    this.canvas = document.createElement("canvas");
    this.canvas.className = "sprites";
    this.canvas.setAttribute("aria-hidden", "true");
    host.append(this.canvas);
    this.ctx = this.canvas.getContext("2d")!;
    this.ready = Promise.all(
      ["depth", "water"].map(async (name) => {
        const image = new Image();
        image.src = `${import.meta.env.BASE_URL}map/v1/${name}.png`;
        await image.decode();
        const c = document.createElement("canvas");
        c.width = data.width;
        c.height = data.height;
        const ctx = c.getContext("2d", { willReadFrequently: true })!;
        ctx.drawImage(image, 0, 0);
        const pixels = ctx.getImageData(0, 0, c.width, c.height).data;
        if (name === "depth") this.depth = pixels;
        else this.water = pixels;
      }),
    ).then(() => {});
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
    const q = project(p, this.data.projection),
      x = Math.round(q.x),
      y = Math.round(q.y);
    if (x < 0 || y < 0 || x >= this.data.width || y >= this.data.height)
      return false;
    if (plane || !this.depth) return true;
    const i = (y * this.data.width + x) * 4;
    const z = ((this.depth[i] * 256 + this.depth[i + 1]) / 65535) * 4000 - 2000;
    return q.depth + 4.5 >= z;
  }
  isWater(p: Point3) {
    if (!this.water) return false;
    const q = project(p, this.data.projection),
      x = Math.round(q.x),
      y = Math.round(q.y);
    return (
      x >= 0 &&
      y >= 0 &&
      x < this.data.width &&
      y < this.data.height &&
      this.water[(y * this.data.width + x) * 4] > 128
    );
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
        if (w.seed > 62 || !this.isVisible(w.p)) continue;
        const p = this.point(w.p, v);
        if (p.x < 0 || p.x > v.width || p.y < 0 || p.y > v.height) continue;
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
      const next = this.point(
        pose.point.map((value, i) => value + pose.direction[i]) as Point3,
        v,
      );
      const angle = Math.atan2(next.y - p.y, next.x - p.x),
        factor = Math.hypot(next.x - p.x, next.y - p.y);
      if (pose.kind === "ferry" || pose.kind === "cargo") {
        if (pose.moving) {
          const len = pose.kind === "cargo" ? 65 : 33;
          for (const side of [-1, 1]) {
            ctx.beginPath();
            let drawing = false;
            for (let j = 8; j < 70; j += 3) {
              const wobble =
                1 + Math.sin(j * 0.25 - frame.clock.transportTime * 3) * 0.1;
              const wp = pose.point.map(
                (value, i) =>
                  value -
                  pose.direction[i] * (len * 0.5 + j) +
                  (i === 0
                    ? -pose.direction[1]
                    : i === 1
                      ? pose.direction[0]
                      : 0) *
                    j *
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
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(angle);
      if (pose.kind === "car") {
        this.visible.cars++;
        const length = Math.max(4.5, 5 * factor),
          width = Math.max(2, 2.1 * unit * 0.8);
        ctx.fillStyle = "rgba(10,22,30,.35)";
        ctx.fillRect(-length / 2 + 1, -width / 2 + 1, length, width);
        ctx.fillStyle = pose.color;
        ctx.beginPath();
        ctx.roundRect(
          -length / 2,
          -width / 2,
          length,
          width,
          Math.min(1, width / 3),
        );
        ctx.fill();
        ctx.fillStyle = "#30414b";
        ctx.fillRect(-length * 0.12, -width * 0.4, length * 0.32, width * 0.8);
        if (night > 0.2) {
          ctx.fillStyle = `rgba(255,240,190,${night})`;
          ctx.fillRect(length / 2 - 1, -width / 2, 0.9, width);
          ctx.fillStyle = `rgba(239,79,54,${night})`;
          ctx.fillRect(-length / 2, -width / 2, 0.8, width);
          ctx.beginPath();
          ctx.moveTo(length / 2, -width * 0.35);
          ctx.lineTo(length * 1.8, -width * 1.8);
          ctx.lineTo(length * 1.8, width * 1.8);
          ctx.lineTo(length / 2, width * 0.35);
          ctx.closePath();
          ctx.fillStyle = `rgba(255,230,174,${night * 0.1})`;
          ctx.fill();
        }
      } else if (pose.kind === "plane") {
        this.visible.planes++;
        const u = Math.max(0.6, unit * 0.82);
        ctx.scale(u, u);
        ctx.beginPath();
        ctx.moveTo(19, 0);
        ctx.lineTo(8, -2);
        ctx.lineTo(-2, -15);
        ctx.lineTo(-5, -15);
        ctx.lineTo(-1, -2);
        ctx.lineTo(-12, -1.5);
        ctx.lineTo(-17, -6);
        ctx.lineTo(-19, -6);
        ctx.lineTo(-16, 0);
        ctx.lineTo(-19, 6);
        ctx.lineTo(-17, 6);
        ctx.lineTo(-12, 1.5);
        ctx.lineTo(-1, 2);
        ctx.lineTo(-5, 15);
        ctx.lineTo(-2, 15);
        ctx.lineTo(8, 2);
        ctx.closePath();
        ctx.fillStyle = "#e8e9e4";
        ctx.fill();
        ctx.strokeStyle = "#8d9d9e";
        ctx.lineWidth = 0.6;
        ctx.stroke();
        ctx.fillStyle = "#48697c";
        ctx.fillRect(10, -1, 4, 2);
        ctx.fillStyle = "#bb5038";
        ctx.fillRect(-15, -0.9, 6, 1.8);
        const pulse =
          0.45 + 0.55 * Math.max(0, Math.sin(frame.clock.transportTime * 4));
        ctx.fillStyle = `rgba(244,70,55,${pulse})`;
        ctx.fillRect(-4, -15, 2, 1.5);
        ctx.fillStyle = `rgba(116,225,157,${pulse})`;
        ctx.fillRect(-4, 14, 2, 1.5);
      } else {
        this.visible.boats++;
        const cargo = pose.kind === "cargo",
          length = (cargo ? 65 : 31) * factor,
          width = (cargo ? 15 : 9) * unit * 0.7;
        ctx.beginPath();
        ctx.moveTo(length / 2, 0);
        ctx.lineTo(length * 0.32, -width / 2);
        ctx.lineTo(-length * 0.46, -width / 2);
        ctx.lineTo(-length / 2, 0);
        ctx.lineTo(-length * 0.46, width / 2);
        ctx.lineTo(length * 0.32, width / 2);
        ctx.closePath();
        ctx.fillStyle = cargo ? "#543d36" : "#e8e8dc";
        ctx.fill();
        ctx.strokeStyle = "rgba(25,44,50,.6)";
        ctx.lineWidth = 0.8;
        ctx.stroke();
        if (cargo) {
          for (let i = 0; i < 6; i++) {
            ctx.fillStyle = ["#a56544", "#768c8a", "#b69b5e"][i % 3];
            ctx.fillRect(
              -length * 0.22 + i * length * 0.085,
              -width * 0.34,
              length * 0.07,
              width * 0.68,
            );
          }
          ctx.fillStyle = "#dddcd0";
          ctx.fillRect(
            -length * 0.43,
            -width * 0.35,
            length * 0.16,
            width * 0.7,
          );
        } else {
          ctx.fillStyle = "#a7b9bd";
          ctx.fillRect(
            -length * 0.28,
            -width * 0.33,
            length * 0.62,
            width * 0.66,
          );
          ctx.fillStyle = "#eef0e5";
          ctx.fillRect(
            -length * 0.21,
            -width * 0.2,
            length * 0.42,
            width * 0.4,
          );
          ctx.fillStyle = "#447484";
          ctx.fillRect(
            length * 0.15,
            -width * 0.22,
            length * 0.06,
            width * 0.44,
          );
        }
        if (night > 0.2) {
          ctx.fillStyle = `rgba(255,225,150,${night * 0.85})`;
          ctx.fillRect(
            -length * 0.2,
            -width * 0.37,
            length * 0.45,
            Math.max(1, unit * 0.5),
          );
        }
      }
      ctx.restore();
    }
    if (labels) {
      for (const landmark of this.data.landmarks) {
        const p = this.point(landmark.p, v);
        ctx.font = '500 11px "Segoe UI", "Microsoft YaHei", sans-serif';
        const width = ctx.measureText(landmark.nameZh).width + 20;
        ctx.fillStyle = "rgba(14,27,35,.78)";
        ctx.beginPath();
        ctx.roundRect(p.x - width / 2, p.y - 27, width, 23, 4);
        ctx.fill();
        ctx.fillStyle = "#efefe5";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(landmark.nameZh, p.x, p.y - 15.5);
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
