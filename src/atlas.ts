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

export function interpolateImageOffset(samples: number[][], x: number) {
  const next = samples.findIndex(([at]) => at > x);
  if (next < 1) return 0;
  const [start, from] = samples[next - 1];
  const [end, to] = samples[next];
  return from + (to - from) * (x - start) / (end - start);
}

/** Resize to the GPU limit without interpolating the packed depth and surface bytes. */
export function fitMaskTexture(
  pixels: Uint8ClampedArray,
  width: number,
  height: number,
  limit: number,
) {
  if (Math.max(width, height) <= limit)
    return { width, height, pixels: new Uint8Array(pixels.buffer, pixels.byteOffset, pixels.byteLength) };

  const scale = limit / Math.max(width, height);
  const targetWidth = Math.max(1, Math.floor(width * scale));
  const targetHeight = Math.max(1, Math.floor(height * scale));
  const source = new Uint32Array(pixels.buffer, pixels.byteOffset, width * height);
  const target = new Uint32Array(targetWidth * targetHeight);
  const columns = Array.from({ length: targetWidth }, (_, column) =>
    Math.floor((column + .5) * width / targetWidth));
  for (let row = 0; row < targetHeight; row++) {
    const sourceRow = Math.floor((row + .5) * height / targetHeight) * width;
    for (let column = 0; column < targetWidth; column++)
      target[row * targetWidth + column] = source[sourceRow + columns[column]];
  }
  return { width: targetWidth, height: targetHeight, pixels: new Uint8Array(target.buffer) };
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
