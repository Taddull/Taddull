import React from 'react';
import {AbsoluteFill, Easing, random} from 'remotion';
import {Emoji, Sparkle} from './primitives';
import {C, lerp, prog} from './theme';
import {CAMERA, SX, SY, StationId, center} from './timeline';

/* ================================================================ camera */
export type Cam = {x: number; y: number; z: number; r: number};

const moveEase = Easing.bezier(0.72, 0, 0.28, 1);
const zoomEase = Easing.bezier(0.65, 0, 0.3, 1);
const driftEase = Easing.bezier(0.37, 0, 0.63, 1);

export const camAt = (f: number): Cam => {
	const last = CAMERA[CAMERA.length - 1];
	if (f <= CAMERA[0].f) return {...CAMERA[0], r: 0};
	if (f >= last.f) return {...last, r: 0};
	const i = CAMERA.findIndex((k) => k.f > f);
	const a = CAMERA[i - 1];
	const b = CAMERA[i];
	const t = (f - a.f) / (b.f - a.f);
	const dx = b.x - a.x;
	const dy = b.y - a.y;
	if (b.ease === 'move') {
		const e = moveEase(t);
		const dist = Math.hypot(dx, dy);
		const breath = 0.22 * Math.min(1, dist / 2200);
		return {
			x: lerp(a.x, b.x, e),
			y: lerp(a.y, b.y, e),
			z: lerp(a.z, b.z, e) * (1 - breath * Math.sin(Math.PI * e)),
			r: Math.sin(Math.PI * e) * 2.2 * Math.min(1, dist / 2200) * (Math.sign(dx) || Math.sign(dy)),
		};
	}
	if (b.ease === 'zoom') {
		const e = zoomEase(t);
		const z = Math.exp(lerp(Math.log(a.z), Math.log(b.z), e));
		// keep the zoom anchored: position follows the zoom progress in log space
		const pz = (Math.log(z) - Math.log(a.z)) / (Math.log(b.z) - Math.log(a.z));
		return {x: lerp(a.x, b.x, pz), y: lerp(a.y, b.y, pz), z, r: Math.sin(Math.PI * e) * -1.5};
	}
	const e = driftEase(t);
	return {x: lerp(a.x, b.x, e), y: lerp(a.y, b.y, e), z: lerp(a.z, b.z, e), r: 0};
};

/** A layer that follows the camera. k=1 is the world; k<1 is behind (parallax), k>1 is in front. */
export const Layer: React.FC<{cam: Cam; k?: number; children: React.ReactNode}> = ({cam, k = 1, children}) => (
	<div
		style={{
			position: 'absolute',
			left: 0,
			top: 0,
			width: 0,
			height: 0,
			transform: `translate(960px, 540px) rotate(${cam.r * k}deg) scale(${Math.pow(cam.z, k)}) translate(${-cam.x * k}px, ${-cam.y * k}px)`,
			transformOrigin: '0 0',
		}}
	>
		{children}
	</div>
);

/** cull stations that are far outside the viewport */
export const inView = (cam: Cam, x: number, y: number, hw = 1500, hh = 900) => {
	const vw = (960 / cam.z) * 1.2;
	const vh = (540 / cam.z) * 1.2;
	return Math.abs(cam.x - x) < vw + hw && Math.abs(cam.y - y) < vh + hh;
};

export const Station: React.FC<{id: StationId; cam: Cam; hw?: number; children: React.ReactNode}> = ({id, cam, hw = 1500, children}) => {
	const c = center(id);
	if (!inView(cam, c.x, c.y, hw)) return null;
	return <div style={{position: 'absolute', left: c.x - 960, top: c.y - 540, width: 1920, height: 1080}}>{children}</div>;
};

/* ================================================================ background */
export const Backdrop: React.FC<{cam: Cam; f: number}> = ({cam, f}) => {
	const glows = [
		{x: -400, y: -500, s: 1800, o: 0.22},
		{x: 2400, y: 300, s: 2200, o: 0.18},
		{x: 5600, y: -300, s: 1900, o: 0.2},
		{x: 900, y: 2100, s: 2400, o: 0.16},
		{x: 4300, y: 2600, s: 2000, o: 0.2},
		{x: -600, y: 3000, s: 1800, o: 0.18},
	];
	return (
		<AbsoluteFill style={{background: `radial-gradient(120% 90% at 20% 0%, ${C.bgHi} 0%, ${C.bg} 45%, ${C.bgLo} 100%)`, overflow: 'hidden'}}>
			<Layer cam={cam} k={0.6}>
				<div
					style={{
						position: 'absolute',
						left: -2600,
						top: -1900,
						width: 8400,
						height: 5400,
						backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.22) 2.2px, transparent 2.6px)',
						backgroundSize: '56px 56px',
					}}
				/>
				{glows.map((g, i) => (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: g.x * 0.6 - g.s / 2 + Math.sin(f / 70 + i) * 60,
							top: g.y * 0.6 - g.s / 2 + Math.cos(f / 80 + i) * 40,
							width: g.s,
							height: g.s,
							borderRadius: '50%',
							background: `radial-gradient(closest-side, rgba(255,255,255,${g.o}), rgba(255,255,255,0))`,
						}}
					/>
				))}
			</Layer>
			{/* vignette (screen-space) */}
			<AbsoluteFill style={{background: 'radial-gradient(85% 80% at 50% 50%, transparent 55%, rgba(30,34,120,0.45) 100%)'}} />
		</AbsoluteFill>
	);
};

/* dashed route between stations — revealed when the camera pulls back */
const ORDER: StationId[] = ['intro', 'hero', 'app', 'voice', 'live', 'devices', 'apps', 'roles', 'cta'];
export const Journey: React.FC<{cam: Cam}> = ({cam}) => {
	const o = Math.min(1, Math.max(0, (0.8 - cam.z) / 0.35));
	if (o <= 0) return null;
	const pts = ORDER.map((id) => center(id));
	const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p.x + 1500} ${p.y + 1000}`).join(' ');
	return (
		<svg width={2 * SX + 3000} height={2 * SY + 2000} style={{position: 'absolute', left: -1500, top: -1000, opacity: o}}>
			<path d={d} fill="none" stroke="rgba(255,255,255,0.55)" strokeWidth={14} strokeDasharray="6 44" strokeLinecap="round" />
			{pts.slice(0, -1).map((p, i) => (
				<circle key={i} cx={p.x + 1500} cy={p.y + 1000} r={34} fill="#fff" opacity={0.7} />
			))}
		</svg>
	);
};

/* foreground parallax decor: sparkles + emoji stickers floating between stations */
const STICKERS = ['🎮', '💬', '🔊', '🎉', '✨', '💜', '🎧', '🚀', '🍕', '🏆', '👾', '🎨'];
// stickers + sparkles placed around the midpoint of every camera move, so they sit off-screen while
// the camera holds and zip past in parallax while it travels; plus a scatter for the overview shot
const DECOR = (() => {
	const out: {x: number; y: number; kind: 'sticker' | 'spark'; e: string; s: number; ph: number}[] = [];
	let n = 0;
	const push = (x: number, y: number, kind: 'sticker' | 'spark') => {
		out.push({x, y, kind, e: STICKERS[n % STICKERS.length], s: 0.75 + random(`ds${n}`) * 0.6, ph: random(`dp${n}`) * 100});
		n++;
	};
	for (let i = 1; i < ORDER.length - 1; i++) {
		const a = center(ORDER[i - 1]);
		const b = center(ORDER[i]);
		const mx = (a.x + b.x) / 2;
		const my = (a.y + b.y) / 2;
		const horiz = Math.abs(b.x - a.x) > Math.abs(b.y - a.y);
		const jit = (k: string) => (random(`${k}${i}`) - 0.5) * 160;
		if (horiz) {
			push(mx - 120 + jit('a'), my - 390, 'sticker');
			push(mx + 160 + jit('b'), my + 360, 'sticker');
			push(mx + 40 + jit('c'), my - 120, 'spark');
			push(mx - 200 + jit('d'), my + 120, 'spark');
		} else {
			push(mx - 700, my - 60 + jit('a'), 'sticker');
			push(mx + 680, my + 80 + jit('b'), 'sticker');
			push(mx - 260, my + jit('c'), 'spark');
			push(mx + 300, my - 40 + jit('d'), 'spark');
		}
	}
	for (let i = 0; i < 14; i++) push((random(`ox${i}`) * 3.4 - 0.6) * SX, (random(`oy${i}`) * 3 - 0.5) * SY, 'spark');
	return out;
})();

export const Foreground: React.FC<{cam: Cam; f: number}> = ({cam, f}) => {
	const k = 1.3;
	return (
		<Layer cam={cam} k={k}>
			{DECOR.map((d, i) => {
				const bob = Math.sin((f + d.ph) / 28) * 14;
				if (d.kind === 'sticker')
					return (
						<div
							key={i}
							style={{
								position: 'absolute',
								left: d.x * k - 50,
								top: d.y * k - 50 + bob,
								width: 100 * d.s,
								height: 100 * d.s,
								borderRadius: '50%',
								background: '#fff',
								boxShadow: `0 20px 40px ${C.shadow}`,
								display: 'flex',
								alignItems: 'center',
								justifyContent: 'center',
								transform: `rotate(${Math.sin((f + d.ph) / 40) * 12}deg)`,
							}}
						>
							<Emoji e={d.e} size={52 * d.s} />
						</div>
					);
				return (
					<Sparkle
						key={i}
						size={34 * d.s}
						color="#fff"
						style={{position: 'absolute', left: d.x * k, top: d.y * k + bob, opacity: 0.75, transform: `rotate(${f * 1.2 + d.ph}deg) scale(${0.75 + 0.25 * Math.sin((f + d.ph) / 12)})`}}
					/>
				);
			})}
		</Layer>
	);
};

/* ================================================================ cursor */
export const Cursor: React.FC<{t: number; path: {t: number; x: number; y: number}[]; clicks: number[]}> = ({t, path, clicks}) => {
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
	let ring = 0;
	let ringO = 0;
	for (const c of clicks) {
		if (t >= c - 3 && t <= c + 6) sc = Math.min(sc, t < c ? lerp(1, 0.8, (t - c + 3) / 3) : lerp(0.8, 1, (t - c) / 6));
		if (t >= c && t <= c + 16) {
			ring = (t - c) / 16;
			ringO = 1 - ring;
		}
	}
	return (
		<div style={{position: 'absolute', left: x, top: y, opacity: op, zIndex: 50, pointerEvents: 'none'}}>
			{ringO > 0 && (
				<div
					style={{
						position: 'absolute',
						left: -40 * ring - 6,
						top: -40 * ring - 6,
						width: 80 * ring + 12,
						height: 80 * ring + 12,
						borderRadius: '50%',
						border: '4px solid #fff',
						opacity: ringO,
					}}
				/>
			)}
			<svg width="40" height="52" viewBox="0 0 20 26" style={{transform: `scale(${sc})`, transformOrigin: '0 0', filter: `drop-shadow(0 6px 10px ${C.shadow})`}}>
				<path d="M1 1 L1 20 L6 15.5 L9.5 23.5 L13 22 L9.6 14.2 L16 14.2 Z" fill={C.ink} stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" />
			</svg>
		</div>
	);
};
