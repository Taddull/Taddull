import React from 'react';
import {AbsoluteFill, Easing, random} from 'remotion';
import {Emoji, Sparkle} from './primitives';
import {C, lerp, prog} from './theme';
import {Cam, PERSPECTIVE, SX, SY, StationId, center} from './timeline';

export type {Cam};

/* Supersampling factor: Chrome rasterises perspective-transformed layers at ~1x of their local CSS
 * pixels, so close-ups go soft. Laying content out at 2x (CSS zoom) and scaling it back down by 0.5
 * keeps text and icons crisp up to ~2x camera zoom. */
const SS = 2;

const preserve: React.CSSProperties = {transformStyle: 'preserve-3d'};

/** The 3D camera rig: a perspective viewport and a world root transformed by the inverse camera. */
export const Scene3D: React.FC<{cam: Cam; children: React.ReactNode}> = ({cam, children}) => (
	<AbsoluteFill style={{perspective: PERSPECTIVE, perspectiveOrigin: '50% 50%'}}>
		<div
			style={{
				...preserve,
				position: 'absolute',
				left: 960,
				top: 540,
				width: 0,
				height: 0,
				transformOrigin: '0 0',
				transform: `translateZ(${PERSPECTIVE - cam.d}px) rotateZ(${cam.roll}deg) rotateX(${-cam.pitch}deg) rotateY(${-cam.yaw}deg) translate3d(${-cam.x}px, ${-cam.y}px, ${-cam.z}px)`,
			}}
		>
			{children}
		</div>
	</AbsoluteFill>
);

/** generous visibility test so off-screen stations are skipped */
const inView = (cam: Cam, x: number, y: number) => {
	const vw = ((960 * cam.d) / PERSPECTIVE) * 1.7 + 1600;
	const vh = ((540 * cam.d) / PERSPECTIVE) * 1.7 + 1000;
	return Math.abs(cam.x - x) < vw && Math.abs(cam.y - y) < vh;
};

/** A 1920x1080 station panel on the gallery wall (z = 0), supersampled. Children use local px. */
export const Station: React.FC<{id: StationId; cam: Cam; children: React.ReactNode}> = ({id, cam, children}) => {
	const c = center(id);
	if (!inView(cam, c.x, c.y)) return null;
	return (
		<div style={{...preserve, position: 'absolute', left: c.x - 960, top: c.y - 540, width: 1920, height: 1080, transformOrigin: '0 0', transform: `scale3d(${1 / SS}, ${1 / SS}, ${1 / SS})`}}>
			<div style={{...preserve, position: 'relative', width: 1920, height: 1080, zoom: SS}}>{children}</div>
		</div>
	);
};

/** wrapper that lifts its absolutely-positioned children off the panel by z px */
export const Z: React.FC<{z: number; children: React.ReactNode; style?: React.CSSProperties}> = ({z, children, style}) => (
	<div style={{position: 'absolute', inset: 0, transform: `translateZ(${z}px)`, ...style}}>{children}</div>
);

/* ================================================================ environment */
export const Sky: React.FC = () => (
	<AbsoluteFill style={{background: `radial-gradient(120% 90% at 30% 0%, ${C.bgHi} 0%, ${C.bg} 45%, ${C.bgLo} 100%)`}} />
);

export const Vignette: React.FC = () => (
	<AbsoluteFill style={{background: 'radial-gradient(85% 80% at 50% 50%, transparent 55%, rgba(30,34,120,0.45) 100%)'}} />
);

/* the gallery wall behind the stations and the floor in front of it — dot grids that make every
 * change of camera angle read as real 3D. Laid out small and scaled up to keep raster sizes sane. */
const WALL = {x0: -2600, y0: -1900, w: 10600, h: 6400};
const WALL_Z = -520; // far enough back that tilted devices never intersect it
const FLOOR_Y = 2 * SY + 950;
const dots = (alpha: number, step: number, r: number): React.CSSProperties => ({
	backgroundImage: `radial-gradient(circle, rgba(255,255,255,${alpha}) ${r}px, transparent ${r + 0.6}px)`,
	backgroundSize: `${step}px ${step}px`,
});

export const Environment: React.FC<{f: number}> = ({f}) => {
	const k = 4; // layout at 1/4 then scale x4
	const glows = [
		{x: -300, y: -300, s: 2600, o: 0.2},
		{x: 2600, y: 600, s: 3200, o: 0.16},
		{x: 5200, y: -200, s: 2800, o: 0.18},
		{x: 1200, y: 2600, s: 3200, o: 0.14},
		{x: 4600, y: 2900, s: 2600, o: 0.18},
	];
	return (
		<>
			<div
				style={{
					position: 'absolute',
					left: WALL.x0,
					top: WALL.y0,
					width: WALL.w / k,
					height: WALL.h / k,
					transformOrigin: '0 0',
					transform: `translateZ(${WALL_Z}px) scale(${k})`,
					...dots(0.22, 14, 0.55),
				}}
			>
				{glows.map((g, i) => (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: (g.x - WALL.x0 - g.s / 2) / k + Math.sin(f / 70 + i) * 10,
							top: (g.y - WALL.y0 - g.s / 2) / k + Math.cos(f / 80 + i) * 8,
							width: g.s / k,
							height: g.s / k,
							borderRadius: '50%',
							background: `radial-gradient(closest-side, rgba(255,255,255,${g.o}), rgba(255,255,255,0))`,
						}}
					/>
				))}
			</div>
			<div
				style={{
					position: 'absolute',
					left: WALL.x0,
					top: FLOOR_Y,
					width: WALL.w / k,
					height: 9000 / k,
					transformOrigin: '0 0',
					transform: `translateZ(${WALL_Z}px) rotateX(90deg) scale(${k})`,
					...dots(0.3, 16, 0.7),
					WebkitMaskImage: 'linear-gradient(180deg, #000 0%, rgba(0,0,0,0.6) 40%, transparent 100%)',
					maskImage: 'linear-gradient(180deg, #000 0%, rgba(0,0,0,0.6) 40%, transparent 100%)',
				}}
			/>
		</>
	);
};

/* dashed route between stations on the wall — revealed as the camera pulls back */
const ORDER: StationId[] = ['intro', 'hero', 'app', 'voice', 'live', 'devices', 'apps', 'roles', 'cta'];
export const Journey: React.FC<{cam: Cam}> = ({cam}) => {
	const o = Math.min(1, Math.max(0, (cam.d - 2200) / 2000));
	if (o <= 0) return null;
	const pts = ORDER.map((id) => center(id));
	const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p.x + 1500} ${p.y + 1000}`).join(' ');
	return (
		<svg width={2 * SX + 3000} height={2 * SY + 2000} style={{position: 'absolute', left: -1500, top: -1000, opacity: o, transform: 'translateZ(-480px)'}}>
			<path d={d} fill="none" stroke="rgba(255,255,255,0.55)" strokeWidth={14} strokeDasharray="6 44" strokeLinecap="round" />
			{pts.slice(0, -1).map((p, i) => (
				<circle key={i} cx={p.x + 1500} cy={p.y + 1000} r={34} fill="#fff" opacity={0.7} />
			))}
		</svg>
	);
};

/* stickers + sparkles floating in front of the wall at different depths (real parallax) */
const STICKERS = ['🎮', '💬', '🔊', '🎉', '✨', '💜', '🎧', '🚀', '🍕', '🏆', '👾', '🎨'];
const DECOR = (() => {
	const out: {x: number; y: number; z: number; kind: 'sticker' | 'spark'; e: string; s: number; ph: number}[] = [];
	let n = 0;
	const push = (x: number, y: number, kind: 'sticker' | 'spark') => {
		out.push({x, y, z: 150 + random(`dz${n}`) * 320, kind, e: STICKERS[n % STICKERS.length], s: 0.75 + random(`ds${n}`) * 0.6, ph: random(`dp${n}`) * 100});
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
})();

export const Decor: React.FC<{f: number}> = ({f}) => (
	<>
		{DECOR.map((d, i) => {
			const bob = Math.sin((f + d.ph) / 28) * 14;
			const tf = `translate3d(${d.x}px, ${d.y + bob}px, ${d.z}px)`;
			if (d.kind === 'sticker')
				return (
					<div key={i} style={{position: 'absolute', left: 0, top: 0, transform: `${tf} rotate(${Math.sin((f + d.ph) / 40) * 12}deg)`}}>
						<div
							style={{
								marginLeft: -50 * d.s,
								marginTop: -50 * d.s,
								width: 100 * d.s,
								height: 100 * d.s,
								borderRadius: '50%',
								background: '#fff',
								boxShadow: `0 20px 40px ${C.shadow}`,
								display: 'flex',
								alignItems: 'center',
								justifyContent: 'center',
							}}
						>
							<Emoji e={d.e} size={52 * d.s} />
						</div>
					</div>
				);
			return (
				<div key={i} style={{position: 'absolute', left: 0, top: 0, transform: tf}}>
					<Sparkle size={34 * d.s} color="#fff" style={{opacity: 0.8, transform: `rotate(${f * 1.2 + d.ph}deg) scale(${0.75 + 0.25 * Math.sin((f + d.ph) / 12)})`}} />
				</div>
			);
		})}
	</>
);

/* ================================================================ cursor */
export const Cursor: React.FC<{t: number; path: {t: number; x: number; y: number}[]; clicks: number[]; z?: number}> = ({t, path, clicks, z = 0}) => {
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
		<div style={{position: 'absolute', left: x, top: y, transform: `translateZ(${z}px)`, opacity: op, pointerEvents: 'none'}}>
			{ringO > 0 && (
				<div style={{position: 'absolute', left: -40 * ring - 6, top: -40 * ring - 6, width: 80 * ring + 12, height: 80 * ring + 12, borderRadius: '50%', border: '4px solid #fff', opacity: ringO}} />
			)}
			<svg width="40" height="52" viewBox="0 0 20 26" style={{transform: `scale(${sc})`, transformOrigin: '0 0', filter: `drop-shadow(0 6px 10px ${C.shadow})`}}>
				<path d="M1 1 L1 20 L6 15.5 L9.5 23.5 L13 22 L9.6 14.2 L16 14.2 Z" fill={C.ink} stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" />
			</svg>
		</div>
	);
};
