export type Point3 = [number, number, number];
export type Weather = "clear" | "fog" | "rain";
export type Projection = {
  scale: number;
  origin: [number, number];
  sinElevation: number;
  cosElevation: number;
  east: [number, number];
  north: [number, number];
};
export type Controls = {
  paused: boolean;
  rate: number;
  autoHour: boolean;
  weather: Weather;
  intensity: number;
  cars: boolean;
  boats: boolean;
  planes: boolean;
};
export type Clock = {
  transportTime: number;
  environmentTime: number;
  hour: number;
};
export type Route = {
  id: string;
  kind: "car" | "ferry" | "cargo" | "plane";
  points: Point3[];
  speed: number;
  phase: number;
  dwell?: number;
  color?: string;
};
export type Pose = {
  id: string;
  kind: Route["kind"];
  point: Point3;
  direction: Point3;
  speed: number;
  moving: boolean;
  color: string;
};
export type SceneData = {
  width: number;
  height: number;
  release: string;
  projection: Projection;
  extent: number[];
  sourceBuildings: number;
  routes: Route[];
  lamps: Point3[];
  windows: { p: Point3; seed: number; angle: number }[];
  landmarks: { name: string; p: Point3 }[];
};
export type Frame = {
  clock: Clock;
  controls: Controls;
  poses: Pose[];
  sequence: number;
};
