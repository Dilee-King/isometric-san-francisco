import type { Point3, Pose } from "./types.ts";

export type VehicleFace = {
  points: Point3[];
  color: string;
  alpha?: number;
  emissive?: boolean;
  nightOnly?: boolean;
  pulse?: boolean;
};
type Point2 = [number, number];

/** Vehicle-local forward, left and up are measured in metres. */
export function worldOffset(
  pose: Pose,
  forward: number,
  side: number,
  up: number,
): Point3 {
  const length = Math.hypot(pose.direction[0], pose.direction[1]) || 1;
  const x = pose.direction[0] / length || (!pose.direction[1] ? 1 : 0),
    n = pose.direction[1] / length;
  return [
    pose.point[0] + x * forward - n * side,
    pose.point[1] + n * forward + x * side,
    pose.point[2] + up,
  ];
}

export function vehicleFaces(pose: Pose): VehicleFace[] {
  const faces: VehicleFace[] = [];
  const add = (
    points: Point3[],
    color: string,
    options: Partial<VehicleFace> = {},
  ) =>
    faces.push({
      points: points.map(([f, s, h]) => worldOffset(pose, f, s, h)),
      color,
      ...options,
    });
  const extrude = (
    ring: Point2[],
    bottom: number,
    top: number,
    color: string,
    roof = color,
  ) => {
    if (
      ring.reduce((sum, p, i) => {
        const q = ring[(i + 1) % ring.length];
        return sum + p[0] * q[1] - q[0] * p[1];
      }, 0) < 0
    )
      ring = ring.slice().reverse();
    for (let i = 0; i < ring.length; i++) {
      const a = ring[i],
        b = ring[(i + 1) % ring.length];
      add(
        [
          [...a, bottom],
          [...b, bottom],
          [...b, top],
          [...a, top],
        ],
        color,
      );
    }
    add(
      ring.map(([f, s]) => [f, s, top]),
      roof,
    );
  };
  const rectangle = (a: number, b: number, w: number): Point2[] => [
    [a, -w / 2],
    [b, -w / 2],
    [b, w / 2],
    [a, w / 2],
  ];
  const box = (
    f: number,
    s: number,
    l: number,
    w: number,
    bottom: number,
    top: number,
    color: string,
    roof = color,
  ) =>
    extrude(
      rectangle(f - l / 2, f + l / 2, w).map(([x, y]) => [x, y + s]),
      bottom,
      top,
      color,
      roof,
    );
  const patch = (
    f: number,
    s: number,
    l: number,
    w: number,
    h: number,
    color: string,
    options: Partial<VehicleFace> = {},
  ) =>
    add(
      rectangle(f - l / 2, f + l / 2, w).map(([x, y]) => [x, y + s, h]),
      color,
      options,
    );

  if (pose.kind === "car") {
    const index = Number(pose.id.split("-").at(-1)) || 0;
    const suv = index % 7 === 3,
      van = index % 11 === 5;
    const l = van ? 5.6 : suv ? 4.9 : 4.5,
      w = van ? 2 : suv ? 1.95 : 1.8,
      h = van ? 1.95 : suv ? 0.95 : 0.8;
    const shadow = rectangle(-l * 0.53, l * 0.53, w * 1.13).map(([f, s]) =>
      worldOffset(pose, f, s, -0.18),
    );
    faces.push({
      points: shadow.map((p) => [p[0] + 0.35, p[1] - 0.2, p[2]]),
      color: "#101b22",
      alpha: 0.22,
      emissive: true,
    });
    box(0, 0, l, w, 0.18, h, pose.color);
    for (const f of [-l * 0.3, l * 0.3])
      for (const s of [-w * 0.46, w * 0.46])
        box(f, s, 0.62, 0.12, 0.02, 0.42, "#202830");
    if (!van) {
      box(
        -0.3,
        0,
        l * 0.45,
        w * 0.81,
        h,
        h + (suv ? 0.76 : 0.65),
        "#324955",
        pose.color,
      );
      // Sloping windscreen, rear glass and roof all use projected world vertices.
      add(
        [
          [l * 0.17, -w * 0.39, h + 0.06],
          [l * 0.17, w * 0.39, h + 0.06],
          [l * 0.1, w * 0.39, h + 0.56],
          [l * 0.1, -w * 0.39, h + 0.56],
        ],
        "#486577",
      );
    } else patch(l * 0.3, 0, l * 0.18, w * 0.85, h + 0.012, "#385663");
    for (const s of [-w * 0.32, w * 0.32]) {
      patch(l / 2 - 0.08, s, 0.13, 0.27, h + 0.016, "#fff0c2", {
        emissive: true,
        nightOnly: true,
      });
      patch(-l / 2 + 0.08, s, 0.13, 0.23, h + 0.017, "#f45237", {
        emissive: true,
        nightOnly: true,
      });
    }
    add(
      [
        [l / 2, -w * 0.35, -0.15],
        [l / 2 + 14, -3.2, -0.15],
        [l / 2 + 14, 3.2, -0.15],
        [l / 2, w * 0.35, -0.15],
      ],
      "#f8e5b1",
      { alpha: 0.09, emissive: true, nightOnly: true },
    );
  } else if (pose.kind === "ferry" || pose.kind === "cargo") {
    const cargo = pose.kind === "cargo",
      l = cargo ? 65 : 31,
      w = cargo ? 15 : 9;
    const hull: Point2[] = [
      [-l * 0.5, w * 0.43],
      [-l * 0.5, -w * 0.43],
      [l * 0.31, -w * 0.5],
      [l * 0.5, 0],
      [l * 0.31, w * 0.5],
    ];
    extrude(
      hull,
      -0.55,
      cargo ? 2.1 : 1.35,
      cargo ? "#67453c" : "#d8d9d1",
      cargo ? "#88918a" : "#e9e8dd",
    );
    if (cargo) {
      box(-l * 0.35, 0, 11, 10.5, 2.1, 6.9, "#c0c9c3", "#e5e3d5");
      box(-l * 0.35, 0, 9.5, 9.8, 5.8, 7.1, "#5b7c88", "#d9d9cc");
      for (let bay = 0; bay < 6; bay++)
        for (let row = 0; row < 3; row++) {
          const f = -13 + bay * 6.5,
            s = (row - 1) * 2.55;
          box(
            f,
            s,
            6.1,
            2.4,
            2.12,
            4.72,
            ["#9b5d42", "#748d90", "#a99b6c", "#59757b"][(bay + row) % 4],
          );
          // Small ridges are actual raised top strips, not screen-rotated lines.
          for (const offset of [-0.65, 0, 0.65])
            patch(f, s + offset, 5.9, 0.045, 4.735, "#b5b5a0");
        }
      box(-22, 0, 0.35, 0.35, 7.1, 9.4, "#56636b");
    } else {
      box(-1, 0, 21, 7.5, 1.36, 3.5, "#aebdbd", "#e7e8dc");
      box(-0.6, 0, 18.4, 7.55, 2.2, 3.25, "#3b6273", "#c5ceca");
      box(-2, 0, 14, 5.5, 3.5, 4.85, "#ced5cf", "#e7e8de");
      box(4.5, 0, 4, 5.6, 3.5, 4.5, "#4e7180", "#e2e3d7");
      box(-2, 0, 0.25, 0.25, 4.85, 6.0, "#67787d");
      for (const s of [-3.81, 3.81])
        for (let f = -9; f < 8; f += 2.4)
          box(f, s, 0.8, 0.035, 2.35, 2.85, "#e9c788");
    }
    patch(l * 0.2, w * 0.43, 0.5, 0.4, 2.3, "#6cc29a", {
      emissive: true,
      nightOnly: true,
    });
    patch(l * 0.2, -w * 0.43, 0.5, 0.4, 2.3, "#e15e49", {
      emissive: true,
      nightOnly: true,
    });
  } else {
    const sections = [
      [-16, 0.14, 1.5],
      [-13, 0.95, 1.6],
      [-5, 1.18, 1.6],
      [7, 1.05, 1.65],
      [12, 0.6, 1.6],
      [16, 0.05, 1.45],
    ];
    const ring = (section: number[], i: number): Point3 => [
      section[0],
      section[1] * Math.cos((i * Math.PI) / 4),
      section[2] + section[1] * 0.78 * Math.sin((i * Math.PI) / 4),
    ];
    for (let j = 0; j < sections.length - 1; j++)
      for (let i = 0; i < 8; i++)
        add(
          [
            ring(sections[j], i),
            ring(sections[j], i + 1),
            ring(sections[j + 1], i + 1),
            ring(sections[j + 1], i),
          ],
          "#dbe1de",
        );
    for (const side of [-1, 1]) {
      const wing: Point2[] = [
        [3, side * 1],
        [-4, side * 14],
        [-7, side * 14],
        [-2.8, side * 0.9],
      ];
      extrude(
        side < 0 ? wing.reverse() : wing,
        1.15,
        1.38,
        "#9aaab0",
        "#c6d2d2",
      );
      const tail: Point2[] = [
        [-10, side * 0.7],
        [-15, side * 6],
        [-17, side * 6],
        [-14.8, side * 0.5],
      ];
      extrude(
        side < 0 ? tail.reverse() : tail,
        1.75,
        1.95,
        "#a5b3b5",
        "#ccd4d0",
      );
      box(-0.7, side * 5.8, 3.5, 1.15, -0.05, 1.1, "#aebdc2", "#cad4d4");
      patch(
        -5.8,
        side * 14,
        0.6,
        0.36,
        1.42,
        side > 0 ? "#71d0a6" : "#ed6c55",
        { emissive: true, pulse: true },
      );
    }
    // A vertical tail introduces the height missing from a plan-view icon.
    add(
      [
        [-11, 0, 2.2],
        [-15.8, 0, 6.3],
        [-17.7, 0, 6.3],
        [-16.5, 0, 2.1],
      ],
      "#a75f4d",
    );
    add(
      [
        [-11, 0.16, 2.2],
        [-15.8, 0.16, 6.3],
        [-17.7, 0.16, 6.3],
        [-16.5, 0.16, 2.1],
      ],
      "#d4dcd8",
    );
    patch(11, 0, 1.6, 1.05, 2.2, "#466475");
    for (let f = -9; f < 9; f += 1.2)
      for (const s of [-1.13, 1.13]) box(f, s, 0.4, 0.03, 1.7, 2.0, "#506b76");
  }
  return faces;
}
