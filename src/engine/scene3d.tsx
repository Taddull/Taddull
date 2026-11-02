import React from 'react';
import {AbsoluteFill, Easing, interpolate, random} from 'remotion';
import type {Cam} from './camera.ts';

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const prog = (f: number, a: number, b: number, easing = Easing.bezier(0.16, 1, 0.3, 1)) =>
	interpolate(f, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing});

const preserve: React.CSSProperties = {transformStyle: 'preserve-3d'};

/** Perspective viewport + world root transformed by the inverse of the orbit camera. */
export const Scene3D: React.FC<{cam: Cam; perspective: number; children: React.ReactNode}> = ({cam, perspective, children}) => (
	<AbsoluteFill style={{perspective, perspectiveOrigin: '50% 50%'}}>
		<div
			style={{
				...preserve,
				position: 'absolute',
				left: 960,
				top: 540,
				width: 0,
				height: 0,
				transformOrigin: '0 0',
				transform: `translateZ(${perspective - cam.d}px) rotateZ(${cam.roll}deg) rotateX(${-cam.pitch}deg) rotateY(${-cam.yaw}deg) translate3d(${-cam.x}px, ${-cam.y}px, ${-cam.z}px)`,
			}}
		>
			{children}
		</div>
	</AbsoluteFill>
);

/** A 1920x1080 panel centred at (x, y) on the z = 0 wall. Content is laid out at `ss`x (CSS zoom) and
 *  scaled back down, because Chrome rasterises perspective layers at ~1x of their local pixels —
 *  this keeps text crisp in camera close-ups. Panels far outside the view are skipped. */
export const StationFrame: React.FC<{x: number; y: number; cam: Cam; perspective: number; ss?: number; children: React.ReactNode}> = ({
	x,
	y,
	cam,
	perspective,
	ss = 2,
	children,
}) => {
	const vw = ((960 * cam.d) / perspective) * 1.7 + 1600;
	const vh = ((540 * cam.d) / perspective) * 1.7 + 1000;
	if (Math.abs(cam.x - x) > vw || Math.abs(cam.y - y) > vh) return null;
	return (
		<div style={{...preserve, position: 'absolute', left: x - 960, top: y - 540, width: 1920, height: 1080, transformOrigin: '0 0', transform: `scale3d(${1 / ss}, ${1 / ss}, ${1 / ss})`}}>
			<div style={{...preserve, position: 'relative', width: 1920, height: 1080, zoom: ss}}>{children}</div>
		</div>
	);
};

/** lifts absolutely-positioned children off the panel by z px */
export const Z: React.FC<{z: number; children: React.ReactNode; style?: React.CSSProperties}> = ({z, children, style}) => (
	<div style={{position: 'absolute', inset: 0, transform: `translateZ(${z}px)`, ...style}}>{children}</div>
);

/* ---------------------------------------------------------------- environment */
export type EnvTheme = {dot: string; floorDot: string; glow: string; wallZ: number};

/** dotted back wall + floor (laid out at 1/4 and scaled x4 to keep raster sizes sane) */
export const Environment: React.FC<{f: number; theme: EnvTheme; x0: number; y0: number; w: number; h: number; floorY: number}> = ({f, theme, x0, y0, w, h, floorY}) => {
	const k = 4;
	const dots = (c: string, step: number, r: number): React.CSSProperties => ({
		backgroundImage: `radial-gradient(circle, ${c} ${r}px, transparent ${r + 0.6}px)`,
		backgroundSize: `${step}px ${step}px`,
	});
	const glows = [
		{x: x0 + w * 0.2, y: y0 + h * 0.25, s: 2800},
		{x: x0 + w * 0.5, y: y0 + h * 0.5, s: 3200},
		{x: x0 + w * 0.8, y: y0 + h * 0.3, s: 2800},
		{x: x0 + w * 0.35, y: y0 + h * 0.8, s: 3000},
		{x: x0 + w * 0.75, y: y0 + h * 0.8, s: 2600},
	];
	return (
		<>
			<div style={{position: 'absolute', left: x0, top: y0, width: w / k, height: h / k, transformOrigin: '0 0', transform: `translateZ(${theme.wallZ}px) scale(${k})`, ...dots(theme.dot, 14, 0.55)}}>
				{glows.map((g, i) => (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: (g.x - x0 - g.s / 2) / k + Math.sin(f / 70 + i) * 10,
							top: (g.y - y0 - g.s / 2) / k + Math.cos(f / 80 + i) * 8,
							width: g.s / k,
							height: g.s / k,
							borderRadius: '50%',
							background: `radial-gradient(closest-side, ${theme.glow}, transparent)`,
						}}
					/>
				))}
			</div>
			<div
				style={{
					position: 'absolute',
					left: x0,
					top: floorY,
					width: w / k,
					height: 9000 / k,
					transformOrigin: '0 0',
					transform: `translateZ(${theme.wallZ}px) rotateX(90deg) scale(${k})`,
					...dots(theme.floorDot, 16, 0.7),
					WebkitMaskImage: 'linear-gradient(180deg, #000 0%, rgba(0,0,0,0.6) 40%, transparent 100%)',
					maskImage: 'linear-gradient(180deg, #000 0%, rgba(0,0,0,0.6) 40%, transparent 100%)',
				}}
			/>
		</>
	);
};

/** dashed route between station centres, shown as the camera pulls back */
export const Journey: React.FC<{cam: Cam; points: {x: number; y: number}[]; color: string; z: number}> = ({cam, points, color, z}) => {
	const o = Math.min(1, Math.max(0, (cam.d - 2200) / 2000));
	if (o <= 0) return null;
	const xs = points.map((p) => p.x);
	const ys = points.map((p) => p.y);
	const ox = Math.min(...xs) - 500;
	const oy = Math.min(...ys) - 500;
	const d = points.map((p, i) => `${i ? 'L' : 'M'}${p.x - ox} ${p.y - oy}`).join(' ');
	return (
		<svg width={Math.max(...xs) - ox + 500} height={Math.max(...ys) - oy + 500} style={{position: 'absolute', left: ox, top: oy, opacity: o, transform: `translateZ(${z}px)`}}>
			<path d={d} fill="none" stroke={color} strokeWidth={14} strokeDasharray="6 44" strokeLinecap="round" />
			{points.slice(0, -1).map((p, i) => (
				<circle key={i} cx={p.x - ox} cy={p.y - oy} r={34} fill={color} />
			))}
		</svg>
	);
};

/* ---------------------------------------------------------------- floating decor */
export type DecorItem = {x: number; y: number; z: number; kind: 'sticker' | 'spark'; e: string; s: number; ph: number};

/** stickers/sparkles around the midpoint of each camera move: off-screen during holds, they sweep past
 *  in real parallax while the camera travels */
export const placeDecor = (points: {x: number; y: number}[], stickers: string[], seed: string): DecorItem[] => {
	const out: DecorItem[] = [];
	let n = 0;
	const push = (x: number, y: number, kind: 'sticker' | 'spark') => {
		out.push({x, y, z: 150 + random(`${seed}z${n}`) * 320, kind, e: stickers[n % stickers.length], s: 0.75 + random(`${seed}s${n}`) * 0.6, ph: random(`${seed}p${n}`) * 100});
		n++;
	};
	for (let i = 1; i < points.length - 1; i++) {
		const a = points[i - 1];
		const b = points[i];
		const mx = (a.x + b.x) / 2;
		const my = (a.y + b.y) / 2;
		const jit = (k: string) => (random(`${seed}${k}${i}`) - 0.5) * 160;
		if (Math.abs(b.x - a.x) > Math.abs(b.y - a.y)) {
			push(mx - 120 + jit('a'), my - 420, 'sticker');
			push(mx + 160 + jit('b'), my + 400, 'sticker');
			push(mx + 40 + jit('c'), my - 120, 'spark');
		} else {
			push(mx - 760, my - 60 + jit('a'), 'sticker');
			push(mx + 720, my + 80 + jit('b'), 'sticker');
			push(mx + 300, my - 40 + jit('d'), 'spark');
		}
	}
	return out;
};

export const Decor: React.FC<{f: number; items: DecorItem[]; sticker: (e: string, size: number) => React.ReactNode; spark: (size: number) => React.ReactNode}> = ({f, items, sticker, spark}) => (
	<>
		{items.map((d, i) => {
			const bob = Math.sin((f + d.ph) / 28) * 14;
			const tf = `translate3d(${d.x}px, ${d.y + bob}px, ${d.z}px)`;
			return (
				<div key={i} style={{position: 'absolute', left: 0, top: 0, transform: d.kind === 'sticker' ? `${tf} rotate(${Math.sin((f + d.ph) / 40) * 12}deg)` : tf}}>
					<div style={{transform: d.kind === 'spark' ? `rotate(${f * 1.2 + d.ph}deg) scale(${0.75 + 0.25 * Math.sin((f + d.ph) / 12)})` : undefined}}>
						{d.kind === 'sticker' ? sticker(d.e, 100 * d.s) : spark(34 * d.s)}
					</div>
				</div>
			);
		})}
	</>
);

/* ---------------------------------------------------------------- cursor */
export const Cursor: React.FC<{
	t: number;
	path: {t: number; x: number; y: number}[];
	clicks: number[];
	z?: number;
	fill?: string;
	stroke?: string;
	shadow?: string;
	ring?: string;
}> = ({t, path, clicks, z = 0, fill = '#0F0F0F', stroke = '#fff', shadow = 'rgba(0,0,0,0.3)', ring = '#fff'}) => {
	const first = path[0];
	const last = path[path.length - 1];
	if (t < first.t - 2 || t > last.t + 30) return null;
	let x = first.x;
	let y = first.y;
	for (let i = 1; i < path.length; i++) {
		if (t >= path[i - 1].t) {
			const e = prog(t, path[i - 1].t, path[i].t, Easing.bezier(0.6, 0, 0.25, 1));
			x = lerp(path[i - 1].x, path[i].x, e);
			y = lerp(path[i - 1].y, path[i].y, e);
		}
	}
	const op = prog(t, first.t, first.t + 8) * (1 - prog(t, last.t + 16, last.t + 28));
	let sc = 1;
	let r = 0;
	let rO = 0;
	for (const c of clicks) {
		if (t >= c - 3 && t <= c + 6) sc = Math.min(sc, t < c ? lerp(1, 0.8, (t - c + 3) / 3) : lerp(0.8, 1, (t - c) / 6));
		if (t >= c && t <= c + 16) {
			r = (t - c) / 16;
			rO = 1 - r;
		}
	}
	return (
		<div style={{position: 'absolute', left: x, top: y, transform: `translateZ(${z}px)`, opacity: op, pointerEvents: 'none'}}>
			{rO > 0 && <div style={{position: 'absolute', left: -40 * r - 6, top: -40 * r - 6, width: 80 * r + 12, height: 80 * r + 12, borderRadius: '50%', border: `4px solid ${ring}`, opacity: rO}} />}
			<svg width="40" height="52" viewBox="0 0 20 26" style={{transform: `scale(${sc})`, transformOrigin: '0 0', filter: `drop-shadow(0 6px 10px ${shadow})`}}>
				<path d="M1 1 L1 20 L6 15.5 L9.5 23.5 L13 22 L9.6 14.2 L16 14.2 Z" fill={fill} stroke={stroke} strokeWidth="1.6" strokeLinejoin="round" />
			</svg>
		</div>
	);
};
