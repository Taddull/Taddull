import React from 'react';
import {AbsoluteFill, random} from 'remotion';
import {IPhone} from '../discord/devices';
import {Avatar, CLYDE_PATH, Emoji, Icon, Sparkle, USERS, UserKey} from '../discord/primitives';
import {talk} from '../discord/stations';
import {BODY, C as DC, DISPLAY} from '../discord/theme';
import {SERVERS} from '../discord/ui';
import {Scene3D} from '../engine/scene3d';
import {Dust, HEAVY, Letters, Orbits, Sphere} from '../ytfilm/objects';
import {At, DarkBg, World} from '../ytfilm/scenes';
import {Controller3D} from '../ytfilm/objects';
import {easeInOut, lerp, prog, spr} from '../youtube/kit';
import {CAMS, CUE, MOODS, PERSPECTIVE, SCENES} from './film';
import {BADGE_D, Badge3D, Bolt3D, Book3D, CLYDE_IN_BADGE, Palette3D} from './objects';

const BLURPLE = '#5865F2';
const ease3 = (x: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);
// Discord display voice: Archivo (Ginto Nord stand-in), slightly expanded, sentence case
const LINE: React.CSSProperties = {fontFamily: DISPLAY, fontStretch: '112%', fontWeight: 800, letterSpacing: '-0.025em'};
const MOOD_TYPE: React.CSSProperties = {...HEAVY, fontFamily: DISPLAY, fontStretch: '125%', fontWeight: 900, letterSpacing: '-0.01em'};
const BG = {glow: 'rgba(88,101,242,0.22)', glow2: 'rgba(235,69,158,0.10)'};

/* more server identities for the fan, the floaters and the carousel */
const MORE = [
	{e: '🍥', g: ['#FF8A4C', '#EB459E'], name: 'Anime Club'},
	{e: '📖', g: ['#57F287', '#00A8FC'], name: 'Book Nook'},
	{e: '⏱️', g: ['#FEE75C', '#ED4245'], name: 'Speedrunners'},
	{e: '📷', g: ['#9B59B6', '#5865F2'], name: 'Photo Walks'},
];
const ALL = [...SERVERS, ...MORE];

const ServerTile: React.FC<{i: number; size: number; radius?: number; glow?: boolean}> = ({i, size, radius = 0.3, glow}) => {
	const s = ALL[i % ALL.length];
	return (
		<div
			style={{
				width: size,
				height: size,
				borderRadius: size * radius,
				background: `linear-gradient(135deg, ${s.g[0]}, ${s.g[1]})`,
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
				boxShadow: glow ? `0 0 ${size * 0.25}px ${s.g[0]}CC, 0 0 4px ${s.g[0]}` : `0 20px 40px rgba(0,0,0,0.45)`,
				position: 'relative',
				overflow: 'hidden',
			}}
		>
			<div style={{position: 'absolute', inset: 0, background: 'radial-gradient(circle at 30% 22%, rgba(255,255,255,0.45), transparent 45%)'}} />
			<Emoji e={s.e} size={size * 0.52} />
		</div>
	);
};

/* ================================================================ 1. INTRO */
const LINE_RIGHT = 1460;
const LINE_TOP = 470;
const FONT = 118;
export const IntroScene: React.FC<{f: number}> = ({f}) => {
	const I = CUE.intro;
	const dotIn = spr(f, I.dot, {damping: 10, stiffness: 160});
	const rings = prog(f, I.rings, I.rings + 34) * (1 - prog(f, 52, 80));
	const fly = prog(f, 66, I.land, easeInOut);
	const zoom = prog(f, I.out + 4, 150, (x) => x * x);
	const start = {x: 960, y: 430};
	const end = {x: LINE_RIGHT + FONT * 0.13, y: LINE_TOP + FONT * 0.8};
	let x = lerp(start.x, end.x, fly);
	let y = lerp(start.y, end.y, fly) + Math.sin(fly * Math.PI) * -120;
	let size = lerp(46, FONT * 0.2, fly) * dotIn;
	if (f > I.out) {
		x = lerp(end.x, 960, zoom);
		y = lerp(end.y, 540, zoom);
		size = lerp(FONT * 0.2, 2600, zoom);
	}
	const pulse = f >= I.land && f < I.out ? 1 + 0.25 * Math.max(0, Math.sin(((f - I.land) / 15) * Math.PI)) * Math.exp(-(f - I.land) / 20) : 1;
	return (
		<AbsoluteFill style={{background: '#05060F'}}>
			<Dust t={f} opacity={0.6} />
			<div style={{position: 'absolute', left: 960 - 450, top: 430 - 200, opacity: rings}}>
				<Orbits p={ease3(prog(f, I.rings, I.rings + 34))} t={f} color={BLURPLE} />
			</div>
			<div style={{position: 'absolute', right: 1920 - LINE_RIGHT, top: LINE_TOP, whiteSpace: 'nowrap'}}>
				<Letters text="Imagine a place" f={f} start={I.words[0]} step={1.8} out={I.out} size={FONT} style={LINE} />
			</div>
			<div style={{position: 'absolute', left: x - (size * pulse) / 2, top: y - (size * pulse) / 2, width: size * pulse, height: size * pulse, borderRadius: '50%', background: BLURPLE, boxShadow: `0 0 ${30 + zoom * 200}px rgba(88,101,242,0.9)`}} />
		</AbsoluteFill>
	);
};

/* ================================================================ 2. HERO: glossy app badge fanning into server icons */
const FAN = [0, 1, 2, 4, 5, 9];
export const HeroScene: React.FC<{f: number}> = ({f}) => {
	const H = CUE.hero;
	const t = f - SCENES.hero.from;
	return (
		<AbsoluteFill>
			<DarkBg t={f} {...BG} />
			<Scene3D cam={CAMS.hero(f)} perspective={PERSPECTIVE}>
				<World>
					{FAN.map((si, i) => {
						const s = spr(f, H.fan + i * H.fanStep, {damping: 15, stiffness: 90});
						return (
							<At key={i} x={160 + lerp(0, 170 + i * 120, s)} y={lerp(0, -30 - i * 34, s) + Math.sin((t + i * 12) / 30) * 6} z={lerp(-40 - i * 6, -140 - i * 120, s)} ry={lerp(-18, -14 - i * 3, s)} rx={8}>
								<div style={{opacity: Math.min(1, s * 3)}}>
									<ServerTile i={si} size={380} glow />
								</div>
							</At>
						);
					})}
					<At x={160} ry={-18 + Math.sin(t / 40) * 14} rx={10 + Math.sin(t / 50) * 4} rz={-4} y={Math.sin(t / 30) * 10}>
						<Badge3D w={420} sheen={((t / 110) % 1.4) - 0.2} />
					</At>
					<At x={-500} y={20} z={160}>
						<div style={{whiteSpace: 'nowrap'}}>
							<Letters text="Find your people." f={f} start={H.title} out={H.out} size={86} style={LINE} dot={BLURPLE} />
						</div>
					</At>
				</World>
			</Scene3D>
		</AbsoluteFill>
	);
};

/* ================================================================ 3. PHONE: join a voice channel, "Hop in." */
const FLOAT = new Array(18).fill(0).map((_, i) => {
	const side = i % 2 ? 1 : -1;
	const y = (random(`dfy${i}`) - 0.5) * 1250;
	const yy = side < 0 && Math.abs(y - 40) < 260 ? y + Math.sign(y - 40 || 1) * 300 : y;
	return {
		x: 240 + side * (420 + random(`dfx${i}`) * 900),
		y: yy,
		z: -1500 + random(`dfz${i}`) * 1600,
		kind: i % 3,
		size: 130 + random(`dfs${i}`) * 90,
		i,
		ph: random(`dfp${i}`) * 100,
	};
});
const EMOJI = ['🎉', '🔥', '💜', '😂', '👀', '🎮'];
const PEOPLE: UserKey[] = ['nova', 'kai', 'mila', 'luna', 'zed', 'you'];

const MobileVoice: React.FC<{f: number}> = ({f}) => {
	const P = CUE.phone;
	const joined = f >= P.tap;
	const jp = spr(f, P.tap + 4, {damping: 13});
	return (
		<div style={{position: 'absolute', inset: 0, background: '#0E0F12', fontFamily: BODY, color: DC.text, paddingTop: 54, display: 'flex', flexDirection: 'column'}}>
			<div style={{padding: '8px 18px 12px', display: 'flex', alignItems: 'center', gap: 10}}>
				<Icon name="chevron" size={24} color={DC.muted} style={{transform: 'rotate(90deg)'}} />
				<div style={{flex: 1, lineHeight: 1.15}}>
					<div style={{fontWeight: 800, fontSize: 19, display: 'flex', alignItems: 'center', gap: 6}}>
						<Icon name="speaker" size={18} color={DC.muted} /> Lounge
					</div>
					<div style={{fontSize: 13, color: DC.faint}}>Pixel Party · {joined ? 6 : 5} in voice</div>
				</div>
				<Icon name="users" size={22} color={DC.muted} />
			</div>
			<div style={{flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gridAutoRows: '1fr', gap: 8, padding: '0 10px'}}>
				{PEOPLE.map((u, i) => {
					const you = u === 'you';
					const sp = joined && !you ? talk(f - P.tap, i) : 0;
					return (
						<div
							key={u}
							style={{
								borderRadius: 16,
								background: you && !joined ? 'transparent' : `linear-gradient(160deg, ${USERS[u].g[0]}33, #1E1F22 70%)`,
								border: you && !joined ? '2px dashed #3F4147' : undefined,
								boxShadow: sp > 0.05 ? `inset 0 0 0 3px rgba(35,165,90,${sp})` : undefined,
								display: 'flex',
								flexDirection: 'column',
								alignItems: 'center',
								justifyContent: 'center',
								gap: 8,
							}}
						>
							{(!you || joined) && (
								<div style={{transform: `scale(${you ? jp : 1})`, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8}}>
									<Avatar u={u} size={70} speaking={sp} />
									<div style={{fontWeight: 700, fontSize: 14}}>{USERS[u].name}</div>
								</div>
							)}
						</div>
					);
				})}
			</div>
			<div style={{height: 200, background: '#1E1F22', borderRadius: '24px 24px 0 0', marginTop: 10, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12}}>
				{!joined ? (
					<>
						<div style={{fontSize: 14, color: DC.muted}}>nova, kai.exe and 3 others are here</div>
						<div style={{width: 300, height: 56, borderRadius: 28, background: DC.online, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, fontWeight: 800, fontSize: 18}}>
							<Icon name="speaker" size={20} color="#fff" /> Join Voice
						</div>
					</>
				) : (
					<>
						<div style={{fontSize: 15, color: DC.online, fontWeight: 800, opacity: jp}}>● Voice Connected</div>
						<div style={{display: 'flex', gap: 14, transform: `scale(${jp})`}}>
							{(['video', 'mic', 'speaker', 'screen'] as const).map((n) => (
								<div key={n} style={{width: 54, height: 54, borderRadius: 27, background: '#2B2D31', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
									<Icon name={n} size={24} color="#fff" />
								</div>
							))}
							<div style={{width: 54, height: 54, borderRadius: 27, background: DC.dnd, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
								<Icon name="hangup" size={26} color="#fff" />
							</div>
						</div>
					</>
				)}
			</div>
		</div>
	);
};

export const PhoneScene: React.FC<{f: number}> = ({f}) => {
	const P = CUE.phone;
	const t = f - SCENES.phone.from;
	const ring = prog(f, P.ring, P.tap, easeInOut);
	const burst = prog(f, P.tap, P.tap + 24);
	return (
		<AbsoluteFill>
			<DarkBg t={f} glow="rgba(88,101,242,0.2)" glow2="rgba(87,242,135,0.08)" />
			<Scene3D cam={CAMS.phone(f)} perspective={PERSPECTIVE}>
				<World>
					{FLOAT.map((c) => {
						const blur = Math.min(9, Math.abs(c.z) / 170);
						const node =
							c.kind === 0 ? (
								<ServerTile i={c.i} size={c.size} />
							) : c.kind === 1 ? (
								<Avatar u={PEOPLE[c.i % 5]} size={c.size * 0.8} />
							) : (
								<div style={{width: c.size * 0.75, height: c.size * 0.75, borderRadius: '50%', background: '#2B2D31', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 20px 40px rgba(0,0,0,0.45)'}}>
									<Emoji e={EMOJI[c.i % EMOJI.length]} size={c.size * 0.42} />
								</div>
							);
						return (
							<At key={c.i} x={c.x + Math.sin((t + c.ph) / 50) * 20} y={c.y + Math.cos((t + c.ph) / 40) * 16} z={c.z} rx={4}>
								<div style={{filter: blur > 0.6 ? `blur(${blur.toFixed(1)}px)` : undefined, opacity: 0.94}}>{node}</div>
							</At>
						);
					})}
					<At x={240} ry={-12 + Math.sin(t / 50) * 6} rx={4} y={Math.sin(t / 34) * 8}>
						<div style={{position: 'relative'}}>
							<IPhone frame="black">
								<MobileVoice f={f} />
							</IPhone>
							<svg width="427" height="886" style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', transform: 'translateZ(4px)'}}>
								<rect
									x={54 - burst * 18}
									y={717 - burst * 14}
									width={320 + burst * 36}
									height={80 + burst * 28}
									rx={40 + burst * 14}
									fill="none"
									stroke={DC.online}
									strokeWidth={6 - burst * 4}
									pathLength={1}
									strokeDasharray={`${ring} 1`}
									opacity={1 - burst}
									style={{filter: 'drop-shadow(0 0 8px rgba(87,242,135,0.9))'}}
								/>
							</svg>
						</div>
					</At>
					<At x={-430} y={40} z={200}>
						<div style={{whiteSpace: 'nowrap', textShadow: '0 10px 40px rgba(0,0,0,0.6)'}}>
							<Letters text="Hop in." f={f} start={P.title} out={P.out} size={118} style={LINE} dot={DC.online} />
						</div>
					</At>
				</World>
			</Scene3D>
		</AbsoluteFill>
	);
};

/* ================================================================ 4. MOODS */
const OBJ = {x: 1400, y: 560};
const Marquee: React.FC<{word: string; color: string; t: number; y: number; dir: 1 | -1}> = ({word, color, t, y, dir}) => (
	<div style={{position: 'absolute', left: 0, top: y, whiteSpace: 'nowrap', ...MOOD_TYPE, fontSize: 130, color: 'transparent', WebkitTextStroke: `2.5px ${color}`, transform: `translateX(${dir * ((t * 3.2) % 1100) - 1100}px)`}}>
		{`${word.replace('\n', ' ')}  •  `.repeat(7)}
	</div>
);

const MoodObject: React.FC<{id: string; t: number}> = ({id, t}) => {
	const sheen = ((t / 70) % 1.4) - 0.2;
	if (id === 'game')
		return (
			<div style={{position: 'relative', transformStyle: 'preserve-3d'}}>
				<Controller3D w={470} sheen={sheen} color={['#F6FF9A', '#CBEA3C']} side={['#9DB728', '#3E4A08']} />
				<div style={{position: 'absolute', left: 235 - 340, top: 157 - 170, width: 680, height: 340, borderRadius: '50%', border: '12px solid #F2FF7A', boxShadow: '0 0 34px #E9FF5B, inset 0 0 24px #E9FF5B', transform: `rotateX(64deg) rotateZ(${t * 1.5}deg)`}} />
			</div>
		);
	if (id === 'study')
		return (
			<div style={{position: 'relative', transformStyle: 'preserve-3d'}}>
				<div style={{position: 'absolute', left: -110, top: -120, width: 700, height: 560, borderRadius: '50%', background: 'radial-gradient(closest-side, rgba(255,255,255,0.55), transparent)', transform: 'translateZ(-80px)'}} />
				<Book3D w={480} sheen={sheen} />
			</div>
		);
	if (id === 'art') return <Palette3D w={460} sheen={sheen} />;
	return (
		<div style={{position: 'relative', transformStyle: 'preserve-3d'}}>
			<div style={{position: 'absolute', left: -200, top: -100, width: 640, height: 640, borderRadius: '50%', background: 'radial-gradient(closest-side, rgba(255,255,255,0.45), transparent)', transform: 'translateZ(-80px)'}} />
			<Bolt3D w={250} sheen={sheen} />
			{[0, 1, 2, 3].map((i) => (
				<Sparkle key={i} size={[30, 22, 26, 18][i]} color={i % 2 ? '#fff' : '#5865F2'} style={{position: 'absolute', left: [-70, 270, 250, -40][i], top: [40, 20, 330, 360][i], transform: `translateZ(${40 + i * 20}px) scale(${0.6 + 0.4 * Math.sin(t / 8 + i)}) rotate(${t * 2}deg)`}} />
			))}
		</div>
	);
};

export const MoodsScene: React.FC<{f: number}> = ({f}) => (
	<AbsoluteFill>
		{MOODS.map((m, i) => {
			if (f < m.at - 1) return null;
			const t = f - m.at;
			const r = 2400 * easeInOut(prog(f, m.at, m.at + 14, (x) => x));
			const o = i === 0 ? {x: 960, y: 540} : OBJ;
			const lines = m.word.split('\n');
			const s = spr(f, m.at + 6, {damping: 12, stiffness: 120});
			const total = m.word.replace('\n', '').length;
			let k = 0;
			return (
				<AbsoluteFill key={m.id} style={{clipPath: `circle(${r}px at ${o.x}px ${o.y}px)`, background: m.bg}}>
					<AbsoluteFill style={{background: 'radial-gradient(80% 80% at 70% 50%, rgba(255,255,255,0.18), transparent 60%), radial-gradient(120% 100% at 50% 50%, transparent 60%, rgba(0,0,0,0.25) 100%)'}} />
					<Marquee word={m.word} color={m.outline} t={t} y={40} dir={-1} />
					<Marquee word={m.word} color={m.outline} t={t} y={890} dir={1} />
					<div style={{position: 'absolute', left: 140, top: lines.length > 1 ? 250 : 340, display: 'flex', alignItems: 'center', gap: 10, fontFamily: BODY, fontWeight: 800, fontSize: 32, color: m.ink, opacity: prog(f, m.at + 10, m.at + 22)}}>
						<Icon name="hash" size={32} color={m.ink} /> {m.label}
					</div>
					<div style={{position: 'absolute', left: 128, top: lines.length > 1 ? 304 : 392, ...MOOD_TYPE, fontSize: lines.length > 1 ? 190 : 210, color: m.ink}}>
						{lines.map((ln, li) => (
							<div key={li} style={{whiteSpace: 'nowrap'}}>
								{ln.split('').map((ch, ci) => {
									const j = k++;
									const p = ease3((f - m.at - 4 - j * 1.6) / 14);
									return (
										<span key={ci} style={{display: 'inline-block', opacity: p, transform: `translateX(${(1 - p) * (j - total / 2) * 70}px) scale(${lerp(1.35, 1, p)})`}}>
											{ch}
										</span>
									);
								})}
							</div>
						))}
					</div>
					<div style={{position: 'absolute', left: OBJ.x - 300, top: OBJ.y + 250, width: 600, height: 80, borderRadius: '50%', background: 'radial-gradient(closest-side, rgba(0,0,0,0.28), transparent)', transform: `scale(${s})`}} />
					<div style={{position: 'absolute', left: OBJ.x, top: OBJ.y + Math.sin(t / 16) * 12, perspective: 1400}}>
						<div style={{transformStyle: 'preserve-3d', transform: `translate(-50%, -50%) scale(${s}) rotateY(${Math.sin(t / 18) * 26 - 10}deg) rotateX(${8 + Math.sin(t / 25) * 6}deg) rotateZ(${Math.sin(t / 30) * 4}deg)`}}>
							<MoodObject id={m.id} t={t} />
						</div>
					</div>
				</AbsoluteFill>
			);
		})}
	</AbsoluteFill>
);

/* ================================================================ 5. LANDSCAPE */
const COLS = 40;
const ROWS = 16;
const STOPS = ['#5865F2', '#9B59F6', '#EB459E', '#FEE75C', '#57F287'];
const hx = (c: string) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
const brandAt = (u: number, light: number) => {
	const p = Math.min(0.9999, Math.max(0, u)) * (STOPS.length - 1);
	const i = Math.floor(p);
	const a = hx(STOPS[i]);
	const b = hx(STOPS[i + 1]);
	const c = a.map((v, k) => v + (b[k] - v) * (p - i)).map((v) => Math.round(v + (255 - v) * light));
	return `rgb(${c.join(',')})`;
};

const Rolling: React.FC<{value: number; target: number; size: number}> = ({value, target, size}) => {
	const digits = String(target).length;
	const cells: React.ReactNode[] = [];
	for (let p = digits - 1; p >= 0; p--) {
		const d = (value / Math.pow(10, p)) % 10;
		cells.push(
			<span key={p} style={{display: 'inline-block', height: '1em', overflow: 'hidden', verticalAlign: 'top'}}>
				<span style={{display: 'block', transform: `translateY(${-d}em)`}}>
					{[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0].map((n, i) => (
						<span key={i} style={{display: 'block', height: '1em', lineHeight: '1em'}}>
							{n}
						</span>
					))}
				</span>
			</span>,
		);
		if (p > 0 && p % 3 === 0) cells.push(<span key={`c${p}`}>,</span>);
	}
	return (
		<div style={{...LINE, color: '#fff', fontSize: size, lineHeight: '1em', display: 'flex', fontVariantNumeric: 'tabular-nums'}}>
			{cells}
			<span style={{color: BLURPLE}}>+</span>
		</div>
	);
};

export const LandScene: React.FC<{f: number}> = ({f}) => {
	const L = CUE.land;
	const reveal = 2400 * easeInOut(prog(f, SCENES.land.from, SCENES.land.from + 14, (x) => x));
	const TARGET = 200000000;
	const counter = TARGET * ease3(prog(f, L.counter, L.counterTo, (x) => x));
	const cOut = prog(f, L.words[0] - 8, L.words[0]);
	const bars: React.ReactNode[] = [];
	for (let r = ROWS - 1; r >= 0; r--) {
		const grow = r === 0 ? prog(f, L.title - 6, L.title + 14) : prog(f, L.tilt + r * 3, L.tilt + r * 3 + 24);
		if (grow <= 0) continue;
		for (let c = 0; c < COLS; c++) {
			const env = 0.55 + 0.45 * Math.sin((c / (COLS - 1)) * Math.PI);
			const w = 0.5 + 0.5 * Math.sin(c * 0.32 + f * 0.11 + r * 0.55) * (0.6 + 0.4 * Math.sin(r * 0.37 - f * 0.045 + c * 0.05));
			const h = (24 + 260 * w * env) * grow;
			const u = c / (COLS - 1);
			bars.push(
				<div
					key={`${r}-${c}`}
					style={{
						position: 'absolute',
						left: (c - (COLS - 1) / 2) * 40 - 13,
						top: 300 - h,
						width: 26,
						height: h,
						borderRadius: 4,
						transform: `translateZ(${200 - r * 95}px)`,
						background: `linear-gradient(180deg, ${brandAt(u, 0.45 - r * 0.012)}, ${brandAt(u, 0.02)})`,
						opacity: 1 - r * 0.025,
					}}
				/>,
			);
		}
	}
	const word = (text: string, start: number, out: number) => (
		<div style={{position: 'absolute', left: 120, top: 110}}>
			<Letters text={text} f={f} start={start} out={out} size={110} step={1.2} style={LINE} dot={BLURPLE} />
		</div>
	);
	return (
		<AbsoluteFill style={{clipPath: `circle(${reveal}px at ${OBJ.x}px ${OBJ.y}px)`}}>
			<AbsoluteFill style={{background: 'radial-gradient(100% 90% at 50% 70%, #171A33 0%, #0A0B18 55%, #03030A 100%)'}} />
			<div style={{position: 'absolute', left: 300, top: 560, width: 1320, height: 500, background: 'radial-gradient(closest-side, rgba(88,101,242,0.22), transparent)'}} />
			<Scene3D cam={CAMS.land(f)} perspective={PERSPECTIVE}>
				<World>{bars}</World>
			</Scene3D>
			<div style={{position: 'absolute', left: 0, right: 0, top: 170, display: 'flex', justifyContent: 'center'}}>
				<Letters text="For every community." f={f} start={L.title} out={1036} size={96} align="center" style={LINE} dot={BLURPLE} />
			</div>
			{f >= L.counter - 2 && f < L.words[0] + 2 && (
				<div style={{position: 'absolute', left: 120, top: 100, opacity: prog(f, L.counter - 2, L.counter + 8) * (1 - cOut), transform: `translateY(${-cOut * 30}px)`}}>
					<Rolling value={counter} target={TARGET} size={112} />
					<div style={{...LINE, color: '#fff', fontSize: 42, marginTop: 12}}>
						people every month<span style={{color: BLURPLE}}>.</span>
					</div>
				</div>
			)}
			{word('Voice.', L.words[0], L.words[1] - 6)}
			{word('Video.', L.words[1], L.words[2] - 6)}
			{word('Streams.', L.words[2], L.all - 6)}
			{word('All in one place.', L.all, 1278)}
		</AbsoluteFill>
	);
};

/* ================================================================ 6. CAROUSEL: server cards, "Your place to talk." */
export const CarouselScene: React.FC<{f: number}> = ({f}) => {
	const C = CUE.carousel;
	const t = f - SCENES.carousel.from;
	const cp = prog(f, C.collapse, C.collapse + 45, (x) => x * x);
	const R = 1000 * (1 - cp);
	const base = t * 0.45 + cp * cp * 140;
	const sphere = spr(f, C.collapse + 15, {damping: 14, stiffness: 120});
	return (
		<AbsoluteFill>
			<DarkBg t={f} glow="rgba(88,101,242,0.16)" glow2="rgba(235,69,158,0.08)" />
			<Scene3D cam={CAMS.carousel(f)} perspective={PERSPECTIVE}>
				<World>
					{ALL.map((sv, i) => {
						const a = ((base + i * 30) * Math.PI) / 180;
						const x = Math.sin(a) * R;
						const z = Math.cos(a) * R - R * 0.35;
						const back = Math.max(0, (R * 0.65 - z) / (R * 1.6 + 1));
						const online = 120 + ((i * 397) % 1900);
						return (
							<At key={i} x={x} y={90} z={z} ry={-Math.sin(a) * 22}>
								<div style={{width: 340, borderRadius: 18, overflow: 'hidden', background: '#232428', boxShadow: '0 30px 60px rgba(0,0,0,0.6)', opacity: 1 - cp, transform: `scale(${1 - cp * 0.6})`, position: 'relative', fontFamily: BODY}}>
									<div style={{height: 110, background: `linear-gradient(120deg, ${sv.g[0]}, ${sv.g[1]})`}} />
									<div style={{padding: '0 18px 18px', marginTop: -38}}>
										<div style={{width: 76, height: 76, borderRadius: 22, border: '5px solid #232428', background: `linear-gradient(135deg, ${sv.g[0]}, ${sv.g[1]})`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
											<Emoji e={sv.e} size={38} />
										</div>
										<div style={{color: '#fff', fontWeight: 800, fontSize: 24, marginTop: 8}}>{sv.name}</div>
										<div style={{display: 'flex', gap: 14, color: '#B5BAC1', fontSize: 16, marginTop: 4}}>
											<span>
												<span style={{color: DC.online}}>●</span> {online.toLocaleString('en-US')} online
											</span>
										</div>
									</div>
									<div style={{position: 'absolute', inset: 0, background: `rgba(0,0,0,${(back * 0.6).toFixed(3)})`}} />
								</div>
							</At>
						);
					})}
					<At>
						<Sphere size={340 * sphere} base="#7983F5" dark="#3A44B0" glow="rgba(88,101,242,0.6)" t={t} />
					</At>
					<At y={-430} z={320}>
						<div style={{whiteSpace: 'nowrap', textShadow: '0 0 24px rgba(255,255,255,0.65), 0 0 60px rgba(255,255,255,0.3)'}}>
							<Letters text="Your place to talk." f={f} start={C.title} out={C.collapse - 10} size={112} align="center" style={LINE} dot={BLURPLE} />
						</div>
					</At>
				</World>
			</Scene3D>
		</AbsoluteFill>
	);
};

/* ================================================================ 7. LOGO */
export const LogoScene: React.FC<{f: number}> = ({f}) => {
	const G = CUE.logo;
	const t = f - SCENES.logo.from;
	const flat = prog(f, G.flatten, G.flatten + 16, easeInOut);
	const clyde = spr(f, G.clyde, {damping: 11, stiffness: 180});
	const slide = prog(f, G.wordmark, G.wordmark + 24, easeInOut);
	const iconW = 230;
	const iconX = lerp(960, 450, slide);
	const iconY = lerp(540, 450, prog(f, G.flatten, G.wordmark + 24, easeInOut));
	const btn = spr(f, G.button, {damping: 12, stiffness: 160});
	return (
		<AbsoluteFill>
			<DarkBg t={f} glow="rgba(88,101,242,0.22)" glow2="rgba(235,69,158,0.08)" />
			<div style={{position: 'absolute', left: iconX - 600, top: iconY - 400, width: 1200, height: 800, background: `radial-gradient(closest-side, rgba(88,101,242,${0.26 + 0.08 * Math.sin(t / 20)}), transparent)`}} />
			<div style={{position: 'absolute', left: iconX - 160, top: iconY - 160, opacity: 1 - flat, transform: `scale(${lerp(1, 1.06, flat)}) scaleY(${lerp(1, 0.85, flat)})`}}>
				<Sphere size={320} base="#7983F5" dark="#3A44B0" glow="rgba(88,101,242,0.55)" t={t} />
			</div>
			<svg width={iconW} height={iconW} viewBox="0 0 24 24" style={{position: 'absolute', left: iconX - iconW / 2, top: iconY - iconW / 2, opacity: flat, transform: `scale(${lerp(0.85, 1, flat)})`, overflow: 'visible', filter: 'drop-shadow(0 20px 40px rgba(88,101,242,0.55))'}}>
				<path d={BADGE_D} fill={BLURPLE} />
				<g style={{transform: `scale(${clyde})`, transformOrigin: '12px 12px'}}>
					<path d={CLYDE_PATH} fill="#fff" transform={CLYDE_IN_BADGE} />
				</g>
			</svg>
			<div style={{position: 'absolute', left: 605, top: iconY - 100, height: 200, display: 'flex', alignItems: 'center', clipPath: `inset(-20% ${(1 - slide) * 100}% -20% 0)`}}>
				<span style={{fontFamily: DISPLAY, fontStretch: '125%', fontWeight: 900, fontSize: 168, color: '#fff', letterSpacing: `${lerp(0.25, -0.01, slide)}em`, opacity: slide}}>DISCORD</span>
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, top: 640, display: 'flex', justifyContent: 'center'}}>
				<Letters text="Group chat that's all fun & games." f={f} start={G.tagline} size={40} step={0.7} align="center" style={{fontFamily: BODY, fontWeight: 700, color: '#D6D8F2', letterSpacing: '-0.005em'}} dot={BLURPLE} />
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, top: 740, display: 'flex', justifyContent: 'center'}}>
				<div style={{position: 'relative', overflow: 'hidden', padding: '22px 52px', borderRadius: 999, background: BLURPLE, color: '#fff', fontFamily: BODY, fontWeight: 800, fontSize: 24, letterSpacing: '0.14em', transform: `scale(${btn})`, boxShadow: '0 16px 50px rgba(88,101,242,0.55)'}}>
					OPEN DISCORD
					<div style={{position: 'absolute', top: 0, bottom: 0, width: 80, left: `${-30 + ((t * 2.2) % 160)}%`, background: 'linear-gradient(100deg, transparent, rgba(255,255,255,0.35), transparent)'}} />
				</div>
			</div>
		</AbsoluteFill>
	);
};
