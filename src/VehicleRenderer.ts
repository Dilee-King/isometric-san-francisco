import { carStyle, heading, vehicleFaces } from "./VehicleGeometry.ts";
import { interpolateImageOffset, legacyDepthEncoding } from "./atlas.ts";
import bridgeOffsets from "../data/illustrated-expansion/bridge-image-offsets.json";
import type { VehicleFace } from "./VehicleGeometry.ts";
import { nightAmount, project, transportMagnification } from "./model.ts";
import type { Frame, Pose, SceneData } from "./types.ts";
import type { SpriteRenderer, ViewTransform } from "./SpriteRenderer.ts";

const vertex = `#version 300 es
precision highp float;
in vec3 localPosition;
in vec3 localNormal;
in vec4 paint;
in float emission;
in vec2 worldShift;
in vec3 anchor;
in vec2 heading;
in float imageOffsetY;
uniform float modelScale;
uniform vec4 view;
uniform vec2 viewport;
uniform vec4 basis;
uniform vec3 camera;
uniform vec2 origin;
uniform float clipDepth;
out vec2 imagePoint;
out float cameraDepth;
out vec4 color;
out float lit;
vec2 rotateENU(vec2 p){
 return vec2(p.x*heading.x-p.y*heading.y,p.x*heading.y+p.y*heading.x);
}
void main(){
 vec3 position=anchor+modelScale*vec3(rotateENU(localPosition.xy)+worldShift,localPosition.z);
 float u=position.x*basis.x+position.y*basis.z;
 float q=position.x*basis.y+position.y*basis.w;
 imagePoint=origin+camera.x*vec2(u,q*camera.y-position.z*camera.z);
 cameraDepth=q*camera.z+position.z*camera.y;
 vec2 screen=view.xy+(imagePoint+vec2(0.,imageOffsetY))*view.z;
 gl_Position=vec4(screen.x/viewport.x*2.-1.,1.-screen.y/viewport.y*2.,-cameraDepth/clipDepth,1.);
 vec3 normal=vec3(rotateENU(localNormal.xy),localNormal.z);
 float shade=emission>.5 ? 1. : .64+.36*max(0.,dot(vec3(-.37,-.22,.9),normal));
 color=vec4(paint.rgb*shade,paint.a);lit=emission;
}`;
const fragment = `#version 300 es
precision highp float;
in vec2 imagePoint;
in float cameraDepth;
in vec4 color;
in float lit;
uniform sampler2D sourceDepth;
uniform vec2 imageSize;
uniform vec2 depthEncoding;
uniform float depthSlope;
uniform float sourceRows;
uniform float night;
uniform float time;
out vec4 pixel;
void main(){
 vec2 uv=imagePoint/imageSize;
 if(any(lessThan(uv,vec2(0.)))||any(greaterThan(uv,vec2(1.))))discard;
 vec2 packed=texture(sourceDepth,uv).rg;
 float structure=(packed.r*65280.+packed.g*255.)/65535.*depthEncoding.y-depthEncoding.x;
 float rows=float(textureSize(sourceDepth,0).y);
 float row=min(rows-1.,floor(uv.y*rows));
 float sourceRow=floor((row+.5)*sourceRows/rows);
 float cell=(sourceRow+.5)*imageSize.y/sourceRows;
 structure+=(imagePoint.y-cell)*depthSlope;
 if(structure>cameraDepth+2.0)discard;
 vec3 paint=color.rgb*(1.-night*.48);
 if(lit>.5)paint=color.rgb;
 float alpha=color.a;
 if(lit>2.5)alpha*=night;
 else if(lit>1.5)alpha*=.45+.55*smoothstep(-.4,.7,sin(time*4.));
 pixel=vec4(paint,alpha);
}`;

function normalOf(face: VehicleFace) {
  const [a, b, c] = face.points;
  const u = b.map((value, i) => value - a[i]),
    v = c.map((value, i) => value - a[i]);
  const n = [
    u[1] * v[2] - u[2] * v[1],
    u[2] * v[0] - u[0] * v[2],
    u[0] * v[1] - u[1] * v[0],
  ];
  const length = Math.hypot(...n) || 1;
  return n.map(component => component / length);
}

function paintOf(face: VehicleFace, shade = 1) {
  const color = face.color.replace("#", "");
  return [0, 2, 4]
    .map((i) => (parseInt(color.slice(i, i + 2), 16) / 255) * shade)
    .concat(face.alpha ?? 1);
}

function rgba(face: VehicleFace) {
  if (face.emissive) return paintOf(face);
  const [e, n, z] = normalOf(face);
  return paintOf(face, 0.64 + 0.36 * Math.max(0, -0.37 * e - 0.22 * n + 0.9 * z));
}

type Mesh = {
  vao: WebGLVertexArrayObject | null;
  geometry: WebGLBuffer | null;
  instanceBuffer: WebGLBuffer | null;
  instances: number[];
  opaque: number;
  transparent: number;
};

/** Each hull/body/wing vertex shares the city's world-to-image camera. */
const floatsPerVertex = 13;
const floatsPerInstance = 6;
export class VehicleRenderer {
  canvas: HTMLCanvasElement;
  gl: WebGL2RenderingContext | null;
  fallback: CanvasRenderingContext2D | null = null;
  data: SceneData;
  sprites: SpriteRenderer;
  program: WebGLProgram | null = null;
  texture: WebGLTexture | null = null;
  meshes = new Map<string, Mesh>();
  activeMeshes: Mesh[] = [];
  uniforms: Record<string, WebGLUniformLocation | null> = {};
  ready: Promise<void>;
  disposed = false;
  lastCandidates: Pose[] = [];
  private lastScale = 1;
  opaqueCount = 0;
  transparentCount = 0;
  faces: (VehicleFace & { imageOffsetY?: number })[] = [];
  constructor(host: HTMLElement, data: SceneData, sprites: SpriteRenderer) {
    this.data = data;
    this.sprites = sprites;
    this.canvas = document.createElement("canvas");
    this.canvas.className = "vehicles";
    this.canvas.setAttribute("aria-hidden", "true");
    host.append(this.canvas);
    this.gl = this.canvas.getContext("webgl2", {
      alpha: true,
      premultipliedAlpha: true,
      antialias: true,
      depth: true,
    });
    const gl = this.gl;
    if (!gl) {
      this.fallback = this.canvas.getContext("2d");
      this.ready = sprites.ready;
      return;
    }
    const shader = (type: number, text: string) => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, text);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS))
        throw new Error(
          gl.getShaderInfoLog(s) ?? "Vehicle shader compilation failed",
        );
      return s;
    };
    const vs = shader(gl.VERTEX_SHADER, vertex),
      fs = shader(gl.FRAGMENT_SHADER, fragment),
      program = gl.createProgram()!;
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS))
      throw new Error(
        gl.getProgramInfoLog(program) ?? "Vehicle shader link failed",
      );
    this.program = program;
    gl.useProgram(program);
    for (const name of [
      "view",
      "viewport",
      "basis",
      "camera",
      "origin",
      "clipDepth",
      "depthEncoding",
      "depthSlope",
      "sourceRows",
      "sourceDepth",
      "imageSize",
      "modelScale",
      "night",
      "time",
    ])
      this.uniforms[name] = gl.getUniformLocation(program, name);
    this.ready = sprites.ready.then(() => {
      if (this.disposed) return;
      gl.useProgram(program);
      this.texture = gl.createTexture();
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, this.texture);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      const depth = sprites.depthTexture(gl);
      gl.texImage2D(
        gl.TEXTURE_2D,
        0,
        gl.RGBA,
        depth.width,
        depth.height,
        0,
        gl.RGBA,
        gl.UNSIGNED_BYTE,
        depth.pixels,
      );
      gl.uniform1i(this.uniforms.sourceDepth, 0);
      gl.uniform1f(this.uniforms.sourceRows, sprites.maskHeight);
    });
  }
  imageOffsetY(pose: Pose) {
    if (this.data.maskBundle !== "map/illustrated-bay/masks.png") return 0;
    const direction = pose.id.startsWith("bay-bridge-westbound-") ? "westbound"
      : pose.id.startsWith("bay-bridge-eastbound-") ? "eastbound" : undefined;
    if (!direction) return 0;
    const projection = this.data.projection;
    const x = project(pose.point, projection).x - projection.origin[0];
    // Shift the painted position while keeping the registered source-depth sample.
    return interpolateImageOffset(bridgeOffsets[direction], x);
  }
  private meshFor(pose: Pose, gl: WebGL2RenderingContext) {
    const key = pose.kind === "car" ? `${carStyle(pose.id)}/${pose.color}` : pose.kind;
    const cached = this.meshes.get(key);
    if (cached) return cached;
    // Bake the same faces used by Canvas once, in the vehicle's local axes.
    const faces = vehicleFaces({ ...pose, point: [0, 0, 0], direction: [1, 0, 0] });
    const opaque: number[] = [], transparent: number[] = [];
    for (const face of faces) {
      const target = (face.alpha ?? 1) < 1 || face.nightOnly ? transparent : opaque;
      const normal = normalOf(face), paint = paintOf(face);
      const flag = face.nightOnly ? 3 : face.pulse ? 2 : face.emissive ? 1 : 0;
      const [dx, dy] = face.worldShift ?? [0, 0];
      for (let i = 1; i < face.points.length - 1; i++) {
        for (const [e, n, z] of [face.points[0], face.points[i], face.points[i + 1]]) {
          target.push(e - dx, n - dy, z, ...normal, ...paint, flag, dx, dy);
        }
      }
    }
    const mesh: Mesh = {
      vao: gl.createVertexArray(),
      geometry: gl.createBuffer(),
      instanceBuffer: gl.createBuffer(),
      instances: [],
      opaque: opaque.length / floatsPerVertex,
      transparent: transparent.length / floatsPerVertex,
    };
    gl.bindVertexArray(mesh.vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, mesh.geometry);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([...opaque, ...transparent]), gl.STATIC_DRAW);
    for (const [name, size, offset] of [
      ["localPosition", 3, 0], ["localNormal", 3, 3], ["paint", 4, 6],
      ["emission", 1, 10], ["worldShift", 2, 11],
    ] as const) {
      const location = gl.getAttribLocation(this.program!, name);
      gl.enableVertexAttribArray(location);
      gl.vertexAttribPointer(location, size, gl.FLOAT, false, floatsPerVertex * 4, offset * 4);
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, mesh.instanceBuffer);
    for (const [name, size, offset] of [
      ["anchor", 3, 0], ["heading", 2, 3], ["imageOffsetY", 1, 5],
    ] as const) {
      const location = gl.getAttribLocation(this.program!, name);
      gl.enableVertexAttribArray(location);
      gl.vertexAttribPointer(location, size, gl.FLOAT, false, floatsPerInstance * 4, offset * 4);
      gl.vertexAttribDivisor(location, 1);
    }
    this.meshes.set(key, mesh);
    return mesh;
  }
  private updateInstances(candidates: Pose[], gl: WebGL2RenderingContext) {
    for (const mesh of this.activeMeshes) mesh.instances.length = 0;
    this.activeMeshes.length = 0;
    for (const pose of candidates) {
      const mesh = this.meshFor(pose, gl);
      if (!mesh.instances.length) this.activeMeshes.push(mesh);
      mesh.instances.push(...pose.point, ...heading(pose.direction), this.imageOffsetY(pose));
    }
    this.opaqueCount = this.transparentCount = 0;
    for (const mesh of this.activeMeshes) {
      gl.bindBuffer(gl.ARRAY_BUFFER, mesh.instanceBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(mesh.instances), gl.DYNAMIC_DRAW);
      const count = mesh.instances.length / floatsPerInstance;
      this.opaqueCount += mesh.opaque * count;
      this.transparentCount += mesh.transparent * count;
    }
  }
  draw(frame: Frame, v: ViewTransform) {
    const pixelsPerMetre = this.data.projection.scale * v.scale;
    const scale = transportMagnification(this.data.transportScale ?? 1, pixelsPerMetre, this.data.adaptiveTransport);
    const unit = pixelsPerMetre * scale;
    const candidates = frame.poses.filter((pose) => {
      if (pose.kind === "car" && unit * 5.6 < 0.75) return false;
      const p = project(pose.point, this.data.projection),
        x = p.x * v.scale + v.left,
        y = p.y * v.scale + v.top,
        margin = 85 + 40 * unit;
      return (
        x >= -margin &&
        x <= v.width + margin &&
        y >= -margin &&
        y <= v.height + margin
      );
    });
    if ((!this.gl && this.lastScale !== scale) || candidates.length !== this.lastCandidates.length ||
        candidates.some((pose, i) => pose !== this.lastCandidates[i])) {
      this.lastCandidates = candidates;
      this.lastScale = scale;
      if (this.gl) this.updateInstances(candidates, this.gl);
      else this.faces = candidates.flatMap((pose) => {
        const faces = vehicleFaces(pose);
        const imageOffsetY = this.imageOffsetY(pose);
        if (scale === 1 && imageOffsetY === 0) return faces;
        return faces.map((face) => ({
          ...face,
          imageOffsetY,
          points: scale === 1 ? face.points : face.points.map(
            (p) =>
              p.map(
                (v, i) => pose.point[i] + (v - pose.point[i]) * scale,
              ) as typeof pose.point,
          ),
        }));
      });
    }
    if (
      this.canvas.width !== Math.round(v.width * v.dpr) ||
      this.canvas.height !== Math.round(v.height * v.dpr)
    ) {
      this.canvas.width = Math.round(v.width * v.dpr);
      this.canvas.height = Math.round(v.height * v.dpr);
    }
    const night = nightAmount(frame.clock.hour),
      gl = this.gl;
    if (!gl) {
      const ctx = this.fallback;
      if (!ctx) return;
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
      const sorted = this.faces
        .slice()
        .sort(
          (a, b) =>
            a.points.reduce(
              (s, p) => s + project(p, this.data.projection).depth,
              0,
            ) /
              a.points.length -
            b.points.reduce(
              (s, p) => s + project(p, this.data.projection).depth,
              0,
            ) /
              b.points.length,
        );
      for (const face of sorted) {
        if (face.nightOnly && night < 0.01) continue;
        const centre = face.points.reduce(
          (a, p) =>
            a.map((v, i) => v + p[i] / face.points.length) as [
              number,
              number,
              number,
            ],
          [0, 0, 0],
        );
        if (!this.sprites.isVisible(centre)) continue;
        const color = rgba(face);
        ctx.fillStyle = `rgb(${color
          .slice(0, 3)
          .map((c) =>
            Math.round(c * 255 * (face.emissive ? 1 : 1 - night * 0.48)),
          )
          .join(",")})`;
        ctx.globalAlpha = color[3] * (face.nightOnly ? night : 1);
        ctx.beginPath();
        face.points.forEach((p, i) => {
          const q = project(p, this.data.projection);
          const x = q.x * v.scale + v.left;
          const y = (q.y + (face.imageOffsetY ?? 0)) * v.scale + v.top;
          if (i) ctx.lineTo(x, y);
          else ctx.moveTo(x, y);
        });
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();
      return;
    }
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.depthMask(true);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.disable(gl.CULL_FACE);
    gl.useProgram(this.program);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.texture);
    const p = this.data.projection,
      u = this.uniforms;
    gl.uniform4f(u.view, v.left, v.top, v.scale, 0);
    gl.uniform2f(u.viewport, v.width, v.height);
    gl.uniform4f(u.basis, p.east[0], p.east[1], p.north[0], p.north[1]);
    gl.uniform3f(u.camera, p.scale, p.sinElevation, p.cosElevation);
    gl.uniform2f(u.origin, p.origin[0], p.origin[1]);
    gl.uniform1f(u.clipDepth, this.data.clipDepth ?? 2048);
    const depth = this.data.depthEncoding ?? legacyDepthEncoding;
    gl.uniform2f(u.depthEncoding, depth.offset, depth.range);
    gl.uniform1f(u.depthSlope, this.data.maskBundle ? p.cosElevation / (p.scale * p.sinElevation) : 0);
    gl.uniform2f(u.imageSize, this.data.width, this.data.height);
    gl.uniform1f(u.night, night);
    gl.uniform1f(u.time, frame.clock.transportTime);
    gl.uniform1f(u.modelScale, scale);
    gl.disable(gl.BLEND);
    for (const mesh of this.activeMeshes) {
      gl.bindVertexArray(mesh.vao);
      gl.drawArraysInstanced(gl.TRIANGLES, 0, mesh.opaque, mesh.instances.length / floatsPerInstance);
    }
    gl.enable(gl.BLEND);
    gl.blendFuncSeparate(
      gl.SRC_ALPHA,
      gl.ONE_MINUS_SRC_ALPHA,
      gl.ONE,
      gl.ONE_MINUS_SRC_ALPHA,
    );
    gl.depthMask(false);
    for (const mesh of this.activeMeshes) {
      gl.bindVertexArray(mesh.vao);
      gl.drawArraysInstanced(gl.TRIANGLES, mesh.opaque, mesh.transparent, mesh.instances.length / floatsPerInstance);
    }
    gl.depthMask(true);
  }
  destroy() {
    this.disposed = true;
    const gl = this.gl;
    if (gl) {
      for (const mesh of this.meshes.values()) {
        gl.deleteBuffer(mesh.geometry);
        gl.deleteBuffer(mesh.instanceBuffer);
        gl.deleteVertexArray(mesh.vao);
      }
      gl.deleteTexture(this.texture);
      gl.deleteProgram(this.program);
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    }
    this.canvas.remove();
  }
}
