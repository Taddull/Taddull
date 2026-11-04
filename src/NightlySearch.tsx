import React, {useMemo} from 'react';
import {AbsoluteFill, Easing, interpolate, random, useCurrentFrame} from 'remotion';
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
	Kicker,
	MONO,
	Narration,
	ramp,
	RED,
	SERIF,
	useFonts,
	W,
} from './editorial';

/*
 * "The nightly search" — 28s, 1920x1080, 30fps.
 *
 * A  (0–300)    The ruling: the first page of the Grants Pass v. Johnson
 *               slip opinion, holding highlighted.
 * B  (300–600)  The map: night moves across a city grid, blocks turn
 *               prohibited as it passes, one car looks for what's left.
 * C  (600–840)  The operation: the camera settles on the car in the one
 *               lot still allowed; engine off, lights off, shade up.
 */

export const NIGHTLY_SEARCH_DURATION = 840;

/* ------------------------------------------------------------------ */
/* Scene A — the ruling                                                */
/* ------------------------------------------------------------------ */

const HELD_LINES = [
	'Held: The enforcement of generally applicable laws',
	'regulating camping on public property does not',
	'constitute “cruel and unusual punishment” prohibited',
	'by the Eighth Amendment.',
];
const HIGHLIGHT_AT = 92;

const PaperGrain: React.FC = () => (
	<svg
		width="100%"
		height="100%"
		style={{position: 'absolute', inset: 0, mixBlendMode: 'multiply', opacity: 0.32}}
	>
		<filter id="paperNoise">
			<feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="3" seed={7} />
			<feColorMatrix type="saturate" values="0" />
			<feComponentTransfer>
				<feFuncA type="table" tableValues="0 0.55" />
			</feComponentTransfer>
		</filter>
		<rect width="100%" height="100%" filter="url(#paperNoise)" />
	</svg>
);

const Paper: React.FC<{frame: number}> = ({frame}) => {
	// Rostrum move: drift down the page and settle on the holding.
	const ty = interpolate(frame, [0, 300], [70, -330], {
		...clamp,
		easing: Easing.bezier(0.3, 0, 0.25, 1),
	});
	const scale = interpolate(frame, [0, 300], [1.0, 1.07], clamp);
	// Focus pull: the top of the page softens as we leave it.
	const topBlur = interpolate(frame, [60, 150], [0, 1.6], clamp);

	const small: React.CSSProperties = {fontSize: 17, lineHeight: 1.45};
	const caps: React.CSSProperties = {
		textAlign: 'center',
		letterSpacing: 1.2,
		fontVariant: 'small-caps',
	};

	return (
		<div
			style={{
				position: 'absolute',
				left: 958,
				top: 0,
				width: 860,
				transformOrigin: '50% 30%',
				transform: `translateY(${ty}px) rotate(-1.4deg) scale(${scale})`,
			}}
		>
			<div
				style={{
					position: 'relative',
					background: '#e9e3d4',
					padding: '58px 74px 90px',
					boxShadow:
						'0 40px 90px rgba(0,0,0,0.65), 0 6px 18px rgba(0,0,0,0.45)',
					fontFamily: SERIF,
					color: '#1f1d1a',
					overflow: 'hidden',
				}}
			>
				<PaperGrain />
				<div style={{position: 'relative', filter: `blur(${topBlur}px)`}}>
					<div
						style={{
							display: 'flex',
							justifyContent: 'space-between',
							fontSize: 18,
							letterSpacing: 0.6,
						}}
					>
						<span>(Slip Opinion)</span>
						<span style={{fontVariant: 'small-caps', letterSpacing: 1.4}}>
							October Term, 2023
						</span>
						<span>1</span>
					</div>
					<div style={{textAlign: 'center', fontSize: 19, marginTop: 26}}>
						Syllabus
					</div>
					<div
						style={{
							...small,
							marginTop: 14,
							padding: '12px 0',
							borderTop: '1px solid rgba(31,29,26,0.5)',
							borderBottom: '1px solid rgba(31,29,26,0.5)',
							textAlign: 'justify',
						}}
					>
						NOTE: Where it is feasible, a syllabus (headnote) will be released, as is
						being done in connection with this case, at the time the opinion is
						issued. The syllabus constitutes no part of the opinion of the Court but
						has been prepared by the Reporter of Decisions for the convenience of the
						reader. See <i>United States</i> v. <i>Detroit Timber &amp; Lumber Co.,</i>{' '}
						200 U. S. 321, 337.
					</div>
					<div
						style={{
							...caps,
							fontSize: 27,
							fontWeight: 600,
							letterSpacing: 2.2,
							marginTop: 34,
						}}
					>
						SUPREME COURT OF THE UNITED STATES
					</div>
					<div style={{textAlign: 'center', fontSize: 19, marginTop: 12}}>
						Syllabus
					</div>
					<div style={{...caps, fontSize: 23, lineHeight: 1.35, marginTop: 22}}>
						city of grants pass, oregon <i style={{fontVariant: 'normal'}}>v.</i>{' '}
						johnson et al., on behalf of themselves and all others similarly
						situated
					</div>
					<div style={{...caps, fontSize: 18, marginTop: 20}}>
						certiorari to the united states court of appeals for the ninth circuit
					</div>
				</div>
				<div
					style={{
						position: 'relative',
						textAlign: 'center',
						fontSize: 21,
						marginTop: 20,
						filter: `blur(${topBlur * 0.5}px)`,
					}}
				>
					No. 23–175. Argued April 22, 2024—Decided June 28, 2024
				</div>
				<div
					style={{
						position: 'relative',
						fontSize: 23,
						lineHeight: 1.5,
						marginTop: 26,
						textIndent: 28,
						textAlign: 'justify',
						filter: 'blur(2.2px)',
						opacity: 0.8,
					}}
				>
					Grants Pass, Oregon, has laws that restrict camping on public property.
					Relying on its decision in Martin v. Boise, the Ninth Circuit held that the
					Eighth Amendment barred the city from enforcing those laws against people
					experiencing homelessness when shelter beds were unavailable. The city
					sought review in this Court.
				</div>
				<div style={{position: 'relative', marginTop: 22, fontSize: 25.5, lineHeight: 1.5}}>
					{HELD_LINES.map((line, i) => {
						const p = ramp(
							frame,
							HIGHLIGHT_AT + i * 13,
							HIGHLIGHT_AT + i * 13 + 17,
							Easing.bezier(0.5, 0, 0.3, 1)
						);
						return (
							<div
								key={line}
								style={{whiteSpace: 'nowrap', paddingLeft: i === 0 ? 28 : 0}}
							>
								<span style={{position: 'relative', display: 'inline-block'}}>
									<span
										style={{
											position: 'absolute',
											left: -5,
											top: '16%',
											height: '76%',
											width: `calc(${p.toFixed(4)} * (100% + 10px))`,
											background: 'rgba(242,165,65,0.62)',
											mixBlendMode: 'multiply',
											borderRadius: 2,
										}}
									/>
									<span style={{position: 'relative'}}>
										{i === 0 ? (
											<>
												<i>Held:</i>
												{line.slice(5)}
											</>
										) : (
											line
										)}
									</span>
								</span>
							</div>
						);
					})}
				</div>
				<div
					style={{
						position: 'relative',
						fontSize: 23,
						lineHeight: 1.5,
						marginTop: 18,
						textIndent: 28,
						textAlign: 'justify',
						filter: 'blur(2.6px)',
						opacity: 0.75,
					}}
				>
					(a) The Cruel and Unusual Punishments Clause focuses on the method or kind
					of punishment a government may impose after a criminal conviction, not on
					whether a government may criminalize particular behavior in the first
					place.
				</div>
				<div
					style={{
						position: 'relative',
						fontSize: 23,
						lineHeight: 1.5,
						marginTop: 14,
						marginBottom: 360,
						textIndent: 28,
						textAlign: 'justify',
						filter: 'blur(2.8px)',
						opacity: 0.7,
					}}
				>
					(b) Robinson v. California held that a State may not criminalize the status
					of being addicted to narcotics. The public-camping laws at issue here do not
					criminalize status; they apply to everyone, regulating conduct on public
					property, and Robinson does not reach them.
				</div>
				{/* soft desk light falling across the page */}
				<div
					style={{
						position: 'absolute',
						inset: 0,
						background:
							'linear-gradient(160deg, rgba(255,250,235,0.10) 0%, rgba(0,0,0,0) 40%, rgba(20,14,6,0.22) 100%)',
						pointerEvents: 'none',
					}}
				/>
			</div>
		</div>
	);
};

const SceneRuling: React.FC<{frame: number}> = ({frame}) => (
	<AbsoluteFill>
		<AbsoluteFill
			style={{
				background:
					'radial-gradient(ellipse 70% 90% at 70% 40%, #1c1a17 0%, #121110 55%, #0b0b0b 100%)',
			}}
		/>
		<Paper frame={frame} />
		{/* falloff so the page sits in the dark */}
		<AbsoluteFill
			style={{
				background:
					'linear-gradient(90deg, rgba(11,11,11,0.96) 0%, rgba(11,11,11,0.9) 42%, rgba(11,11,11,0) 52%), linear-gradient(0deg, rgba(11,11,11,0.7) 0%, rgba(11,11,11,0) 22%)',
			}}
		/>
		<Kicker
			frame={frame}
			at={10}
			lines={['City of Grants Pass v. Johnson', 'Decided June 28, 2024 · 6–3']}
			style={{left: 140, top: 286}}
		/>
		<Narration
			frame={frame}
			style={{left: 140, top: 392, width: 700, fontSize: 64, lineHeight: 1.16}}
			segs={[
				{text: 'And in 2024', at: 22},
				{text: 'the Supreme Court cleared the way', at: 52},
				{text: 'for cities to fine people', at: 118},
				{text: 'for sleeping in their own cars.', at: 172},
			]}
		/>
	</AbsoluteFill>
);

/* ------------------------------------------------------------------ */
/* Map data                                                            */
/* ------------------------------------------------------------------ */

const XS = [-380, -150, 100, 310, 570, 810, 1030, 1280, 1510, 1770, 2010, 2230, 2480];
const YS = [-260, -70, 140, 320, 520, 710, 920, 1120, 1310];
const MAIN_X = 1030;
const MAIN_Y = 520;
const streetW = (v: number, main: number) => (v === main ? 44 : 24);

const LOT = {x1: 1526, y1: 546, x2: 1650, y2: 694};
const STALL_X = 1598;
const STALL_H = 21;
const DEST_BLOCK = {i: 8, j: 4};
const DETOUR_BLOCK = {i: 7, j: 3};

type Rect = {x: number; y: number; w: number; h: number};
type Block = Rect & {i: number; j: number; kind: 'parcels' | 'park' | 'dest'; cx: number};
type Parcel = Rect & {shade: number};

const buildMap = () => {
	const blocks: Block[] = [];
	const parcels: Parcel[] = [];
	const trees: {x: number; y: number; r: number}[] = [];
	const alleys: Rect[] = [];

	for (let i = 0; i < XS.length - 1; i++) {
		for (let j = 0; j < YS.length - 1; j++) {
			const x1 = XS[i] + streetW(XS[i], MAIN_X) / 2;
			const x2 = XS[i + 1] - streetW(XS[i + 1], MAIN_X) / 2;
			const y1 = YS[j] + streetW(YS[j], MAIN_Y) / 2;
			const y2 = YS[j + 1] - streetW(YS[j + 1], MAIN_Y) / 2;
			const isDest = i === DEST_BLOCK.i && j === DEST_BLOCK.j;
			const isPark = (i === 2 && j === 5) || (i === 10 && j === 2);
			const kind = isDest ? 'dest' : isPark ? 'park' : 'parcels';
			blocks.push({x: x1, y: y1, w: x2 - x1, h: y2 - y1, i, j, kind, cx: (x1 + x2) / 2});

			if (isPark) {
				const n = 46;
				for (let k = 0; k < n; k++) {
					trees.push({
						x: x1 + 10 + random(`tx${i}${j}${k}`) * (x2 - x1 - 20),
						y: y1 + 10 + random(`ty${i}${j}${k}`) * (y2 - y1 - 20),
						r: 4 + random(`tr${i}${j}${k}`) * 6,
					});
				}
				continue;
			}

			// Sub-blocks split by an alley (forced for the car's starting block)
			const forceAlley = i === 3 && j === 2;
			const hasAlley = !isDest && (forceAlley || random(`al${i}${j}`) > 0.45);
			const subs: Rect[] = [];
			if (isDest) {
				subs.push({x: LOT.x2 + 6, y: y1, w: x2 - LOT.x2 - 6, h: y2 - y1});
			} else if (hasAlley) {
				const mid = (y1 + y2) / 2;
				alleys.push({x: x1, y: mid - 4, w: x2 - x1, h: 8});
				subs.push({x: x1, y: y1, w: x2 - x1, h: mid - 4 - y1});
				subs.push({x: x1, y: mid + 4, w: x2 - x1, h: y2 - mid - 4});
			} else {
				subs.push({x: x1, y: y1, w: x2 - x1, h: y2 - y1});
			}

			subs.forEach((s, si) => {
				const rows = s.h > 82 ? 2 : 1;
				for (let r = 0; r < rows; r++) {
					const ry = s.y + (r * s.h) / rows;
					const rh = s.h / rows;
					let px = s.x;
					let k = 0;
					while (px < s.x + s.w - 12) {
						const pw = Math.min(
							26 + random(`pw${i}${j}${si}${r}${k}`) * 40,
							s.x + s.w - px
						);
						parcels.push({
							x: px + 1.5,
							y: ry + 1.5,
							w: pw - 3,
							h: rh - 3,
							shade: random(`ps${i}${j}${si}${r}${k}`),
						});
						px += pw;
						k++;
					}
				}
			});
		}
	}

	const intersections: {x: number; y: number; on: number}[] = [];
	XS.forEach((x, a) =>
		YS.forEach((y, b) => {
			if (random(`li${a}${b}`) > 0.42) intersections.push({x, y, on: 0});
		})
	);
	return {blocks, parcels, trees, alleys, intersections};
};

/* Car route along street centrelines, corners rounded */
const ROUTE_PTS: [number, number][] = [
	[440, 230],
	[570, 230],
	[570, 520],
	[1030, 520],
	[1280, 520],
	[1280, 320],
	[1510, 320],
	[1510, 620],
	[STALL_X + 24, 620],
];
const CAR_END = {x: STALL_X + 24, y: 620};

const buildRoute = () => {
	const pts: {x: number; y: number}[] = [];
	const R = 16;
	for (let k = 0; k < ROUTE_PTS.length; k++) {
		const [x, y] = ROUTE_PTS[k];
		if (k === 0 || k === ROUTE_PTS.length - 1) {
			pts.push({x, y});
			continue;
		}
		const [px, py] = ROUTE_PTS[k - 1];
		const [nx, ny] = ROUTE_PTS[k + 1];
		const lin = Math.hypot(x - px, y - py);
		const lout = Math.hypot(nx - x, ny - y);
		const a = {x: x - ((x - px) / lin) * R, y: y - ((y - py) / lin) * R};
		const b = {x: x + ((nx - x) / lout) * R, y: y + ((ny - y) / lout) * R};
		for (let t = 0; t <= 1.0001; t += 1 / 10) {
			pts.push({
				x: (1 - t) * (1 - t) * a.x + 2 * (1 - t) * t * x + t * t * b.x,
				y: (1 - t) * (1 - t) * a.y + 2 * (1 - t) * t * y + t * t * b.y,
			});
		}
	}
	const cum = [0];
	for (let k = 1; k < pts.length; k++) {
		cum.push(cum[k - 1] + Math.hypot(pts[k].x - pts[k - 1].x, pts[k].y - pts[k - 1].y));
	}
	return {pts, cum, len: cum[cum.length - 1]};
};

type Route = ReturnType<typeof buildRoute>;

const pointAt = (route: Route, d: number) => {
	const {pts, cum, len} = route;
	const dd = Math.max(0, Math.min(len, d));
	let k = 1;
	while (k < cum.length - 1 && cum[k] < dd) k++;
	const t = (dd - cum[k - 1]) / (cum[k] - cum[k - 1] || 1);
	return {
		x: pts[k - 1].x + (pts[k].x - pts[k - 1].x) * t,
		y: pts[k - 1].y + (pts[k].y - pts[k - 1].y) * t,
		k,
	};
};

const headingAt = (route: Route, d: number) => {
	const a = pointAt(route, d - 3);
	const b = pointAt(route, d + 3);
	return (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI;
};

// Distance along the route over time: piecewise-linear, then box-filtered
// so every start and stop eases instead of snapping.
const DRIVE: [number, number][] = [
	[0, 0],
	[428, 0],
	[452, 128],
	[478, 418],
	[522, 880],
	[540, 1128],
	[558, 1318],
	[576, 1318],
	[598, 1552],
	[622, 1840],
	[648, 1949],
];

const rawDist = (f: number, len: number) =>
	Math.min(
		len,
		interpolate(
			f,
			DRIVE.map((d) => d[0]),
			DRIVE.map((d) => Math.min(d[1], len)),
			clamp
		)
	);

const distAt = (f: number, len: number) => {
	let s = 0;
	const N = 8;
	for (let k = -N; k <= N; k++) s += rawDist(f + k, len);
	return s / (2 * N + 1);
};

/* Camera: world -> screen */
type Cam = {cx: number; cy: number; s: number};
const ZOOM_A = 598;
const ZOOM_B = 672;
const FINAL_SCREEN = {x: 1130, y: 468};

const camB = (f: number): Cam => ({
	cx: interpolate(f, [300, ZOOM_A], [968, 1004], clamp),
	cy: interpolate(f, [300, ZOOM_A], [548, 530], clamp),
	s: interpolate(f, [300, ZOOM_A], [1.0, 1.05], clamp),
});

const toScreen = (c: Cam, x: number, y: number) => ({
	x: (x - c.cx) * c.s + W / 2,
	y: (y - c.cy) * c.s + H / 2,
});

const camAt = (f: number): Cam => {
	if (f <= ZOOM_A) return camB(f);
	const start = camB(ZOOM_A);
	const s0 = toScreen(start, CAR_END.x, CAR_END.y);
	const p = ramp(f, ZOOM_A, ZOOM_B, easeInOut);
	const drift = interpolate(f, [ZOOM_B, NIGHTLY_SEARCH_DURATION], [0, 1], clamp);
	const s1 = 3.4 * Math.exp(Math.log(3.62 / 3.4) * drift);
	const s = Math.exp(Math.log(start.s) + (Math.log(s1) - Math.log(start.s)) * p);
	const target = {
		x: s0.x + (FINAL_SCREEN.x - s0.x) * p - 8 * drift,
		y: s0.y + (FINAL_SCREEN.y - s0.y) * p + 6 * drift,
	};
	return {
		cx: CAR_END.x - (target.x - W / 2) / s,
		cy: CAR_END.y - (target.y - H / 2) / s,
		s,
	};
};

const camTransform = (c: Cam) =>
	`translate(${W / 2} ${H / 2}) scale(${c.s}) translate(${-c.cx} ${-c.cy})`;

/* Night: an edge sweeping east -> west across the screen */
const nightEdge = (f: number) =>
	interpolate(f, [312, 590], [2250, -520], {...clamp, easing: Easing.bezier(0.35, 0, 0.55, 1)});

// First frame the dark side of the edge reaches screen-x `sx`
const darkFrameFor = (worldX: number) => {
	for (let f = 300; f < 640; f++) {
		const sx = toScreen(camB(f), worldX, 0).x;
		if (nightEdge(f) < sx - 120) return f;
	}
	return 640;
};

/* ------------------------------------------------------------------ */
/* Map layers                                                          */
/* ------------------------------------------------------------------ */

type MapData = ReturnType<typeof buildMap>;

const MapBase: React.FC<{map: MapData}> = React.memo(({map}) => (
	<>
		{map.blocks.map((b) =>
			b.kind === 'park' ? (
				<rect key={`b${b.i}-${b.j}`} x={b.x} y={b.y} width={b.w} height={b.h} fill="#18201c" rx={3} />
			) : (
				<rect key={`b${b.i}-${b.j}`} x={b.x} y={b.y} width={b.w} height={b.h} fill="#151920" rx={3} />
			)
		)}
		{map.parcels.map((p, k) => (
			<rect
				key={k}
				x={p.x}
				y={p.y}
				width={p.w}
				height={p.h}
				fill={`hsl(216, 12%, ${12.5 + p.shade * 5}%)`}
				rx={1.5}
			/>
		))}
		{map.trees.map((t, k) => (
			<circle key={k} cx={t.x} cy={t.y} r={t.r} fill="#223026" />
		))}
		{map.alleys.map((a, k) => (
			<rect key={k} x={a.x} y={a.y} width={a.w} height={a.h} fill="#101318" />
		))}
		{/* the lot */}
		<rect
			x={LOT.x1}
			y={LOT.y1}
			width={LOT.x2 - LOT.x1}
			height={LOT.y2 - LOT.y1}
			fill="#13161b"
			rx={2}
		/>
		{Array.from({length: 8}, (_, k) => {
			const y = LOT.y1 + 4 + k * STALL_H;
			return (
				<line
					key={k}
					x1={STALL_X}
					x2={LOT.x2 - 3}
					y1={y}
					y2={y}
					stroke="#3d434c"
					strokeWidth={1.1}
				/>
			);
		})}
		{/* centre lines on the two main roads */}
		<line x1={-600} x2={2700} y1={MAIN_Y} y2={MAIN_Y} stroke="#2a2f37" strokeWidth={1} strokeDasharray="10 9" />
		<line x1={MAIN_X} x2={MAIN_X} y1={-400} y2={1500} stroke="#2a2f37" strokeWidth={1} strokeDasharray="10 9" />
		{[
			{t: 'MAIN ST', x: 1112, y: MAIN_Y + 3.5, r: 0},
			{t: 'MAIN ST', x: 300, y: MAIN_Y + 3.5, r: 0},
			{t: 'GRANT AVE', x: MAIN_X + 3.5, y: 240, r: 90},
			{t: 'OAK ST', x: 1510 + 3, y: 430, r: 90},
			{t: 'W 3RD ST', x: 1350, y: 320 + 3, r: 0},
			{t: 'W 5TH ST', x: 1600, y: 710 + 3, r: 0},
			{t: 'ELM ST', x: 570 + 3, y: 400, r: 90},
		].map((l, k) => (
			<text
				key={k}
				x={l.x}
				y={l.y}
				transform={l.r ? `rotate(${l.r} ${l.x} ${l.y})` : undefined}
				fontFamily={MONO}
				fontSize={9}
				letterSpacing={1.6}
				fill="rgba(200,206,216,0.32)"
			>
				{l.t}
			</text>
		))}
	</>
));

const Car: React.FC<{
	x: number;
	y: number;
	angle: number;
	lights: number;
	brake: number;
	shade: number;
	dim: number;
}> = ({x, y, angle, lights, brake, shade, dim}) => (
	<g transform={`translate(${x} ${y}) rotate(${angle}) scale(1.25)`}>
		{/* headlight throw */}
		<g style={{mixBlendMode: 'screen'}} opacity={lights}>
			<polygon points="14,-5 14,5 74,26 74,-26" fill="url(#beam)" />
		</g>
		<rect x={-16} y={-8} width={32} height={16} rx={4.5} fill="#000" opacity={0.35} transform="translate(1.2 1.6)" />
		<g opacity={dim}>
			<rect x={-15.5} y={-7.2} width={31} height={14.4} rx={4.2} fill="#c9c2b2" />
			{/* windscreen, roof, rear window */}
			<path d="M3.2,-6 L8.6,-5.2 Q9.6,0 8.6,5.2 L3.2,6 Z" fill="#262b33" />
			<rect x={-8.5} y={-5.6} width={11.4} height={11.2} rx={1.6} fill="#b7b09f" />
			<path d="M-9,-5.6 L-12,-4.8 Q-12.8,0 -12,4.8 L-9,5.6 Z" fill="#262b33" />
			{/* windscreen shade */}
			<path
				d="M3.2,-6 L8.6,-5.2 Q9.6,0 8.6,5.2 L3.2,6 Z"
				fill="#d8dbe0"
				clipPath="url(#shadeClip)"
				opacity={shade > 0 ? 1 : 0}
			/>
			{/* headlamps & tail lamps */}
			<rect x={13.6} y={-6} width={1.6} height={3} rx={0.6} fill="#fff1d2" opacity={0.25 + 0.75 * lights} />
			<rect x={13.6} y={3} width={1.6} height={3} rx={0.6} fill="#fff1d2" opacity={0.25 + 0.75 * lights} />
			<rect x={-15.6} y={-6} width={1.4} height={3} rx={0.6} fill="#ff4a3a" opacity={0.2 + 0.8 * brake} />
			<rect x={-15.6} y={3} width={1.4} height={3} rx={0.6} fill="#ff4a3a" opacity={0.2 + 0.8 * brake} />
		</g>
		<g style={{mixBlendMode: 'screen'}} opacity={brake * 0.8}>
			<circle cx={-17} cy={-4.5} r={5} fill="url(#tail)" />
			<circle cx={-17} cy={4.5} r={5} fill="url(#tail)" />
		</g>
		<defs>
			<clipPath id="shadeClip">
				<rect x={3} y={-7} width={7} height={14 * shade} />
			</clipPath>
		</defs>
	</g>
);

const SceneMap: React.FC<{frame: number}> = ({frame}) => {
	const map = useMemo(buildMap, []);
	const route = useMemo(buildRoute, []);
	const blockDark = useMemo(
		() =>
			map.blocks.map((b) => {
				if (b.i === DETOUR_BLOCK.i && b.j === DETOUR_BLOCK.j) return 556;
				return darkFrameFor(b.cx) + Math.round(random(`hj${b.i}${b.j}`) * 22) - 4;
			}),
		[map]
	);
	const lightOn = useMemo(
		() => map.intersections.map((l, k) => darkFrameFor(l.x) - 10 + Math.round(random(`lo${k}`) * 26)),
		[map]
	);

	const cam = camAt(frame);
	const tf = camTransform(cam);
	const hatchGap = 7 * Math.pow(cam.s, -0.6);
	const hatchStroke = 1.5 * Math.pow(cam.s, -0.75);

	const d = distAt(frame, route.len);
	const car = pointAt(route, d);
	const heading = headingAt(route, Math.max(4, Math.min(route.len - 4, d)));
	const speed = Math.abs(distAt(frame + 1, route.len) - distAt(frame - 1, route.len));

	// Operation beats
	const ENGINE_OFF = 652;
	const LIGHTS_OFF = 700;
	const SHADE_UP = 744;
	const lights =
		ramp(frame, 418, 428) * (1 - ramp(frame, LIGHTS_OFF, LIGHTS_OFF + 5, Easing.linear));
	const brakeBase = speed < 1.2 && frame > 430 ? 1 : 0;
	const brake = frame > ENGINE_OFF ? 0 : frame < 430 ? 0 : brakeBase * 0.9;
	const shade = ramp(frame, SHADE_UP, SHADE_UP + 26, easeInOut);
	const dim = interpolate(frame, [300, 418, 428], [0.55, 0.55, 1], clamp);

	// Trail of the search so far
	const trail: string[] = [];
	for (let k = 0; k < route.pts.length && route.cum[k] < d; k++) {
		trail.push(`${route.pts[k].x.toFixed(1)},${route.pts[k].y.toFixed(1)}`);
	}
	trail.push(`${car.x.toFixed(1)},${car.y.toFixed(1)}`);
	const trailFade = 1 - ramp(frame, 660, 720, Easing.linear) * 0.75;

	// "Still allowed" outline
	const allowP = ramp(frame, 500, 548, easeInOut);
	const lotPerim = 2 * (LOT.x2 - LOT.x1 + LOT.y2 - LOT.y1 + 16) * 1.12;

	// Screen-space light
	const edge = nightEdge(frame);
	const settle = ramp(frame, 690, 760, Easing.linear);

	return (
		<AbsoluteFill style={{background: '#0c0f13'}}>
			<svg width={W} height={H} style={{position: 'absolute'}}>
				<g transform={tf}>
					<rect x={-800} y={-600} width={3600} height={2400} fill="#0c0f13" />
					<MapBase map={map} />
				</g>
			</svg>

			{/* last light in the west, night arriving from the east */}
			<div
				style={{
					position: 'absolute',
					top: 0,
					height: H,
					left: edge - 3200,
					width: 6400,
					background:
						'linear-gradient(90deg, rgba(238,158,88,0.17) 0px, rgba(238,158,88,0.07) 2700px, rgba(4,7,14,0.64) 3600px, rgba(4,7,14,0.64) 6400px)',
				}}
			/>
			<AbsoluteFill style={{background: 'rgba(3,4,7,1)', opacity: settle * 0.18}} />

			<svg width={W} height={H} style={{position: 'absolute'}}>
				<defs>
					<pattern
						id="hatch"
						patternUnits="userSpaceOnUse"
						width={hatchGap}
						height={hatchGap}
						patternTransform="rotate(45)"
					>
						<line x1={0} y1={0} x2={0} y2={hatchGap} stroke={RED} strokeWidth={hatchStroke} />
					</pattern>
					<radialGradient id="lamp">
						<stop offset="0%" stopColor="#ffb760" stopOpacity={0.42} />
						<stop offset="35%" stopColor="#f29a3c" stopOpacity={0.16} />
						<stop offset="100%" stopColor="#f29a3c" stopOpacity={0} />
					</radialGradient>
					<linearGradient id="beam" x1="0" x2="1" y1="0" y2="0">
						<stop offset="0%" stopColor="#ffe6b8" stopOpacity={0.55} />
						<stop offset="100%" stopColor="#ffe6b8" stopOpacity={0} />
					</linearGradient>
					<radialGradient id="tail">
						<stop offset="0%" stopColor="#ff3b2e" stopOpacity={0.7} />
						<stop offset="100%" stopColor="#ff3b2e" stopOpacity={0} />
					</radialGradient>
				</defs>
				<g transform={tf}>
					{/* prohibited after dark */}
					{map.blocks.map((b, k) => {
						if (b.kind === 'dest') return null;
						const p = ramp(frame, blockDark[k], blockDark[k] + 14, Easing.linear);
						if (p <= 0) return null;
						return (
							<g key={k} opacity={p * (1 - settle * 0.25)}>
								<rect x={b.x} y={b.y} width={b.w} height={b.h} fill="url(#hatch)" opacity={0.5} rx={3} />
								<rect
									x={b.x + 0.75}
									y={b.y + 0.75}
									width={b.w - 1.5}
									height={b.h - 1.5}
									fill="none"
									stroke={RED}
									strokeOpacity={0.6}
									strokeWidth={1.2}
									vectorEffect="non-scaling-stroke"
									rx={3}
								/>
							</g>
						);
					})}

					{/* the one place still allowed */}
					<rect
						x={LOT.x1 - 4}
						y={LOT.y1 - 4}
						width={LOT.x2 - LOT.x1 + 8}
						height={LOT.y2 - LOT.y1 + 8}
						fill={AMBER}
						fillOpacity={0.05 * allowP}
						stroke={AMBER}
						strokeWidth={1.8}
						vectorEffect="non-scaling-stroke"
						strokeDasharray={allowP >= 1 ? undefined : `${lotPerim * allowP} ${lotPerim}`}
						rx={3}
					/>

					{/* street lamps */}
					<g style={{mixBlendMode: 'screen'}}>
						{map.intersections.map((l, k) => {
							const p = ramp(frame, lightOn[k], lightOn[k] + 22, Easing.bezier(0.5, 0, 0.6, 1));
							if (p <= 0) return null;
							return (
								<g key={k} opacity={p}>
									<circle cx={l.x} cy={l.y} r={40} fill="url(#lamp)" />
									<circle cx={l.x} cy={l.y} r={1.8} fill="#ffd9a6" />
								</g>
							);
						})}
						{(() => {
							const p = ramp(frame, 470, 495, Easing.bezier(0.5, 0, 0.6, 1));
							return (
								<g opacity={p}>
									<circle cx={1556} cy={572} r={64} fill="url(#lamp)" />
									<circle cx={1556} cy={572} r={1.8} fill="#ffd9a6" />
								</g>
							);
						})()}
					</g>

					{/* the search so far */}
					<polyline
						points={trail.join(' ')}
						fill="none"
						stroke={AMBER}
						strokeOpacity={0.62 * trailFade}
						strokeWidth={1.7 / Math.max(1, cam.s * 0.7)}
						strokeDasharray={`${3 / Math.max(1, cam.s * 0.6)} ${5 / Math.max(1, cam.s * 0.6)}`}
						strokeLinecap="round"
					/>

					<Car
						x={car.x}
						y={car.y}
						angle={heading}
						lights={lights}
						brake={brake}
						shade={shade}
						dim={dim}
					/>
				</g>
			</svg>

			<OperationLog frame={frame} cam={cam} beats={[ENGINE_OFF, LIGHTS_OFF, SHADE_UP]} />
			<Clock frame={frame} />
			<Legend frame={frame} />

			{/* text scrim */}
			<AbsoluteFill
				style={{
					background:
						'linear-gradient(0deg, rgba(8,9,12,0.94) 0%, rgba(8,9,12,0.8) 22%, rgba(8,9,12,0) 46%)',
				}}
			/>
			<Narration
				frame={frame}
				style={{
					left: 140,
					bottom: 104,
					width: 1240,
					fontSize: 58,
					lineHeight: 1.16,
					opacity: 1 - ramp(frame, 596, 616, Easing.linear),
				}}
				segs={[
					{text: 'The nightly task shifted from', at: 334},
					{text: 'staying hidden', at: 364, strikeAt: 414},
					{text: 'to finding a patch of ground', at: 412, br: true},
					{text: 'that’s still allowed', at: 458},
					{text: 'when the sun goes down.', at: 506, br: true},
				]}
			/>
			<Narration
				frame={frame}
				style={{left: 140, bottom: 104, width: 1240, fontSize: 58, lineHeight: 1.16}}
				segs={[
					{text: 'That search turns every evening', at: 628},
					{text: 'into a quiet,', at: 686, br: true},
					{text: 'careful operation.', at: 726},
				]}
			/>
		</AbsoluteFill>
	);
};

/* clock: a time-lapse from dusk to after nine */
const CLOCK: [number, number][] = [
	[300, 19 * 60 + 36],
	[598, 20 * 60 + 58],
	[652, 21 * 60 + 2],
	[700, 21 * 60 + 3],
	[744, 21 * 60 + 9],
	[840, 21 * 60 + 11],
];
const fmt = (mins: number) => {
	const m = Math.floor(mins);
	const h24 = Math.floor(m / 60);
	const h = h24 > 12 ? h24 - 12 : h24;
	return `${h}:${String(m % 60).padStart(2, '0')} PM`;
};
const clockAt = (f: number) =>
	interpolate(f, CLOCK.map((c) => c[0]), CLOCK.map((c) => c[1]), clamp);

const Clock: React.FC<{frame: number}> = ({frame}) => {
	const p = ramp(frame, 318, 342);
	return (
		<div
			style={{
				position: 'absolute',
				right: 140,
				top: 92,
				textAlign: 'right',
				opacity: p,
				fontFamily: MONO,
				color: INK,
			}}
		>
			<div
				style={{
					fontSize: 46,
					fontWeight: 400,
					letterSpacing: 1,
					fontVariantNumeric: 'tabular-nums',
					textShadow: '0 0 24px rgba(0,0,0,0.9), 0 0 6px rgba(0,0,0,0.8)',
				}}
			>
				{fmt(clockAt(frame))}
			</div>
		</div>
	);
};

const Legend: React.FC<{frame: number}> = ({frame}) => {
	const out = 1 - ramp(frame, 600, 624, Easing.linear);
	const a = ramp(frame, 360, 384) * out;
	const b = ramp(frame, 516, 540) * out;
	const row: React.CSSProperties = {
		display: 'flex',
		alignItems: 'center',
		justifyContent: 'flex-end',
		gap: 14,
	};
	return (
		<div
			style={{
				position: 'absolute',
				right: 140,
				top: 166,
				fontFamily: MONO,
				fontSize: 15,
				fontWeight: 500,
				letterSpacing: 2.2,
				color: INK_DIM,
				lineHeight: 2.1,
			}}
		>
			<div style={{...row, opacity: a}}>
				Overnight parking prohibited
				<svg width={22} height={14}>
					<defs>
						<pattern id="lh" patternUnits="userSpaceOnUse" width={5} height={5} patternTransform="rotate(45)">
							<line x1={0} y1={0} x2={0} y2={5} stroke={RED} strokeWidth={1.4} />
						</pattern>
					</defs>
					<rect x={1} y={1} width={20} height={12} fill="url(#lh)" stroke={RED} strokeWidth={1} rx={2} />
				</svg>
			</div>
			<div style={{...row, opacity: b}}>
				Still allowed
				<svg width={22} height={14}>
					<rect
						x={1}
						y={1}
						width={20}
						height={12}
						fill="rgba(242,165,65,0.08)"
						stroke={AMBER}
						strokeWidth={1.3}
						rx={2}
					/>
				</svg>
			</div>
		</div>
	);
};

const OperationLog: React.FC<{frame: number; cam: Cam; beats: number[]}> = ({
	frame,
	cam,
	beats,
}) => {
	const entries = ['Engine off', 'Lights off', 'Shade up'];
	const carS = toScreen(cam, CAR_END.x, CAR_END.y);
	const x0 = carS.x + 120;
	const top = carS.y - 74;
	const lead = ramp(frame, beats[0] - 6, beats[0] + 14, easeInOut);
	const fadeAll = 1 - ramp(frame, 806, 830, Easing.linear);
	return (
		<div style={{position: 'absolute', inset: 0, opacity: fadeAll}}>
			<svg width={W} height={H} style={{position: 'absolute'}}>
				<line
					x1={carS.x + 76}
					y1={carS.y}
					x2={carS.x + 76 + (x0 - 18 - carS.x - 76) * lead}
					y2={carS.y}
					stroke={INK_DIM}
					strokeWidth={1}
				/>
				<line
					x1={x0 - 18}
					x2={x0 - 18}
					y1={carS.y - (carS.y - top - 8) * lead}
					y2={top + 8 + 2 * 46 * lead}
					stroke={INK_DIM}
					strokeWidth={1}
					opacity={lead}
				/>
			</svg>
			{entries.map((e, i) => {
				const p = ramp(frame, beats[i], beats[i] + 16);
				return (
					<div
						key={e}
						style={{
							position: 'absolute',
							left: x0,
							top: top + i * 46,
							fontFamily: MONO,
							fontSize: 19,
							letterSpacing: 1.8,
							color: INK,
							textTransform: 'uppercase',
							opacity: p,
							transform: `translateX(${(1 - p) * 10}px)`,
							whiteSpace: 'nowrap',
						}}
					>
						<span style={{color: INK_DIM, marginRight: 18, fontVariantNumeric: 'tabular-nums'}}>
							{fmt(clockAt(beats[i]))}
						</span>
						{e}
					</div>
				);
			})}
		</div>
	);
};


export const NightlySearch: React.FC = () => {
	useFonts();
	const frame = useCurrentFrame();
	const aOpacity = interpolate(frame, [0, 18, 276, 298], [0, 1, 1, 0], clamp);
	const bOpacity = interpolate(
		frame,
		[300, 326, NIGHTLY_SEARCH_DURATION - 34, NIGHTLY_SEARCH_DURATION - 6],
		[0, 1, 1, 0],
		clamp
	);
	return (
		<AbsoluteFill style={{backgroundColor: BG}}>
			{frame < 300 ? (
				<AbsoluteFill style={{opacity: aOpacity}}>
					<SceneRuling frame={frame} />
				</AbsoluteFill>
			) : (
				<AbsoluteFill style={{opacity: bOpacity}}>
					<SceneMap frame={frame} />
				</AbsoluteFill>
			)}
			<AbsoluteFill
				style={{
					background:
						'radial-gradient(ellipse at center, rgba(0,0,0,0) 58%, rgba(0,0,0,0.5) 100%)',
					pointerEvents: 'none',
				}}
			/>
			<Grain frame={frame} />
		</AbsoluteFill>
	);
};
