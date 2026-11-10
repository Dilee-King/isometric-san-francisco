import OpenSeadragon from "openseadragon";
import { Atmosphere } from "./Atmosphere.ts";
import { SpriteRenderer } from "./SpriteRenderer.ts";
import { defaultControls, nightAmount, project } from "./model.ts";
import type { Frame, Controls, SceneData } from "./types.ts";
import type { ViewTransform } from "./SpriteRenderer.ts";

export class MapView {
  host: HTMLElement;
  data: SceneData;
  viewer: OpenSeadragon.Viewer;
  sprites: SpriteRenderer;
  atmosphere: Atmosphere;
  worker: Worker;
  frame: Frame;
  sequence = 0;
  raf = 0;
  lastUI = 0;
  ready = false;
  labels = false;
  disposed = false;
  nightLayer: OpenSeadragon.TiledImage | null = null;
  transform: ViewTransform = {
    left: 0,
    top: 0,
    scale: 1,
    width: 1,
    height: 1,
    dpr: 1,
  };
  onFrame: (frame: Frame) => void;
  constructor(
    host: HTMLElement,
    data: SceneData,
    onFrame: (frame: Frame) => void,
    onReady: () => void,
    onError: (message: string) => void,
  ) {
    this.host = host;
    this.data = data;
    this.onFrame = onFrame;
    const paused = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    this.frame = {
      clock: { transportTime: 0, environmentTime: 0, hour: 14.25 },
      controls: { ...defaultControls, paused },
      poses: [],
      sequence: 0,
    };
    const base = document.createElement("div");
    base.className = "base-map";
    host.append(base);
    this.viewer = OpenSeadragon({
      element: base,
      tileSources: `${import.meta.env.BASE_URL}map/v1/scene.dzi`,
      homeFillsViewer: true,
      showNavigationControl: false,
      showNavigator: false,
      showFullPageControl: false,
      showHomeControl: false,
      showSequenceControl: false,
      animationTime: 0.32,
      blendTime: 0.1,
      visibilityRatio: 1,
      constrainDuringPan: true,
      minZoomImageRatio: 0.85,
      maxZoomPixelRatio: 3,
      gestureSettingsMouse: { clickToZoom: false, dblClickToZoom: true },
      gestureSettingsTouch: { pinchToZoom: true },
      imageLoaderLimit: 6,
    });
    this.sprites = new SpriteRenderer(host, data);
    this.atmosphere = new Atmosphere(host, data);
    this.worker = new Worker(
      new URL("./simulation.worker.ts", import.meta.url),
      { type: "module" },
    );
    this.worker.onmessage = (event: MessageEvent<Frame>) => {
      if (event.data.sequence < this.sequence) return;
      this.frame = event.data;
      const now = performance.now();
      if (now - this.lastUI > 100 || this.frame.controls.paused) {
        this.onFrame(this.frame);
        this.lastUI = now;
      }
    };
    this.worker.onerror = () => onError("交通动画未能启动，请刷新后重试。");
    this.viewer.addHandler("open-failed", () =>
      onError("地图图块未能载入，请检查本地服务。"),
    );
    this.viewer.addHandler("open", () => {
      this.viewer.addTiledImage({
        tileSource: `${import.meta.env.BASE_URL}map/v1/night.dzi`,
        x: 0,
        y: 0,
        width: 1,
        opacity: 0.001,
        success: (event) => {
          this.nightLayer = (
            event as unknown as { item: OpenSeadragon.TiledImage }
          ).item;
        },
      });
      Promise.all([this.sprites.ready, this.atmosphere.ready])
        .then(() => {
          if (this.disposed) return;
          this.ready = true;
          onReady();
          this.tick();
        })
        .catch(() => onError("场景图层未能载入，请刷新后重试。"));
    });
    host.tabIndex = 0;
    host.setAttribute(
      "aria-label",
      "旧金山连续地图；拖动平移，滚轮缩放，空格暂停，Home 全景",
    );
    host.addEventListener("keydown", this.keydown);
    document.addEventListener("visibilitychange", this.visibility);
    this.visibility();
    this.setControls({ paused });
  }
  visibility = () => this.worker.postMessage({ hidden: document.hidden });
  setControls(partial: Partial<Controls>, hour?: number) {
    this.sequence++;
    this.frame = {
      ...this.frame,
      controls: { ...this.frame.controls, ...partial },
      clock: { ...this.frame.clock, ...(hour === undefined ? {} : { hour }) },
    };
    this.worker.postMessage({
      controls: partial,
      hour,
      sequence: this.sequence,
      ...(this.sequence === 1 ? { routes: this.data.routes } : {}),
    });
    this.onFrame(this.frame);
  }
  setHour(hour: number) {
    this.setControls({ autoHour: false }, hour);
  }
  zoom(factor: number) {
    this.viewer.viewport.zoomBy(factor);
    this.viewer.viewport.applyConstraints();
  }
  home() {
    this.viewer.viewport.goHome();
  }
  keydown = (e: KeyboardEvent) => {
    if (e.key === " ") {
      e.preventDefault();
      this.setControls({ paused: !this.frame.controls.paused });
    } else if (e.key === "Home") {
      e.preventDefault();
      this.home();
    } else if (e.key === "+" || e.key === "=") {
      e.preventDefault();
      this.zoom(1.3);
    } else if (e.key === "-") {
      e.preventDefault();
      this.zoom(1 / 1.3);
    }
  };
  tick = () => {
    if (this.disposed) return;
    const item = this.viewer.world.getItemAt(0);
    if (item) {
      const origin = item.imageToViewerElementCoordinates(
        new OpenSeadragon.Point(0, 0),
      );
      const px = item.imageToViewerElementCoordinates(
        new OpenSeadragon.Point(1, 0),
      );
      this.transform = {
        left: origin.x,
        top: origin.y,
        scale: px.x - origin.x,
        width: this.host.clientWidth,
        height: this.host.clientHeight,
        dpr: Math.min(1.5, window.devicePixelRatio),
      };
      const night = nightAmount(this.frame.clock.hour),
        dusk = Math.max(0, 1 - Math.abs(this.frame.clock.hour - 18.5) / 2.5);
      const base = this.host.querySelector<HTMLElement>(".base-map")!;
      this.nightLayer?.setOpacity(night);
      base.style.filter = `sepia(${dusk * 0.12}) saturate(${1 + dusk * 0.08})`;
      this.sprites.draw(this.frame, this.transform, this.labels);
      this.atmosphere.draw(this.frame, this.transform);
    }
    this.raf = requestAnimationFrame(this.tick);
  };
  snapshot() {
    const landmark = this.data.landmarks.map((l) => {
      const p = project(l.p, this.data.projection);
      return {
        name: l.name,
        image: [p.x, p.y],
        screen: [
          p.x * this.transform.scale + this.transform.left,
          p.y * this.transform.scale + this.transform.top,
        ],
      };
    });
    return {
      ready: this.ready,
      frame: this.frame,
      visible: { ...this.sprites.visible },
      transform: { ...this.transform },
      landmarks: landmark,
      webgl2: !!this.atmosphere.gl,
    };
  }
  destroy() {
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    this.worker.terminate();
    this.viewer.destroy();
    this.sprites.destroy();
    this.atmosphere.destroy();
    this.host.removeEventListener("keydown", this.keydown);
    document.removeEventListener("visibilitychange", this.visibility);
  }
}
