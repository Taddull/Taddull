import React, {useMemo} from 'react';
import {
	AbsoluteFill,
	Easing,
	interpolate,
	interpolateColors,
	random,
	useCurrentFrame,
} from 'remotion';
import {
	AMBER,
	BG,
	clamp,
	easeInOut,
	easeOut,
	Grain,
	H,
	INK,
	INK_DIM,
	MONO,
	Narration,
	ramp,
	SERIF,
	useFonts,
	W,
} from './editorial';

/*
 * "Winter nights" — 34s, 1920x1080, 30fps. Follows "Nightly search".
 *
 * A  (0–400)    One car idling for heat. A night is time-lapsed while a
 *               ledger runs: 1/3 gal an hour at ~$3/gal is $1 an hour,
 *               ten hours is $10.
 * B  (400–560)  The camera pulls back: the car is one of a full lot, and
 *               the lot frosts over.
 * C  (560–1020) The lot becomes a unit chart, one car per 1% of vehicle
 *               households: 19% with children, then 57% with pets.
 *
 * Survey figures: Santa Barbara County survey of 90 vehicle households
 * (2026), as reported by the Santa Barbara Independent.
 */

export const WINTER_NIGHTS_DURATION = 1020;

const CHILDREN = 19;
const PETS = 57;

/* ------------------------------------------------------------------ */
/* The lot (world units)                                               */
/* ------------------------------------------------------------------ */

const COLS = 25;
const ROWS = 4;
const STALL_W = 26;
const STALL_D = 48;
const AISLE = 30;
const LOT_W = COLS * STALL_W;
const LOT_H = ROWS * STALL_D + (ROWS - 1) * AISLE;
const rowTop = (r: number) => r * (STALL_D + AISLE);
const stallCenter = (c: number, r: number) => ({
	x: c * STALL_W + STALL_W / 2,
	y: rowTop(r) + STALL_D / 2,
});

const HERO = {c: 8, r: 1};
const HERO_POS = stallCenter(HERO.c, HERO.r);
const LAMP = {x: HERO_POS.x + 30, y: rowTop(1) - AISLE / 2};

const PAINT = ['#7d8590', '#5d6670', '#8a8174', '#6b5f57', '#4f5a66', '#9a948a', '#40484f', '#77706a', '#6f7a72'];
const CHART_GREY = '#525963';
const HERO_BODY = '#c9c2b2';

type Stall = {c: number; r: number; x: number; y: number; paint: string; ripple: number};

const buildLot = () => {
	const stalls: Stall[] = [];
	for (let r = 0; r < ROWS; r++) {
		for (let c = 0; c < COLS; c++) {
			const {x, y} = stallCenter(c, r);
			const isHero = c === HERO.c && r === HERO.r;
			stalls.push({
				c,
				r,
				x,
				y,
				paint: isHero ? HERO_BODY : PAINT[Math.floor(random(`paint${c}-${r}`) * PAINT.length)],
				ripple: Math.hypot(x - HERO_POS.x, (y - HERO_POS.y) * 0.8),
			});
		}
	}
	// Deterministic picks for the unit chart, revealed left to right.
	const pick = (n: number, seed: string) =>
		stalls
			.map((s, i) => ({i, k: random(`${seed}${i}`)}))
			.sort((a, b) => a.k - b.k)
			.slice(0, n)
			.map((p) => p.i)
			.sort((a, b) => stalls[a].c - stalls[b].c || stalls[a].r - stalls[b].r);
	return {stalls, kids: pick(CHILDREN, 'kids'), pets: pick(PETS, 'pets')};
};

/* ------------------------------------------------------------------ */
/* Camera                                                              */
/* ------------------------------------------------------------------ */

type Cam = {cx: number; cy: number; s: number};
const PULL_A = 404;
const PULL_B = 532;

// Final framing: the lot fills the right of the frame.
const CHART_LEFT = 780;
const CHART_TOP = 168;
const CHART_S = (1780 - CHART_LEFT) / LOT_W;
const CHART_CAM: Cam = {
	cx: (W / 2 - CHART_LEFT) / CHART_S,
	cy: (H / 2 - CHART_TOP) / CHART_S,
	s: CHART_S,
};
const toScreen = (c: Cam, x: number, y: number) => ({
	x: (x - c.cx) * c.s + W / 2,
	y: (y - c.cy) * c.s + H / 2,
});

const camAt = (f: number): Cam => {
	// Scene A: close on the hero car, a slow push.
	const s0 = interpolate(f, [0, PULL_A], [3.2, 3.36], clamp);
	const hero0 = {
		x: interpolate(f, [0, PULL_A], [612, 600], clamp),
		y: interpolate(f, [0, PULL_A], [326, 334], clamp),
	};
	const p = ramp(f, PULL_A, PULL_B, Easing.bezier(0.6, 0, 0.2, 1));
	const hero1 = toScreen(CHART_CAM, HERO_POS.x, HERO_POS.y);
	const s = Math.exp(Math.log(s0) + (Math.log(CHART_S) - Math.log(s0)) * p);
	const hx = hero0.x + (hero1.x - hero0.x) * p;
	const hy = hero0.y + (hero1.y - hero0.y) * p;
	return {cx: HERO_POS.x - (hx - W / 2) / s, cy: HERO_POS.y - (hy - H / 2) / s, s};
};

const camTransform = (c: Cam) =>
	`translate(${W / 2} ${H / 2}) scale(${c.s}) translate(${-c.cx} ${-c.cy})`;

/* ------------------------------------------------------------------ */
/* Pieces                                                              */
/* ------------------------------------------------------------------ */

const darker = (hex: string, k: number) => interpolateColors(k, [0, 1], [hex, '#000000']);

// Top-down car, nose up. Drawn nose-right then rotated.
const CarIcon: React.FC<{
	x: number;
	y: number;
	body: string;
	opacity: number;
	frost: number;
	tail: number;
}> = ({x, y, body, opacity, frost, tail}) => (
	<g transform={`translate(${x} ${y}) rotate(-90) scale(1.25)`} opacity={opacity}>
		<rect x={-15.3} y={-6.6} width={31} height={14.4} rx={4.2} fill="#000" opacity={0.4} />
		<rect x={-15.5} y={-7.2} width={31} height={14.4} rx={4.2} fill={body} />
		<path d="M3.2,-6 L8.6,-5.2 Q9.6,0 8.6,5.2 L3.2,6 Z" fill="#232831" />
		<rect x={-8.5} y={-5.6} width={11.4} height={11.2} rx={1.6} fill={darker(body, 0.1)} />
		<path d="M-9,-5.6 L-12,-4.8 Q-12.8,0 -12,4.8 L-9,5.6 Z" fill="#232831" />
		{frost > 0 ? (
			<>
				<rect x={-15.5} y={-7.2} width={31} height={14.4} rx={4.2} fill="#dce6ee" opacity={frost * 0.26} />
				<path d="M3.2,-6 L8.6,-5.2 Q9.6,0 8.6,5.2 L3.2,6 Z" fill="#c6d2dc" opacity={frost * 0.62} />
				<path d="M-9,-5.6 L-12,-4.8 Q-12.8,0 -12,4.8 L-9,5.6 Z" fill="#c6d2dc" opacity={frost * 0.62} />
			</>
		) : null}
		<rect x={-15.6} y={-6} width={1.4} height={3} rx={0.6} fill="#ff4a3a" opacity={0.15 + 0.85 * tail} />
		<rect x={-15.6} y={3} width={1.4} height={3} rx={0.6} fill="#ff4a3a" opacity={0.15 + 0.85 * tail} />
	</g>
);

const Exhaust: React.FC<{frame: number; strength: number}> = ({frame, strength}) => {
	if (strength <= 0) return null;
	const LIFE = 96;
	const EVERY = 6;
	const pipe = {x: HERO_POS.x + 4.5, y: HERO_POS.y + 20};
	const puffs = [];
	const first = Math.max(0, Math.floor((frame - LIFE) / EVERY));
	for (let k = first; k * EVERY <= frame; k++) {
		const age = frame - k * EVERY;
		if (age < 0 || age > LIFE) continue;
		const t = age / LIFE;
		// A slow wind that wanders, so the plume bends instead of forming a cone.
		const wind = 12 + Math.sin(k * 0.23) * 16 + Math.sin(k * 0.71) * 6;
		const spread = (random(`ex${k}`) - 0.5) * 26;
		const lift = 0.6 + random(`el${k}`) * 0.7;
		const wob = Math.sin(age / 13 + k * 1.7) * 5;
		puffs.push(
			<circle
				key={k}
				cx={pipe.x + (wind + spread + wob) * Math.pow(t, 0.9)}
				cy={pipe.y + 3 + 40 * lift * Math.pow(t, 0.7)}
				r={3 + 24 * Math.pow(t, 0.8) * (0.7 + random(`er${k}`) * 0.6)}
				fill="url(#puff)"
				opacity={strength * ramp(age, 0, 10, Easing.linear) * Math.pow(1 - t, 1.5) * 0.7}
			/>
		);
	}
	return <g filter="url(#vapour)">{puffs}</g>;
};

/* clock: 8 PM to 6 AM during the time-lapse */
const LAPSE_A = 150;
const LAPSE_B = 222;
const hoursAt = (f: number) => 10 * ramp(f, LAPSE_A, LAPSE_B, easeInOut);
const fmtClock = (hours: number) => {
	const mins = Math.floor((20 + hours) * 60) % (24 * 60);
	const h24 = Math.floor(mins / 60);
	const h = h24 % 12 === 0 ? 12 : h24 % 12;
	return `${h}:${String(mins % 60).padStart(2, '0')} ${h24 >= 12 ? 'PM' : 'AM'}`;
};

const Ledger: React.FC<{frame: number}> = ({frame}) => {
	const hours = hoursAt(frame);
	const gallons = hours / 3;
	const dollars = hours; // 1/3 gal/hr at ~$3/gal = $1/hr
	const temp = Math.round(interpolate(frame, [LAPSE_A, LAPSE_B], [28, 19], clamp));
	const out = 1 - ramp(frame, 384, 404, Easing.linear);
	const rowIn = (at: number) => ramp(frame, at, at + 18) * out;
	const label: React.CSSProperties = {
		fontFamily: MONO,
		fontSize: 17,
		fontWeight: 500,
		letterSpacing: 2.4,
		color: INK_DIM,
		textTransform: 'uppercase',
	};
	const value: React.CSSProperties = {
		fontFamily: MONO,
		fontSize: 25,
		color: INK,
		fontVariantNumeric: 'tabular-nums',
	};
	const row = (at: number, l: string, v: React.ReactNode) => {
		const p = rowIn(at);
		return (
			<div
				style={{
					display: 'flex',
					justifyContent: 'space-between',
					alignItems: 'baseline',
					padding: '13px 0',
					borderBottom: '1px solid rgba(236,230,217,0.12)',
					opacity: p,
					transform: `translateY(${(1 - p) * 8}px)`,
				}}
			>
				<span style={label}>{l}</span>
				<span style={value}>{v}</span>
			</div>
		);
	};
	const costIn = rowIn(LAPSE_A);
	const perNight = rowIn(LAPSE_B + 6);
	return (
		<div style={{position: 'absolute', left: 1180, top: 104, width: 600}}>
			<div
				style={{
					display: 'flex',
					justifyContent: 'space-between',
					alignItems: 'baseline',
					opacity: rowIn(8),
					paddingBottom: 18,
					borderBottom: '1px solid rgba(236,230,217,0.3)',
				}}
			>
				<span style={{fontFamily: MONO, fontSize: 46, color: INK, fontVariantNumeric: 'tabular-nums'}}>
					{fmtClock(hours)}
				</span>
				<span style={{fontFamily: MONO, fontSize: 30, color: '#a9c4d8', fontVariantNumeric: 'tabular-nums'}}>
					{temp}°F
				</span>
			</div>
			{row(78, 'Idling for heat', '⅓ gal / hour')}
			{row(112, 'Regular gas', '≈ $3 / gal')}
			{row(LAPSE_A - 6, 'Hours idling', hours.toFixed(1))}
			{row(LAPSE_A - 2, 'Fuel burned', `${gallons.toFixed(1)} gal`)}
			<div style={{marginTop: 22, opacity: costIn, display: 'flex', alignItems: 'flex-end', gap: 22}}>
				<span
					style={{
						fontFamily: SERIF,
						fontWeight: 600,
						fontSize: 132,
						lineHeight: 0.9,
						color: AMBER,
						letterSpacing: -2,
						fontVariantNumeric: 'tabular-nums',
					}}
				>
					${dollars.toFixed(2)}
				</span>
				<span style={{...label, opacity: perNight, paddingBottom: 10}}>a night</span>
			</div>
		</div>
	);
};

const UnitStat: React.FC<{
	frame: number;
	at: number;
	until: number;
	count: number;
	kicker: string;
}> = ({frame, at, until, count, kicker}) => {
	const p = ramp(frame, at, at + 22) * (1 - ramp(frame, until, until + 16, Easing.linear));
	if (p <= 0) return null;
	return (
		<div style={{position: 'absolute', left: 140, top: 176, opacity: p}}>
			<div
				style={{
					fontFamily: MONO,
					fontWeight: 500,
					fontSize: 18,
					letterSpacing: 2.6,
					color: INK_DIM,
					textTransform: 'uppercase',
					transform: `translateX(${(1 - p) * -10}px)`,
				}}
			>
				{kicker}
			</div>
			<div
				style={{
					fontFamily: SERIF,
					fontWeight: 600,
					fontSize: 236,
					lineHeight: 1,
					letterSpacing: -6,
					color: AMBER,
					marginTop: 14,
					fontVariantNumeric: 'tabular-nums',
				}}
			>
				{count}
				<span style={{fontSize: 120, letterSpacing: 0, marginLeft: 6}}>%</span>
			</div>
			<div
				style={{
					fontFamily: MONO,
					fontWeight: 500,
					fontSize: 18,
					letterSpacing: 2.6,
					color: INK_DIM,
					textTransform: 'uppercase',
					marginTop: 18,
				}}
			>
				of vehicle households
			</div>
		</div>
	);
};

/* ------------------------------------------------------------------ */
/* Composition                                                         */
/* ------------------------------------------------------------------ */

const KIDS_AT = 600;
const KIDS_CLEAR = 726;
const PETS_AT = 760;
const STAGGER_KIDS = 3;
const STAGGER_PETS = 1.15;

export const WinterNights: React.FC = () => {
	useFonts();
	const frame = useCurrentFrame();
	const lot = useMemo(buildLot, []);
	const cam = camAt(frame);
	const tf = camTransform(cam);

	const fadeIn = ramp(frame, 0, 24, Easing.linear);
	const fadeOut = 1 - ramp(frame, WINTER_NIGHTS_DURATION - 36, WINTER_NIGHTS_DURATION - 6, Easing.linear);

	// Lot lighting
	const reveal = (s: Stall) => ramp(frame, PULL_A + 20 + s.ripple * 0.16, PULL_A + 50 + s.ripple * 0.16);
	const frostNight = ramp(frame, LAPSE_A, LAPSE_B + 40, Easing.linear);
	const toChart = ramp(frame, 548, 584, easeInOut);
	const lampOn = 1 - ramp(frame, PULL_A + 10, PULL_A + 70, Easing.linear);
	const exhaust = 1 - ramp(frame, 560, 610, Easing.linear);

	const kidsRank = new Map(lot.kids.map((idx, k) => [idx, k]));
	const petsRank = new Map(lot.pets.map((idx, k) => [idx, k]));
	const kidsLit = (k: number) =>
		ramp(frame, KIDS_AT + k * STAGGER_KIDS, KIDS_AT + k * STAGGER_KIDS + 10, Easing.linear) *
		(1 - ramp(frame, KIDS_CLEAR, KIDS_CLEAR + 18, Easing.linear));
	const petsLit = (k: number) =>
		ramp(frame, PETS_AT + k * STAGGER_PETS, PETS_AT + k * STAGGER_PETS + 10, Easing.linear);
	const countLit = (n: number, at: number, stagger: number) =>
		// a car counts once it is half lit
		Math.min(n, Math.max(0, Math.floor((frame - at - 5) / stagger + 1)));
	const chartPhase = ramp(frame, KIDS_AT - 6, KIDS_AT + 10, Easing.linear);

	const legendIn = ramp(frame, 540, 566);
	const lotLines = 'rgba(200,206,216,0.16)';

	return (
		<AbsoluteFill style={{backgroundColor: BG}}>
			<AbsoluteFill style={{opacity: fadeIn * fadeOut}}>
				<AbsoluteFill style={{background: '#0a0c0f'}} />
				<svg width={W} height={H} style={{position: 'absolute'}}>
					<defs>
						<radialGradient id="puff">
							<stop offset="0%" stopColor="#e8eef3" stopOpacity={0.2} />
							<stop offset="100%" stopColor="#e8eef3" stopOpacity={0} />
						</radialGradient>
						<filter id="vapour" x="-50%" y="-50%" width="200%" height="200%">
							<feGaussianBlur stdDeviation={2.2} />
						</filter>
						<radialGradient id="lamp">
							<stop offset="0%" stopColor="#ffb760" stopOpacity={0.34} />
							<stop offset="40%" stopColor="#f29a3c" stopOpacity={0.12} />
							<stop offset="100%" stopColor="#f29a3c" stopOpacity={0} />
						</radialGradient>
					</defs>
					<g transform={tf}>
						{/* asphalt + stall paint */}
						<rect x={-22} y={-22} width={LOT_W + 44} height={LOT_H + 44} rx={4} fill="#0f1216" />
						{Array.from({length: ROWS}, (_, r) => (
							<g key={r}>
								<line
									x1={0}
									x2={LOT_W}
									y1={rowTop(r)}
									y2={rowTop(r)}
									stroke={lotLines}
									strokeWidth={1}
									vectorEffect="non-scaling-stroke"
								/>
								{Array.from({length: COLS + 1}, (_, c) => (
									<line
										key={c}
										x1={c * STALL_W}
										x2={c * STALL_W}
										y1={rowTop(r)}
										y2={rowTop(r) + STALL_D}
										stroke={lotLines}
										strokeWidth={1}
										vectorEffect="non-scaling-stroke"
									/>
								))}
							</g>
						))}

						<g style={{mixBlendMode: 'screen'}} opacity={lampOn}>
							<circle cx={LAMP.x} cy={LAMP.y} r={70} fill="url(#lamp)" />
							<circle cx={LAMP.x} cy={LAMP.y} r={1.6} fill="#ffd9a6" />
						</g>

						{lot.stalls.map((s, i) => {
							const isHero = s.c === HERO.c && s.r === HERO.r;
							const kr = kidsRank.get(i);
							const pr = petsRank.get(i);
							const lit = Math.max(
								kr === undefined ? 0 : kidsLit(kr),
								pr === undefined ? 0 : petsLit(pr)
							);
							const base = interpolateColors(toChart, [0, 1], [s.paint, CHART_GREY]);
							const body = interpolateColors(lit, [0, 1], [base, AMBER]);
							const visibility = isHero
								? 1
								: interpolate(reveal(s), [0, 1], [0.12, 0.92]);
							const chartDim = interpolate(chartPhase, [0, 1], [1, 0.5]) + lit * 0.5 * chartPhase;
							// The idling car stays clear until the chart; parked ones frost over.
							const frost =
								(isHero
									? interpolate(toChart, [0, 1], [0, 0.45])
									: Math.max(frostNight * 0.75, reveal(s) * 0.8)) *
								(1 - lit);
							return (
								<CarIcon
									key={i}
									x={s.x}
									y={s.y}
									body={body}
									opacity={visibility * Math.min(1, chartDim)}
									frost={frost}
									tail={isHero ? 0.45 * exhaust : 0}
								/>
							);
						})}

						<Exhaust frame={frame} strength={exhaust} />
					</g>
				</svg>

				{/* right-hand scrim for the ledger */}
				<AbsoluteFill
					style={{
						background:
							'linear-gradient(270deg, rgba(8,9,12,0.95) 0%, rgba(8,9,12,0.88) 30%, rgba(8,9,12,0) 52%)',
						opacity: 1 - ramp(frame, 384, 420, Easing.linear),
					}}
				/>
				<Ledger frame={frame} />

				{/* chart key */}
				<div
					style={{
						position: 'absolute',
						right: 140,
						top: CHART_TOP + LOT_H * CHART_S + 34,
						display: 'flex',
						alignItems: 'center',
						gap: 14,
						fontFamily: MONO,
						fontSize: 16,
						fontWeight: 500,
						letterSpacing: 2.2,
						color: INK_DIM,
						textTransform: 'uppercase',
						opacity: legendIn * fadeOut,
					}}
				>
					<svg width={16} height={30} viewBox="-8 -15 16 30">
						<g transform="scale(0.8)">
							<rect x={-7.2} y={-15.5} width={14.4} height={31} rx={4.2} fill={CHART_GREY} />
							<path d="M-6,-3.2 L-5.2,-8.6 Q0,-9.6 5.2,-8.6 L6,-3.2 Z" fill="#232831" />
						</g>
					</svg>
					Each car = 1% of vehicle households
				</div>

				<UnitStat
					frame={frame}
					at={KIDS_AT - 8}
					until={KIDS_CLEAR}
					count={countLit(CHILDREN, KIDS_AT, STAGGER_KIDS)}
					kicker="With children"
				/>
				<UnitStat
					frame={frame}
					at={PETS_AT - 8}
					until={WINTER_NIGHTS_DURATION}
					count={countLit(PETS, PETS_AT, STAGGER_PETS)}
					kicker="With pets"
				/>

				{/* text scrim + narration */}
				<AbsoluteFill
					style={{
						background:
							'linear-gradient(0deg, rgba(8,9,12,0.95) 0%, rgba(8,9,12,0.82) 22%, rgba(8,9,12,0) 44%)',
					}}
				/>
				<Narration
					frame={frame}
					style={{
						left: 140,
						bottom: 104,
						width: 1300,
						fontSize: 54,
						lineHeight: 1.17,
						opacity: 1 - ramp(frame, 382, 400, Easing.linear),
					}}
					segs={[
						{text: 'Idling an engine for warmth burns', at: 16},
						{text: 'about a third of a gallon an hour,', at: 64, br: true},
						{text: 'so a single freezing night', at: 148, br: true},
						{text: 'quietly adds ten dollars', at: 190},
						{text: 'to a budget that never had ten dollars to give.', at: 246, br: true},
					]}
				/>
				<Narration
					frame={frame}
					style={{
						left: 140,
						bottom: 104,
						width: 1300,
						fontSize: 58,
						lineHeight: 1.16,
						opacity: 1 - ramp(frame, 554, 570, Easing.linear),
					}}
					segs={[
						{text: 'And winter is where this population', at: 412},
						{text: 'stops matching the stereotype completely.', at: 458, br: true},
					]}
				/>
				<Narration
					frame={frame}
					style={{
						left: 140,
						bottom: 104,
						width: 1300,
						fontSize: 58,
						lineHeight: 1.16,
						opacity: 1 - ramp(frame, KIDS_CLEAR, KIDS_CLEAR + 16, Easing.linear),
					}}
					segs={[
						{text: 'Close to a fifth of these vehicle households', at: 578},
						{text: 'have children in them.', at: 628, br: true},
					]}
				/>
				<Narration
					frame={frame}
					style={{left: 140, bottom: 104, width: 1300, fontSize: 58, lineHeight: 1.16}}
					segs={[
						{text: 'Over half have pets', at: 752},
						{text: 'they won’t give up.', at: 800, br: true},
					]}
				/>

				<div
					style={{
						position: 'absolute',
						right: 140,
						bottom: 112,
						textAlign: 'right',
						fontFamily: MONO,
						fontSize: 14,
						letterSpacing: 1.6,
						lineHeight: 1.7,
						color: 'rgba(236,230,217,0.42)',
						textTransform: 'uppercase',
						opacity: ramp(frame, KIDS_AT + 20, KIDS_AT + 44),
					}}
				>
					Survey of 90 vehicle households
					<br />
					Santa Barbara County, 2026
				</div>
			</AbsoluteFill>
			<AbsoluteFill
				style={{
					background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 58%, rgba(0,0,0,0.5) 100%)',
					pointerEvents: 'none',
				}}
			/>
			<Grain frame={frame} />
		</AbsoluteFill>
	);
};
