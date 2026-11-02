import React from 'react';
import {interpolate} from 'remotion';
import {Avatar, Clyde, Emoji, Icon, USERS, UserKey, Sparkle} from './primitives';
import {BODY, C, MONO, clamp, prog, spr, lerp} from './theme';

/* ================================================================ DESKTOP */
export const SERVERS: {e: string; g: [string, string]; name: string}[] = [
	{e: '🎮', g: ['#5865F2', '#8C54FF'], name: 'Pixel Party'},
	{e: '🎨', g: ['#EB459E', '#FF8A4C'], name: 'Art Club'},
	{e: '🎧', g: ['#23A55A', '#00A8FC'], name: 'Lo-fi Lounge'},
	{e: '📚', g: ['#F0B232', '#FF8A4C'], name: 'Study Hall'},
	{e: '🚀', g: ['#ED4245', '#EB459E'], name: 'Dev Hub'},
	{e: '🌙', g: ['#3B3F8F', '#5865F2'], name: 'Night Owls'},
	{e: '⚽', g: ['#1F8B4C', '#57F287'], name: 'Sunday League'},
	{e: '🍕', g: ['#FF8A4C', '#FEE75C'], name: 'Pizza Friday'},
];

export const TitleBar: React.FC = () => (
	<div style={{height: 34, background: C.rail, display: 'flex', alignItems: 'center', padding: '0 16px', gap: 9, flexShrink: 0}}>
		{['#FF5F57', '#FEBC2E', '#28C840'].map((c) => (
			<div key={c} style={{width: 13, height: 13, borderRadius: '50%', background: c}} />
		))}
		<div style={{flex: 1}} />
	</div>
);

export const DesktopShell: React.FC<{
	rail: React.ReactNode;
	sidebar: React.ReactNode;
	main: React.ReactNode;
	members?: React.ReactNode;
}> = ({rail, sidebar, main, members}) => (
	<div style={{width: 1440, height: 900, background: C.rail, display: 'flex', flexDirection: 'column', fontFamily: BODY, color: C.text}}>
		<TitleBar />
		<div style={{flex: 1, display: 'flex', minHeight: 0}}>
			<div style={{width: 76, flexShrink: 0}}>{rail}</div>
			<div style={{width: 262, background: C.side, borderTopLeftRadius: 10, display: 'flex', flexDirection: 'column', flexShrink: 0, overflow: 'hidden'}}>
				{sidebar}
			</div>
			<div style={{flex: 1, background: C.chat, display: 'flex', flexDirection: 'column', minWidth: 0, position: 'relative', overflow: 'hidden'}}>{main}</div>
			{members && <div style={{width: 250, background: C.side, flexShrink: 0, overflow: 'hidden'}}>{members}</div>}
		</div>
	</div>
);

const RailIcon: React.FC<{
	children: React.ReactNode;
	bg: string;
	selected?: boolean;
	pill?: number; // 0 none, small 8, 40 selected
	scale?: number;
	badge?: number;
	radius?: number;
}> = ({children, bg, pill = 0, scale = 1, badge, radius = 24}) => (
	<div style={{position: 'relative', width: 76, height: 56, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
		<div
			style={{
				position: 'absolute',
				left: 0,
				top: 28 - pill / 2,
				width: 4,
				height: pill,
				borderRadius: '0 4px 4px 0',
				background: '#fff',
				opacity: pill > 0 ? 1 : 0,
			}}
		/>
		<div
			style={{
				width: 50,
				height: 50,
				borderRadius: radius,
				background: bg,
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
				transform: `scale(${scale})`,
				position: 'relative',
			}}
		>
			{children}
			{badge !== undefined && (
				<div
					style={{
						position: 'absolute',
						right: -6,
						bottom: -4,
						minWidth: 22,
						height: 22,
						padding: '0 6px',
						borderRadius: 11,
						background: C.dnd,
						border: `4px solid ${C.rail}`,
						boxSizing: 'content-box',
						fontSize: 13,
						fontWeight: 800,
						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',
						color: '#fff',
					}}
				>
					{badge}
				</div>
			)}
		</div>
	</div>
);

export const ServerRail: React.FC<{
	f: number;
	start?: number;
	selected?: number;
	morph?: number; // selected icon circle -> squircle progress
	badges?: Record<number, number>;
	count?: number;
}> = ({f, start, selected = 0, morph = 1, badges = {}, count = 7}) => {
	const sc = (i: number) => (start === undefined ? 1 : spr(f, start + i * 3, {damping: 12, stiffness: 180}));
	return (
		<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 4}}>
			<RailIcon bg={C.chat} scale={sc(0)} radius={16}>
				<Clyde size={30} color="#DBDEE1" />
			</RailIcon>
			<div style={{width: 34, height: 2, background: '#35363C', borderRadius: 1, margin: '4px 0'}} />
			{SERVERS.slice(0, count).map((s, i) => {
				const isSel = i === selected;
				return (
					<RailIcon
						key={i}
						bg={`linear-gradient(135deg, ${s.g[0]}, ${s.g[1]})`}
						pill={isSel ? lerp(8, 40, morph) : badges[i] ? 8 : 0}
						radius={isSel ? lerp(25, 16, morph) : 25}
						scale={sc(i + 1)}
						badge={badges[i]}
					>
						<Emoji e={s.e} size={26} />
					</RailIcon>
				);
			})}
			<RailIcon bg={C.chat} scale={sc(count + 1)}>
				<Icon name="plus" size={26} color={C.online} />
			</RailIcon>
			<RailIcon bg={C.chat} scale={sc(count + 2)}>
				<Icon name="compass" size={26} color={C.online} />
			</RailIcon>
		</div>
	);
};

export type VoiceUser = {u: UserKey; speaking?: number; live?: boolean; muted?: boolean; video?: boolean};
export type Row =
	| {type: 'cat'; label: string}
	| {type: 'ch'; name: string; icon?: 'hash' | 'speaker' | 'stage' | 'thread' | 'calendar'; unread?: boolean; active?: boolean; badge?: number}
	| {type: 'voice'; name: string; icon?: 'speaker' | 'stage'; users?: VoiceUser[]; active?: boolean; userStart?: number[]};

export const ServerBanner: React.FC<{name: string; f: number}> = ({name, f}) => (
	<div style={{height: 132, position: 'relative', overflow: 'hidden', flexShrink: 0}}>
		<div style={{position: 'absolute', inset: 0, background: `linear-gradient(125deg, ${C.blurple} 0%, #8C54FF 50%, ${C.fuchsia} 100%)`}} />
		{[0, 1, 2, 3, 4].map((i) => (
			<Sparkle
				key={i}
				size={14 + (i % 3) * 8}
				color="rgba(255,255,255,0.7)"
				style={{position: 'absolute', left: 20 + i * 52, top: 18 + ((i * 37) % 60), transform: `rotate(${f * 1.5 + i * 30}deg)`}}
			/>
		))}
		<Emoji e="🎮" size={86} style={{position: 'absolute', right: -8, top: 18, transform: `rotate(-14deg) translateY(${Math.sin(f / 20) * 4}px)`}} />
		<div style={{position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(0,0,0,0) 40%, rgba(0,0,0,0.55))'}} />
		<div style={{position: 'absolute', left: 16, bottom: 12, display: 'flex', alignItems: 'center', gap: 8, fontWeight: 800, fontSize: 18}}>
			<div style={{width: 20, height: 20, borderRadius: 6, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
				<Icon name="gem" size={14} color={C.fuchsia} />
			</div>
			{name}
			<Icon name="chevron" size={18} color="#fff" />
		</div>
	</div>
);

export const ChannelSidebar: React.FC<{
	f: number;
	rows: Row[];
	start?: number;
	server?: string;
	voice?: string; // "Voice Connected" panel channel name
	banner?: boolean;
}> = ({f, rows, start, server = 'Pixel Party', voice, banner = true}) => {
	let k = 0;
	const ap = (i: number) => (start === undefined ? 1 : prog(f, start + i * 2.5, start + i * 2.5 + 16));
	return (
		<>
			{banner ? (
				<ServerBanner name={server} f={f} />
			) : (
				<div style={{height: 52, display: 'flex', alignItems: 'center', padding: '0 16px', fontWeight: 800, fontSize: 17, boxShadow: '0 1px 0 rgba(0,0,0,0.25)', gap: 8}}>
					{server}
					<div style={{flex: 1}} />
					<Icon name="chevron" size={18} color={C.muted} />
				</div>
			)}
			<div style={{flex: 1, padding: '10px 8px', overflow: 'hidden'}}>
				{rows.map((r, idx) => {
					const p = ap(k++);
					const st: React.CSSProperties = {opacity: p, transform: `translateX(${(1 - p) * -24}px)`};
					if (r.type === 'cat')
						return (
							<div
								key={idx}
								style={{
									...st,
									display: 'flex',
									alignItems: 'center',
									gap: 2,
									padding: '16px 6px 6px 2px',
									fontSize: 12.5,
									fontWeight: 800,
									letterSpacing: '0.04em',
									color: C.faint,
									textTransform: 'uppercase',
								}}
							>
								<Icon name="chevron" size={12} color={C.faint} />
								{r.label}
							</div>
						);
					if (r.type === 'ch')
						return (
							<div
								key={idx}
								style={{
									...st,
									position: 'relative',
									display: 'flex',
									alignItems: 'center',
									gap: 8,
									height: 36,
									padding: '0 10px',
									margin: '2px 0',
									borderRadius: 6,
									background: r.active ? '#404249' : 'transparent',
									color: r.active || r.unread ? '#fff' : C.channel,
									fontWeight: r.active || r.unread ? 700 : 500,
									fontSize: 16.5,
								}}
							>
								{r.unread && <div style={{position: 'absolute', left: -8, width: 4, height: 8, borderRadius: '0 4px 4px 0', background: '#fff'}} />}
								<Icon name={r.icon ?? 'hash'} size={20} color={r.active || r.unread ? C.muted : C.channel} />
								<span style={{flex: 1}}>{r.name}</span>
								{r.badge !== undefined && (
									<span style={{background: C.dnd, color: '#fff', borderRadius: 9, fontSize: 12, fontWeight: 800, padding: '1px 6px'}}>{r.badge}</span>
								)}
							</div>
						);
					return (
						<div key={idx} style={st}>
							<div
								style={{
									display: 'flex',
									alignItems: 'center',
									gap: 8,
									height: 36,
									padding: '0 10px',
									margin: '2px 0',
									borderRadius: 6,
									background: r.active ? '#404249' : 'transparent',
									color: r.active ? '#fff' : C.channel,
									fontWeight: r.active ? 700 : 500,
									fontSize: 16.5,
								}}
							>
								<Icon name={r.icon ?? 'speaker'} size={20} color={r.active ? C.muted : C.channel} />
								{r.name}
							</div>
							{(r.users ?? []).map((v, ui) => {
								const us = r.userStart?.[ui];
								const up = us === undefined ? 1 : spr(f, us, {damping: 15});
								if (up <= 0.001) return null;
								return (
									<div
										key={ui}
										style={{
											display: 'flex',
											alignItems: 'center',
											gap: 9,
											height: 34 * Math.min(1, up),
											padding: '0 0 0 34px',
											opacity: Math.min(1, up),
											transform: `translateX(${(1 - Math.min(1, up)) * -20}px)`,
											fontSize: 15.5,
											fontWeight: 600,
											color: (v.speaking ?? 0) > 0.3 ? '#fff' : C.muted,
										}}
									>
										<Avatar u={v.u} size={26} speaking={v.speaking} />
										<span style={{flex: 1}}>{USERS[v.u].name}</span>
										{v.live && (
											<span style={{background: C.dnd, color: '#fff', fontSize: 11, fontWeight: 900, padding: '2px 6px', borderRadius: 4, letterSpacing: '0.04em'}}>
												LIVE
											</span>
										)}
										{v.video && <Icon name="video" size={16} color={C.faint} />}
										{v.muted && <Icon name="micOff" size={16} color={C.faint} />}
										<div style={{width: 6}} />
									</div>
								);
							})}
						</div>
					);
				})}
			</div>
			{voice && (
				<div style={{background: C.userPanel, padding: '10px 12px', borderBottom: '1px solid #1E1F22'}}>
					<div style={{display: 'flex', alignItems: 'center', gap: 8}}>
						<svg width="18" height="16" viewBox="0 0 18 16">
							{[0, 1, 2].map((i) => (
								<rect key={i} x={i * 6} y={10 - i * 5} width="4" height={6 + i * 5} rx="1" fill={C.online} />
							))}
						</svg>
						<span style={{color: C.online, fontWeight: 800, fontSize: 15}}>Voice Connected</span>
						<div style={{flex: 1}} />
						<Icon name="hangup" size={22} color={C.muted} />
					</div>
					<div style={{color: C.faint, fontSize: 13.5, marginTop: 2}}>{voice} / Pixel Party</div>
					<div style={{display: 'flex', gap: 8, marginTop: 10}}>
						{(['video', 'screen', 'apps'] as const).map((n) => (
							<div key={n} style={{flex: 1, height: 34, borderRadius: 8, background: '#2B2D31', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
								<Icon name={n} size={20} color={C.body} />
							</div>
						))}
					</div>
				</div>
			)}
			<UserPanel />
		</>
	);
};

export const UserPanel: React.FC = () => (
	<div style={{height: 60, background: C.userPanel, display: 'flex', alignItems: 'center', padding: '0 10px', gap: 10, flexShrink: 0}}>
		<Avatar u="you" size={36} status="online" statusBg={C.userPanel} />
		<div style={{flex: 1, lineHeight: 1.2}}>
			<div style={{fontWeight: 700, fontSize: 15}}>you</div>
			<div style={{fontSize: 12.5, color: C.faint}}>Online</div>
		</div>
		<Icon name="mic" size={21} color={C.muted} />
		<Icon name="headphones" size={21} color={C.muted} />
		<Icon name="gear" size={21} color={C.muted} />
	</div>
);

export const ChatHeader: React.FC<{name: string; topic?: string; icon?: 'hash' | 'speaker' | 'stage'}> = ({name, topic, icon = 'hash'}) => (
	<div
		style={{
			height: 54,
			display: 'flex',
			alignItems: 'center',
			gap: 10,
			padding: '0 18px',
			boxShadow: '0 1px 0 rgba(0,0,0,0.28)',
			flexShrink: 0,
			zIndex: 2,
		}}
	>
		<Icon name={icon} size={24} color={C.channel} />
		<span style={{fontWeight: 800, fontSize: 17}}>{name}</span>
		{topic && (
			<>
				<div style={{width: 1, height: 24, background: '#3F4147', margin: '0 6px'}} />
				<span style={{color: C.faint, fontSize: 15}}>{topic}</span>
			</>
		)}
		<div style={{flex: 1}} />
		{(['thread', 'bell', 'pin', 'users'] as const).map((n) => (
			<Icon key={n} name={n} size={23} color={C.muted} style={{marginLeft: 12}} />
		))}
		<div
			style={{
				marginLeft: 16,
				width: 170,
				height: 30,
				borderRadius: 6,
				background: C.rail,
				display: 'flex',
				alignItems: 'center',
				padding: '0 8px',
				color: C.faint,
				fontSize: 14,
			}}
		>
			<span style={{flex: 1}}>Search</span>
			<Icon name="search" size={16} color={C.faint} />
		</div>
	</div>
);

export type Reaction = {e: string; n: number; me?: boolean; at?: number};

export const Reactions: React.FC<{f: number; list: Reaction[]; scale?: number}> = ({f, list, scale = 1}) => (
	<div style={{display: 'flex', gap: 6 * scale, marginTop: 6 * scale, flexWrap: 'wrap'}}>
		{list.map((r, i) => {
			const s = r.at === undefined ? 1 : spr(f, r.at, {damping: 9, stiffness: 220});
			if (r.at !== undefined && f < r.at) return null;
			return (
				<div
					key={i}
					style={{
						display: 'flex',
						alignItems: 'center',
						gap: 6 * scale,
						padding: `${3 * scale}px ${9 * scale}px`,
						borderRadius: 9 * scale,
						background: r.me ? 'rgba(88,101,242,0.18)' : '#2B2D31',
						border: `${1.5 * scale}px solid ${r.me ? C.blurple : 'transparent'}`,
						transform: `scale(${s})`,
					}}
				>
					<Emoji e={r.e} size={18 * scale} />
					<span style={{fontSize: 15 * scale, fontWeight: 700, color: r.me ? '#DEE0FC' : C.muted}}>{r.n}</span>
				</div>
			);
		})}
	</div>
);

export const Msg: React.FC<{
	f: number;
	u: UserKey;
	at?: number; // appear frame
	h?: number; // est. height for push-up animation
	time?: string;
	children?: React.ReactNode;
	reply?: {u: UserKey; text: string};
	reactions?: Reaction[];
	bot?: boolean;
	compact?: boolean;
	mention?: boolean;
	scale?: number;
}> = ({f, u, at, h = 120, time = 'Today at 9:41 PM', children, reply, reactions, bot, compact, mention, scale = 1}) => {
	const p = at === undefined ? 1 : prog(f, at, at + 14);
	if (p <= 0) return null;
	const user = USERS[u];
	return (
		<div style={{maxHeight: h * scale * p, overflow: p < 1 ? 'hidden' : 'visible', flexShrink: 0}}>
			<div
				style={{
					position: 'relative',
					padding: `${compact ? 2 * scale : 10 * scale}px ${18 * scale}px ${4 * scale}px ${18 * scale}px`,
					opacity: p,
					transform: `translateY(${(1 - p) * 18}px)`,
					background: mention ? 'rgba(240,178,50,0.08)' : undefined,
					borderLeft: mention ? `${2 * scale}px solid ${C.idle}` : undefined,
				}}
			>
				{reply && (
					<div style={{display: 'flex', alignItems: 'center', gap: 6 * scale, marginLeft: 22 * scale, marginBottom: 4 * scale, fontSize: 14 * scale, color: C.faint}}>
						<div
							style={{
								width: 30 * scale,
								height: 12 * scale,
								borderLeft: `${2 * scale}px solid #4E5058`,
								borderTop: `${2 * scale}px solid #4E5058`,
								borderTopLeftRadius: 6 * scale,
								marginTop: 8 * scale,
							}}
						/>
						<Avatar u={reply.u} size={16 * scale} />
						<span style={{color: USERS[reply.u].color, fontWeight: 600}}>@{USERS[reply.u].name}</span>
						<span style={{color: C.muted}}>{reply.text}</span>
					</div>
				)}
				<div style={{display: 'flex', gap: 16 * scale}}>
					{compact ? <div style={{width: 42 * scale}} /> : <Avatar u={u} size={42 * scale} />}
					<div style={{flex: 1, minWidth: 0}}>
						{!compact && (
							<div style={{display: 'flex', alignItems: 'baseline', gap: 8 * scale, marginBottom: 2 * scale}}>
								<span style={{fontWeight: 700, fontSize: 16.5 * scale, color: user.color}}>{user.name}</span>
								{bot && (
									<span
										style={{
											background: C.blurple,
											color: '#fff',
											fontSize: 11 * scale,
											fontWeight: 800,
											padding: `${1 * scale}px ${5 * scale}px`,
											borderRadius: 4 * scale,
											alignSelf: 'center',
										}}
									>
										✓ APP
									</span>
								)}
								<span style={{fontSize: 12.5 * scale, color: C.faint}}>{time}</span>
							</div>
						)}
						<div style={{fontSize: 16.5 * scale, lineHeight: 1.4, color: C.body}}>{children}</div>
						{reactions && <Reactions f={f} list={reactions} scale={scale} />}
					</div>
				</div>
			</div>
		</div>
	);
};

export const Mention: React.FC<{children: React.ReactNode}> = ({children}) => (
	<span style={{background: 'rgba(88,101,242,0.3)', color: '#C9CDFB', borderRadius: 4, padding: '0 3px', fontWeight: 600}}>{children}</span>
);

export const Typing: React.FC<{f: number; text: string; scale?: number}> = ({f, text, scale = 1}) => (
	<div style={{display: 'flex', alignItems: 'center', gap: 8 * scale, fontSize: 13.5 * scale, color: C.muted, padding: `0 ${18 * scale}px`, height: 24 * scale}}>
		<div style={{display: 'flex', gap: 3 * scale}}>
			{[0, 1, 2].map((i) => (
				<div
					key={i}
					style={{
						width: 6 * scale,
						height: 6 * scale,
						borderRadius: '50%',
						background: C.text,
						opacity: 0.4 + 0.6 * Math.max(0, Math.sin((f - i * 4) / 4)),
						transform: `translateY(${-Math.max(0, Math.sin((f - i * 4) / 4)) * 3 * scale}px)`,
					}}
				/>
			))}
		</div>
		<span>
			<b style={{color: C.text}}>{text}</b> is typing…
		</span>
	</div>
);

export const InputBar: React.FC<{f: number; placeholder: string; text?: string; scale?: number}> = ({f, placeholder, text, scale = 1}) => (
	<div style={{padding: `0 ${18 * scale}px ${22 * scale}px`, flexShrink: 0}}>
		<div
			style={{
				height: 50 * scale,
				borderRadius: 10 * scale,
				background: C.input,
				display: 'flex',
				alignItems: 'center',
				padding: `0 ${14 * scale}px`,
				gap: 14 * scale,
			}}
		>
			<div style={{width: 26 * scale, height: 26 * scale, borderRadius: '50%', background: '#B5BAC1', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
				<Icon name="plus" size={18 * scale} color={C.input} />
			</div>
			<div style={{flex: 1, fontSize: 16.5 * scale, color: text ? C.body : '#6D6F78', fontFamily: text?.startsWith('/') ? MONO : BODY}}>
				{text || placeholder}
				{text !== undefined && <span style={{opacity: Math.floor(f / 8) % 2 ? 0 : 1, color: C.text}}>|</span>}
			</div>
			{(['gift', 'gif', 'sticker', 'emoji'] as const).map((n) => (
				<Icon key={n} name={n} size={25 * scale} color={C.muted} />
			))}
		</div>
	</div>
);

export const MemberList: React.FC<{f?: number; start?: number; groups: {label: string; color?: string; users: UserKey[]}[]}> = ({f = 0, start, groups}) => {
	let k = 0;
	return (
		<div style={{padding: '16px 10px'}}>
			{groups.map((g, gi) => (
				<div key={gi}>
					<div style={{fontSize: 12.5, fontWeight: 800, color: C.faint, letterSpacing: '0.04em', padding: '14px 8px 6px', textTransform: 'uppercase'}}>
						{g.label} — {g.users.length}
					</div>
					{g.users.map((u) => {
						const p = start === undefined ? 1 : prog(f, start + k * 2, start + k * 2 + 14);
						k++;
						return (
							<div key={u} style={{display: 'flex', alignItems: 'center', gap: 12, height: 46, padding: '0 8px', opacity: p, transform: `translateX(${(1 - p) * 20}px)`}}>
								<Avatar u={u} size={34} status={gi === groups.length - 1 && u === 'ozzy' ? 'idle' : 'online'} />
								<span style={{fontWeight: 600, fontSize: 16, color: g.color ?? USERS[u].color}}>{USERS[u].name}</span>
							</div>
						);
					})}
				</div>
			))}
		</div>
	);
};

/* ================================================================ VISUALS */
export const GameScene: React.FC<{f: number; style?: React.CSSProperties}> = ({f, style}) => (
	<div style={{position: 'absolute', inset: 0, overflow: 'hidden', background: 'linear-gradient(180deg, #120428 0%, #3a0b5c 38%, #ff3d7f 52%, #1a0630 52.2%, #0a0118 100%)', ...style}}>
		{/* sun */}
		<div
			style={{
				position: 'absolute',
				left: '50%',
				top: '16%',
				width: '30%',
				aspectRatio: '1',
				transform: 'translateX(-50%)',
				borderRadius: '50%',
				background: 'linear-gradient(180deg, #FEE75C 0%, #FF8A4C 45%, #EB459E 100%)',
				WebkitMaskImage:
					'repeating-linear-gradient(180deg, #000 0px, #000 14px, transparent 14px, transparent 20px)',
				boxShadow: '0 0 80px #ff3d7f',
			}}
		/>
		{/* mountains */}
		<svg viewBox="0 0 100 20" preserveAspectRatio="none" style={{position: 'absolute', left: 0, top: '38%', width: '100%', height: '14.5%'}}>
			<path d="M0 20 L8 9 L15 15 L24 4 L33 14 L42 8 L50 16 L58 6 L67 13 L76 3 L86 12 L93 7 L100 14 L100 20Z" fill="#2a0845" stroke="#ff3d7f" strokeWidth="0.25" />
		</svg>
		{/* grid floor */}
		<div style={{position: 'absolute', left: '-50%', right: '-50%', top: '52%', bottom: '-40%', perspective: 300, perspectiveOrigin: '50% 0%'}}>
			<div
				style={{
					position: 'absolute',
					inset: 0,
					transform: 'rotateX(62deg)',
					transformOrigin: '50% 0%',
					backgroundImage:
						'linear-gradient(rgba(235,69,158,0.9) 2px, transparent 2px), linear-gradient(90deg, rgba(88,101,242,0.9) 2px, transparent 2px)',
					backgroundSize: '60px 60px',
					backgroundPosition: `0px ${(f * 6) % 60}px`,
				}}
			/>
		</div>
		{/* ship */}
		<svg
			viewBox="0 0 40 20"
			style={{position: 'absolute', left: `calc(50% - 7% + ${Math.sin(f / 14) * 6}%)`, bottom: '12%', width: '14%', filter: 'drop-shadow(0 0 8px #57F287)'}}
		>
			<path d="M20 0 L40 18 L28 15 L20 20 L12 15 L0 18 Z" fill="#0b0c1a" stroke="#57F287" strokeWidth="1.4" />
			<path d="M16 16 L20 19 L24 16" stroke="#FEE75C" strokeWidth="1.5" fill="none" />
		</svg>
		<div style={{position: 'absolute', left: '3%', top: '4%', fontFamily: MONO, color: '#57F287', fontSize: '2.2cqw', fontWeight: 500, textShadow: '0 0 8px #57F287'}}>
			SCORE {String(48210 + Math.floor(f * 37)).padStart(7, '0')}
		</div>
		<div style={{position: 'absolute', right: '3%', top: '4%', fontFamily: MONO, color: '#FEE75C', fontSize: '2.2cqw', textShadow: '0 0 8px #FEE75C'}}>
			LAP 2/3
		</div>
	</div>
);

export const CamTile: React.FC<{
	f: number;
	u: UserKey;
	speaking?: number;
	cam?: boolean;
	label?: boolean;
	radius?: number;
	scale?: number;
	style?: React.CSSProperties;
	seed?: number;
}> = ({f, u, speaking = 0, cam = true, label = true, radius = 12, scale = 1, style, seed = 0}) => {
	const user = USERS[u];
	const sway = Math.sin((f + seed * 17) / 26) * 3;
	return (
		<div
			style={{
				position: 'relative',
				borderRadius: radius,
				overflow: 'hidden',
				background: cam ? `linear-gradient(160deg, ${user.g[0]}55, #15161a 70%)` : '#232428',
				boxShadow: speaking > 0 ? `inset 0 0 0 ${3 * scale}px rgba(35,165,90,${speaking})` : undefined,
				containerType: 'size',
				...style,
			}}
		>
			{cam ? (
				<>
					{/* room */}
					<div style={{position: 'absolute', inset: 0, background: `radial-gradient(60% 50% at 75% 20%, ${user.g[1]}55, transparent)`}} />
					<div style={{position: 'absolute', left: '8%', top: '12%', width: '16%', height: '30%', borderRadius: 6, background: 'rgba(255,255,255,0.06)'}} />
					{/* person silhouette */}
					<div
						style={{
							position: 'absolute',
							left: '50%',
							bottom: '-8%',
							width: '62%',
							height: '46%',
							transform: `translateX(calc(-50% + ${sway}px))`,
							borderRadius: '50% 50% 0 0',
							background: `linear-gradient(180deg, ${user.g[0]}, ${user.g[1]})`,
						}}
					/>
					<div
						style={{
							position: 'absolute',
							left: '50%',
							top: '22%',
							width: '30%',
							aspectRatio: '1',
							transform: `translateX(calc(-50% + ${sway * 1.3}px))`,
							borderRadius: '50%',
							background: '#F5D0B5',
							display: 'flex',
							alignItems: 'center',
							justifyContent: 'center',
							overflow: 'hidden',
						}}
					>
						<Emoji e={user.emoji} size={100} style={{fontSize: '24cqmin'}} />
					</div>
				</>
			) : (
				<div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
					<Avatar u={u} size={90 * scale} speaking={speaking} />
				</div>
			)}
			{label && (
				<div
					style={{
						position: 'absolute',
						left: 10 * scale,
						bottom: 10 * scale,
						background: 'rgba(0,0,0,0.6)',
						borderRadius: 6 * scale,
						padding: `${3 * scale}px ${8 * scale}px`,
						fontSize: 14 * scale,
						fontWeight: 700,
						color: '#fff',
						display: 'flex',
						gap: 5 * scale,
						alignItems: 'center',
					}}
				>
					{user.name}
				</div>
			)}
		</div>
	);
};

export const CallControls: React.FC<{scale?: number; f: number}> = ({scale = 1}) => (
	<div style={{display: 'flex', gap: 14 * scale, alignItems: 'center', justifyContent: 'center'}}>
		{(['video', 'screen', 'apps', 'mic'] as const).map((n) => (
			<div
				key={n}
				style={{
					width: 56 * scale,
					height: 56 * scale,
					borderRadius: '50%',
					background: n === 'screen' ? C.blurple : '#2B2D31',
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'center',
				}}
			>
				<Icon name={n} size={26 * scale} color="#fff" />
			</div>
		))}
		<div style={{width: 72 * scale, height: 56 * scale, borderRadius: 28 * scale, background: C.dnd, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
			<Icon name="hangup" size={30 * scale} color="#fff" />
		</div>
	</div>
);

/* ================================================================ MOBILE */
export const MobileHeader: React.FC<{title: string; sub?: string; icon?: 'hash' | 'speaker' | 'stage'}> = ({title, sub, icon = 'hash'}) => (
	<div style={{paddingTop: 58, height: 112, display: 'flex', alignItems: 'center', gap: 10, padding: '58px 16px 0', background: C.chat, boxShadow: '0 1px 0 rgba(0,0,0,0.3)', flexShrink: 0}}>
		<Icon name="back" size={24} color={C.muted} />
		<div style={{width: 36, height: 36, borderRadius: '50%', background: '#2B2D31', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
			<Icon name={icon} size={20} color={C.muted} />
		</div>
		<div style={{flex: 1, lineHeight: 1.15}}>
			<div style={{fontWeight: 800, fontSize: 18, color: '#fff'}}>{title}</div>
			{sub && <div style={{fontSize: 13, color: C.faint}}>{sub}</div>}
		</div>
		<Icon name="search" size={22} color={C.muted} />
		<Icon name="users" size={22} color={C.muted} style={{marginLeft: 10}} />
	</div>
);

export const MobileInput: React.FC<{f: number; text?: string; placeholder?: string}> = ({f, text, placeholder = 'Message #general'}) => (
	<div style={{display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px 34px', flexShrink: 0}}>
		<div style={{width: 40, height: 40, borderRadius: '50%', background: '#2B2D31', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
			<Icon name="plus" size={22} color={C.muted} />
		</div>
		<div style={{width: 40, height: 40, borderRadius: '50%', background: '#2B2D31', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
			<Icon name="gift" size={20} color={C.muted} />
		</div>
		<div
			style={{
				flex: 1,
				height: 42,
				borderRadius: 21,
				background: '#2B2D31',
				display: 'flex',
				alignItems: 'center',
				padding: '0 14px',
				fontSize: 15.5,
				color: text ? C.body : '#80848E',
				gap: 6,
			}}
		>
			<span style={{flex: 1, whiteSpace: 'nowrap', overflow: 'hidden'}}>
				{text || placeholder}
				{text !== undefined && <span style={{opacity: Math.floor(f / 8) % 2 ? 0 : 1}}>|</span>}
			</span>
			<Icon name="emoji" size={22} color={C.muted} />
		</div>
		<div
			style={{
				width: 40,
				height: 40,
				borderRadius: '50%',
				background: text ? C.blurple : '#2B2D31',
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
			}}
		>
			<Icon name={text ? 'arrowUp' : 'mic'} size={20} color={text ? '#fff' : C.muted} />
		</div>
	</div>
);

export const MobileChat: React.FC<{title: string; sub?: string; children: React.ReactNode; input?: React.ReactNode}> = ({title, sub, children, input}) => (
	<div style={{position: 'absolute', inset: 0, background: C.chat, display: 'flex', flexDirection: 'column', fontFamily: BODY, color: C.text}}>
		<MobileHeader title={title} sub={sub} />
		<div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', overflow: 'hidden', paddingBottom: 6}}>{children}</div>
		{input}
	</div>
);

/* mobile home: server rail + channel list */
export const MobileHome: React.FC<{f: number; start?: number}> = ({f, start}) => {
	const rows: Row[] = [
		{type: 'ch', name: 'welcome', icon: 'hash'},
		{type: 'ch', name: 'announcements', unread: true, badge: 2},
		{type: 'cat', label: 'Text Channels'},
		{type: 'ch', name: 'general', unread: true},
		{type: 'ch', name: 'memes'},
		{type: 'ch', name: 'clips-and-highlights'},
		{type: 'cat', label: 'Voice Channels'},
		{type: 'voice', name: 'Lounge', users: [{u: 'nova', speaking: 1}, {u: 'kai'}, {u: 'mila'}]},
		{type: 'voice', name: 'Gaming'},
	];
	return (
		<div style={{position: 'absolute', inset: 0, background: C.rail, display: 'flex', fontFamily: BODY, color: C.text, paddingTop: 56}}>
			<div style={{width: 76}}>
				<ServerRail f={f} start={start} count={7} badges={{2: 4}} />
			</div>
			<div style={{flex: 1, background: C.side, borderTopLeftRadius: 18, overflow: 'hidden', display: 'flex', flexDirection: 'column'}}>
				<ServerBanner name="Pixel Party" f={f} />
				<div style={{transform: 'scale(0.94)', transformOrigin: 'top left', width: '106%'}}>
					<ChannelSidebarRows f={f} rows={rows} start={start === undefined ? undefined : start + 6} />
				</div>
			</div>
		</div>
	);
};

/* rows only (for mobile) */
const ChannelSidebarRows: React.FC<{f: number; rows: Row[]; start?: number}> = ({f, rows, start}) => {
	// reuse ChannelSidebar visuals without header/footer
	return (
		<div style={{display: 'flex', flexDirection: 'column'}}>
			<SidebarRowsOnly f={f} rows={rows} start={start} />
		</div>
	);
};

const SidebarRowsOnly: React.FC<{f: number; rows: Row[]; start?: number}> = ({f, rows, start}) => {
	// small wrapper: render ChannelSidebar and hide banner/user panel via clipping
	return (
		<div style={{position: 'relative', height: 640, overflow: 'hidden'}}>
			<div style={{position: 'absolute', top: -132, left: 0, right: 0}}>
				<ChannelSidebar f={f} rows={rows} start={start} />
			</div>
		</div>
	);
};

export const Bar: React.FC<{p: number; color: string; h?: number}> = ({p, color, h = 8}) => (
	<div style={{height: h, borderRadius: h, background: 'rgba(255,255,255,0.08)', overflow: 'hidden'}}>
		<div style={{width: `${p * 100}%`, height: '100%', borderRadius: h, background: color}} />
	</div>
);

export const Toggle: React.FC<{on: number}> = ({on}) => (
	<div
		style={{
			width: 46,
			height: 26,
			borderRadius: 13,
			background: interpolate(on, [0, 1], [0, 1], clamp) > 0.5 ? C.online : '#80848E',
			position: 'relative',
			flexShrink: 0,
		}}
	>
		<div
			style={{
				position: 'absolute',
				top: 3,
				left: lerp(3, 23, on),
				width: 20,
				height: 20,
				borderRadius: '50%',
				background: '#fff',
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
			}}
		>
			<Icon name={on > 0.5 ? 'check' : 'plus'} size={13} color={on > 0.5 ? C.online : '#80848E'} style={{transform: on > 0.5 ? undefined : 'rotate(45deg)'}} />
		</div>
	</div>
);
