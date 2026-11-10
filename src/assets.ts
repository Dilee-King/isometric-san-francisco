import type { SceneData } from "./types.ts";

export type SceneKey = "waterfront" | "bay";
export const ATLAS_ROOT = `${import.meta.env.BASE_URL}map/v3/`;
export const sceneRoot = (data: SceneData) =>
  `${import.meta.env.BASE_URL}${data.assetRoot ?? "map/v2/"}`;
