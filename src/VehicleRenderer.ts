import { vehicleFaces } from "./VehicleGeometry.ts";
import { legacyDepthEncoding } from "./atlas.ts";
import type { VehicleFace } from "./VehicleGeometry.ts";
import { nightAmount, project } from "./model.ts";
import type { Frame, SceneData } from "./types.ts";
import type { SpriteRenderer, ViewTransform } from "./SpriteRenderer.ts";

const vertex = `#version 300 es
precision highp float;
in vec3 position;
in vec4 paint;
in float emission;
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
void main(){
 float u=position.x*basis.x+position.y*basis.z;
 float q=position.x*basis.y+position.y*basis.w;
 imagePoint=origin+camera.x*vec2(u,q*camera.y-position.z*camera.z);
 cameraDepth=q*camera.z+position.z*camera.y;
 vec2 screen=view.xy+imagePoint*view.z;
 gl_Position=vec4(screen.x/viewport.x*2.-1.,1.-screen.y/viewport.y*2.,-cameraDepth/clipDepth,1.);
 color=paint;lit=emission;
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
uniform float night;
uniform float time;
out vec4 pixel;
void main(){
 vec2 uv=imagePoint/imageSize;
 if(any(lessThan(uv,vec2(0.)))||any(greaterThan(uv,vec2(1.))))discard;
 vec2 packed=texture(sourceDepth,uv).rg;
 float structure=(packed.r*65280.+packed.g*255.)/65535.*depthEncoding.y-depthEncoding.x;
 float rows=float(textureSize(sourceDepth,0).y);
 float cell=(floor(uv.y*rows)+.5)*imageSize.y/rows;
 structure+=(imagePoint.y-cell)*depthSlope;
 if(structure>cameraDepth+2.0)discard;
 vec3 paint=color.rgb*(1.-night*.48);
 if(lit>.5)paint=color.rgb;
 float alpha=color.a;
 if(lit>2.5)alpha*=night;
 else if(lit>1.5)alpha*=.45+.55*smoothstep(-.4,.7,sin(time*4.));
 pixel=vec4(paint,alpha);
}`;

function rgba(face: VehicleFace): number[] {
  const color = face.color.replace("#", "");
  let shade = 1;
  if (!face.emissive) {
    const [a, b, c] = face.points,
      u = b.map((v, i) => v - a[i]),
      v = c.map((value, i) => value - a[i]);
    const n = [
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
      ],
      length = Math.hypot(...n) || 1;
    shade =
      0.64 +
      0.36 * Math.max(0, (-0.37 * n[0] - 0.22 * n[1] + 0.9 * n[2]) / length);
  }
  return [0, 2, 4]
    .map((i) => (parseInt(color.slice(i, i + 2), 16) / 255) * shade)
    .concat(face.alpha ?? 1);
}

/** Each hull/body/wing vertex shares the city's world-to-image camera. */
export class VehicleRenderer {
  canvas: HTMLCanvasElement;
  gl: WebGL2RenderingContext | null;
  fallback: CanvasRenderingContext2D | null = null;
  data: SceneData;
  sprites: SpriteRenderer;
  program: WebGLProgram | null = null;
  buffer: WebGLBuffer | null = null;
  texture: WebGLTexture | null = null;
  vao: WebGLVertexArrayObject | null = null;
  uniforms: Record<string, WebGLUniformLocation | null> = {};
  ready: Promise<void>;
  disposed = false;
  lastKey = "";
  opaqueCount = 0;
  transparentCount = 0;
  faces: VehicleFace[] = [];
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
    this.vao = gl.createVertexArray();
    gl.bindVertexArray(this.vao);
    this.buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
    for (const [name, size, offset] of [
      ["position", 3, 0],
      ["paint", 4, 12],
      ["emission", 1, 28],
    ] as const) {
      const location = gl.getAttribLocation(program, name);
      gl.enableVertexAttribArray(location);
      gl.vertexAttribPointer(location, size, gl.FLOAT, false, 32, offset);
    }
    for (const name of [
      "view",
      "viewport",
      "basis",
      "camera",
      "origin",
      "clipDepth",
      "depthEncoding",
      "depthSlope",
      "sourceDepth",
      "imageSize",
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
      gl.texImage2D(
        gl.TEXTURE_2D,
        0,
        gl.RGBA,
        sprites.maskWidth,
        sprites.maskHeight,
        0,
        gl.RGBA,
        gl.UNSIGNED_BYTE,
        new Uint8Array(sprites.depth!),
      );
      gl.uniform1i(this.uniforms.sourceDepth, 0);
    });
  }
  draw(frame: Frame, v: ViewTransform) {
    const candidates = frame.poses.filter((pose) => {
      const p = project(pose.point, this.data.projection),
        x = p.x * v.scale + v.left,
        y = p.y * v.scale + v.top,
        margin =
          85 +
          40 *
            this.data.projection.scale *
            v.scale *
            (this.data.transportScale ?? 1);
      return (
        x >= -margin &&
        x <= v.width + margin &&
        y >= -margin &&
        y <= v.height + margin
      );
    });
    const key = `${frame.clock.transportTime}/${candidates.map((p) => p.id).join(",")}`;
    if (key !== this.lastKey) {
      this.lastKey = key;
      const scale = this.data.transportScale ?? 1;
      this.faces = candidates.flatMap((pose) => {
        const faces = vehicleFaces(pose);
        if (scale === 1) return faces;
        return faces.map((face) => ({
          ...face,
          points: face.points.map(
            (p) =>
              p.map(
                (v, i) => pose.point[i] + (v - pose.point[i]) * scale,
              ) as typeof pose.point,
          ),
        }));
      });
      if (this.gl) {
        const opaque: number[] = [],
          transparent: number[] = [];
        for (const face of this.faces) {
          const target =
              (face.alpha ?? 1) < 1 || face.nightOnly ? transparent : opaque,
            color = rgba(face),
            flag = face.nightOnly ? 3 : face.pulse ? 2 : face.emissive ? 1 : 0;
          for (let i = 1; i < face.points.length - 1; i++)
            for (const point of [
              face.points[0],
              face.points[i],
              face.points[i + 1],
            ])
              target.push(...point, ...color, flag);
        }
        this.opaqueCount = opaque.length / 8;
        this.transparentCount = transparent.length / 8;
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.buffer);
        this.gl.bufferData(
          this.gl.ARRAY_BUFFER,
          new Float32Array([...opaque, ...transparent]),
          this.gl.DYNAMIC_DRAW,
        );
      }
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
          if (i) ctx.lineTo(q.x * v.scale + v.left, q.y * v.scale + v.top);
          else ctx.moveTo(q.x * v.scale + v.left, q.y * v.scale + v.top);
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
    gl.bindVertexArray(this.vao);
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
    gl.disable(gl.BLEND);
    gl.drawArrays(gl.TRIANGLES, 0, this.opaqueCount);
    gl.enable(gl.BLEND);
    gl.blendFuncSeparate(
      gl.SRC_ALPHA,
      gl.ONE_MINUS_SRC_ALPHA,
      gl.ONE,
      gl.ONE_MINUS_SRC_ALPHA,
    );
    gl.depthMask(false);
    gl.drawArrays(gl.TRIANGLES, this.opaqueCount, this.transparentCount);
    gl.depthMask(true);
  }
  destroy() {
    this.disposed = true;
    const gl = this.gl;
    if (gl) {
      gl.deleteBuffer(this.buffer);
      gl.deleteTexture(this.texture);
      gl.deleteVertexArray(this.vao);
      gl.deleteProgram(this.program);
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    }
    this.canvas.remove();
  }
}
