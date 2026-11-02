import React from 'react';
import {interpolate} from 'remotion';
import {Emoji, Sparkle} from '../discord/primitives';
import {clamp, easeInOut, lerp, prog, spr} from '../discord/theme';
import {Y, YBODY, ydisplay} from './theme';

export {Emoji, Sparkle, clamp, easeInOut, lerp, prog, spr};

/* ---------------------------------------------------------------- logo */
export const PlayIcon: React.FC<{h: number; color?: string; tri?: string; style?: React.CSSProperties}> = ({h, color = Y.red, tri = '#fff', style}) => (
	<svg width={h * 1.4} height={h} viewBox="0 0 28 20" style={{display: 'block', ...style}}>
		<path
			fill={color}
			d="M27.4 3.1A3.5 3.5 0 0 0 24.9.6C22.7 0 14 0 14 0S5.3 0 3.1.6A3.5 3.5 0 0 0 .6 3.1C0 5.3 0 10 0 10s0 4.7.6 6.9a3.5 3.5 0 0 0 2.5 2.5C5.3 20 14 20 14 20s8.7 0 10.9-.6a3.5 3.5 0 0 0 2.5-2.5C28 14.7 28 10 28 10s0-4.7-.6-6.9z"
		/>
		<path fill={tri} d="M11.2 14.3 18.5 10l-7.3-4.3z" />
	</svg>
);

export const Wordmark: React.FC<{size: number; color?: string}> = ({size, color = Y.ink}) => (
	<div style={{display: 'flex', alignItems: 'center', gap: size * 0.18}}>
		<PlayIcon h={size * 0.82} />
		<span style={{fontFamily: YBODY, fontWeight: 700, fontSize: size, letterSpacing: '-0.06em', color, lineHeight: 1}}>YouTube</span>
	</div>
);

/* ---------------------------------------------------------------- icons */
export type YIcon =
	| 'home' | 'shorts' | 'subs' | 'you' | 'history' | 'playlist' | 'later' | 'like' | 'dislike' | 'menu' | 'search' | 'mic'
	| 'create' | 'bell' | 'bellRing' | 'share' | 'download' | 'more' | 'comment' | 'remix' | 'music' | 'live' | 'dollar' | 'chart'
	| 'eye' | 'clock' | 'gear' | 'play' | 'pause' | 'volume' | 'cc' | 'full' | 'next' | 'prev' | 'check' | 'tv' | 'globe'
	| 'noad' | 'bgplay' | 'heart' | 'shuffle' | 'repeat' | 'users' | 'camera' | 'flip' | 'timer' | 'sparkle' | 'phone' | 'plus';

export const Icon: React.FC<{name: YIcon; size?: number; color?: string; style?: React.CSSProperties}> = ({name, size = 24, color = 'currentColor', style}) => {
	const s = {fill: 'none', stroke: color, strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const};
	const fl = {fill: color};
	const g: Record<YIcon, React.ReactNode> = {
		home: <path {...fl} d="M4 10.5 12 4l8 6.5V20h-5.5v-5.5h-5V20H4z" />,
		shorts: (
			<>
				<path {...fl} d="M16.6 2.9c1.9-1 4.2-.3 5.2 1.6 1 1.9.3 4.2-1.6 5.2l-1.6.9c1.5.3 2.8 1.3 3.2 2.8.7 2.1-.4 4.3-2.4 5.1l-8.6 4.6c-1.9 1-4.2.3-5.2-1.6-1-1.9-.3-4.2 1.6-5.2l1.6-.9c-1.5-.3-2.8-1.3-3.2-2.8-.7-2.1.4-4.3 2.4-5.1z" transform="translate(-2 -1) scale(.95)" />
				<path fill="#fff" d="M10 8.6v6.8l5.6-3.4z" />
			</>
		),
		subs: (
			<>
				<rect {...s} x="3" y="8" width="18" height="13" rx="2.5" />
				<path {...s} d="M6 5h12M8 2h8" />
				<path {...fl} d="M10.5 11.5v6l5-3z" />
			</>
		),
		you: (
			<>
				<circle {...s} cx="12" cy="8" r="4" />
				<path {...s} d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7" />
			</>
		),
		history: (
			<>
				<path {...s} d="M3.5 12a8.5 8.5 0 1 0 2.5-6L3.5 8.5M3.5 4v4.5H8" />
				<path {...s} d="M12 7.5V12l3 2" />
			</>
		),
		playlist: <path {...s} d="M3 6h13M3 11h13M3 16h8M17 14v7l5-3.5z" />,
		later: (
			<>
				<circle {...s} cx="12" cy="12" r="9" />
				<path {...s} d="M12 7v5.5l3.5 2" />
			</>
		),
		like: <path {...fl} d="M2 10h4v11H2zM8 21h9.5c1 0 1.8-.7 2-1.6l1.5-7c.2-1.2-.7-2.4-2-2.4H14l.9-4.3c.2-1-.4-2-1.4-2.3-.7-.2-1.4.1-1.8.6L8 9.5z" />,
		dislike: <path {...fl} d="M22 14h-4V3h4zM16 3H6.5c-1 0-1.8.7-2 1.6l-1.5 7c-.2 1.2.7 2.4 2 2.4H10l-.9 4.3c-.2 1 .4 2 1.4 2.3.7.2 1.4-.1 1.8-.6L16 14.5z" />,
		menu: <path {...s} strokeWidth={2.2} d="M3 6h18M3 12h18M3 18h18" />,
		search: (
			<>
				<circle {...s} cx="10.5" cy="10.5" r="6.5" />
				<path {...s} d="m15.5 15.5 5.5 5.5" />
			</>
		),
		mic: (
			<>
				<rect {...fl} x="9" y="2.5" width="6" height="12" rx="3" />
				<path {...s} d="M5 11a7 7 0 0 0 14 0M12 18v3.5" />
			</>
		),
		create: (
			<>
				<rect {...s} x="2" y="6" width="14" height="12" rx="2.5" />
				<path {...s} d="m16 10.5 6-3.5v10l-6-3.5M9 9v6M6 12h6" />
			</>
		),
		bell: <path {...s} d="M12 3a6 6 0 0 0-6 6v4l-2 3.5h16L18 13V9a6 6 0 0 0-6-6zM10 20a2.2 2.2 0 0 0 4 0" />,
		bellRing: (
			<>
				<path {...fl} d="M12 3a6 6 0 0 0-6 6v4l-2 3.5h16L18 13V9a6 6 0 0 0-6-6z" />
				<path {...s} d="M10 20a2.2 2.2 0 0 0 4 0M3 7.5a9 9 0 0 1 2.5-4M21 7.5a9 9 0 0 0-2.5-4" />
			</>
		),
		share: <path {...fl} d="M14 4.5 22 12l-8 7.5V15c-5.5 0-9 1.8-12 6 1-6 4-11 12-12z" />,
		download: <path {...s} strokeWidth={2.2} d="M12 3.5v12M6.5 10 12 15.5 17.5 10M4 20.5h16" />,
		more: (
			<>
				<circle {...fl} cx="12" cy="5" r="2" />
				<circle {...fl} cx="12" cy="12" r="2" />
				<circle {...fl} cx="12" cy="19" r="2" />
			</>
		),
		comment: <path {...fl} d="M4 3h16a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 1-2z" />,
		remix: <path {...s} strokeWidth={2.2} d="M4 7h12l-3-3M20 17H8l3 3M4 7v4M20 17v-4" />,
		music: (
			<>
				<path {...fl} d="M9 17V5l11-2v12" />
				<circle {...fl} cx="6.5" cy="17.5" r="3" />
				<circle {...fl} cx="17.5" cy="15.5" r="3" />
			</>
		),
		live: (
			<>
				<circle {...fl} cx="12" cy="12" r="3" />
				<path {...s} d="M7.8 7.8a6 6 0 0 0 0 8.4M16.2 7.8a6 6 0 0 1 0 8.4M5 5a10 10 0 0 0 0 14M19 5a10 10 0 0 1 0 14" />
			</>
		),
		dollar: (
			<>
				<circle {...fl} cx="12" cy="12" r="10" />
				<path stroke="#fff" fill="none" strokeWidth={2} strokeLinecap="round" d="M15 8.5c-.6-1-1.7-1.5-3-1.5-1.8 0-3 .9-3 2.3 0 3.2 6 1.7 6 4.9 0 1.4-1.3 2.3-3 2.3-1.4 0-2.6-.6-3.1-1.6M12 5.5v13" />
			</>
		),
		chart: <path {...s} strokeWidth={2.2} d="M3 20h18M5 16l4.5-5 3.5 3 6-7" />,
		eye: (
			<>
				<path {...s} d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" />
				<circle {...fl} cx="12" cy="12" r="3" />
			</>
		),
		clock: (
			<>
				<circle {...s} cx="12" cy="12" r="9" />
				<path {...s} d="M12 7v5l3 2" />
			</>
		),
		gear: (
			<>
				<circle {...s} cx="12" cy="12" r="3.2" />
				<path {...s} d="M12 2.8v2.6M12 18.6v2.6M2.8 12h2.6M18.6 12h2.6M5.5 5.5l1.8 1.8M16.7 16.7l1.8 1.8M5.5 18.5l1.8-1.8M16.7 7.3l1.8-1.8" />
			</>
		),
		play: <path {...fl} d="M7 4l13 8-13 8z" />,
		pause: <path {...fl} d="M6 4h4v16H6zM14 4h4v16h-4z" />,
		volume: (
			<>
				<path {...fl} d="M3 9v6h4l5 4V5L7 9z" />
				<path {...s} d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" />
			</>
		),
		cc: (
			<>
				<rect {...s} x="2.5" y="5" width="19" height="14" rx="2.5" />
				<path {...s} d="M10 10.5a2 2 0 1 0 0 3M16.5 10.5a2 2 0 1 0 0 3" />
			</>
		),
		full: <path {...s} strokeWidth={2.2} d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />,
		next: <path {...fl} d="M5 4l10 8-10 8zM17 4h3v16h-3z" />,
		prev: <path {...fl} d="M19 4 9 12l10 8zM4 4h3v16H4z" />,
		check: <path {...s} strokeWidth={3} d="m5 12.5 4.5 4.5L19 7.5" />,
		tv: (
			<>
				<rect {...s} x="2" y="4" width="20" height="13" rx="2" />
				<path {...s} d="M8 21h8" />
			</>
		),
		globe: (
			<>
				<circle {...s} cx="12" cy="12" r="9.2" />
				<path {...s} d="M2.8 12h18.4M12 2.8c2.6 2.6 3.8 5.6 3.8 9.2s-1.2 6.6-3.8 9.2c-2.6-2.6-3.8-5.6-3.8-9.2S9.4 5.4 12 2.8z" />
			</>
		),
		noad: (
			<>
				<rect {...s} x="2.5" y="5" width="19" height="14" rx="3" />
				<path {...s} d="M7 15l2.2-6 2.2 6M7.7 13h3M14 9v6h1.5a3 3 0 0 0 0-6z" />
				<path stroke={color} strokeWidth={2.2} d="M3 21 21 3" />
			</>
		),
		bgplay: (
			<>
				<path {...s} d="M4 15v-3a8 8 0 0 1 16 0v3" />
				<rect {...fl} x="2.8" y="13.5" width="5" height="7.5" rx="2" />
				<rect {...fl} x="16.2" y="13.5" width="5" height="7.5" rx="2" />
			</>
		),
		heart: <path {...fl} d="M12 21s-8.5-5.2-8.5-11A4.8 4.8 0 0 1 12 6.6 4.8 4.8 0 0 1 20.5 10c0 5.8-8.5 11-8.5 11z" />,
		shuffle: <path {...s} d="M3 7h3.5c4 0 6.5 10 11 10H21M3 17h3.5c1.6 0 2.8-1.5 3.8-3.3M14 8.6c.9-.9 2-1.6 3.5-1.6H21M18 4l3 3-3 3M18 14l3 3-3 3" />,
		repeat: <path {...s} d="M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3" />,
		users: (
			<>
				<circle {...fl} cx="9" cy="8" r="4" />
				<path {...fl} d="M1.5 20c0-4 3.4-6.5 7.5-6.5s7.5 2.5 7.5 6.5z" />
				<circle {...fl} cx="17" cy="8.5" r="3" opacity={0.7} />
			</>
		),
		camera: (
			<>
				<path {...s} d="M3 8h3.5l2-3h7l2 3H21v12H3z" />
				<circle {...s} cx="12" cy="13.5" r="3.5" />
			</>
		),
		flip: <path {...s} d="M4 12a8 8 0 0 1 14-5.3M20 12a8 8 0 0 1-14 5.3M18 3v4h-4M6 21v-4h4" />,
		timer: (
			<>
				<circle {...s} cx="12" cy="13" r="8" />
				<path {...s} d="M12 9v4l2.5 2M9.5 2h5" />
			</>
		),
		sparkle: <path {...fl} d="M12 2c.6 5.3 4.7 9.4 10 10-5.3.6-9.4 4.7-10 10-.6-5.3-4.7-9.4-10-10C7.3 11.4 11.4 7.3 12 2z" />,
		phone: (
			<>
				<rect {...s} x="6" y="2" width="12" height="20" rx="3" />
				<path {...s} d="M10.5 18.5h3" />
			</>
		),
		plus: <path {...s} strokeWidth={2.4} d="M12 5v14M5 12h14" />,
	};
	return (
		<svg width={size} height={size} viewBox="0 0 24 24" style={{display: 'block', flexShrink: 0, ...style}}>
			{g[name]}
		</svg>
	);
};

/* ---------------------------------------------------------------- channels + videos (fictional) */
export const CH = {
	maya: {name: 'Maya Makes', e: '🛠️', g: ['#FF8A3D', '#FF3D6E'], subs: '2.1M'},
	noodle: {name: 'Noodle Lab', e: '🍜', g: ['#FFB800', '#FF5A1F'], subs: '864K'},
	chill: {name: 'Chill Station', e: '🎧', g: ['#7B61FF', '#C04CFD'], subs: '5.3M'},
	pixel: {name: 'PixelPro', e: '🎮', g: ['#00C2FF', '#3D5AFE'], subs: '1.4M'},
	wander: {name: 'Wander Wide', e: '🏔️', g: ['#00D4A6', '#0091FF'], subs: '3.2M'},
	strum: {name: 'Strum School', e: '🎸', g: ['#FF3D3D', '#FF9A3D'], subs: '742K'},
	cosmo: {name: 'Cosmo Clips', e: '🪐', g: ['#3D2BFF', '#00C2FF'], subs: '4.8M'},
	taste: {name: 'Taste Trip', e: '🍢', g: ['#FFD23D', '#FF6B3D'], subs: '1.9M'},
	setup: {name: 'Setup Wars', e: '💻', g: ['#9AA0A6', '#3C4043'], subs: '388K'},
	you: {name: 'You', e: '😎', g: ['#FF0000', '#FF8A3D'], subs: ''},
} as const;
export type ChKey = keyof typeof CH;

export const ChAvatar: React.FC<{c: ChKey; size: number; ring?: boolean; style?: React.CSSProperties}> = ({c, size, ring, style}) => (
	<div
		style={{
			width: size,
			height: size,
			borderRadius: '50%',
			flexShrink: 0,
			background: `linear-gradient(135deg, ${CH[c].g[0]}, ${CH[c].g[1]})`,
			display: 'flex',
			alignItems: 'center',
			justifyContent: 'center',
			boxShadow: ring ? `0 0 0 ${size * 0.06}px ${Y.red}` : undefined,
			...style,
		}}
	>
		<Emoji e={CH[c].e} size={size * 0.55} />
	</div>
);

export type Video = {title: string; ch: ChKey; views: string; ago: string; dur: string; text: string; e: string; bg: [string, string]; live?: boolean};
export const VIDEOS: Video[] = [
	{title: 'I Built a Tiny Cabin in 7 Days (Solo)', ch: 'maya', views: '2.4M views', ago: '3 days ago', dur: '18:42', text: '7 DAYS', e: '🏡', bg: ['#FF8A3D', '#B3245C']},
	{title: 'Restaurant-Level Ramen at Home', ch: 'noodle', views: '812K views', ago: '1 week ago', dur: '12:05', text: 'RAMEN 101', e: '🍜', bg: ['#FFB800', '#D9430F']},
	{title: 'lofi beats to study / relax to ✨', ch: 'chill', views: '31K watching', ago: '', dur: '', text: 'LOFI', e: '🎧', bg: ['#7B61FF', '#2A1A6E'], live: true},
	{title: 'Speedrun World Record?! (Any%)', ch: 'pixel', views: '1.1M views', ago: '2 days ago', dur: '24:17', text: 'WR?!', e: '🎮', bg: ['#00C2FF', '#1E2A9E']},
	{title: 'Iceland in 4K — The Road Less Taken', ch: 'wander', views: '3.6M views', ago: '1 month ago', dur: '15:30', text: 'ICELAND', e: '🏔️', bg: ['#00D4A6', '#0B3D91']},
	{title: 'Learn Guitar in 30 Days — Day 1', ch: 'strum', views: '640K views', ago: '5 days ago', dur: '9:58', text: 'DAY 1', e: '🎸', bg: ['#FF3D3D', '#8A1C1C']},
	{title: 'Space Facts That Break Your Brain', ch: 'cosmo', views: '5.2M views', ago: '2 weeks ago', dur: '11:11', text: 'WAIT WHAT?', e: '🪐', bg: ['#3D2BFF', '#06061E']},
	{title: 'Bangkok Street Food Tour', ch: 'taste', views: '1.9M views', ago: '4 days ago', dur: '21:03', text: '$1 FOOD', e: '🍢', bg: ['#FFD23D', '#E0521A']},
	{title: 'My Desk Setup 2026', ch: 'setup', views: '430K views', ago: '6 days ago', dur: '8:44', text: 'SETUP', e: '💻', bg: ['#5F6368', '#202124']},
];
export const ICELAND = 4;

/** procedural YouTube-style thumbnail (scales with its box via container units) */
export const Thumb: React.FC<{v: Video; style?: React.CSSProperties; radius?: number; progress?: number}> = ({v, style, radius = 12, progress}) => (
	<div style={{position: 'relative', aspectRatio: '16 / 9', borderRadius: radius, overflow: 'hidden', background: `linear-gradient(135deg, ${v.bg[0]}, ${v.bg[1]})`, containerType: 'size', ...style}}>
		<div style={{position: 'absolute', right: '-12cqw', top: '-30cqh', width: '70cqw', height: '70cqw', borderRadius: '50%', background: 'rgba(255,255,255,0.14)'}} />
		<div style={{position: 'absolute', left: '-10cqw', bottom: '-40cqh', width: '50cqw', height: '50cqw', borderRadius: '50%', background: 'rgba(0,0,0,0.14)'}} />
		<Emoji e={v.e} size={10} style={{position: 'absolute', right: '6cqw', top: '14cqh', fontSize: '58cqh', transform: 'rotate(-6deg)'}} />
		<div
			style={{
				position: 'absolute',
				left: '6cqw',
				bottom: '12cqh',
				...ydisplay(10, 900),
				fontSize: '19cqh',
				color: '#fff',
				fontStretch: '80%',
				WebkitTextStroke: '0.6cqh #000',
				paintOrder: 'stroke fill',
				textShadow: '0 1cqh 0 rgba(0,0,0,0.35)',
				transform: 'rotate(-3deg)',
				maxWidth: '62cqw',
			}}
		>
			{v.text}
		</div>
		{v.live ? (
			<div style={{position: 'absolute', right: '3cqw', bottom: '4cqh', background: Y.red, color: '#fff', fontFamily: YBODY, fontWeight: 700, fontSize: '7cqh', padding: '0.6cqh 2cqh', borderRadius: '1cqh', display: 'flex', alignItems: 'center', gap: '1.5cqh'}}>
				<Icon name="live" size={10} color="#fff" style={{width: '7cqh', height: '7cqh'}} />
				LIVE
			</div>
		) : v.dur ? (
			<div style={{position: 'absolute', right: '3cqw', bottom: '4cqh', background: 'rgba(0,0,0,0.8)', color: '#fff', fontFamily: YBODY, fontWeight: 500, fontSize: '7cqh', padding: '0.4cqh 1.6cqh', borderRadius: '1cqh'}}>{v.dur}</div>
		) : null}
		{progress !== undefined && (
			<div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: '2.4cqh', background: 'rgba(255,255,255,0.35)'}}>
				<div style={{width: `${progress * 100}%`, height: '100%', background: Y.red}} />
			</div>
		)}
	</div>
);

/* ---------------------------------------------------------------- animated "videos" */
/** Iceland road-trip footage: aurora, layered mountains, drifting snow */
export const IcelandScene: React.FC<{f: number}> = ({f}) => (
	<div style={{position: 'absolute', inset: 0, overflow: 'hidden', background: 'linear-gradient(180deg, #071228 0%, #0E2A4F 45%, #1B5B73 70%, #A8D8E0 100%)'}}>
		{[0, 1, 2].map((i) => (
			<div
				key={i}
				style={{
					position: 'absolute',
					left: `${-30 + i * 25 + Math.sin(f / 40 + i) * 8}%`,
					top: `${4 + i * 6}%`,
					width: '90%',
					height: '38%',
					borderRadius: '50%',
					background: `radial-gradient(closest-side, ${['rgba(80,255,170,0.55)', 'rgba(140,90,255,0.45)', 'rgba(60,220,255,0.4)'][i]}, transparent)`,
					transform: `rotate(${-12 + i * 9 + Math.sin(f / 50 + i) * 4}deg) scaleY(0.45)`,
				}}
			/>
		))}
		{new Array(40).fill(0).map((_, i) => (
			<div key={`s${i}`} style={{position: 'absolute', left: `${(i * 37) % 100}%`, top: `${(i * 23) % 40}%`, width: 2, height: 2, borderRadius: 1, background: '#fff', opacity: 0.5 + 0.5 * Math.sin(f / 9 + i)}} />
		))}
		<svg viewBox="0 0 100 40" preserveAspectRatio="none" style={{position: 'absolute', left: `${-5 - ((f * 0.03) % 5)}%`, bottom: '18%', width: '115%', height: '42%'}}>
			<path d="M0 40 L10 18 L18 26 L30 8 L40 22 L52 12 L64 26 L76 6 L88 20 L100 14 L100 40Z" fill="#1E3A57" />
			<path d="M28 10 L30 8 L33 12 Z M74 9 L76 6 L79 10Z" fill="#E8F4F8" />
		</svg>
		<svg viewBox="0 0 100 40" preserveAspectRatio="none" style={{position: 'absolute', left: `${-10 - ((f * 0.08) % 10)}%`, bottom: 0, width: '125%', height: '36%'}}>
			<path d="M0 40 L0 20 L14 12 L26 22 L40 10 L55 24 L70 14 L85 24 L100 16 L100 40Z" fill="#0B2236" />
		</svg>
		<div style={{position: 'absolute', left: '42%', bottom: 0, width: '16%', height: '22%', background: 'linear-gradient(180deg, #2B2B2B, #444)', clipPath: 'polygon(42% 0, 58% 0, 100% 100%, 0 100%)'}} />
		<div style={{position: 'absolute', left: '49.4%', bottom: 0, width: '1.2%', height: '22%', backgroundImage: 'repeating-linear-gradient(180deg, #F2C94C 0 8%, transparent 8% 18%)', backgroundPosition: `0 ${(f * 3) % 100}%`, clipPath: 'polygon(40% 0, 60% 0, 100% 100%, 0 100%)'}} />
	</div>
);

/** vertical Short: big emoji subject on a punchy gradient with on-screen captions */
export const ShortScene: React.FC<{f: number; kind: 'cook' | 'skate' | 'art'}> = ({f, kind}) => {
	const cfg = {
		cook: {bg: 'linear-gradient(160deg, #FFB347, #FF5E62)', e: '🥞', cap: '60-SECOND PANCAKES', sub: 'step 2: the flip 👀', motion: Math.abs(Math.sin(f / 9)) * -60},
		skate: {bg: 'linear-gradient(160deg, #7F7FD5, #86A8E7 50%, #91EAE4)', e: '🛹', cap: 'FIRST KICKFLIP!!', sub: 'took me 300 tries 😭', motion: Math.sin(f / 7) * -30},
		art: {bg: 'linear-gradient(160deg, #F857A6, #FF5858)', e: '🎨', cap: 'SPEED PAINTING', sub: 'guess what it is 👇', motion: Math.sin(f / 12) * -12},
	}[kind];
	return (
		<div style={{position: 'absolute', inset: 0, overflow: 'hidden', background: cfg.bg}}>
			<div style={{position: 'absolute', left: '-20%', top: '30%', width: '140%', height: '40%', borderRadius: '50%', background: 'rgba(255,255,255,0.18)'}} />
			<Emoji e={cfg.e} size={210} style={{position: 'absolute', left: '50%', top: '42%', transform: `translate(-50%, calc(-50% + ${cfg.motion}px)) rotate(${Math.sin(f / 10) * 10}deg)`}} />
			<div style={{position: 'absolute', left: 0, right: 0, top: '18%', textAlign: 'center', ...ydisplay(34, 900), color: '#fff', WebkitTextStroke: '3px #000', paintOrder: 'stroke fill'}}>{cfg.cap}</div>
			<div style={{position: 'absolute', left: 0, right: 0, top: '64%', textAlign: 'center', fontFamily: YBODY, fontWeight: 700, fontSize: 22, color: '#fff', textShadow: '0 2px 6px rgba(0,0,0,0.5)'}}>{cfg.sub}</div>
		</div>
	);
};

/* ---------------------------------------------------------------- copy + cards on the light canvas */
export const Eyebrow: React.FC<{f: number; start: number; label: string; num?: string; icon?: YIcon}> = ({f, start, label, num, icon = 'play'}) => {
	const s = spr(f, start, {damping: 15, stiffness: 170});
	const w = prog(f, start + 3, start + 20);
	return (
		<div
			style={{
				display: 'inline-flex',
				alignItems: 'center',
				gap: 12,
				padding: '7px 22px 7px 7px',
				borderRadius: 999,
				background: '#fff',
				boxShadow: `0 8px 24px ${Y.shadow}`,
				transform: `scale(${lerp(0.5, 1, s)})`,
				transformOrigin: 'left center',
				opacity: Math.min(1, s * 1.6),
			}}
		>
			<div style={{width: 36, height: 36, borderRadius: 999, background: Y.red, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
				<Icon name={icon} size={20} color="#fff" />
			</div>
			<div style={{fontFamily: YBODY, fontWeight: 700, fontSize: 18, letterSpacing: '0.16em', textTransform: 'uppercase', color: Y.ink, clipPath: `inset(0 ${(1 - w) * 100}% 0 0)`, whiteSpace: 'nowrap'}}>
				{num && <span style={{color: Y.red, marginRight: 12}}>{num}</span>}
				{label}
			</div>
		</div>
	);
};

export const Body: React.FC<{f: number; start: number; children: React.ReactNode; w?: number; size?: number; align?: 'left' | 'center'}> = ({f, start, children, w = 620, size = 26, align = 'left'}) => {
	const p = prog(f, start, start + 18);
	return (
		<div style={{opacity: p, transform: `translateY(${(1 - p) * 26}px)`}}>
			<div style={{fontFamily: YBODY, fontWeight: 400, fontSize: size, lineHeight: 1.45, color: Y.body, maxWidth: w, textAlign: align}}>{children}</div>
		</div>
	);
};

export const Card: React.FC<{f: number; at: number; x: number; y: number; children: React.ReactNode; dark?: boolean; float?: number; radius?: number; z?: number; style?: React.CSSProperties}> = ({
	f,
	at,
	x,
	y,
	children,
	dark,
	float = 0,
	radius = 20,
	z = 240,
	style,
}) => {
	const s = spr(f, at, {damping: 13, stiffness: 170});
	const bob = Math.sin((f + float * 40) / 24) * 6;
	return (
		<div
			style={{
				position: 'absolute',
				left: x,
				top: y,
				transform: `translateZ(${z}px) translateY(${bob + (1 - Math.min(1, s)) * 30}px) scale(${lerp(0.6, 1, s)})`,
				opacity: interpolate(s, [0, 0.35], [0, 1], clamp),
				...style,
			}}
		>
			<div style={{background: dark ? Y.ui2 : '#fff', color: dark ? Y.text : Y.ink, borderRadius: radius, boxShadow: `0 26px 60px ${Y.shadowStrong}`, fontFamily: YBODY, overflow: 'hidden'}}>{children}</div>
		</div>
	);
};

export const Sticker = (e: string, size: number) => (
	<div style={{marginLeft: -size / 2, marginTop: -size / 2, width: size, height: size, borderRadius: '50%', background: '#fff', boxShadow: `0 20px 40px ${Y.shadow}`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
		{e === '▶' ? <PlayIcon h={size * 0.38} /> : <Emoji e={e} size={size * 0.52} />}
	</div>
);
export const Spark = (size: number) => <Sparkle size={size} color={Y.red} style={{opacity: 0.55}} />;
