import React from 'react';
import {AbsoluteFill, interpolate, random} from 'remotion';
import {IPhone} from '../discord/devices';
import {Scene3D} from '../engine/scene3d';
import {CH, ChAvatar, Icon, IcelandScene, Sparkle, Thumb, VIDEOS, clamp, easeInOut, lerp, prog, spr} from '../youtube/kit';
import {Y, YBODY} from '../youtube/theme';
import {CAMS, CUE, MOODS, MOOD_LEN, PERSPECTIVE, SCENES} from './film';
import {Blob, Bulb3D, Controller3D, Dust, HEAVY, Letters, Moon3D, Note3D, Orbits, PLAY_D, PlayButton3D, SENT, Sphere, TRI_D} from './objects';

const RED = '#FF0000';
const ease3 = (x: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);

/* supersampled 3D world root (see engine/scene3d StationFrame for why) + a positioned node */
export const World: React.FC<{children: React.ReactNode}> = ({children}) => (
	<div style={{position: 'absolute', left: 0, top: 0, transformStyle: 'preserve-3d', transformOrigin: '0 0', transform: 'scale3d(0.5,0.5,0.5)'}}>
		<div style={{position: 'relative', width: 0, height: 0, zoom: 2, transformStyle: 'preserve-3d'}}>{children}</div>
	</div>
);
export const At: React.FC<{x?: number; y?: number; z?: number; rx?: number; ry?: number; rz?: number; s?: number; children: React.ReactNode; style?: React.CSSProperties}> = ({
	x = 0,
	y = 0,
	z = 0,
	rx = 0,
	ry = 0,
	rz = 0,
	s = 1,
	children,
	style,
}) => (
	<div style={{position: 'absolute', left: x, top: y, transformStyle: 'preserve-3d', transform: `translateZ(${z}px) rotateY(${ry}deg) rotateX(${rx}deg) rotateZ(${rz}deg) scale(${s})`, ...style}}>
		<div style={{position: 'absolute', left: 0, top: 0, transformStyle: 'preserve-3d', transform: 'translate(-50%, -50%)'}}>{children}</div>
	</div>
);

export const DarkBg: React.FC<{t: number; glow?: string; glow2?: string}> = ({t, glow = 'rgba(255,0,0,0.16)', glow2 = 'rgba(120,40,255,0.10)'}) => (
	<AbsoluteFill style={{background: 'radial-gradient(100% 90% at 50% 45%, #151010 0%, #0A0A0A 55%, #030303 100%)'}}>
		<div style={{position: 'absolute', left: 300 + Math.sin(t / 60) * 80, top: 120, width: 1300, height: 900, background: `radial-gradient(closest-side, ${glow}, transparent)`}} />
		<div style={{position: 'absolute', right: -200 + Math.cos(t / 70) * 60, bottom: -300, width: 1200, height: 900, background: `radial-gradient(closest-side, ${glow2}, transparent)`}} />
		<Dust t={t} />
	</AbsoluteFill>
);

/* ================================================================ 1. INTRO: dot in orbit -> "Every idea has an audience." */
const LINE_RIGHT = 1676; // the line is right-aligned here so the flying dot always lands as its full stop
const LINE_TOP = 470;
const FONT = 104;
export const IntroScene: React.FC<{f: number}> = ({f}) => {
	const I = CUE.intro;
	const dotIn = spr(f, I.dot, {damping: 10, stiffness: 160});
	const rings = prog(f, I.rings, I.rings + 34) * (1 - prog(f, 52, 80));
	const fly = prog(f, 66, I.land, easeInOut);
	const zoom = prog(f, I.out + 4, 150, (x) => x * x);
	const start = {x: 960, y: 430};
	const end = {x: LINE_RIGHT + FONT * 0.12, y: LINE_TOP + FONT * 0.76};
	const arc = Math.sin(fly * Math.PI) * -120;
	let x = lerp(start.x, end.x, fly);
	let y = lerp(start.y, end.y, fly) + arc;
	let size = lerp(46, FONT * 0.2, fly) * dotIn;
	if (f > I.out) {
		x = lerp(end.x, 960, zoom);
		y = lerp(end.y, 540, zoom);
		size = lerp(FONT * 0.2, 2600, zoom);
	}
	const pulse = f >= I.land && f < I.out ? 1 + 0.25 * Math.max(0, Math.sin(((f - I.land) / 15) * Math.PI)) * Math.exp(-(f - I.land) / 20) : 1;
	return (
		<AbsoluteFill style={{background: '#050505'}}>
			<Dust t={f} opacity={0.6} />
			<div style={{position: 'absolute', left: 960 - 450, top: 430 - 200, opacity: rings}}>
				<Orbits p={ease3(prog(f, I.rings, I.rings + 34))} t={f} color={RED} />
			</div>
			<div style={{position: 'absolute', right: 1920 - LINE_RIGHT, top: LINE_TOP, whiteSpace: 'nowrap'}}>
				<Letters text="Every idea has an audience" f={f} start={I.words[0]} step={1.4} out={I.out} size={FONT} />
			</div>
			<div
				style={{
					position: 'absolute',
					left: x - (size * pulse) / 2,
					top: y - (size * pulse) / 2,
					width: size * pulse,
					height: size * pulse,
					borderRadius: '50%',
					background: RED,
					boxShadow: `0 0 ${30 + zoom * 200}px rgba(255,0,0,0.8)`,
				}}
			/>
		</AbsoluteFill>
	);
};

/* ================================================================ 2. HERO: glossy 3D play button fanning into thumbnails */
const FAN = [0, 6, 2, 7, 3, 1];
export const HeroScene: React.FC<{f: number}> = ({f}) => {
	const H = CUE.hero;
	const t = f - SCENES.hero.from;
	const cam = CAMS.hero(f);
	return (
		<AbsoluteFill>
			<DarkBg t={f} />
			<Scene3D cam={cam} perspective={PERSPECTIVE}>
				<World>
					{FAN.map((vi, i) => {
						const s = spr(f, H.fan + i * H.fanStep, {damping: 15, stiffness: 90});
						const v = VIDEOS[vi];
						const n = FAN.length - i;
						return (
							<At key={i} x={160 + lerp(0, 150 + i * 120, s)} y={lerp(0, -30 - i * 34, s) + Math.sin((t + i * 12) / 30) * 6} z={lerp(-40 - i * 6, -140 - i * 120, s)} ry={lerp(-18, -14 - i * 3, s)} rx={8}>
								<div style={{width: 460, borderRadius: 18, boxShadow: `0 0 ${40 + n * 6}px ${v.bg[0]}AA, 0 0 6px ${v.bg[0]}`, opacity: Math.min(1, s * 3)}}>
									<Thumb v={v} radius={18} style={{width: 460}} />
								</div>
							</At>
						);
					})}
					<At x={160} ry={-18 + Math.sin(t / 40) * 14} rx={10 + Math.sin(t / 50) * 4} rz={-4} y={Math.sin(t / 30) * 10}>
						<PlayButton3D w={480} sheen={((t / 110) % 1.4) - 0.2} />
					</At>
					<At x={-500} y={20} z={160}>
						<div style={{whiteSpace: 'nowrap'}}>
							<Letters text="Find your thing." f={f} start={H.title} out={H.out} size={92} />
						</div>
					</At>
				</World>
			</Scene3D>
		</AbsoluteFill>
	);
};

/* ================================================================ 3. PHONE: watch page among floating thumbnails, "Press play." */
// floating thumbnails stay behind the "Press play." line (z < 120) and out of its band on the left
const FLOAT = new Array(16).fill(0).map((_, i) => {
	const side = i % 2 ? 1 : -1;
	const y = (random(`fy${i}`) - 0.5) * 1250;
	const yy = side < 0 && Math.abs(y - 40) < 260 ? y + Math.sign(y - 40 || 1) * 300 : y;
	return {
		x: 240 + side * (420 + random(`fx${i}`) * 900),
		y: yy,
		z: -1500 + random(`fz${i}`) * 1600,
		w: 280 + random(`fw${i}`) * 120,
		ry: side * -(10 + random(`fr${i}`) * 25),
		v: i % VIDEOS.length,
		ph: random(`fp${i}`) * 100,
	};
});

const MobileWatch: React.FC<{f: number}> = ({f}) => {
	const P = CUE.phone;
	const playing = f >= P.tap;
	const tapP = prog(f, P.tap, P.tap + 18);
	const v = VIDEOS[4];
	return (
		<div style={{position: 'absolute', inset: 0, background: Y.ui, fontFamily: YBODY, color: Y.text, paddingTop: 54}}>
			<div style={{position: 'relative', width: '100%', aspectRatio: '16 / 9', overflow: 'hidden'}}>
				<IcelandScene f={playing ? f - P.tap + 200 : 200} />
				<div style={{position: 'absolute', inset: 0, background: `rgba(0,0,0,${0.35 * (1 - tapP)})`}} />
				<div
					style={{
						position: 'absolute',
						left: '50%',
						top: '50%',
						width: 76,
						height: 76,
						marginLeft: -38,
						marginTop: -38,
						borderRadius: 38,
						background: 'rgba(0,0,0,0.55)',
						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',
						transform: `scale(${playing ? 1 + 0.2 * Math.sin(Math.min(1, tapP * 2) * Math.PI) : 1})`,
						opacity: playing ? 1 - prog(f, P.tap + 14, P.tap + 30) : 1,
					}}
				>
					<Icon name={playing ? 'pause' : 'play'} size={34} color="#fff" />
				</div>
				<div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 3, background: 'rgba(255,255,255,0.3)'}}>
					<div style={{width: `${(playing ? 8 + (f - P.tap) * 0.05 : 8).toFixed(2)}%`, height: '100%', background: RED}} />
				</div>
			</div>
			<div style={{padding: '12px 14px'}}>
				<div style={{fontSize: 17, fontWeight: 700, lineHeight: 1.3}}>{v.title}</div>
				<div style={{fontSize: 12, color: Y.text2, marginTop: 4}}>3.6M views · 1mo · #iceland</div>
				<div style={{display: 'flex', alignItems: 'center', gap: 10, marginTop: 12}}>
					<ChAvatar c="wander" size={34} />
					<div style={{flex: 1, lineHeight: 1.2}}>
						<div style={{fontSize: 14, fontWeight: 500}}>{CH.wander.name}</div>
						<div style={{fontSize: 11, color: Y.text2}}>3.2M subscribers</div>
					</div>
					<div style={{background: '#fff', color: Y.ui, borderRadius: 16, padding: '7px 13px', fontSize: 13, fontWeight: 700}}>Subscribe</div>
				</div>
				<div style={{display: 'flex', gap: 8, marginTop: 14}}>
					{[
						['like', '96K'],
						['share', 'Share'],
						['download', 'Download'],
					].map(([i, l]) => (
						<div key={l} style={{background: Y.ui3, borderRadius: 16, padding: '8px 12px', fontSize: 13, display: 'flex', gap: 6, alignItems: 'center'}}>
							<Icon name={i as 'like'} size={16} color={Y.text} /> {l}
						</div>
					))}
				</div>
				<div style={{marginTop: 14, background: Y.ui3, borderRadius: 12, padding: '10px 12px', fontSize: 13}}>
					<b>Comments 12K</b>
					<div style={{display: 'flex', gap: 8, marginTop: 8, alignItems: 'center'}}>
						<ChAvatar c="maya" size={22} /> The drone shot at 6:12 is unreal 😍
					</div>
				</div>
				{[0, 6].map((i) => (
					<div key={i} style={{display: 'flex', gap: 10, marginTop: 14}}>
						<Thumb v={VIDEOS[i]} radius={8} style={{width: 150, flexShrink: 0}} />
						<div style={{fontSize: 13, lineHeight: 1.3}}>
							<div style={{fontWeight: 500}}>{VIDEOS[i].title}</div>
							<div style={{color: Y.text2, fontSize: 11, marginTop: 3}}>{CH[VIDEOS[i].ch].name}</div>
						</div>
					</div>
				))}
			</div>
		</div>
	);
};

export const PhoneScene: React.FC<{f: number}> = ({f}) => {
	const P = CUE.phone;
	const t = f - SCENES.phone.from;
	const cam = CAMS.phone(f);
	const ring = prog(f, P.ring, P.tap, easeInOut);
	const burst = prog(f, P.tap, P.tap + 24);
	return (
		<AbsoluteFill>
			<DarkBg t={f} glow="rgba(255,40,80,0.14)" glow2="rgba(255,0,0,0.08)" />
			<Scene3D cam={cam} perspective={PERSPECTIVE}>
				<World>
					{FLOAT.map((c, i) => {
						const blur = Math.min(9, Math.abs(c.z) / 170);
						return (
							<At key={i} x={c.x + Math.sin((t + c.ph) / 50) * 20} y={c.y + Math.cos((t + c.ph) / 40) * 16} z={c.z} ry={c.ry} rx={4}>
								<div style={{width: c.w, filter: blur > 0.6 ? `blur(${blur.toFixed(1)}px)` : undefined, opacity: 0.92}}>
									<Thumb v={VIDEOS[c.v]} radius={14} style={{width: c.w}} />
								</div>
							</At>
						);
					})}
					<At x={240} ry={-12 + Math.sin(t / 50) * 6} rx={4} y={Math.sin(t / 34) * 8}>
						<div style={{position: 'relative'}}>
							<IPhone>
								<MobileWatch f={f} />
							</IPhone>
							<svg width="427" height="886" style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', transform: 'translateZ(4px)'}}>
								<circle cx={213} cy={181} r={64 + burst * 40} fill="none" stroke={RED} strokeWidth={6 - burst * 4} pathLength={1} strokeDasharray={`${ring} 1`} transform="rotate(-90 213 181)" opacity={1 - burst} style={{filter: 'drop-shadow(0 0 8px rgba(255,0,0,0.9))'}} />
							</svg>
						</div>
					</At>
					<At x={-430} y={40} z={200}>
						<div style={{whiteSpace: 'nowrap', textShadow: '0 10px 40px rgba(0,0,0,0.6)'}}>
							<Letters text="Press play." f={f} start={P.title} out={P.out} size={104} />
						</div>
					</At>
				</World>
			</Scene3D>
		</AbsoluteFill>
	);
};

/* ================================================================ 4. MOODS: full-colour scenes with heavy type + 3D objects */
const OBJ = {x: 1400, y: 560};
const Marquee: React.FC<{word: string; color: string; t: number; y: number; dir: 1 | -1}> = ({word, color, t, y, dir}) => {
	const unit = `${word.replace('\n', ' ')}  •  `;
	return (
		<div style={{position: 'absolute', left: 0, top: y, whiteSpace: 'nowrap', ...HEAVY, fontSize: 150, color: 'transparent', WebkitTextStroke: `2.5px ${color}`, transform: `translateX(${dir * ((t * 3.2) % 900) - 900}px)`}}>
			{unit.repeat(8)}
		</div>
	);
};

const MoodObject: React.FC<{id: string; t: number}> = ({id, t}) => {
	const sheen = ((t / 70) % 1.4) - 0.2;
	if (id === 'gaming')
		return (
			<div style={{position: 'relative', transformStyle: 'preserve-3d'}}>
				<Controller3D w={480} sheen={sheen} color={['#F6FF9A', '#CBEA3C']} side={['#9DB728', '#3E4A08']} />
				<div style={{position: 'absolute', left: 240 - 340, top: 160 - 170, width: 680, height: 340, borderRadius: '50%', border: '12px solid #F2FF7A', boxShadow: '0 0 34px #E9FF5B, inset 0 0 24px #E9FF5B', transform: `rotateX(64deg) rotateZ(${t * 1.5}deg)`}} />
			</div>
		);
	if (id === 'music') return <Note3D w={440} sheen={sheen} />;
	if (id === 'learn')
		return (
			<div style={{position: 'relative', transformStyle: 'preserve-3d'}}>
				<div style={{position: 'absolute', left: -120, top: -100, width: 560, height: 560, borderRadius: '50%', background: 'radial-gradient(closest-side, rgba(255,240,120,0.65), transparent)', transform: 'translateZ(-80px)'}} />
				<Bulb3D w={320} sheen={sheen} />
			</div>
		);
	return (
		<div style={{position: 'relative', transformStyle: 'preserve-3d'}}>
			<div style={{position: 'absolute', left: -160, top: -160, width: 760, height: 760, borderRadius: '50%', background: 'radial-gradient(closest-side, rgba(255,211,107,0.35), transparent)', transform: 'translateZ(-80px)'}} />
			<Moon3D w={440} sheen={sheen} />
			{[0, 1, 2, 3, 4].map((i) => (
				<Sparkle key={i} size={[34, 22, 28, 18, 24][i]} color={i % 2 ? '#fff' : '#FFE38A'} style={{position: 'absolute', left: [-40, 420, 380, 30, 470][i], top: [60, 10, 380, 400, 220][i], transform: `translateZ(${40 + i * 20}px) scale(${0.6 + 0.4 * Math.sin(t / 8 + i)}) rotate(${t * 2}deg)`}} />
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
			const letters = m.word.split('\n');
			const s = spr(f, m.at + 6, {damping: 12, stiffness: 120});
			let k = 0;
			const total = m.word.replace('\n', '').length;
			return (
				<AbsoluteFill key={m.id} style={{clipPath: `circle(${r}px at ${o.x}px ${o.y}px)`, background: m.bg}}>
					<AbsoluteFill style={{background: 'radial-gradient(80% 80% at 70% 50%, rgba(255,255,255,0.18), transparent 60%), radial-gradient(120% 100% at 50% 50%, transparent 60%, rgba(0,0,0,0.25) 100%)'}} />
					<Marquee word={m.word} color={m.outline} t={t} y={30} dir={-1} />
					<Marquee word={m.word} color={m.outline} t={t} y={880} dir={1} />
					<div style={{position: 'absolute', left: 140, top: letters.length > 1 ? 250 : 330, display: 'flex', alignItems: 'center', gap: 12, fontFamily: YBODY, fontWeight: 700, fontSize: 30, color: m.ink, opacity: prog(f, m.at + 10, m.at + 22)}}>
						<svg width="34" height="24" viewBox="0 0 28 20">
							<path d={PLAY_D} fill={m.ink} />
							<path d={TRI_D} fill={m.bg} />
						</svg>
						{m.label}
					</div>
					<div style={{position: 'absolute', left: 128, top: letters.length > 1 ? 300 : 380, ...HEAVY, fontSize: letters.length > 1 ? 230 : m.word.length > 5 ? 228 : 270, color: m.ink}}>
						{letters.map((ln, li) => (
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

/* ================================================================ 5. LANDSCAPE: equalizer -> 3D field, counter, "All in one place." */
const COLS = 40;
const ROWS = 16;
const Rolling: React.FC<{value: number; size: number}> = ({value, size}) => {
	const digits = String(Math.floor(720000)).length;
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
		if (p === 3) cells.push(<span key="c">,</span>);
	}
	return (
		<div style={{...SENT, fontSize: size, lineHeight: '1em', display: 'flex', fontVariantNumeric: 'tabular-nums'}}>
			{cells}
			<span style={{color: RED}}>+</span>
		</div>
	);
};

export const LandScene: React.FC<{f: number}> = ({f}) => {
	const L = CUE.land;
	const cam = CAMS.land(f);
	const reveal = 2400 * easeInOut(prog(f, SCENES.land.from, SCENES.land.from + 14, (x) => x));
	const counter = 720000 * ease3(prog(f, L.counter, L.counterTo, (x) => x));
	const cOut = prog(f, L.words[0] - 8, L.words[0]);
	const bars: React.ReactNode[] = [];
	for (let r = ROWS - 1; r >= 0; r--) {
		const grow = r === 0 ? prog(f, L.title - 6, L.title + 14) : prog(f, L.tilt + r * 3, L.tilt + r * 3 + 24);
		if (grow <= 0) continue;
		for (let c = 0; c < COLS; c++) {
			const env = 0.55 + 0.45 * Math.sin((c / (COLS - 1)) * Math.PI);
			const w = 0.5 + 0.5 * Math.sin(c * 0.32 + f * 0.11 + r * 0.55) * (0.6 + 0.4 * Math.sin(r * 0.37 - f * 0.045 + c * 0.05));
			const h = (24 + 260 * w * env) * grow;
			const hue = 300 - (c / (COLS - 1)) * 245;
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
						background: `linear-gradient(180deg, hsl(${hue},100%,${80 - r}%), hsl(${hue},95%,${56 - r * 1.5}%))`,
						opacity: 1 - r * 0.025,
					}}
				/>,
			);
		}
	}
	return (
		<AbsoluteFill style={{clipPath: `circle(${reveal}px at ${OBJ.x}px ${OBJ.y}px)`}}>
			<AbsoluteFill style={{background: 'radial-gradient(100% 90% at 50% 70%, #1B1B1B 0%, #0B0B0B 55%, #030303 100%)'}} />
			<div style={{position: 'absolute', left: 300, top: 560, width: 1320, height: 500, background: 'radial-gradient(closest-side, rgba(180,120,255,0.18), transparent)'}} />
			<Scene3D cam={cam} perspective={PERSPECTIVE}>
				<World>{bars}</World>
			</Scene3D>
			<div style={{position: 'absolute', left: 0, right: 0, top: 170, display: 'flex', justifyContent: 'center'}}>
				<Letters text="For every curiosity." f={f} start={L.title} out={1036} size={100} align="center" />
			</div>
			{f >= L.counter - 2 && f < L.words[0] + 2 && (
				<div style={{position: 'absolute', left: 120, top: 100, opacity: prog(f, L.counter - 2, L.counter + 8) * (1 - cOut), transform: `translateY(${-cOut * 30}px)`}}>
					<Rolling value={counter} size={124} />
					<div style={{...SENT, fontSize: 44, marginTop: 10}}>
						hours uploaded every day<span style={{color: RED}}>.</span>
					</div>
				</div>
			)}
			{['Shorts.', 'Live.', 'Podcasts.'].map((w, i) => (
				<div key={w} style={{position: 'absolute', left: 120, top: 110}}>
					<Letters text={w} f={f} start={L.words[i]} out={i < 2 ? L.words[i + 1] - 6 : L.all - 6} size={120} step={1.2} />
				</div>
			))}
			<div style={{position: 'absolute', left: 120, top: 110}}>
				<Letters text="All in one place." f={f} start={L.all} out={1278} size={120} step={1.2} />
			</div>
		</AbsoluteFill>
	);
};

/* ================================================================ 6. CAROUSEL: "Made for you." */
const MIXES = [
	{v: 2, t: 'Your Mix'},
	{v: 4, t: 'Travel Mix'},
	{v: 0, t: 'Made for You'},
	{v: 6, t: 'Learn: Space'},
	{v: 1, t: 'Cooking Mix'},
	{v: 3, t: 'Gaming Mix'},
	{v: 5, t: 'Practice Daily'},
	{v: 7, t: 'Food Trips'},
	{v: 8, t: 'Setup Tours'},
	{v: 2, t: 'Lo-fi Radio'},
	{v: 4, t: 'Watch Later'},
	{v: 0, t: 'Liked Videos'},
];
export const CarouselScene: React.FC<{f: number}> = ({f}) => {
	const C = CUE.carousel;
	const t = f - SCENES.carousel.from;
	const cam = CAMS.carousel(f);
	const cp = prog(f, C.collapse, C.collapse + 45, (x) => x * x);
	const R = 1000 * (1 - cp);
	const base = t * 0.45 + cp * cp * 140;
	const sphere = spr(f, C.collapse + 15, {damping: 14, stiffness: 120});
	return (
		<AbsoluteFill>
			<DarkBg t={f} glow="rgba(255,0,0,0.12)" glow2="rgba(255,120,60,0.08)" />
			<Scene3D cam={cam} perspective={PERSPECTIVE}>
				<World>
					{MIXES.map((m, i) => {
						const a = ((base + i * 30) * Math.PI) / 180;
						const x = Math.sin(a) * R;
						const z = Math.cos(a) * R - R * 0.35;
						const back = Math.max(0, (R * 0.65 - z) / (R * 1.6 + 1));
						return (
							<At key={i} x={x} y={90} z={z} ry={-Math.sin(a) * 22}>
								<div style={{width: 360, borderRadius: 18, overflow: 'hidden', background: '#181818', boxShadow: '0 30px 60px rgba(0,0,0,0.6)', opacity: (1 - cp) * (1 - back * 0.2), transform: `scale(${1 - cp * 0.6})`, position: 'relative'}}>
									<Thumb v={VIDEOS[m.v]} radius={0} style={{width: 360}} />
									<div style={{padding: '14px 16px 16px', fontFamily: YBODY}}>
										<div style={{display: 'flex', alignItems: 'center', gap: 8, color: '#fff', fontWeight: 700, fontSize: 24}}>
											<svg width="24" height="17" viewBox="0 0 28 20">
												<path d={PLAY_D} fill={RED} />
												<path d={TRI_D} fill="#fff" />
											</svg>
											{m.t}
										</div>
										<div style={{color: '#AAA', fontSize: 16, marginTop: 4}}>Updated today · 50 videos</div>
									</div>
									<div style={{position: 'absolute', inset: 0, background: `rgba(0,0,0,${(back * 0.6).toFixed(3)})`}} />
								</div>
							</At>
						);
					})}
					<At y={0} z={0}>
						<Sphere size={340 * sphere} base="#FF2A2A" dark="#A30000" glow="rgba(255,0,0,0.55)" t={t} />
					</At>
					<At y={-430} z={320}>
						<div style={{whiteSpace: 'nowrap', textShadow: '0 0 24px rgba(255,255,255,0.65), 0 0 60px rgba(255,255,255,0.3)'}}>
							<Letters text="Made for you." f={f} start={C.title} out={C.collapse - 10} size={130} align="center" />
						</div>
					</At>
				</World>
			</Scene3D>
		</AbsoluteFill>
	);
};

/* ================================================================ 7. LOGO: sphere -> play button -> wordmark + CTA */
export const LogoScene: React.FC<{f: number}> = ({f}) => {
	const G = CUE.logo;
	const t = f - SCENES.logo.from;
	const flat = prog(f, G.flatten, G.flatten + 16, easeInOut);
	const tri = spr(f, G.tri, {damping: 11, stiffness: 180});
	const slide = prog(f, G.wordmark, G.wordmark + 24, easeInOut);
	const iconW = 300;
	const iconX = lerp(960, 578, slide);
	const iconY = lerp(540, 450, prog(f, G.flatten, G.wordmark + 24, easeInOut));
	const btn = spr(f, G.button, {damping: 12, stiffness: 160});
	return (
		<AbsoluteFill>
			<DarkBg t={f} glow="rgba(255,0,0,0.18)" />
			<div style={{position: 'absolute', left: iconX - 600, top: iconY - 400, width: 1200, height: 800, background: `radial-gradient(closest-side, rgba(255,0,0,${0.22 + 0.08 * Math.sin(t / 20)}), transparent)`}} />
			<div style={{position: 'absolute', left: iconX - 160, top: iconY - 160, opacity: 1 - flat, transform: `scale(${lerp(1, 1.06, flat)}) scaleY(${lerp(1, 0.8, flat)})`}}>
				<Sphere size={320} base="#FF2A2A" dark="#A30000" glow="rgba(255,0,0,0.5)" t={t} />
			</div>
			<svg
				width={iconW}
				height={(iconW * 20) / 28}
				viewBox="0 0 28 20"
				style={{position: 'absolute', left: iconX - iconW / 2, top: iconY - (iconW * 10) / 28, opacity: flat, transform: `scale(${lerp(0.85, 1, flat)})`, overflow: 'visible', filter: 'drop-shadow(0 20px 40px rgba(255,0,0,0.45))'}}
			>
				<path d={PLAY_D} fill={RED} />
				<g style={{transform: `scale(${tri})`, transformOrigin: '14.6px 10px'}}>
					<path d={TRI_D} fill="#fff" />
				</g>
			</svg>
			<div style={{position: 'absolute', left: 762, top: iconY - 112, height: 224, display: 'flex', alignItems: 'center', clipPath: `inset(-20% ${(1 - slide) * 100}% -20% 0)`}}>
				<span style={{fontFamily: YBODY, fontWeight: 700, fontSize: 196, color: '#fff', letterSpacing: `${lerp(0.25, -0.055, slide)}em`, opacity: slide}}>YouTube</span>
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, top: 640, display: 'flex', justifyContent: 'center'}}>
				<Letters text="Every idea has an audience." f={f} start={G.tagline} size={44} step={0.8} align="center" style={{fontWeight: 600, color: '#D6D6D6', letterSpacing: '-0.01em'}} />
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, top: 740, display: 'flex', justifyContent: 'center'}}>
				<div
					style={{
						position: 'relative',
						overflow: 'hidden',
						padding: '22px 52px',
						borderRadius: 999,
						background: RED,
						color: '#fff',
						fontFamily: YBODY,
						fontWeight: 900,
						fontSize: 24,
						letterSpacing: '0.14em',
						transform: `scale(${btn})`,
						boxShadow: '0 16px 50px rgba(255,0,0,0.45)',
					}}
				>
					START WATCHING
					<div style={{position: 'absolute', top: 0, bottom: 0, width: 80, left: `${-30 + ((t * 2.2) % 160)}%`, background: 'linear-gradient(100deg, transparent, rgba(255,255,255,0.35), transparent)'}} />
				</div>
			</div>
		</AbsoluteFill>
	);
};

export {interpolate, clamp, MOOD_LEN};
