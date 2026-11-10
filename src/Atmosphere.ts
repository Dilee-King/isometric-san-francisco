import { nightAmount } from "./model.ts";
import { MAP_ROOT } from "./assets.ts";
import type { Frame, SceneData } from "./types.ts";
import type { ViewTransform } from "./SpriteRenderer.ts";

const fragment = `#version 300 es
precision highp float;
in vec2 uv;
out vec4 fragColor;
uniform vec2 resolution;
uniform vec4 rect;
uniform vec2 imageSize;
uniform vec3 camera;
uniform vec2 cameraOrigin;
uniform float time;
uniform float night;
uniform float intensity;
uniform int weather;
uniform sampler2D waterTex;
uniform sampler2D depthTex;
uniform sampler2D hardTex;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1.,0.)),f.x),mix(hash(i+vec2(0.,1.)),hash(i+vec2(1.,1.)),f.x),f.y);}
void main(){
 vec2 screen=vec2(uv.x,1.-uv.y)*resolution;
 vec2 p=(screen-rect.xy)/rect.zw;
 if(any(lessThan(p,vec2(0.)))||any(greaterThan(p,vec2(1.)))){fragColor=vec4(0.);return;}
 float water=texture(waterTex,p).r;
 vec2 packed=texture(depthTex,p).rg;
 float depth=(packed.r*65280.+packed.g*255.)/65535.*4000.-2000.;
 float y=(p.y*imageSize.y-cameraOrigin.y)/camera.x;
 float height=clamp(depth*camera.y-y*camera.z,0.,250.);
 float swell=sin(p.x*620.+p.y*340.+time*.9)*sin(p.y*690.-time*.7);
 float sparkle=smoothstep(.90,1.,swell)*water;
 vec3 color=mix(vec3(.70,.85,.83),vec3(.35,.59,.65),night);
 float alpha=sparkle*(.045+night*.02);
 if(weather==1){
   float a=noise(p*4.+vec2(-time*.012,time*.006));
   float b=noise(p*11.+vec2(-time*.018,0.));
   float bank=smoothstep(.05,.85,p.x*.7+a*.55);
   float altitude=1.-clamp(height/260.,0.,.7);
   float fog=intensity*(.15+.75*bank)*(.58+.42*b)*altitude;
   color=mix(vec3(.73,.80,.79),vec3(.20,.29,.35),night);alpha=max(alpha,fog);
 }
 if(weather==2){
   vec2 world=p*imageSize;
   float drops=0.;
   for(int layer=0;layer<3;layer++){
     float k=float(layer),rate=180.+k*95.;
     vec2 rain=vec2((world.x-world.y*.12+k*31.)/(10.+k*4.),(world.y-time*rate)/(39.+k*16.));
     vec2 cell=floor(rain);vec2 f=fract(rain);
     float phase=hash(vec2(cell.x,k+8.));
     float streak=(1.-smoothstep(.018,.064,abs(f.x-phase)))*smoothstep(.08,.25,f.y)*(1.-smoothstep(.5,.85,f.y));
     drops+=streak*step(.65-intensity*.35,hash(cell+vec2(k*49.,13.)))*(.55-k*.12);
   }
   vec2 impactCell=floor(world/13.);vec2 impact=fract(world/13.);
   float seed=hash(impactCell),age=fract(time*(1.2+seed)+seed*9.);
   float radial=length((impact-vec2(.2+seed*.6,.25+hash(impactCell+8.)*.5))*vec2(1.,1.65));
   float ring=(1.-smoothstep(.015,.05,abs(radial-age*.47)))*(1.-age)*step(.35,seed);
   float hard=texture(hardTex,p).r;
   float surface=max(water,hard*.55);
   float impactAlpha=ring*surface*intensity*.17;
   float veil=intensity*(.035+.07*noise(p*5.+vec2(time*.01,0.)));
   vec3 rainColor=mix(vec3(.58,.69,.72),vec3(.23,.34,.43),night);
   float rainAlpha=veil+clamp(drops,0.,1.)*(.22+intensity*.2)+impactAlpha;
   color=mix(rainColor,vec3(.74,.84,.85),min(1.,drops+ring*surface));alpha=max(alpha,rainAlpha);
 }
 fragColor=vec4(color,clamp(alpha,0.,.84));
}`;

export class Atmosphere {
  canvas: HTMLCanvasElement;
  gl: WebGL2RenderingContext | null;
  program: WebGLProgram | null = null;
  uniforms: Record<string, WebGLUniformLocation | null> = {};
  data: SceneData;
  ready: Promise<void>;
  constructor(host: HTMLElement, data: SceneData) {
    this.data = data;
    this.canvas = document.createElement("canvas");
    this.canvas.className = "atmosphere";
    this.canvas.setAttribute("aria-hidden", "true");
    host.append(this.canvas);
    this.gl = this.canvas.getContext("webgl2", {
      alpha: true,
      premultipliedAlpha: false,
      antialias: false,
    });
    const gl = this.gl;
    if (!gl) {
      this.ready = Promise.resolve();
      return;
    }
    const shader = (type: number, source: string) => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, source);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS))
        throw new Error(gl.getShaderInfoLog(s) ?? "Shader failed");
      return s;
    };
    const p = gl.createProgram()!;
    gl.attachShader(
      p,
      shader(
        gl.VERTEX_SHADER,
        `#version 300 es\nout vec2 uv;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=p;gl_Position=vec4(p*2.-1.,0.,1.);}`,
      ),
    );
    gl.attachShader(p, shader(gl.FRAGMENT_SHADER, fragment));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS))
      throw new Error(gl.getProgramInfoLog(p) ?? "GL link failed");
    this.program = p;
    gl.useProgram(p);
    for (const name of [
      "resolution",
      "rect",
      "imageSize",
      "camera",
      "cameraOrigin",
      "time",
      "night",
      "intensity",
      "weather",
      "waterTex",
      "depthTex",
      "hardTex",
    ])
      this.uniforms[name] = gl.getUniformLocation(p, name);
    this.ready = Promise.all(
      ["water", "depth", "hard"].map(async (name, index) => {
        const image = new Image();
        image.src = `${MAP_ROOT}${name}.png`;
        await image.decode();
        const tex = gl.createTexture();
        gl.activeTexture(gl.TEXTURE0 + index);
        gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        gl.texImage2D(
          gl.TEXTURE_2D,
          0,
          gl.RGB,
          gl.RGB,
          gl.UNSIGNED_BYTE,
          image,
        );
        gl.uniform1i(this.uniforms[`${name}Tex`], index);
      }),
    ).then(() => {});
  }
  draw(frame: Frame, v: ViewTransform) {
    const gl = this.gl;
    if (!gl || !this.program) return;
    if (
      this.canvas.width !== Math.round(v.width * v.dpr) ||
      this.canvas.height !== Math.round(v.height * v.dpr)
    ) {
      this.canvas.width = Math.round(v.width * v.dpr);
      this.canvas.height = Math.round(v.height * v.dpr);
    }
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.useProgram(this.program);
    const u = this.uniforms,
      p = this.data.projection;
    gl.uniform2f(u.resolution, v.width, v.height);
    gl.uniform4f(
      u.rect,
      v.left,
      v.top,
      this.data.width * v.scale,
      this.data.height * v.scale,
    );
    gl.uniform2f(u.imageSize, this.data.width, this.data.height);
    gl.uniform3f(u.camera, p.scale, p.sinElevation, p.cosElevation);
    gl.uniform2f(u.cameraOrigin, p.origin[0], p.origin[1]);
    gl.uniform1f(u.time, frame.clock.environmentTime);
    gl.uniform1f(u.night, nightAmount(frame.clock.hour));
    gl.uniform1f(u.intensity, frame.controls.intensity);
    gl.uniform1i(
      u.weather,
      ["clear", "fog", "rain"].indexOf(frame.controls.weather),
    );
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  destroy() {
    this.gl?.getExtension("WEBGL_lose_context")?.loseContext();
    this.canvas.remove();
  }
}
