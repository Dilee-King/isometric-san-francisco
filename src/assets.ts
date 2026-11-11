import type { SceneData } from "./types.ts";
import { version as packageVersion } from "../package.json";

export type SceneKey = "waterfront" | "bay";
const releases = ["0.5.0", "0.6.1", "0.7.1", "0.8.1", "0.9.0"] as const;
const params = new URLSearchParams(window.location.search);
const requested = params.get("v")?.replace(/^0\.([678])\.0$/, "0.$1.1");
export const ATLAS_VERSION = releases.find(release => release === requested)
  ?? releases.find(release => release === packageVersion) ?? "0.8.1";
const releaseFolder = ATLAS_VERSION === "0.5.0" ? "v5" : `v${ATLAS_VERSION.split(".")[1]}-art`;
export const FULL_BAY = ATLAS_VERSION === "0.9.0";
export const START_SCENE: SceneKey = FULL_BAY && params.get("view") !== "city" ? "bay" : "waterfront";
export const START_LOCATION = params.get("p") ?? undefined;
export const scenePath = (key: SceneKey) =>
  `${import.meta.env.BASE_URL}map/${FULL_BAY && key === "waterfront" ? "v8-art" : releaseFolder}/${key}/scene.json`;
export const sceneRoot = (data: SceneData) =>
  `${import.meta.env.BASE_URL}${data.assetRoot ?? "map/v2/"}`;
export const maskPath = (data: SceneData, name: string) =>
  data.maskBundle
    ? `${import.meta.env.BASE_URL}${data.maskBundle}`
    : `${sceneRoot(data)}${name}.png`;
