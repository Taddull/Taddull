import React from 'react';
import {AbsoluteFill, random} from 'remotion';
import {BODY, C, EMOJI, display, easeOut, prog, lerp, spr, clamp} from './theme';
import {interpolate} from 'remotion';

/* ---------------------------------------------------------------- Clyde */
export const CLYDE_PATH =
	'M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z';

export const Clyde: React.FC<{size: number; color?: string; style?: React.CSSProperties}> = ({
	size,
	color = '#fff',
	style,
}) => (
	<svg width={size} height={size * 0.77} viewBox="0 2.6 24 18.6" style={{display: 'block', ...style}}>
		<path d={CLYDE_PATH} fill={color} />
	</svg>
);

/* ---------------------------------------------------------------- Icons */
type IconName =
	| 'hash'
	| 'speaker'
	| 'mic'
	| 'micOff'
	| 'headphones'
	| 'gear'
	| 'plus'
	| 'video'
	| 'screen'
	| 'hangup'
	| 'emoji'
	| 'gift'
	| 'gif'
	| 'search'
	| 'bell'
	| 'pin'
	| 'users'
	| 'calendar'
	| 'shield'
	| 'check'
	| 'rocket'
	| 'eye'
	| 'hand'
	| 'crown'
	| 'lock'
	| 'bolt'
	| 'globe'
	| 'download'
	| 'chevron'
	| 'stage'
	| 'thread'
	| 'compass'
	| 'sticker'
	| 'gem'
	| 'chat'
	| 'apps'
	| 'image'
	| 'heart'
	| 'arrowUp'
	| 'back';

export const Icon: React.FC<{name: IconName; size?: number; color?: string; style?: React.CSSProperties}> = ({
	name,
	size = 24,
	color = 'currentColor',
	style,
}) => {
	const s = {fill: 'none', stroke: color, strokeWidth: 2.2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const};
	const fl = {fill: color};
	const g: Record<IconName, React.ReactNode> = {
		hash: <path {...s} d="M10 3 8 21M16 3l-2 18M4.5 8.5h16M3.5 15.5h16" />,
		speaker: (
			<>
				<path {...fl} d="M3 9.2v5.6h3.8L12 19V5L6.8 9.2z" />
				<path {...s} d="M15.6 8.6a4.8 4.8 0 0 1 0 6.8M18.4 5.8a8.8 8.8 0 0 1 0 12.4" />
			</>
		),
		mic: (
			<>
				<rect {...fl} x="8.6" y="2.5" width="6.8" height="12" rx="3.4" />
				<path {...s} d="M5 11.2a7 7 0 0 0 14 0M12 18.3v3" />
			</>
		),
		micOff: (
			<>
				<rect {...fl} x="8.6" y="2.5" width="6.8" height="12" rx="3.4" />
				<path {...s} d="M5 11.2a7 7 0 0 0 14 0M12 18.3v3" />
				<path stroke={C.red} strokeWidth={2.6} strokeLinecap="round" d="M4 3l16 18" />
			</>
		),
		headphones: (
			<>
				<path {...s} d="M4 15v-3a8 8 0 0 1 16 0v3" />
				<rect {...fl} x="2.8" y="13.5" width="5" height="7.5" rx="2" />
				<rect {...fl} x="16.2" y="13.5" width="5" height="7.5" rx="2" />
			</>
		),
		gear: (
			<>
				<circle {...s} cx="12" cy="12" r="3.2" />
				<path
					{...s}
					d="M12 2.8v2.6M12 18.6v2.6M2.8 12h2.6M18.6 12h2.6M5.5 5.5l1.8 1.8M16.7 16.7l1.8 1.8M5.5 18.5l1.8-1.8M16.7 7.3l1.8-1.8"
				/>
			</>
		),
		plus: <path {...s} d="M12 5v14M5 12h14" />,
		video: (
			<>
				<rect {...fl} x="2" y="6" width="13" height="12" rx="2.5" />
				<path {...fl} d="M16.5 10.2 22 7v10l-5.5-3.2z" />
			</>
		),
		screen: (
			<>
				<rect {...s} x="2.5" y="4" width="19" height="13" rx="2" />
				<path {...s} d="M8 21h8M12 14V8.5M9.2 11.2 12 8.4l2.8 2.8" />
			</>
		),
		hangup: (
			<path
				{...fl}
				d="M2.5 13.6c5.3-5 13.7-5 19 0l-2.6 2.6-3.6-1.6v-2.8a11 11 0 0 0-6.6 0v2.8l-3.6 1.6z"
			/>
		),
		emoji: (
			<>
				<circle {...s} cx="12" cy="12" r="9" />
				<path {...s} d="M8 14.2a4.6 4.6 0 0 0 8 0" />
				<circle {...fl} cx="9" cy="9.8" r="1.3" />
				<circle {...fl} cx="15" cy="9.8" r="1.3" />
			</>
		),
		gift: (
			<>
				<rect {...s} x="3.5" y="9" width="17" height="11.5" rx="1.5" />
				<path {...s} d="M2.5 9h19M12 9v11.5M12 9C10 4 6.5 4.5 7 7.5 7.4 9 12 9 12 9zm0 0c2-5 5.5-4.5 5-1.5C16.6 9 12 9 12 9z" />
			</>
		),
		gif: (
			<>
				<rect {...s} x="2.5" y="5" width="19" height="14" rx="3" />
				<text x="12" y="15.4" textAnchor="middle" fontSize="8.2" fontWeight="800" fontFamily="Figtree" fill={color}>
					GIF
				</text>
			</>
		),
		search: (
			<>
				<circle {...s} cx="10.5" cy="10.5" r="6.5" />
				<path {...s} d="m15.5 15.5 5 5" />
			</>
		),
		bell: (
			<>
				<path {...fl} d="M12 3a6 6 0 0 0-6 6v4l-2 3.5h16L18 13V9a6 6 0 0 0-6-6z" />
				<path {...s} d="M10 19.5a2.2 2.2 0 0 0 4 0" />
			</>
		),
		pin: <path {...fl} d="M14.5 2.5 21.5 9.5l-2 .6-4.1 4.1.4 4.3-1.4 1.4-4.2-4.2L5 20.9l-1.9.1.1-1.9 5.2-5.2-4.2-4.2 1.4-1.4 4.3.4 4.1-4.1z" />,
		users: (
			<>
				<circle {...fl} cx="9" cy="8" r="4" />
				<path {...fl} d="M1.5 20c0-4 3.4-6.5 7.5-6.5s7.5 2.5 7.5 6.5z" />
				<circle {...fl} cx="17" cy="8.5" r="3" opacity={0.7} />
				<path {...fl} d="M17.6 13.6c3 .3 5 2.4 5 5.4h-4.8c0-2.2-.6-3.8-2-5.2z" opacity={0.7} />
			</>
		),
		calendar: (
			<>
				<rect {...s} x="3" y="5" width="18" height="16" rx="3" />
				<path {...s} d="M3 10h18M8 3v4M16 3v4" />
			</>
		),
		shield: (
			<>
				<path {...fl} d="M12 2 4 5v6c0 5 3.4 9.3 8 11 4.6-1.7 8-6 8-11V5z" />
				<path stroke="#fff" fill="none" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" d="m8.4 12 2.6 2.6 4.8-5" />
			</>
		),
		check: <path {...s} strokeWidth={3} d="m5 12.5 4.5 4.5L19 7.5" />,
		rocket: (
			<>
				<path {...fl} d="M12 2c3.5 2.2 5.5 6 5.5 10.5l-2.3 3h-6.4l-2.3-3C6.5 8 8.5 4.2 12 2z" />
				<circle cx="12" cy="9.5" r="2" fill="#fff" />
				<path {...fl} d="M9.2 16.5h5.6L12 22z" opacity={0.75} />
			</>
		),
		eye: (
			<>
				<path {...s} d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" />
				<circle {...fl} cx="12" cy="12" r="3.2" />
			</>
		),
		hand: <path {...fl} d="M8 11V4.5a1.5 1.5 0 0 1 3 0V10V3a1.5 1.5 0 0 1 3 0v7V4.5a1.5 1.5 0 0 1 3 0V12V8.5a1.5 1.5 0 0 1 3 0V15a7 7 0 0 1-7 7h-.6a7 7 0 0 1-5.6-2.8L3.6 14.6a1.6 1.6 0 0 1 2.4-2.1z" />,
		crown: <path {...fl} d="M3 8l4.5 3.5L12 4l4.5 7.5L21 8l-2 11H5z" />,
		lock: (
			<>
				<rect {...fl} x="4" y="10" width="16" height="11.5" rx="2.5" />
				<path {...s} d="M7.5 10V7.5a4.5 4.5 0 0 1 9 0V10" />
			</>
		),
		bolt: <path {...fl} d="M13.5 2 4 13.5h7L9.5 22 20 9.5h-7z" />,
		globe: (
			<>
				<circle {...s} cx="12" cy="12" r="9.2" />
				<path {...s} d="M2.8 12h18.4M12 2.8c2.6 2.6 3.8 5.6 3.8 9.2s-1.2 6.6-3.8 9.2c-2.6-2.6-3.8-5.6-3.8-9.2S9.4 5.4 12 2.8z" />
			</>
		),
		download: <path {...s} strokeWidth={2.6} d="M12 3.5v12M6.5 10.5 12 16l5.5-5.5M4 20.5h16" />,
		chevron: <path {...s} d="m6 9 6 6 6-6" />,
		stage: (
			<>
				<path {...s} d="M4.5 9.5a8.5 8.5 0 0 1 15 0M7.5 12a5 5 0 0 1 9 0" />
				<rect {...fl} x="10" y="11.5" width="4" height="7" rx="2" />
				<path {...s} d="M8 21.5h8" />
			</>
		),
		thread: (
			<>
				<path {...s} d="M4 5.5h13a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H9l-5 3.5z" />
				<path {...s} d="M8 10h8M8 13.5h5" />
			</>
		),
		compass: (
			<>
				<circle {...s} cx="12" cy="12" r="9.2" />
				<path {...fl} d="m15.8 8.2-2.2 5.4-5.4 2.2 2.2-5.4z" />
			</>
		),
		sticker: (
			<>
				<path {...s} d="M20.5 13V6a2.5 2.5 0 0 0-2.5-2.5H6A2.5 2.5 0 0 0 3.5 6v12A2.5 2.5 0 0 0 6 20.5h7z" />
				<path {...s} d="M20.5 13H16a3 3 0 0 0-3 3v4.5z" />
			</>
		),
		gem: <path {...fl} d="M6.5 3h11l4 5.5L12 21 2.5 8.5z" />,
		chat: <path {...fl} d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-9l-5.5 4v-4H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" />,
		apps: (
			<>
				<rect {...fl} x="3" y="3" width="8" height="8" rx="2.5" />
				<rect {...fl} x="13" y="3" width="8" height="8" rx="4" />
				<rect {...fl} x="3" y="13" width="8" height="8" rx="2.5" />
				<path {...fl} d="M17 13l4.3 4-4.3 4-4.3-4z" />
			</>
		),
		image: (
			<>
				<rect {...s} x="3" y="4" width="18" height="16" rx="3" />
				<circle {...fl} cx="9" cy="9.5" r="2" />
				<path {...fl} d="M4 18.5 9.5 13l3 3 3.5-4 4.5 5.5V19H4z" />
			</>
		),
		heart: <path {...fl} d="M12 21s-8.5-5.2-8.5-11A4.8 4.8 0 0 1 12 6.6 4.8 4.8 0 0 1 20.5 10c0 5.8-8.5 11-8.5 11z" />,
		arrowUp: <path {...s} strokeWidth={2.8} d="M12 19V5M5.5 11.5 12 5l6.5 6.5" />,
		back: <path {...s} strokeWidth={2.6} d="M15 4.5 7.5 12l7.5 7.5" />,
	};
	return (
		<svg width={size} height={size} viewBox="0 0 24 24" style={{display: 'block', flexShrink: 0, ...style}}>
			{g[name]}
		</svg>
	);
};

/* ---------------------------------------------------------------- People */
export type User = {name: string; emoji: string; g: [string, string]; color: string};
export const USERS = {
	nova: {name: 'nova', emoji: '🦊', g: ['#FF9A5A', '#EB459E'], color: '#FF6B6B'},
	kai: {name: 'kai.exe', emoji: '🐼', g: ['#5865F2', '#00A8FC'], color: C.green},
	mila: {name: 'mila', emoji: '🐸', g: ['#57F287', '#16A085'], color: '#F47FFF'},
	zed: {name: 'zed', emoji: '👾', g: ['#9B59B6', '#5865F2'], color: '#A5B4FF'},
	luna: {name: 'luna', emoji: '🐱', g: ['#FEE75C', '#FF9A5A'], color: C.yellow},
	rio: {name: 'rio', emoji: '🐙', g: ['#EB459E', '#9B59B6'], color: '#A5B4FF'},
	jun: {name: 'jun', emoji: '🐧', g: ['#00A8FC', '#57F287'], color: C.green},
	ava: {name: 'ava', emoji: '🦄', g: ['#F47FFF', '#5865F2'], color: '#F47FFF'},
	ozzy: {name: 'ozzy', emoji: '🦖', g: ['#43B581', '#FEE75C'], color: '#A5B4FF'},
	you: {name: 'you', emoji: '😎', g: ['#5865F2', '#EB459E'], color: '#fff'},
} satisfies Record<string, User>;
export type UserKey = keyof typeof USERS;

export const Emoji: React.FC<{e: string; size: number; style?: React.CSSProperties}> = ({e, size, style}) => (
	<span style={{fontFamily: EMOJI, fontSize: size, lineHeight: 1, display: 'inline-block', ...style}}>{e}</span>
);

export const Avatar: React.FC<{
	u: UserKey;
	size: number;
	speaking?: number; // 0..1 ring intensity
	status?: 'online' | 'idle' | 'dnd' | 'none';
	statusBg?: string;
	style?: React.CSSProperties;
}> = ({u, size, speaking = 0, status = 'none', statusBg = C.side, style}) => {
	const user = USERS[u];
	const ring = Math.max(2, size * 0.06);
	return (
		<div style={{position: 'relative', width: size, height: size, flexShrink: 0, ...style}}>
			<div
				style={{
					width: size,
					height: size,
					borderRadius: '50%',
					background: `linear-gradient(135deg, ${user.g[0]}, ${user.g[1]})`,
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'center',
					boxShadow:
						speaking > 0
							? `0 0 0 ${ring}px ${C.chat}, 0 0 0 ${ring * 2}px rgba(35,165,90,${speaking}), 0 0 ${size * 0.3}px rgba(35,165,90,${speaking * 0.6})`
							: undefined,
				}}
			>
				<Emoji e={user.emoji} size={size * 0.56} style={{transform: `translateY(${size * 0.02}px)`}} />
			</div>
			{status !== 'none' && (
				<div
					style={{
						position: 'absolute',
						right: -size * 0.04,
						bottom: -size * 0.04,
						width: size * 0.36,
						height: size * 0.36,
						borderRadius: '50%',
						background: statusBg,
						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',
					}}
				>
					<div
						style={{
							width: size * 0.24,
							height: size * 0.24,
							borderRadius: '50%',
							background: status === 'online' ? C.online : status === 'idle' ? C.idle : C.dnd,
						}}
					/>
				</div>
			)}
		</div>
	);
};

/* Discord default avatar: Clyde on a brand-coloured circle */
export const DefaultAvatar: React.FC<{size: number; color: string}> = ({size, color}) => (
	<div
		style={{
			width: size,
			height: size,
			borderRadius: '50%',
			background: color,
			display: 'flex',
			alignItems: 'center',
			justifyContent: 'center',
			flexShrink: 0,
		}}
	>
		<Clyde size={size * 0.6} />
	</div>
);

/* ---------------------------------------------------------------- Sparkle */
export const Sparkle: React.FC<{size: number; color?: string; style?: React.CSSProperties}> = ({
	size,
	color = '#fff',
	style,
}) => (
	<svg width={size} height={size} viewBox="0 0 24 24" style={{display: 'block', ...style}}>
		<path fill={color} d="M12 0c.7 6.2 5.8 11.3 12 12-6.2.7-11.3 5.8-12 12-.7-6.2-5.8-11.3-12-12C6.2 11.3 11.3.7 12 0z" />
	</svg>
);

/* ---------------------------------------------------------------- Background */
const STARS = new Array(150).fill(0).map((_, i) => ({
	x: random(`sx${i}`) * 1920,
	y: random(`sy${i}`) * 1080,
	s: 0.8 + random(`ss${i}`) * 2.2,
	ph: random(`sp${i}`) * Math.PI * 2,
	sp: 0.03 + random(`sv${i}`) * 0.06,
	d: 0.2 + random(`sd${i}`) * 0.8,
}));
const SPARKS = new Array(9).fill(0).map((_, i) => ({
	x: 80 + random(`kx${i}`) * 1760,
	y: 60 + random(`ky${i}`) * 960,
	s: 10 + random(`ks${i}`) * 18,
	ph: random(`kp${i}`) * 100,
}));

export const SpaceBg: React.FC<{
	f: number;
	a?: string;
	b?: string;
	grid?: boolean;
	drift?: number;
}> = ({f, a = C.blurple, b = C.fuchsia, grid = true, drift = 1}) => {
	const t = f / 30;
	return (
		<AbsoluteFill style={{background: `radial-gradient(120% 90% at 50% 120%, #1B1F7A 0%, #0B0D2E 45%, ${C.space} 100%)`, overflow: 'hidden'}}>
			<div
				style={{
					position: 'absolute',
					width: 1400,
					height: 1400,
					left: -300 + Math.sin(t * 0.4) * 120,
					top: -700 + Math.cos(t * 0.3) * 80,
					background: `radial-gradient(closest-side, ${a}88, ${a}00)`,
					opacity: 0.85,
				}}
			/>
			<div
				style={{
					position: 'absolute',
					width: 1300,
					height: 1300,
					right: -420 + Math.cos(t * 0.35) * 140,
					bottom: -760 + Math.sin(t * 0.25) * 90,
					background: `radial-gradient(closest-side, ${b}66, ${b}00)`,
					opacity: 0.9,
				}}
			/>
			<div
				style={{
					position: 'absolute',
					width: 900,
					height: 900,
					left: 760 + Math.sin(t * 0.5 + 1) * 160,
					top: 300 + Math.cos(t * 0.45) * 100,
					background: `radial-gradient(closest-side, ${C.blurpleDeep}55, transparent)`,
				}}
			/>
			{grid && (
				<div
					style={{
						position: 'absolute',
						inset: -80,
						backgroundImage:
							'linear-gradient(rgba(255,255,255,0.045) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px)',
						backgroundSize: '80px 80px',
						backgroundPosition: `${(-t * 12 * drift) % 80}px ${(-t * 6 * drift) % 80}px`,
						WebkitMaskImage: 'radial-gradient(70% 60% at 50% 50%, #000 0%, transparent 100%)',
						maskImage: 'radial-gradient(70% 60% at 50% 50%, #000 0%, transparent 100%)',
					}}
				/>
			)}
			{STARS.map((s, i) => {
				const tw = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(f * s.sp + s.ph));
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: (s.x - t * 8 * s.d * drift + 1920) % 1920,
							top: s.y,
							width: s.s,
							height: s.s,
							borderRadius: '50%',
							background: '#fff',
							opacity: tw * (0.3 + s.d * 0.5),
						}}
					/>
				);
			})}
			{SPARKS.map((s, i) => {
				const tw = 0.5 + 0.5 * Math.sin((f + s.ph) * 0.06);
				return (
					<Sparkle
						key={i}
						size={s.s * (0.6 + tw * 0.5)}
						color="#C9CDFB"
						style={{position: 'absolute', left: s.x, top: s.y, opacity: 0.15 + tw * 0.5, transform: `rotate(${f * 0.5 + i * 20}deg)`}}
					/>
				);
			})}
			<AbsoluteFill style={{background: 'radial-gradient(90% 80% at 50% 50%, transparent 55%, rgba(0,0,0,0.55) 100%)'}} />
		</AbsoluteFill>
	);
};

/* ---------------------------------------------------------------- Kinetic type */
export const GRAD = `linear-gradient(92deg, #8EA1FF 0%, ${C.blurple} 35%, ${C.fuchsia} 100%)`;

export const Reveal: React.FC<{
	text: string;
	f: number;
	start: number;
	stagger?: number;
	dur?: number;
	style?: React.CSSProperties;
	hl?: string[];
	hlBg?: string;
	align?: 'left' | 'center' | 'right';
	out?: number; // frame to start exit
}> = ({text, f, start, stagger = 3, dur = 22, style, hl = [], hlBg = GRAD, align = 'left', out}) => {
	let idx = 0;
	const lines = text.split('\n');
	return (
		<div style={{textAlign: align, ...style}}>
			{lines.map((line, li) => (
				<div key={li} style={{whiteSpace: 'nowrap'}}>
					{line.split(' ').map((w, wi) => {
						const i = idx++;
						const p = prog(f, start + i * stagger, start + i * stagger + dur);
						const o = out !== undefined ? prog(f, out + i * 1.5, out + i * 1.5 + 14) : 0;
						const isHl = hl.includes(w.replace(/[.,!?]/g, ''));
						return (
							<span
								key={wi}
								style={{
									display: 'inline-block',
									overflow: 'hidden',
									verticalAlign: 'top',
									padding: '0.06em 0.04em 0.1em',
									margin: '-0.06em 0.24em -0.1em 0',
								}}
							>
								<span
									style={{
										display: 'inline-block',
										transform: `translateY(${(1 - p) * 110 - o * 110}%) rotate(${(1 - p) * 6}deg)`,
										transformOrigin: 'left bottom',
										...(isHl
											? {
													backgroundImage: hlBg,
													WebkitBackgroundClip: 'text',
													backgroundClip: 'text',
													color: 'transparent',
												}
											: {}),
									}}
								>
									{w}
								</span>
							</span>
						);
					})}
				</div>
			))}
		</div>
	);
};

export const FadeUp: React.FC<{
	f: number;
	start: number;
	dist?: number;
	dur?: number;
	children: React.ReactNode;
	style?: React.CSSProperties;
	blur?: boolean;
}> = ({f, start, dist = 30, dur = 20, children, style, blur = false}) => {
	const p = prog(f, start, start + dur);
	return (
		<div
			style={{
				opacity: p,
				transform: `translateY(${(1 - p) * dist}px)`,
				filter: blur && p < 1 ? `blur(${(1 - p) * 8}px)` : undefined,
				...style,
			}}
		>
			{children}
		</div>
	);
};

export const Eyebrow: React.FC<{
	f: number;
	start: number;
	label: string;
	num?: string;
	color?: string;
	icon?: IconName;
}> = ({f, start, label, num, color = C.blurple, icon = 'bolt'}) => {
	const s = spr(f, start, {damping: 16});
	const w = prog(f, start + 4, start + 26);
	return (
		<div
			style={{
				display: 'inline-flex',
				alignItems: 'center',
				gap: 14,
				padding: '8px 22px 8px 8px',
				borderRadius: 999,
				background: 'rgba(255,255,255,0.06)',
				border: `1.5px solid ${color}88`,
				boxShadow: `0 0 30px ${color}33, inset 0 0 20px ${color}22`,
				transform: `scale(${lerp(0.6, 1, s)})`,
				transformOrigin: 'left center',
				opacity: Math.min(1, s * 1.5),
			}}
		>
			<div
				style={{
					width: 38,
					height: 38,
					borderRadius: 999,
					background: color,
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'center',
					color: color === C.yellow || color === C.green ? C.black : '#fff',
				}}
			>
				<Icon name={icon} size={22} />
			</div>
			<div
				style={{
					fontFamily: BODY,
					fontWeight: 800,
					fontSize: 20,
					letterSpacing: '0.16em',
					textTransform: 'uppercase',
					color: '#E3E5FF',
					clipPath: `inset(0 ${(1 - w) * 100}% 0 0)`,
					whiteSpace: 'nowrap',
				}}
			>
				{num && <span style={{color, marginRight: 12}}>{num}</span>}
				{label}
			</div>
		</div>
	);
};

export const Body: React.FC<{f: number; start: number; children: React.ReactNode; w?: number; size?: number; align?: 'left' | 'center'}> = ({
	f,
	start,
	children,
	w = 640,
	size = 28,
	align = 'left',
}) => (
	<FadeUp f={f} start={start} dist={24} dur={24}>
		<div style={{fontFamily: BODY, fontWeight: 500, fontSize: size, lineHeight: 1.45, color: '#B9BEE8', maxWidth: w, textAlign: align}}>
			{children}
		</div>
	</FadeUp>
);

/* Pill/badge used for floating callouts */
export const Callout: React.FC<{
	f: number;
	start: number;
	children: React.ReactNode;
	style?: React.CSSProperties;
	float?: number;
}> = ({f, start, children, style, float = 0}) => {
	const s = spr(f, start, {damping: 13, stiffness: 160});
	const bob = Math.sin((f + float * 30) / 22) * 6;
	return (
		<div
			style={{
				position: 'absolute',
				transform: `translateY(${bob}px) scale(${s})`,
				opacity: interpolate(s, [0, 0.4], [0, 1], clamp),
				...style,
			}}
		>
			<div
				style={{
					background: 'rgba(30,31,34,0.92)',
					border: '1px solid rgba(255,255,255,0.10)',
					borderRadius: 18,
					boxShadow: '0 24px 60px rgba(0,0,0,0.55), 0 0 0 1px rgba(0,0,0,0.3)',
					fontFamily: BODY,
					color: C.text,
				}}
			>
				{children}
			</div>
		</div>
	);
};

export const titleStyle = (size = 92): React.CSSProperties => ({...display(size), color: '#fff'});
export {easeOut};
