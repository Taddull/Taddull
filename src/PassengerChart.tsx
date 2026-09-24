import React from 'react';
import {
	AbsoluteFill,
	Easing,
	interpolate,
	random,
	spring,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';
import '@fontsource/crimson-pro/600.css';
import '@fontsource/crimson-pro/700.css';
import '@fontsource/inter/400.css';

const SERIF = '"Crimson Pro", serif';
const SANS = 'Inter, sans-serif';
const BAR = '#fff68f';
const BAR_GLOW = 'rgba(255, 244, 120, 0.55)';

const W = 1920;
const H = 1080;
const PLOT = {left: 210, right: 1790, top: 250, bottom: 905};
const MAX = 100;
const yFor = (v: number) =>
	PLOT.bottom - (v / MAX) * (PLOT.bottom - PLOT.top);

const DATA = [
	{label: 'Heathrow', value: 84.48, x: 640, delay: 78},
	{label: 'Istanbul', value: 84.44, x: 1420, delay: 92},
];
const BAR_W = 214;

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);

const Title: React.FC<{frame: number}> = ({frame}) => {
	const text = 'Annual Passenger Traffic in 2025 (Millions)';
	return (
		<div
			style={{
				position: 'absolute',
				top: 58,
				width: W,
				textAlign: 'center',
				fontFamily: SERIF,
				fontWeight: 700,
				fontSize: 84,
				color: '#f4f1ea',
				letterSpacing: -0.5,
				whiteSpace: 'pre',
			}}
		>
			{text.split('').map((ch, i) => {
				const start = 6 + i * 0.9;
				const p = interpolate(frame, [start, start + 22], [0, 1], {
					...clamp,
					easing: easeOut,
				});
				return (
					<span
						key={i}
						style={{
							display: 'inline-block',
							opacity: p,
							transform: `translateY(${(1 - p) * 38}px) scale(${
								0.9 + 0.1 * p
							})`,
							filter: `blur(${(1 - p) * 10}px)`,
						}}
					>
						{ch}
					</span>
				);
			})}
		</div>
	);
};

const Grid: React.FC<{frame: number}> = ({frame}) => {
	const hLines = Array.from({length: 11}, (_, i) => i * 10);
	const vLines = Array.from({length: 18}, (_, i) => PLOT.left + 90 + i * 88);
	return (
		<svg width={W} height={H} style={{position: 'absolute'}}>
			{hLines.map((v, i) => {
				const p = interpolate(frame, [40 + i * 2.5, 75 + i * 2.5], [0, 1], {
					...clamp,
					easing: easeInOut,
				});
				const y = yFor(v);
				return (
					<line
						key={`h${v}`}
						x1={PLOT.left}
						x2={PLOT.left + (PLOT.right - PLOT.left) * p}
						y1={y}
						y2={y}
						stroke="rgba(255,255,255,0.18)"
						strokeWidth={v % 20 === 0 ? 1.4 : 1}
						strokeDasharray="5 6"
					/>
				);
			})}
			{vLines.map((x, i) => {
				const p = interpolate(frame, [48 + i * 1.6, 82 + i * 1.6], [0, 1], {
					...clamp,
					easing: easeInOut,
				});
				return (
					<line
						key={`v${x}`}
						x1={x}
						x2={x}
						y1={PLOT.bottom}
						y2={PLOT.bottom - (PLOT.bottom - PLOT.top + 25) * p}
						stroke="rgba(255,255,255,0.1)"
						strokeWidth={1}
						strokeDasharray="5 6"
					/>
				);
			})}
		</svg>
	);
};

const Axes: React.FC<{frame: number}> = ({frame}) => {
	const yP = interpolate(frame, [22, 55], [0, 1], {...clamp, easing: easeInOut});
	const xP = interpolate(frame, [34, 72], [0, 1], {...clamp, easing: easeInOut});
	return (
		<svg width={W} height={H} style={{position: 'absolute'}}>
			<defs>
				<filter id="axisGlow" x="-50%" y="-50%" width="200%" height="200%">
					<feGaussianBlur stdDeviation="3" />
				</filter>
			</defs>
			{[
				{f: 'url(#axisGlow)', o: 0.35},
				{f: undefined, o: 1},
			].map((s, i) => (
				<g key={i} filter={s.f} opacity={s.o}>
					<line
						x1={PLOT.left}
						x2={PLOT.left}
						y1={PLOT.bottom + 2}
						y2={PLOT.bottom + 2 - (PLOT.bottom - PLOT.top + 25) * yP}
						stroke="#f4f1ea"
						strokeWidth={5}
					/>
					<line
						x1={PLOT.left - 2.5}
						x2={PLOT.left - 2.5 + (PLOT.right - PLOT.left) * xP}
						y1={PLOT.bottom}
						y2={PLOT.bottom}
						stroke="#f4f1ea"
						strokeWidth={5}
					/>
				</g>
			))}
		</svg>
	);
};

const TickLabels: React.FC<{frame: number}> = ({frame}) => (
	<>
		{Array.from({length: 6}, (_, i) => i * 20).map((v, i) => {
			const p = interpolate(frame, [30 + i * 4, 52 + i * 4], [0, 1], {
				...clamp,
				easing: easeOut,
			});
			return (
				<div
					key={v}
					style={{
						position: 'absolute',
						right: W - PLOT.left + 28,
						top: yFor(v) - 26,
						fontFamily: SERIF,
						fontWeight: 600,
						fontSize: 40,
						color: '#f4f1ea',
						opacity: p,
						transform: `translateX(${(1 - p) * -24}px)`,
						filter: `blur(${(1 - p) * 6}px)`,
					}}
				>
					{v}
				</div>
			);
		})}
	</>
);

const Bar: React.FC<{
	frame: number;
	fps: number;
	label: string;
	value: number;
	x: number;
	delay: number;
}> = ({frame, fps, label, value, x, delay}) => {
	const grow = spring({
		frame: frame - delay,
		fps,
		config: {damping: 18, stiffness: 70, mass: 1.1},
	});
	// Counter tracks the bar's height so the number always matches it
	const shown = value * Math.min(grow, 1);
	const top = yFor(value * grow);
	const height = PLOT.bottom - top;
	const landed = delay + 48;

	// Value pop when the count lands
	const pop = spring({
		frame: frame - landed,
		fps,
		config: {damping: 9, stiffness: 180},
	});
	const popScale = frame < landed ? 1 : 1 + 0.08 * Math.sin(pop * Math.PI);

	const labelP = interpolate(frame, [delay - 10, delay + 22], [0, 1], {
		...clamp,
		easing: easeOut,
	});
	const valueIn = interpolate(frame, [delay + 4, delay + 20], [0, 1], clamp);

	// Glow breathing + one flash on landing
	const flash = interpolate(frame, [landed, landed + 6, landed + 30], [0, 1, 0], clamp);
	const breathe = 0.85 + 0.15 * Math.sin((frame - landed) / 14);
	const glow = (frame > landed ? breathe : grow) + flash * 0.8;

	// Light sweep across the bar
	const sweepStart = 175 + (delay - 78) * 0.6;
	const sweep = interpolate(frame, [sweepStart, sweepStart + 34], [-0.6, 1.6], {
		...clamp,
		easing: easeInOut,
	});

	return (
		<>
			<div
				style={{
					position: 'absolute',
					left: x - BAR_W / 2,
					top,
					width: BAR_W,
					height: Math.max(0, height),
					background: `linear-gradient(180deg, #fffbb8 0%, ${BAR} 18%, #f7ea72 100%)`,
					boxShadow: `0 0 ${28 * glow}px ${6 * glow}px ${BAR_GLOW}, 0 0 ${
						90 * glow
					}px ${10 * glow}px rgba(255,236,90,0.18)`,
					overflow: 'hidden',
				}}
			>
				<div
					style={{
						position: 'absolute',
						top: 0,
						bottom: 0,
						left: `${sweep * 100}%`,
						width: '55%',
						transform: 'translateX(-50%) skewX(-18deg)',
						background:
							'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.75) 50%, rgba(255,255,255,0) 100%)',
					}}
				/>
			</div>
			<div
				style={{
					position: 'absolute',
					left: x - 250,
					width: 500,
					top: top - 92,
					textAlign: 'center',
					fontFamily: SERIF,
					fontWeight: 700,
					fontSize: 70,
					color: '#fff68f',
					textShadow: `0 0 ${18 + flash * 30}px rgba(255,240,110,${0.35 + flash * 0.5})`,
					opacity: valueIn,
					transform: `scale(${popScale})`,
					fontVariantNumeric: 'tabular-nums',
				}}
			>
				{shown.toFixed(2)}M
			</div>
			<div
				style={{
					position: 'absolute',
					left: x - 250,
					width: 500,
					top: PLOT.bottom + 22,
					textAlign: 'center',
					fontFamily: SERIF,
					fontWeight: 700,
					fontSize: 58,
					color: '#f4f1ea',
					opacity: labelP,
					transform: `translateY(${(1 - labelP) * 30}px)`,
					filter: `blur(${(1 - labelP) * 8}px)`,
				}}
			>
				{label}
			</div>
		</>
	);
};

const Grain: React.FC<{frame: number}> = ({frame}) => {
	const seed = Math.floor(frame / 2);
	const ox = random(`gx${seed}`) * 200;
	const oy = random(`gy${seed}`) * 200;
	return (
		<svg
			width={W}
			height={H}
			style={{position: 'absolute', opacity: 0.07, mixBlendMode: 'screen'}}
		>
			<filter id="grain">
				<feTurbulence
					type="fractalNoise"
					baseFrequency="0.9"
					numOctaves="2"
					seed={seed}
				/>
				<feColorMatrix type="saturate" values="0" />
			</filter>
			<rect x={-ox} y={-oy} width={W + 200} height={H + 200} filter="url(#grain)" />
		</svg>
	);
};

export const PassengerChart: React.FC = () => {
	const frame = useCurrentFrame();
	const {fps, durationInFrames} = useVideoConfig();

	// Slow camera push-in with a gentle drift
	const cam = interpolate(frame, [0, durationInFrames], [1.06, 1.0], {
		easing: Easing.bezier(0.25, 0.1, 0.25, 1),
	});
	const driftX = interpolate(frame, [0, durationInFrames], [14, -6]);
	const driftY = interpolate(frame, [0, durationInFrames], [10, -4]);

	const bgIn = interpolate(frame, [0, 18], [0, 1], clamp);
	const fadeOut = interpolate(
		frame,
		[durationInFrames - 14, durationInFrames],
		[1, 0],
		clamp
	);
	const sourceP = interpolate(frame, [34, 56], [0, 1], {...clamp, easing: easeOut});

	return (
		<AbsoluteFill style={{backgroundColor: '#0c0c0c'}}>
			<AbsoluteFill style={{opacity: bgIn * fadeOut}}>
				<AbsoluteFill
					style={{
						background:
							'radial-gradient(ellipse at 50% 45%, #2a2a2a 0%, #1f1f1f 45%, #141414 100%)',
					}}
				/>
				<AbsoluteFill
					style={{
						transform: `translate(${driftX}px, ${driftY}px) scale(${cam})`,
					}}
				>
					<Grid frame={frame} />
					<Axes frame={frame} />
					<TickLabels frame={frame} />
					{DATA.map((d) => (
						<Bar key={d.label} frame={frame} fps={fps} {...d} />
					))}
					<Title frame={frame} />
					<div
						style={{
							position: 'absolute',
							left: PLOT.left + 18,
							top: 188,
							fontFamily: SANS,
							fontSize: 22,
							letterSpacing: 0.4,
							color: 'rgba(235,235,235,0.72)',
							opacity: sourceP,
							transform: `translateX(${(1 - sourceP) * -20}px)`,
						}}
					>
						DATA SOURCE: ACI Europe (2025)
					</div>
				</AbsoluteFill>
				<AbsoluteFill
					style={{
						background:
							'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)',
					}}
				/>
				<Grain frame={frame} />
			</AbsoluteFill>
		</AbsoluteFill>
	);
};
