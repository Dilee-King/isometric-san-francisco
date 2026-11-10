import { useEffect, useRef, useState } from "react";
import { MapView } from "./MapView.ts";
import { defaultControls } from "./model.ts";
import type { Frame, SceneData, Weather } from "./types.ts";

function Icon({ name }: { name: string }) {
  const paths: Record<string, React.ReactNode> = {
    sun: (
      <>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" />
      </>
    ),
    cloud: (
      <path d="M6 18a4 4 0 0 1-.5-8 6 6 0 0 1 11.7-1A4.5 4.5 0 1 1 18 18Z" />
    ),
    fog: (
      <>
        <path d="M4 8h16M2 12h17M5 16h17M3 20h13" />
      </>
    ),
    rain: (
      <>
        <path d="M5 14a4 4 0 0 1 0-8 5.5 5.5 0 0 1 10.5-1A4.5 4.5 0 1 1 18 14" />
        <path d="m7 17-1 3m7-3-1 3m7-3-1 3" />
      </>
    ),
    car: (
      <>
        <path d="m5 9 2-5h10l2 5M4 9h16v9H4zM6 18v2m12-2v2M7 13h1m8 0h1" />
      </>
    ),
    boat: (
      <>
        <path d="m3 14 9-3 9 3-3 5H6zM6 13V6h12v7M12 6V3M2 22l3-1 4 1 3-1 4 1 3-1 3 1" />
      </>
    ),
    plane: <path d="m21 3-7 9 2 7-2 2-4-6-5 3-2-2 3-5-4-4 2-2 7 2 9-7z" />,
    pause: (
      <>
        <path d="M8 5v14M16 5v14" />
      </>
    ),
    play: <path d="m8 4 11 8-11 8Z" />,
    plus: <path d="M12 5v14M5 12h14" />,
    minus: <path d="M5 12h14" />,
    home: (
      <>
        <path d="m3 11 9-8 9 8M6 10v11h12V10M10 21v-7h4v7" />
      </>
    ),
    info: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v6m0-10v1" />
      </>
    ),
    settings: (
      <>
        <path d="M3 6h18M3 12h18M3 18h18" />
        <circle cx="8" cy="6" r="2" />
        <circle cx="16" cy="12" r="2" />
        <circle cx="10" cy="18" r="2" />
      </>
    ),
    close: <path d="m6 6 12 12M6 18 18 6" />,
    pin: (
      <>
        <path d="M18 9c0 5-6 12-6 12S6 14 6 9a6 6 0 1 1 12 0Z" />
        <circle cx="12" cy="9" r="2" />
      </>
    ),
  };
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name] ?? paths.sun}
    </svg>
  );
}
const weatherNames: Record<Weather, string> = {
  clear: "晴朗",
  cloudy: "多云",
  fog: "海雾",
  rain: "下雨",
};
const initial: Frame = {
  clock: { transportTime: 0, environmentTime: 0, hour: 14.25 },
  controls: { ...defaultControls },
  poses: [],
  sequence: 0,
};

export default function App() {
  const host = useRef<HTMLDivElement>(null),
    map = useRef<MapView | null>(null),
    aboutClose = useRef<HTMLButtonElement>(null);
  const [frame, setFrame] = useState(initial),
    [ready, setReady] = useState(false),
    [error, setError] = useState(""),
    [about, setAbout] = useState(false),
    [settings, setSettings] = useState(() => window.innerWidth > 680),
    [labels, setLabels] = useState(false);
  useEffect(() => {
    let stopped = false;
    fetch(`${import.meta.env.BASE_URL}map/v1/scene.json`)
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((data: SceneData) => {
        if (stopped || !host.current) return;
        map.current = new MapView(
          host.current,
          data,
          setFrame,
          () => setReady(true),
          setError,
        );
        (window as unknown as { __sf: MapView }).__sf = map.current;
      })
      .catch(() => setError("地图未能载入，请检查本地服务后刷新。"));
    return () => {
      stopped = true;
      map.current?.destroy();
    };
  }, []);
  useEffect(() => {
    if (!about) return;
    const previous = document.activeElement as HTMLElement | null;
    aboutClose.current?.focus();
    return () => previous?.focus();
  }, [about]);
  const controls = frame.controls,
    hour = frame.clock.hour,
    clockText = `${String(Math.floor(hour) % 24).padStart(2, "0")}:${String(Math.floor((hour % 1) * 60)).padStart(2, "0")}`;
  const toggle = (key: "cars" | "boats" | "planes") =>
    map.current?.setControls({ [key]: !controls[key] });
  return (
    <main className={`app ${settings ? "settings-open" : ""}`}>
      <div ref={host} className="map-stage" />
      <header className="identity panel">
        <div className="identity-mark" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div>
          <p className="eyebrow">ISOMETRIC / LIVING WATERFRONT</p>
          <h1>
            San Francisco<span>旧金山</span>
          </h1>
          <p className="scope">
            Ferry Building · Financial District · Embarcadero
          </p>
        </div>
      </header>
      <div className="top-actions">
        <span className="live-indicator">
          <i />
          {controls.paused ? "时刻已定格" : "城市正在运行"}
        </span>
        <button
          className="icon-button panel"
          aria-label="关于与来源"
          onClick={() => setAbout(true)}
        >
          <Icon name="info" />
        </button>
      </div>
      <button
        className="mobile-settings panel"
        onClick={() => setSettings(!settings)}
        aria-expanded={settings}
        aria-controls="environment-panel"
      >
        <Icon name="settings" />
        {settings ? "收起" : "环境"}
      </button>
      {settings && (
        <aside
          className="environment panel"
          id="environment-panel"
          aria-label="时间天气与交通控制"
        >
          <div className="panel-title">
            <span>海湾的此刻</span>
            <button
              className="close-settings"
              aria-label="关闭环境面板"
              onClick={() => setSettings(false)}
            >
              <Icon name="close" />
            </button>
          </div>
          <div className="clock-row">
            <output aria-label="地图时间">{clockText}</output>
            <div>
              <span>{weatherNames[controls.weather]}</span>
              <small>旧金山 · 演示时间</small>
            </div>
          </div>
          <div className="time-presets" role="group" aria-label="时间预设">
            {[
              ["清晨", 7.2],
              ["白天", 14.25],
              ["黄昏", 18.65],
              ["夜晚", 22.4],
            ].map(([name, h]) => (
              <button
                key={name}
                aria-pressed={
                  !controls.autoHour && Math.abs(hour - Number(h)) < 0.1
                }
                onClick={() => map.current?.setHour(Number(h))}
              >
                {name}
              </button>
            ))}
          </div>
          <label className="range-label" htmlFor="hour">
            <span>时间</span>
            <span>00:00 — 24:00</span>
          </label>
          <input
            id="hour"
            aria-label="一天中的时间"
            type="range"
            min="0"
            max="23.99"
            step=".01"
            value={hour}
            onChange={(e) => map.current?.setHour(Number(e.target.value))}
          />
          <label className="switch-row">
            <span>
              自动昼夜<small>约 5 分钟一昼夜</small>
            </span>
            <input
              type="checkbox"
              checked={controls.autoHour}
              onChange={(e) =>
                map.current?.setControls({ autoHour: e.target.checked })
              }
            />
            <i />
          </label>
          <div className="section-label">天气</div>
          <div className="weather-options" role="group" aria-label="天气预设">
            {(["clear", "cloudy", "fog", "rain"] as Weather[]).map((w) => (
              <button
                key={w}
                aria-pressed={controls.weather === w}
                onClick={() => map.current?.setControls({ weather: w })}
              >
                <Icon
                  name={w === "clear" ? "sun" : w === "cloudy" ? "cloud" : w}
                />
                <span>{weatherNames[w]}</span>
              </button>
            ))}
          </div>
          <label className="range-label" htmlFor="intensity">
            <span>天气强度</span>
            <span>{Math.round(controls.intensity * 100)}%</span>
          </label>
          <input
            id="intensity"
            aria-label="天气强度"
            type="range"
            min=".15"
            max="1"
            step=".01"
            value={controls.intensity}
            onChange={(e) =>
              map.current?.setControls({ intensity: Number(e.target.value) })
            }
          />
          <div className="section-label transport-label">
            流动的城市<span>示意交通</span>
          </div>
          <div className="transport-options">
            {(
              [
                ["cars", "car", "车辆"],
                ["boats", "boat", "船舶"],
                ["planes", "plane", "飞机"],
              ] as const
            ).map(([key, icon, label]) => (
              <button
                key={key}
                aria-pressed={controls[key]}
                aria-label={`显示${label}`}
                onClick={() => toggle(key)}
              >
                <Icon name={icon} />
                <span>{label}</span>
                <i />
              </button>
            ))}
          </div>
        </aside>
      )}
      {!settings && (
        <button
          className="desktop-settings panel"
          aria-label="打开环境面板"
          onClick={() => setSettings(true)}
        >
          <Icon name="settings" />
          时间与天气
        </button>
      )}
      <div className="location-caption">
        <span className="location-line" />
        <div>
          <p>THE CITY MEETS THE BAY</p>
          <span>沿着海湾，慢一点。</span>
        </div>
      </div>
      <nav className="map-tools panel" aria-label="地图工具">
        <button
          aria-label="缩小地图"
          onClick={() => map.current?.zoom(1 / 1.35)}
        >
          <Icon name="minus" />
        </button>
        <button aria-label="放大地图" onClick={() => map.current?.zoom(1.35)}>
          <Icon name="plus" />
        </button>
        <button aria-label="地图全景" onClick={() => map.current?.home()}>
          <Icon name="home" />
        </button>
        <span className="tool-separator" />
        <button
          className="play-control"
          aria-label={controls.paused ? "播放城市动画" : "暂停城市动画"}
          onClick={() => map.current?.setControls({ paused: !controls.paused })}
        >
          <Icon name={controls.paused ? "play" : "pause"} />
          <span>{controls.paused ? "播放" : "暂停"}</span>
        </button>
        <button
          className="speed-control"
          aria-label="切换交通速度"
          onClick={() =>
            map.current?.setControls({
              rate: controls.rate === 1 ? 2 : controls.rate === 2 ? 4 : 1,
            })
          }
        >
          {controls.rate}×
        </button>
        <span className="tool-separator" />
        <button
          aria-label="显示地名"
          aria-pressed={labels}
          onClick={() => {
            const next = !labels;
            setLabels(next);
            if (map.current) map.current.labels = next;
          }}
        >
          <Icon name="pin" />
        </button>
      </nav>
      <footer className="map-credit">
        <span>样区 01 · 固定视角精绘</span>
        <button onClick={() => setAbout(true)}>
          DataSF · USGS · © OpenStreetMap
        </button>
      </footer>
      {(!ready || error) && (
        <div className="loading">
          <span className="loading-orbit" />
          <h2>{error ? "地图暂未就绪" : "正在展开旧金山海湾"}</h2>
          <p>{error || "载入精绘图块与城市动画…"}</p>
        </div>
      )}
      {about && (
        <div className="modal-backdrop" onClick={() => setAbout(false)}>
          <section
            className="about-dialog panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="about-title"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === "Escape") setAbout(false);
              if (e.key === "Tab") {
                const nodes = Array.from(
                  e.currentTarget.querySelectorAll<HTMLElement>("button,a"),
                );
                const first = nodes[0],
                  last = nodes[nodes.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                  e.preventDefault();
                  last.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                  e.preventDefault();
                  first.focus();
                }
              }
            }}
          >
            <div className="panel-title">
              <span>ABOUT THE MAP</span>
              <button
                ref={aboutClose}
                aria-label="关闭说明"
                onClick={() => setAbout(false)}
              >
                <Icon name="close" />
              </button>
            </div>
            <h2 id="about-title">一座会呼吸的海湾城市。</h2>
            <p>
              Ferry Building、Financial District 与 Embarcadero
              的连续精绘样区。拖动浏览街区，试试不同时间与天气。
            </p>
            <h3>画面与数据</h3>
            <p>
              由 DataSF 建筑轮廓、USGS 2023 激光雷达和 2026-11-09 OpenStreetMap
              快照建立统一正交结构参照，再用 imagegen
              精绘。细节与局部边缘可能偏离源几何；遮挡、窗灯与配准属于展示近似。
            </p>
            <p>
              车流、渡轮、货船和飞机均为示意动画。日夜使用配准的昼夜精绘图块与独立局部灯光；天气为视觉效果。当前没有实时交通、机场地面起降或物理太阳阴影计算。
            </p>
            <h3>Inspired by</h3>
            <p>
              <a
                href="https://cannoneyed.com/projects/isometric-nyc"
                target="_blank"
                rel="noreferrer"
              >
                Isometric NYC
              </a>{" "}
              ·{" "}
              <a
                href="https://vancouver.isoworld.xyz/"
                target="_blank"
                rel="noreferrer"
              >
                Isometric Vancouver
              </a>{" "}
              ·{" "}
              <a
                href="https://openseadragon.github.io/"
                target="_blank"
                rel="noreferrer"
              >
                OpenSeadragon
              </a>
            </p>
            <p className="about-license">
              DataSF PDDL · USGS public domain ·{" "}
              <a
                href="https://www.openstreetmap.org/copyright"
                target="_blank"
                rel="noreferrer"
              >
                © OpenStreetMap contributors / ODbL
              </a>
            </p>
            <a
              className="repo-link"
              href="https://github.com/Dilee-King/isometric-san-francisco"
              target="_blank"
              rel="noreferrer"
            >
              在 GitHub 查看项目与更新 ↗
            </a>
          </section>
        </div>
      )}
    </main>
  );
}
