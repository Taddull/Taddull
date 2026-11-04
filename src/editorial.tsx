import React, {useEffect, useState} from 'react';
import {continueRender, delayRender, Easing, interpolate} from 'remotion';
import '@fontsource/newsreader/400.css';
import '@fontsource/newsreader/400-italic.css';
import '@fontsource/newsreader/600.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';

/*
 * Shared look for the documentary pieces: palette, type, narration
 * reveal, film grain and font loading.
 */

export const W = 1920;
export const H = 1080;
export const SERIF = '"Newsreader", Georgia, serif';
export const MONO = '"IBM Plex Mono", monospace';

export const BG = '#0b0d10';
export const INK = '#ece6d9';
export const INK_DIM = 'rgba(236,230,217,0.56)';
export const AMBER = '#f2a541';
export const RED = '#b9473d';

export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);

export const ramp = (f: number, a: number, b: number, easing = easeOut) =>
	interpolate(f, [a, b], [0, 1], {...clamp, easing});

/* ------------------------------------------------------------------ */
/* Narration text                                                      */
/* ------------------------------------------------------------------ */

export type Seg = {text: string; at: number; strikeAt?: number; br?: boolean};

export const Words: React.FC<{text: string; at: number; frame: number}> = ({
	text,
	at,
	frame,
}) => {
	const words = text.split(' ');
	return (
		<>
			{words.map((w, i) => {
				const start = at + i * 3;
				const p = ramp(frame, start, start + 18);
				return (
					<React.Fragment key={i}>
						<span
							style={{
								display: 'inline-block',
								opacity: p,
								transform: `translateY(${(1 - p) * 10}px)`,
							}}
						>
							{w}
						</span>
						{i < words.length - 1 ? ' ' : null}
					</React.Fragment>
				);
			})}
		</>
	);
};

export const Narration: React.FC<{
	segs: Seg[];
	frame: number;
	style: React.CSSProperties;
}> = ({segs, frame, style}) => (
	<div
		style={{
			position: 'absolute',
			fontFamily: SERIF,
			fontWeight: 400,
			color: INK,
			letterSpacing: -0.6,
			...style,
		}}
	>
		{segs.map((seg, si) => {
			const sep = si < segs.length - 1 && !segs[si + 1].br ? ' ' : null;
			const br = seg.br ? <br /> : null;
			if (seg.strikeAt === undefined) {
				return (
					<React.Fragment key={si}>
						{br}
						<Words text={seg.text} at={seg.at} frame={frame} />
						{sep}
					</React.Fragment>
				);
			}
			const s = ramp(frame, seg.strikeAt, seg.strikeAt + 20, easeInOut);
			return (
				<React.Fragment key={si}>
					{br}
					<span style={{position: 'relative', display: 'inline-block'}}>
						<span style={{opacity: 1 - 0.58 * s}}>
							<Words text={seg.text} at={seg.at} frame={frame} />
						</span>
						<span
							style={{
								position: 'absolute',
								left: -6,
								top: '57%',
								height: 3,
								width: `calc(${s * 100}% + ${12 * s}px)`,
								background: INK,
								opacity: 0.85,
							}}
						/>
					</span>
					{sep}
				</React.Fragment>
			);
		})}
	</div>
);

export const Kicker: React.FC<{
	lines: string[];
	frame: number;
	at: number;
	style: React.CSSProperties;
}> = ({lines, frame, at, style}) => (
	<div
		style={{
			position: 'absolute',
			fontFamily: MONO,
			fontWeight: 500,
			fontSize: 17,
			letterSpacing: 2.4,
			lineHeight: 1.75,
			color: INK_DIM,
			textTransform: 'uppercase',
			...style,
		}}
	>
		{lines.map((l, i) => {
			const p = ramp(frame, at + i * 8, at + i * 8 + 20);
			return (
				<div key={l} style={{opacity: p, transform: `translateX(${(1 - p) * -12}px)`}}>
					{l}
				</div>
			);
		})}
	</div>
);

export const Grain: React.FC<{frame: number}> = ({frame}) => {
	const seed = Math.floor(frame / 2);
	return (
		<svg
			width={W}
			height={H}
			style={{position: 'absolute', opacity: 0.06, mixBlendMode: 'screen', pointerEvents: 'none'}}
		>
			<filter id="filmGrain">
				<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={seed} />
				<feColorMatrix type="saturate" values="0" />
			</filter>
			<rect width={W} height={H} filter="url(#filmGrain)" />
		</svg>
	);
};

export const useFonts = () => {
	const [handle] = useState(() => delayRender('fonts'));
	useEffect(() => {
		Promise.all([
			document.fonts.load('400 64px Newsreader'),
			document.fonts.load('italic 400 64px Newsreader'),
			document.fonts.load('600 27px Newsreader'),
			document.fonts.load('400 46px "IBM Plex Mono"'),
			document.fonts.load('500 17px "IBM Plex Mono"'),
		])
			.then(() => document.fonts.ready)
			.then(() => continueRender(handle))
			.catch(() => continueRender(handle));
	}, [handle]);
};
