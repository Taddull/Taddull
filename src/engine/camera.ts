/* Generic 3D orbit-camera path. Pure TS (no imports) so timelines that use it can be loaded by
 * `node` from the audio scripts as well as bundled by Remotion. */

/** target (x, y, z), distance d, azimuth yaw (deg, + = camera right), elevation pitch (deg, + = camera
 *  above) and roll (deg) at frame f */
export type CamKey = {f: number; x: number; y: number; z?: number; d: number; yaw: number; pitch: number; roll?: number};
export type Cam = {x: number; y: number; z: number; d: number; yaw: number; pitch: number; roll: number};

/** Fritsch–Carlson monotone cubic interpolation over non-uniform keys (C1, no overshoot) */
export const monotone = (xs: number[], ys: number[]) => {
	const n = xs.length;
	const h = xs.slice(1).map((x, i) => x - xs[i]);
	const dl = h.map((hi, i) => (ys[i + 1] - ys[i]) / hi);
	const m = new Array(n).fill(0);
	for (let i = 1; i < n - 1; i++) {
		if (dl[i - 1] * dl[i] <= 0) continue;
		const w1 = 2 * h[i] + h[i - 1];
		const w2 = h[i] + 2 * h[i - 1];
		m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i]);
	}
	return (x: number) => {
		if (x <= xs[0]) return ys[0];
		if (x >= xs[n - 1]) return ys[n - 1];
		let i = 0;
		while (xs[i + 1] < x) i++;
		const t = (x - xs[i]) / h[i];
		const t2 = t * t;
		const t3 = t2 * t;
		return (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1];
	};
};

/** Build a camera sampler from keys. Distance is interpolated in log space so zooms feel even. */
export const createCamera = (keys: CamKey[]) => {
	const fs = keys.map((k) => k.f);
	const s = {
		x: monotone(fs, keys.map((k) => k.x)),
		y: monotone(fs, keys.map((k) => k.y)),
		z: monotone(fs, keys.map((k) => k.z ?? 0)),
		ld: monotone(fs, keys.map((k) => Math.log(k.d))),
		yaw: monotone(fs, keys.map((k) => k.yaw)),
		pitch: monotone(fs, keys.map((k) => k.pitch)),
		roll: monotone(fs, keys.map((k) => k.roll ?? 0)),
	};
	return (f: number): Cam => ({x: s.x(f), y: s.y(f), z: s.z(f), d: Math.exp(s.ld(f)), yaw: s.yaw(f), pitch: s.pitch(f), roll: s.roll(f)});
};

/** approximate on-screen motion in px/frame — drives the camera "air" layer in the audio */
export const cameraSpeed = (sample: (f: number) => Cam, duration: number, perspective: number) => {
	const out: number[] = [];
	for (let f = 0; f < duration; f++) {
		const a = sample(f);
		const b = sample(f + 1);
		const pan = (Math.hypot(b.x - a.x, b.y - a.y) * perspective) / a.d;
		const ang = ((Math.abs(b.yaw - a.yaw) + Math.abs(b.pitch - a.pitch) + Math.abs(b.roll - a.roll)) * Math.PI) / 180 * perspective * 0.6;
		const zoom = Math.abs(Math.log(b.d) - Math.log(a.d)) * 960;
		out.push(pan + ang + zoom);
	}
	return out;
};
