import React from 'react';
import {
	AbsoluteFill,
	Easing,
	interpolate,
	spring,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';
import '@fontsource/roboto/900.css';
import {BUYERS, Point, SELLERS, T_END, T_START} from './sellersBuyersData';

const FONT = 'Roboto, sans-serif';
const BLUE = '#3f9fcd';
const RED = '#b71c1c';
const INK = '#111111';
const MUTED = '#8a8a8a';
const GRID = '#e3e3e3';

const W = 1920;
const PLOT = {left: 150, right: 1640, top: 250, bottom: 900};
const V_MIN = 940000;
const V_MAX = 1900000;
const T_AXIS_END = 2026.75;

const xFor = (t: number) =>
	PLOT.left + ((t - T_START) / (T_AXIS_END - T_START)) * (PLOT.right - PLOT.left);
const yFor = (v: number) =>
	PLOT.bottom - ((v - V_MIN) / (V_MAX - V_MIN)) * (PLOT.bottom - PLOT.top);

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);
const drawEase = Easing.bezier(0.42, 0, 0.3, 1);

const DRAW_START = 85;
const DRAW_END = 330;

const valueAt = (pts: Point[], t: number) => {
	if (t <= pts[0].t) return pts[0].v;
	for (let i = 1; i < pts.length; i++) {
		if (pts[i].t >= t) {
			const a = pts[i - 1];
			const b = pts[i];
			return a.v + ((t - a.t) / (b.t - a.t)) * (b.v - a.v);
		}
	}
	return pts[pts.length - 1].v;
};

const pathUpTo = (pts: Point[], t: number) => {
	const visible = pts.filter((p) => p.t < t);
	visible.push({t, v: valueAt(pts, t)});
	return visible
		.map((p, i) => `${i ? 'L' : 'M'}${xFor(p.t).toFixed(2)},${yFor(p.v).toFixed(2)}`)
		.join(' ');
};

const fmt = (v: number) => Math.round(v).toLocaleString('en-US');

const Title: React.FC<{frame: number}> = ({frame}) => {
	const words = 'Number of Sellers Jumps to 6-Year High'.split(' ');
	const sub = interpolate(frame, [22, 52], [0, 1], {...clamp, easing: easeOut});
	return (
		<>
			<div
				style={{
					position: 'absolute',
					left: PLOT.left - 110,
					top: 58,
					fontFamily: FONT,
					fontWeight: 900,
					fontSize: 66,
					color: INK,
					letterSpacing: -1,
					display: 'flex',
					gap: 18,
				}}
			>
				{words.map((w, i) => {
					const p = interpolate(frame, [4 + i * 4, 30 + i * 4], [0, 1], {
						...clamp,
						easing: easeOut,
					});
					return (
						<span
							key={i}
							style={{
								display: 'inline-block',
								opacity: p,
								transform: `translateY(${(1 - p) * 40}px)`,
								filter: `blur(${(1 - p) * 8}px)`,
							}}
						>
							{w}
						</span>
					);
				})}
			</div>
			<div
				style={{
					position: 'absolute',
					left: PLOT.left - 110,
					top: 150,
					fontFamily: FONT,
					fontSize: 34,
					color: '#333',
					opacity: sub,
					transform: `translateY(${(1 - sub) * 20}px)`,
				}}
			>
				Estimated number of U.S. homebuyers and sellers actively in the market
			</div>
		</>
	);
};

const Axes: React.FC<{frame: number}> = ({frame}) => {
	const gridValues = [1e6, 1.1e6, 1.2e6, 1.3e6, 1.4e6, 1.5e6, 1.6e6, 1.7e6, 1.8e6];
	const years = Array.from({length: 14}, (_, i) => 2013 + i);
	return (
		<>
			<svg width={W} height={1080} style={{position: 'absolute'}}>
				{gridValues.map((v, i) => {
					const p = interpolate(frame, [30 + i * 3, 70 + i * 3], [0, 1], {
						...clamp,
						easing: easeInOut,
					});
					const y = yFor(v);
					return (
						<line
							key={v}
							x1={PLOT.left}
							x2={PLOT.left + (PLOT.right - PLOT.left) * p}
							y1={y}
							y2={y}
							stroke={GRID}
							strokeWidth={2}
						/>
					);
				})}
			</svg>
			{gridValues.map((v, i) => {
				const p = interpolate(frame, [38 + i * 3, 62 + i * 3], [0, 1], {
					...clamp,
					easing: easeOut,
				});
				return (
					<div
						key={v}
						style={{
							position: 'absolute',
							left: PLOT.left - 110,
							top: yFor(v) - 20,
							fontFamily: FONT,
							fontSize: 30,
							color: MUTED,
							opacity: p,
							transform: `translateX(${(1 - p) * -16}px)`,
						}}
					>
						{v === 1e6 ? '1M' : `${(v / 1e6).toFixed(1)}M`}
					</div>
				);
			})}
			{years.map((y, i) => {
				const p = interpolate(frame, [50 + i * 2.5, 76 + i * 2.5], [0, 1], {
					...clamp,
					easing: easeOut,
				});
				return (
					<div
						key={y}
						style={{
							position: 'absolute',
							left: xFor(y) - 60,
							width: 120,
							top: PLOT.bottom + 24,
							textAlign: 'center',
							fontFamily: FONT,
							fontSize: 30,
							color: '#555',
							opacity: p,
							transform: `translateY(${(1 - p) * 14}px)`,
						}}
					>
						{y}
					</div>
				);
			})}
		</>
	);
};

const HeadLabel: React.FC<{
	x: number;
	y: number;
	name: string;
	value: number;
	color: string;
	offset: number;
	opacity: number;
	scale: number;
}> = ({x, y, name, value, color, offset, opacity, scale}) => (
	<div
		style={{
			position: 'absolute',
			left: x + 22,
			top: y - 30 + offset,
			fontFamily: FONT,
			lineHeight: 1.12,
			opacity,
			transform: `scale(${scale})`,
			transformOrigin: 'left center',
			whiteSpace: 'nowrap',
		}}
	>
		<div style={{fontSize: 27, color: INK, fontWeight: 500, letterSpacing: 0.5}}>{name}</div>
		<div
			style={{
				fontSize: 32,
				color,
				fontWeight: 700,
				fontVariantNumeric: 'tabular-nums',
			}}
		>
			{fmt(value)}
		</div>
	</div>
);

export const SellersBuyersChart: React.FC = () => {
	const frame = useCurrentFrame();
	const {fps, durationInFrames} = useVideoConfig();

	const drawP = interpolate(frame, [DRAW_START, DRAW_END], [0, 1], {
		...clamp,
		easing: drawEase,
	});
	const t = T_START + 0.0001 + drawP * (T_END - T_START - 0.0001);
	const sv = valueAt(SELLERS, t);
	const bv = valueAt(BUYERS, t);
	const sx = xFor(t);
	const sy = yFor(sv);
	const by = yFor(bv);

	const headIn = interpolate(frame, [DRAW_START - 10, DRAW_START + 12], [0, 1], {
		...clamp,
		easing: easeOut,
	});
	const finish = spring({frame: frame - DRAW_END, fps, config: {damping: 14, mass: 0.7}});
	const playheadOpacity =
		headIn * interpolate(frame, [DRAW_END, DRAW_END + 20], [1, 0], clamp);

	// The higher line's label sits above its head, the lower one below,
	// sliding smoothly when the lines cross.
	const sep = Math.tanh((sv - bv) / 60000);
	const gap = Math.abs(sy - by);
	const push = Math.max(0, 70 - gap) / 2;
	const sOffset = -sep * push;
	const bOffset = sep * push;

	const pulse = (frame - DRAW_END) % 45;
	const pulseP = frame > DRAW_END ? pulse / 45 : 0;

	const fadeAll = interpolate(frame, [durationInFrames - 15, durationInFrames], [1, 0], clamp);
	const camera = interpolate(frame, [0, durationInFrames], [1.035, 1], {easing: easeOut});
	const source = interpolate(frame, [70, 100], [0, 1], clamp);

	const areaPath = (pts: Point[]) =>
		`${pathUpTo(pts, t)} L${sx.toFixed(2)},${PLOT.bottom} L${PLOT.left},${PLOT.bottom} Z`;

	return (
		<AbsoluteFill style={{backgroundColor: '#ffffff', opacity: fadeAll}}>
			<AbsoluteFill style={{transform: `scale(${camera})`, transformOrigin: '50% 55%'}}>
				<Title frame={frame} />
				<Axes frame={frame} />

				<svg width={W} height={1080} style={{position: 'absolute'}}>
					<defs>
						<linearGradient id="blueFill" x1="0" y1="0" x2="0" y2="1">
							<stop offset="0%" stopColor={BLUE} stopOpacity={0.12} />
							<stop offset="100%" stopColor={BLUE} stopOpacity={0} />
						</linearGradient>
					</defs>

					{drawP > 0 && (
<path d={areaPath(SELLERS)} fill="url(#blueFill)" />
					)}

					<line
						x1={sx}
						x2={sx}
						y1={PLOT.top + 10}
						y2={PLOT.bottom}
						stroke="#999"
						strokeWidth={1.5}
						strokeDasharray="4 6"
						opacity={playheadOpacity * 0.8}
					/>

					{drawP > 0 && (
						<>
							<path
								d={pathUpTo(SELLERS, t)}
								fill="none"
								stroke={BLUE}
								strokeWidth={4}
								strokeLinejoin="round"
								strokeLinecap="round"
							/>
							<path
								d={pathUpTo(BUYERS, t)}
								fill="none"
								stroke={RED}
								strokeWidth={4}
								strokeLinejoin="round"
								strokeLinecap="round"
							/>
						</>
					)}

					{[
						{y: by, color: RED, ring: false},
						{y: sy, color: BLUE, ring: true},
					].map(({y, color, ring}) => (
						<g key={color} opacity={headIn}>
							{ring && pulseP > 0 && (
								<circle
									cx={sx}
									cy={y}
									r={9 + pulseP * 34}
									fill="none"
									stroke={color}
									strokeWidth={3}
									opacity={(1 - pulseP) * 0.7}
								/>
							)}
							<circle cx={sx} cy={y} r={16} fill={color} opacity={0.18} />
							<circle cx={sx} cy={y} r={8} fill="#fff" stroke={color} strokeWidth={4} />
						</g>
					))}
				</svg>

				<div
					style={{
						position: 'absolute',
						left: sx - 60,
						width: 120,
						top: PLOT.top - 42,
						textAlign: 'center',
						fontFamily: FONT,
						fontWeight: 700,
						fontSize: 28,
						color: '#fff',
						opacity: playheadOpacity,
					}}
				>
					<span
						style={{
							background: '#333',
							borderRadius: 8,
							padding: '4px 14px',
							fontVariantNumeric: 'tabular-nums',
						}}
					>
						{Math.floor(t)}
					</span>
				</div>

				<HeadLabel
					x={sx}
					y={sy}
					name="SELLERS"
					value={sv}
					color={BLUE}
					offset={sOffset}
					opacity={headIn}
					scale={1 + finish * 0.12}
				/>
				<HeadLabel
					x={sx}
					y={by}
					name="BUYERS"
					value={bv}
					color={RED}
					offset={bOffset}
					opacity={headIn}
					scale={1 + finish * 0.12}
				/>

				<div
					style={{
						position: 'absolute',
						left: PLOT.left - 110,
						top: 1010,
						fontFamily: FONT,
						fontSize: 24,
						color: MUTED,
						opacity: source,
					}}
				>
					Source: Redfin data, MLS data
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};
