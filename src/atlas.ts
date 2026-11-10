import type { Frame } from "./types.ts";

export type DepthEncoding = { offset: number; range: number };

export const legacyDepthEncoding: DepthEncoding = { offset: 2000, range: 4000 };

export function decodeSourceDepth(
  high: number,
  low: number,
  encoding: DepthEncoding,
) {
  return ((high * 256 + low) / 65535) * encoding.range - encoding.offset;
}

export function maskIndex(
  x: number,
  y: number,
  width: number,
  height: number,
  maskWidth: number,
  maskHeight: number,
) {
  if (x < 0 || y < 0 || x >= width || y >= height) return -1;
  return (
    (Math.floor((y / height) * maskHeight) * maskWidth +
      Math.floor((x / width) * maskWidth)) *
    4
  );
}

/** Keep user choices and clocks when the map assets/camera change. */
export function sceneTransfer(frame: Frame): Frame {
  return {
    clock: { ...frame.clock },
    controls: { ...frame.controls },
    poses: [],
    sequence: 0,
  };
}
