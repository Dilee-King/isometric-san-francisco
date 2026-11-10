import OpenSeadragon from "openseadragon";
import { Atmosphere } from "./Atmosphere.ts";
import { SpriteRenderer } from "./SpriteRenderer.ts";
import { VehicleRenderer } from "./VehicleRenderer.ts";
import { sceneRoot } from "./assets.ts";
import { sceneTransfer } from "./atlas.ts";
import { defaultControls, nightAmount, project } from "./model.ts";
import type { Frame, Controls, SceneData } from "./types.ts";
import type { ViewTransform } from "./SpriteRenderer.ts";

export class MapView {
  host: HTMLElement;
  base: HTMLDivElement;
  data: SceneData;
  viewer: OpenSeadragon.Viewer;
  sprites: SpriteRenderer;
  vehicles: VehicleRenderer;
  atmosphere: Atmosphere;
  worker: Worker;
  frame: Frame;
  sequence = 0;
  raf = 0;
  lastUI = 0;
  ready = false;
  labels = false;
  location?: string;
  disposed = false;
  nightLayer: OpenSeadragon.TiledImage | null = null;
  rainDayLayer: OpenSeadragon.TiledImage | null = null;
  rainNightLayer: OpenSeadragon.TiledImage | null = null;
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
    savedFrame?: Frame,
    startLocation?: string,
  ) {
    this.host = host;
    this.data = data;
    this.onFrame = onFrame;
    const paused = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    this.frame = savedFrame
      ? sceneTransfer(savedFrame)
      : {
          clock: { transportTime: 0, environmentTime: 0, hour: 14.25 },
          controls: { ...defaultControls, paused },
          poses: [],
          sequence: 0,
        };
    this.base = document.createElement("div");
    this.base.className = "base-map";
    host.append(this.base);
    this.viewer = OpenSeadragon({
      element: this.base,
      tileSources: `${sceneRoot(data)}scene.dzi`,
      homeFillsViewer: data.kind !== "waterfront",
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
      maxImageCacheCount: 180,
    });
    this.sprites = new SpriteRenderer(host, data);
    this.vehicles = new VehicleRenderer(host, data, this.sprites);
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
    this.worker.onerror = () =>
      onError("Traffic could not start. Please reload the map.");
    this.viewer.addHandler("open-failed", () =>
      onError(
        "Map tiles could not load. Please check the connection and reload.",
      ),
    );
    this.viewer.addHandler("open", () => {
      const addLayer = (name: string) =>
        new Promise<OpenSeadragon.TiledImage>((resolve, reject) =>
          this.viewer.addTiledImage({
            tileSource: `${sceneRoot(data)}${name}.dzi`,
            x: 0,
            y: 0,
            width: 1,
            opacity: 0,
            preload: false,
            success: (event) =>
              resolve(
                (event as unknown as { item: OpenSeadragon.TiledImage }).item,
              ),
            error: () => reject(new Error("Appearance layer could not load")),
          }),
        );
      const appearances = (async () => {
        this.nightLayer = await addLayer("night");
        if (this.disposed) return;
        this.rainDayLayer = await addLayer("rain-day");
        if (this.disposed) return;
        this.rainNightLayer = await addLayer("rain-night");
      })();
      Promise.all([
        this.sprites.ready,
        this.vehicles.ready,
        this.atmosphere.ready,
        appearances,
      ])
        .then(() => {
          if (this.disposed) return;
          this.focusLocation(startLocation ?? data.defaultLocation, true);
          this.ready = true;
          onReady();
          this.tick();
        })
        .catch(() =>
          onError("Scene layers could not load. Please reload the map."),
        );
    });
    host.tabIndex = 0;
    host.setAttribute(
      "aria-label",
      `${data.kind === "bay" ? "Bay Area overview" : "San Francisco waterfront"}. Drag to pan, scroll to zoom, Space to pause, Home to reset.`,
    );
    host.addEventListener("keydown", this.keydown);
    document.addEventListener("visibilitychange", this.visibility);
    this.worker.postMessage({
      clock: this.frame.clock,
      controls: this.frame.controls,
      hidden: document.hidden,
      routes: data.routes,
      sequence: ++this.sequence,
    });
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
    if (!this.focusLocation(this.data.defaultLocation))
      this.viewer.viewport.goHome();
  }
  focusLocation(id?: string, immediate = false) {
    const landmark = this.data.landmarks.find((l) => l.id === id);
    if (!id || !landmark || !this.viewer.viewport) return false;
    const p = project(landmark.p, this.data.projection),
      w = this.data.width,
      h = 1080 / w,
      span = (h * this.host.clientWidth) / Math.max(1, this.host.clientHeight);
    this.viewer.viewport.fitBoundsWithConstraints(
      new OpenSeadragon.Rect(p.x / w - span / 2, p.y / w - h / 2, span, h),
      immediate,
    );
    this.location = id;
    return true;
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
      this.nightLayer?.setOpacity(night);
      const wet = this.frame.controls.weather === "rain" ? 1 : 0;
      this.rainDayLayer?.setOpacity(wet);
      this.rainNightLayer?.setOpacity(wet * night);
      this.base.style.filter = `sepia(${dusk * 0.12}) saturate(${1 + dusk * 0.08})`;
      this.sprites.draw(this.frame, this.transform, this.labels);
      this.vehicles.draw(this.frame, this.transform);
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
      release: this.data.release,
      scene: this.data.kind,
      location: this.location,
      maskSize: [this.sprites.maskWidth, this.sprites.maskHeight],
      vehicleVertices:
        this.vehicles.opaqueCount + this.vehicles.transparentCount,
      frame: this.frame,
      visible: { ...this.sprites.visible },
      transform: { ...this.transform },
      landmarks: landmark,
      webgl2: !!this.atmosphere.gl,
      vehicleRenderer: this.vehicles.gl
        ? "webgl2-world-mesh"
        : "canvas-world-mesh",
    };
  }
  destroy() {
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    this.worker.terminate();
    this.viewer.destroy();
    this.base.remove();
    this.sprites.destroy();
    this.vehicles.destroy();
    this.atmosphere.destroy();
    this.host.removeEventListener("keydown", this.keydown);
    document.removeEventListener("visibilitychange", this.visibility);
  }
}
