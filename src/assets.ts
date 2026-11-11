import type { SceneData } from "./types.ts";
import { version as packageVersion } from "../package.json";

export type SceneKey = "waterfront" | "bay";
const releases = ["0.5.0", "0.6.0", "0.7.0", "0.8.0"] as const;
const requested = new URLSearchParams(window.location.search).get("v");
export const ATLAS_VERSION = releases.find(release => release === requested)
  ?? releases.find(release => release === packageVersion) ?? "0.8.0";
export const ATLAS_ROOT = `${import.meta.env.BASE_URL}map/v${ATLAS_VERSION.split(".")[1]}/`;
export const sceneRoot = (data: SceneData) =>
  `${import.meta.env.BASE_URL}${data.assetRoot ?? "map/v2/"}`;
export const maskPath = (data: SceneData, name: string) =>
  data.maskBundle
    ? `${import.meta.env.BASE_URL}${data.maskBundle}`
    : `${sceneRoot(data)}${name}.png`;
