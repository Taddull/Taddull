import React from 'react';
import {random} from 'remotion';
import {YDISPLAY} from '../youtube/theme';

/* ---------------------------------------------------------------- colour helpers */
const hex = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
export const mix = (a: string, b: string, t: number) => {
	const A = hex(a);
	const B = hex(b);
	return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(',')})`;
};

/* ---------------------------------------------------------------- extruded glossy shape
 * A filled SVG path repeated in `layers` slices along -Z inside a preserve-3d box: when the
 * object turns, the slices read as a solid, lit extrusion. The front face carries a gradient,
 * a soft specular bloom and a moving sheen; `inlay` sits slightly proud of the front face. */
export const Extrude: React.FC<{
	id: string;
	w: number;
	h: number;
	viewBox: string;
	d: string;
	depth: number;
	layers?: number;
	front: [string, string];
	side: [string, string];
	sheen?: number; // 0..1 position of the sweeping highlight
	inlay?: React.ReactNode; // extra SVG drawn on the front face (same viewBox)
	inlayDepth?: number;
	evenodd?: boolean;
	style?: React.CSSProperties;
}> = ({id, w, h, viewBox, d, depth, layers = 22, front, side, sheen = 0.3, inlay, inlayDepth = 0, evenodd, style}) => {
	const rule = evenodd ? 'evenodd' : 'nonzero';
	const slices = [];
	for (let i = layers; i >= 1; i--) {
		const t = i / layers;
		slices.push(
			<svg key={i} width={w} height={h} viewBox={viewBox} style={{position: 'absolute', left: 0, top: 0, transform: `translateZ(${-depth * t}px)`, overflow: 'visible'}}>
				<path d={d} fill={mix(side[0], side[1], t)} fillRule={rule} />
			</svg>,
		);
	}
	return (
		<div style={{position: 'relative', width: w, height: h, transformStyle: 'preserve-3d', ...style}}>
			{slices}
			<svg width={w} height={h} viewBox={viewBox} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
				<defs>
					<linearGradient id={`${id}f`} x1="0" y1="0" x2="0.3" y2="1">
						<stop offset="0" stopColor={front[0]} />
						<stop offset="1" stopColor={front[1]} />
					</linearGradient>
					<radialGradient id={`${id}s`} cx="0.3" cy="0.22" r="0.55">
						<stop offset="0" stopColor="rgba(255,255,255,0.75)" />
						<stop offset="0.35" stopColor="rgba(255,255,255,0.18)" />
						<stop offset="1" stopColor="rgba(255,255,255,0)" />
					</radialGradient>
					<linearGradient id={`${id}h`} x1="0" y1="0" x2="1" y2="0.35">
						<stop offset={Math.max(0, sheen - 0.12)} stopColor="rgba(255,255,255,0)" />
						<stop offset={sheen} stopColor="rgba(255,255,255,0.32)" />
						<stop offset={Math.min(1, sheen + 0.12)} stopColor="rgba(255,255,255,0)" />
					</linearGradient>
				</defs>
				<path d={d} fill={`url(#${id}f)`} fillRule={rule} />
				<path d={d} fill={`url(#${id}s)`} fillRule={rule} />
				<path d={d} fill={`url(#${id}h)`} fillRule={rule} />
			</svg>
			{inlay && (
				<svg width={w} height={h} viewBox={viewBox} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', transform: `translateZ(${inlayDepth}px)`}}>
					{inlay}
				</svg>
			)}
		</div>
	);
};

/* ---------------------------------------------------------------- the objects */
export const PLAY_D =
	'M27.4 3.1A3.5 3.5 0 0 0 24.9.6C22.7 0 14 0 14 0S5.3 0 3.1.6A3.5 3.5 0 0 0 .6 3.1C0 5.3 0 10 0 10s0 4.7.6 6.9a3.5 3.5 0 0 0 2.5 2.5C5.3 20 14 20 14 20s8.7 0 10.9-.6a3.5 3.5 0 0 0 2.5-2.5C28 14.7 28 10 28 10s0-4.7-.6-6.9z';
export const TRI_D = 'M11.2 14.3 18.5 10l-7.3-4.3z';

export const PlayButton3D: React.FC<{w: number; sheen: number; tri?: number}> = ({w, sheen, tri = 1}) => (
	<Extrude
		id="pb"
		w={w}
		h={(w * 20) / 28}
		viewBox="0 0 28 20"
		d={PLAY_D}
		depth={w * 0.14}
		layers={26}
		front={['#FF3B30', '#D60000']}
		side={['#B00000', '#3A0000']}
		sheen={sheen}
		inlayDepth={w * 0.012}
		inlay={
			<g style={{transform: `scale(${tri})`, transformOrigin: '14.6px 10px'}}>
				<path d={TRI_D} fill="#fff" />
				<path d={TRI_D} fill="rgba(0,0,0,0.08)" transform="translate(0.35 0.35)" />
			</g>
		}
	/>
);

const CONTROLLER_D =
	'M30 10 H90 C105 10 112 20 116 36 L120 56 C122 70 110 78 100 70 L88 58 H32 L20 70 C10 78 -2 70 0 56 L4 36 C8 20 15 10 30 10 Z';
export const Controller3D: React.FC<{w: number; sheen: number; color: [string, string]; side: [string, string]}> = ({w, sheen, color, side}) => (
	<Extrude
		id="ctl"
		w={w}
		h={(w * 80) / 120}
		viewBox="0 0 120 80"
		d={CONTROLLER_D}
		depth={w * 0.16}
		front={color}
		side={side}
		sheen={sheen}
		inlayDepth={3}
		inlay={
			<g fill="rgba(31,20,120,0.75)">
				<rect x="26" y="26" width="8" height="22" rx="2" />
				<rect x="19" y="33" width="22" height="8" rx="2" />
				<circle cx="88" cy="27" r="4.5" />
				<circle cx="98" cy="37" r="4.5" />
				<circle cx="78" cy="37" r="4.5" />
				<circle cx="88" cy="47" r="4.5" />
			</g>
		}
	/>
);

const NOTE_D = 'M40 6 L92 0 V62 A15 13 0 1 1 80 50 V24 L52 28 V70 A15 13 0 1 1 40 58 Z';
export const Note3D: React.FC<{w: number; sheen: number}> = ({w, sheen}) => (
	<Extrude id="note" w={w} h={(w * 90) / 100} viewBox="0 0 100 90" d={NOTE_D} depth={w * 0.14} front={['#8C6BFF', '#4F2BE0']} side={['#3B1FB0', '#14084A']} sheen={sheen} />
);

const BULB_D =
	'M40 4 A36 36 0 0 1 64 67 C58 73 56 78 56 84 H24 C24 78 22 73 16 67 A36 36 0 0 1 40 4 Z M25 89 H55 A4 4 0 0 1 55 97 H25 A4 4 0 0 1 25 89 Z M28 101 H52 A4 4 0 0 1 52 109 H28 A4 4 0 0 1 28 101 Z';
export const Bulb3D: React.FC<{w: number; sheen: number}> = ({w, sheen}) => (
	<Extrude
		id="bulb"
		w={w}
		h={(w * 110) / 80}
		viewBox="0 0 80 110"
		d={BULB_D}
		depth={w * 0.2}
		front={['#4148B8', '#1F2366']}
		side={['#1A1D5A', '#07081F']}
		sheen={sheen}
		inlayDepth={2}
		inlay={<path d="M31 62 V52 Q31 44 36 46 Q40 48 40 54 Q40 48 44 46 Q49 44 49 52 V62" fill="none" stroke="#FFE36B" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" style={{filter: 'drop-shadow(0 0 2px #FFE36B)'}} />}
	/>
);

/* crescent: outer circle (50,50,r50) minus inner circle (70,38,r44), built from the two arcs */
const crescent = () => {
	const [x1, y1, r1, x2, y2, r2] = [50, 50, 50, 70, 38, 44];
	const dx = x2 - x1;
	const dy = y2 - y1;
	const d = Math.hypot(dx, dy);
	const a = (r1 * r1 - r2 * r2 + d * d) / (2 * d);
	const hh = Math.sqrt(r1 * r1 - a * a);
	const xm = x1 + (a * dx) / d;
	const ym = y1 + (a * dy) / d;
	const p1 = [xm + (hh * dy) / d, ym - (hh * dx) / d];
	const p2 = [xm - (hh * dy) / d, ym + (hh * dx) / d];
	return `M${p1[0].toFixed(2)} ${p1[1].toFixed(2)} A${r1} ${r1} 0 1 0 ${p2[0].toFixed(2)} ${p2[1].toFixed(2)} A${r2} ${r2} 0 0 1 ${p1[0].toFixed(2)} ${p1[1].toFixed(2)} Z`;
};
const MOON_D = crescent();
export const Moon3D: React.FC<{w: number; sheen: number}> = ({w, sheen}) => (
	<Extrude id="moon" w={w} h={w} viewBox="0 0 100 100" d={MOON_D} depth={w * 0.16} front={['#FFF0A8', '#FFC94A']} side={['#E0A233', '#5A3A08']} sheen={sheen} />
);

/* glossy sphere (shading is view-independent, so it is just layered radial gradients) */
export const Sphere: React.FC<{size: number; base: string; dark: string; glow?: string; t?: number; style?: React.CSSProperties}> = ({size, base, dark, glow, t = 0, style}) => (
	<div
		style={{
			position: 'relative',
			width: size,
			height: size,
			borderRadius: '50%',
			background: `radial-gradient(circle at ${34 + Math.sin(t / 40) * 3}% ${28 + Math.cos(t / 50) * 3}%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.35) 9%, ${base} 32%, ${dark} 78%, ${mix(dark, '#000000', 0.5)} 100%)`,
			boxShadow: glow ? `0 0 ${size * 0.5}px ${glow}, inset -${size * 0.06}px -${size * 0.08}px ${size * 0.2}px rgba(0,0,0,0.35)` : undefined,
			...style,
		}}
	>
		<div style={{position: 'absolute', left: '58%', top: '62%', width: '20%', height: '12%', borderRadius: '50%', background: 'radial-gradient(closest-side, rgba(255,255,255,0.35), transparent)'}} />
	</div>
);

/* wobbling glossy blob */
export const Blob: React.FC<{size: number; t: number; base: string; dark: string}> = ({size, t, base, dark}) => {
	const pts = new Array(64).fill(0).map((_, i) => {
		const a = (i / 64) * Math.PI * 2;
		const r = 46 * (1 + 0.07 * Math.sin(3 * a + t / 14) + 0.05 * Math.sin(5 * a - t / 11) + 0.03 * Math.sin(2 * a + t / 9));
		return [50 + Math.cos(a) * r, 50 + Math.sin(a) * r];
	});
	const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(' ') + 'Z';
	return (
		<svg width={size} height={size} viewBox="0 0 100 100" style={{overflow: 'visible'}}>
			<defs>
				<radialGradient id="blobg" cx="0.34" cy="0.3" r="0.75">
					<stop offset="0" stopColor="#FFFFFF" stopOpacity="0.9" />
					<stop offset="0.12" stopColor={base} />
					<stop offset="0.7" stopColor={dark} />
					<stop offset="1" stopColor="#05061A" />
				</radialGradient>
			</defs>
			<path d={d} fill="url(#blobg)" />
			<ellipse cx="66" cy="70" rx="9" ry="5" fill="rgba(255,255,255,0.18)" />
		</svg>
	);
};

/* thin orbit rings around the intro dot */
export const Orbits: React.FC<{p: number; t: number; color: string}> = ({p, t, color}) => (
	<svg width="900" height="400" viewBox="-450 -200 900 400" style={{overflow: 'visible'}}>
		<circle r={70 * p} fill="none" stroke={color} strokeOpacity={0.7} strokeWidth={2.5} />
		<circle r={128 * p} fill="none" stroke={color} strokeOpacity={0.3} strokeWidth={2} />
		<ellipse rx={300 * p} ry={62 * p} fill="none" stroke={color} strokeOpacity={0.55} strokeWidth={2} transform={`rotate(${-4 + Math.sin(t / 30) * 2})`} />
		<ellipse rx={380 * p} ry={86 * p} fill="none" stroke={color} strokeOpacity={0.25} strokeWidth={1.5} transform={`rotate(${6 + Math.cos(t / 34) * 2})`} />
	</svg>
);

/* drifting dust motes (screen space) */
const MOTES = new Array(70).fill(0).map((_, i) => ({x: random(`mx${i}`) * 1920, y: random(`my${i}`) * 1080, s: 1 + random(`ms${i}`) * 2.6, v: 0.15 + random(`mv${i}`) * 0.5, ph: random(`mp${i}`) * 6.28}));
export const Dust: React.FC<{t: number; color?: string; opacity?: number}> = ({t, color = '#fff', opacity = 1}) => (
	<>
		{MOTES.map((m, i) => (
			<div
				key={i}
				style={{
					position: 'absolute',
					left: (m.x + t * m.v * 2) % 1920,
					top: (m.y - t * m.v + 1080) % 1080,
					width: m.s,
					height: m.s,
					borderRadius: '50%',
					background: color,
					opacity: opacity * (0.25 + 0.35 * (0.5 + 0.5 * Math.sin(t / 20 + m.ph))),
				}}
			/>
		))}
	</>
);

/* ---------------------------------------------------------------- typography */
export const SENT: React.CSSProperties = {fontFamily: YDISPLAY, fontWeight: 800, fontStretch: '100%', letterSpacing: '-0.035em', lineHeight: 1.04, color: '#fff'};
export const HEAVY: React.CSSProperties = {fontFamily: YDISPLAY, fontWeight: 1000, fontStretch: '100%', letterSpacing: '-0.03em', lineHeight: 0.9, textTransform: 'uppercase'};

/** letters drop in one by one (and can fall away); a trailing "." becomes a red dot */
export const Letters: React.FC<{
	text: string;
	f: number;
	start: number;
	step?: number;
	out?: number;
	size: number;
	style?: React.CSSProperties;
	dot?: string;
	align?: 'left' | 'center';
}> = ({text, f, start, step = 1.6, out, size, style, dot = '#FF0000', align = 'left'}) => {
	const lines = text.split('\n');
	let k = 0;
	const ease = (x: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);
	return (
		<div style={{...SENT, fontSize: size, textAlign: align, ...style}}>
			{lines.map((ln, li) => (
				<div key={li} style={{whiteSpace: 'pre'}}>
					{ln.split('').map((ch, ci) => {
						const i = k++;
						const p = ease((f - start - i * step) / 12);
						const o = out === undefined ? 0 : ease((f - out - i * 0.8) / 12);
						const isDot = ch === '.' && ci === ln.length - 1;
						const y = (1 - p) * -0.45 + o * 0.6;
						return (
							<span
								key={ci}
								style={{
									display: 'inline-block',
									opacity: p * (1 - o),
									transform: `translateY(${y}em) rotate(${(1 - p) * -8 + o * 10}deg)`,
									transformOrigin: '50% 100%',
								}}
							>
								{isDot ? <span style={{display: 'inline-block', width: '0.2em', height: '0.2em', borderRadius: '50%', background: dot, marginLeft: '0.04em', boxShadow: `0 0 0.3em ${dot}`}} /> : ch}
							</span>
						);
					})}
				</div>
			))}
		</div>
	);
};
