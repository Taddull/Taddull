import React from 'react';
import {interpolate} from 'remotion';
import {GameScene} from '../discord/ui';
import {CH, ChAvatar, ChKey, Emoji, ICELAND, Icon, IcelandScene, PlayIcon, ShortScene, Thumb, VIDEOS, Video, clamp, easeInOut, lerp, prog, spr} from './kit';
import {Y, YBODY, ydisplay} from './theme';

/* ================================================================ desktop: browser + YouTube chrome */
export const Browser: React.FC<{children: React.ReactNode; url?: string}> = ({children, url = 'youtube.com'}) => (
	<div style={{width: 1440, height: 900, background: Y.ui, display: 'flex', flexDirection: 'column', fontFamily: YBODY, color: Y.text}}>
		<div style={{height: 40, background: '#1F1F1F', display: 'flex', alignItems: 'center', gap: 9, padding: '0 16px', flexShrink: 0}}>
			{['#FF5F57', '#FEBC2E', '#28C840'].map((c) => (
				<div key={c} style={{width: 13, height: 13, borderRadius: '50%', background: c}} />
			))}
			<div style={{marginLeft: 18, height: 28, padding: '0 14px', borderRadius: '10px 10px 0 0', background: Y.ui, display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, alignSelf: 'flex-end'}}>
				<PlayIcon h={11} /> YouTube
			</div>
			<div style={{flex: 1}} />
			<div style={{width: 420, height: 26, borderRadius: 13, background: '#2A2A2A', display: 'flex', alignItems: 'center', padding: '0 12px', fontSize: 13, color: Y.text2, gap: 8}}>
				<Icon name="globe" size={13} color={Y.text2} /> {url}
			</div>
			<div style={{flex: 1}} />
		</div>
		<div style={{flex: 1, position: 'relative', overflow: 'hidden'}}>{children}</div>
	</div>
);

export const TopBar: React.FC<{bell?: number}> = ({bell = 9}) => (
	<div style={{height: 56, display: 'flex', alignItems: 'center', padding: '0 16px', gap: 16, flexShrink: 0}}>
		<Icon name="menu" size={24} color={Y.text} />
		<div style={{display: 'flex', alignItems: 'center', gap: 4}}>
			<PlayIcon h={20} />
			<span style={{fontWeight: 700, fontSize: 20, letterSpacing: '-0.06em'}}>YouTube</span>
		</div>
		<div style={{flex: 1, display: 'flex', justifyContent: 'center', gap: 12}}>
			<div style={{width: 520, height: 40, borderRadius: 20, border: `1px solid ${Y.ui4}`, display: 'flex', overflow: 'hidden'}}>
				<div style={{flex: 1, display: 'flex', alignItems: 'center', padding: '0 16px', color: '#888', fontSize: 16}}>Search</div>
				<div style={{width: 64, background: Y.ui3, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
					<Icon name="search" size={20} color={Y.text} />
				</div>
			</div>
			<div style={{width: 40, height: 40, borderRadius: 20, background: Y.ui3, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
				<Icon name="mic" size={20} color={Y.text} />
			</div>
		</div>
		<div style={{display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 18, background: Y.ui3, fontSize: 14, fontWeight: 500}}>
			<Icon name="plus" size={18} color={Y.text} /> Create
		</div>
		<div style={{position: 'relative'}}>
			<Icon name="bell" size={24} color={Y.text} />
			<div style={{position: 'absolute', right: -8, top: -6, background: Y.red, borderRadius: 9, fontSize: 11, fontWeight: 700, padding: '1px 5px'}}>{bell}+</div>
		</div>
		<ChAvatar c="you" size={32} />
	</div>
);

const SideItem: React.FC<{icon: Parameters<typeof Icon>[0]['name']; label: string; active?: boolean; p?: number}> = ({icon, label, active, p = 1}) => (
	<div style={{display: 'flex', alignItems: 'center', gap: 22, height: 40, padding: '0 12px', borderRadius: 10, background: active ? Y.ui3 : undefined, fontSize: 14, fontWeight: active ? 500 : 400, opacity: p, transform: `translateX(${(1 - p) * -16}px)`}}>
		<Icon name={icon} size={22} color={Y.text} />
		{label}
	</div>
);

export const Sidebar: React.FC<{t: number; start?: number}> = ({t, start}) => {
	const ap = (i: number) => (start === undefined ? 1 : prog(t, start + i * 2.5, start + i * 2.5 + 14));
	const items: [Parameters<typeof Icon>[0]['name'], string][] = [
		['home', 'Home'],
		['shorts', 'Shorts'],
		['subs', 'Subscriptions'],
	];
	const you: [Parameters<typeof Icon>[0]['name'], string][] = [
		['history', 'History'],
		['playlist', 'Playlists'],
		['later', 'Watch later'],
		['like', 'Liked videos'],
	];
	const subs: ChKey[] = ['maya', 'wander', 'chill', 'pixel', 'noodle', 'cosmo'];
	let k = 0;
	return (
		<div style={{width: 230, padding: '8px 12px', flexShrink: 0}}>
			{items.map(([i, l], n) => (
				<SideItem key={l} icon={i} label={l} active={n === 0} p={ap(k++)} />
			))}
			<div style={{height: 1, background: Y.ui4, margin: '12px 0'}} />
			<div style={{fontSize: 16, fontWeight: 500, padding: '4px 12px 8px', opacity: ap(k++)}}>You ›</div>
			{you.map(([i, l]) => (
				<SideItem key={l} icon={i} label={l} p={ap(k++)} />
			))}
			<div style={{height: 1, background: Y.ui4, margin: '12px 0'}} />
			<div style={{fontSize: 16, fontWeight: 500, padding: '4px 12px 8px', opacity: ap(k++)}}>Subscriptions</div>
			{subs.map((c) => {
				const p = ap(k++);
				return (
					<div key={c} style={{display: 'flex', alignItems: 'center', gap: 22, height: 40, padding: '0 12px', fontSize: 14, opacity: p, transform: `translateX(${(1 - p) * -16}px)`}}>
						<ChAvatar c={c} size={24} />
						<span style={{flex: 1}}>{CH[c].name}</span>
						<div style={{width: 4, height: 4, borderRadius: 2, background: Y.blue}} />
					</div>
				);
			})}
		</div>
	);
};

export const CHIPS = ['All', 'Gaming', 'Music', 'Live', 'Cooking', 'Travel', 'Podcasts', 'Recently uploaded', 'New to you'];

export const Chips: React.FC<{t: number; start?: number; step?: number; active?: number}> = ({t, start, step = 3.75, active = 0}) => (
	<div style={{display: 'flex', gap: 12, padding: '8px 0 14px'}}>
		{CHIPS.map((c, i) => {
			const s = start === undefined ? 1 : spr(t, start + i * step, {damping: 12, stiffness: 200});
			return (
				<div key={c} style={{padding: '7px 13px', borderRadius: 8, fontSize: 14, fontWeight: 500, whiteSpace: 'nowrap', background: i === active ? Y.text : Y.ui3, color: i === active ? Y.ui : Y.text, transform: `scale(${s})`}}>
					{c}
				</div>
			);
		})}
	</div>
);

export const VideoCard: React.FC<{v: Video; p?: number; hot?: number; w?: number}> = ({v, p = 1, hot = 0, w = 360}) => (
	<div style={{width: w, opacity: p, transform: `translateY(${(1 - p) * 30}px) scale(${1 + hot * 0.04})`}}>
		<Thumb v={v} style={{width: w, boxShadow: hot > 0 ? `0 0 0 ${3 * hot}px ${Y.text}` : undefined}} />
		<div style={{display: 'flex', gap: 12, marginTop: 12}}>
			<ChAvatar c={v.ch} size={36} />
			<div style={{flex: 1, minWidth: 0}}>
				<div style={{fontSize: 16, fontWeight: 500, lineHeight: 1.35, color: Y.text, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical'}}>{v.title}</div>
				<div style={{fontSize: 14, color: Y.text2, marginTop: 4}}>{CH[v.ch].name} ✓</div>
				<div style={{fontSize: 14, color: Y.text2}}>
					{v.views}
					{v.ago ? ` • ${v.ago}` : ''}
				</div>
			</div>
		</div>
	</div>
);

/** home feed: 3x3 grid. `hot` = index of the card the cursor hovers/clicks */
export const HomeFeed: React.FC<{t: number; gridStart?: number; chipStart?: number; hot?: number; hotP?: number}> = ({t, gridStart, chipStart, hot, hotP = 0}) => (
	<div style={{display: 'flex', height: '100%'}}>
		<Sidebar t={t} start={chipStart} />
		<div style={{flex: 1, paddingRight: 16, overflow: 'hidden'}}>
			<Chips t={t} start={chipStart} />
			<div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 368px)', columnGap: 16, rowGap: 36}}>
				{VIDEOS.map((v, i) => (
					<VideoCard key={i} v={v} w={368} p={gridStart === undefined ? 1 : prog(t, gridStart + i * 3, gridStart + i * 3 + 16)} hot={i === hot ? hotP : 0} />
				))}
			</div>
		</div>
	</div>
);

/* player chrome */
export const Player: React.FC<{f: number; children: React.ReactNode; progress: number; live?: boolean; time?: string; w: number}> = ({f, children, progress, live, time = '3:12 / 15:30', w}) => (
	<div style={{position: 'relative', width: w, aspectRatio: '16 / 9', borderRadius: 12, overflow: 'hidden', background: '#000', containerType: 'inline-size'}}>
		{children}
		<div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 90, background: 'linear-gradient(180deg, transparent, rgba(0,0,0,0.75))'}} />
		<div style={{position: 'absolute', left: 14, right: 14, bottom: 48, height: 4, background: 'rgba(255,255,255,0.3)', borderRadius: 2}}>
			<div style={{width: `${progress * 100}%`, height: '100%', background: Y.red, borderRadius: 2, position: 'relative'}}>
				<div style={{position: 'absolute', right: -7, top: -5, width: 14, height: 14, borderRadius: 7, background: Y.red}} />
			</div>
		</div>
		<div style={{position: 'absolute', left: 18, right: 18, bottom: 12, display: 'flex', alignItems: 'center', gap: 22, fontSize: 14, color: '#fff'}}>
			<Icon name="pause" size={22} color="#fff" />
			<Icon name="next" size={22} color="#fff" />
			<Icon name="volume" size={22} color="#fff" />
			{live ? (
				<span style={{display: 'flex', alignItems: 'center', gap: 6, fontWeight: 500}}>
					<span style={{width: 8, height: 8, borderRadius: 4, background: Y.red}} /> LIVE
				</span>
			) : (
				<span>{time}</span>
			)}
			<div style={{flex: 1}} />
			<Icon name="cc" size={22} color="#fff" />
			<Icon name="gear" size={22} color="#fff" />
			<span style={{fontSize: 12, fontWeight: 700, background: Y.red, padding: '0 3px', borderRadius: 2, marginLeft: -26, marginTop: -16}}>4K</span>
			<Icon name="full" size={22} color="#fff" />
		</div>
		{live && (
			<div style={{position: 'absolute', left: 14, top: 14, background: Y.red, color: '#fff', fontWeight: 700, fontSize: 13, padding: '3px 8px', borderRadius: 4}}>
				LIVE
			</div>
		)}
	</div>
);

const Pill: React.FC<{children: React.ReactNode; bg?: string; color?: string; style?: React.CSSProperties}> = ({children, bg = Y.ui3, color = Y.text, style}) => (
	<div style={{display: 'flex', alignItems: 'center', gap: 8, height: 36, padding: '0 16px', borderRadius: 18, background: bg, color, fontSize: 14, fontWeight: 500, whiteSpace: 'nowrap', ...style}}>{children}</div>
);

const COMMENTS: {c: ChKey; who: string; text: string; likes: string}[] = [
	{c: 'maya', who: '@mayamakes', text: 'The drone shot at 6:12 is unreal 😍', likes: '2.1K'},
	{c: 'pixel', who: '@pixelpro', text: 'Adding Iceland to the bucket list right now', likes: '864'},
	{c: 'taste', who: '@tastetrip', text: 'Collab when?? I know a hot dog stand there 🌭', likes: '512'},
];

/** watch page: player, title, channel row with Subscribe + Like, comments, up-next */
export const WatchPage: React.FC<{t: number; f: number; liked: boolean; subscribed: boolean; subP: number; enter: number; commentsAt?: number}> = ({t, f, liked, subscribed, subP, enter, commentsAt = 1e9}) => {
	const v = VIDEOS[ICELAND];
	const upNext = [0, 6, 1, 7, 3];
	return (
		<div style={{display: 'flex', gap: 24, padding: '20px 24px 0', height: '100%'}}>
			<div style={{width: 1000}}>
				<div style={{transform: `scale(${lerp(0.37, 1, enter)})`, transformOrigin: '93.5% 100%'}}>
					<Player f={f} progress={0.2 + (f % 600) / 3000} w={1000}>
						<IcelandScene f={f} />
					</Player>
				</div>
				<div style={{opacity: prog(enter, 0.6, 1), marginTop: 12}}>
					<div style={{fontSize: 20, fontWeight: 700}}>{v.title}</div>
					<div style={{display: 'flex', alignItems: 'center', gap: 12, marginTop: 12}}>
						<ChAvatar c="wander" size={40} />
						<div style={{lineHeight: 1.25}}>
							<div style={{fontSize: 16, fontWeight: 500}}>Wander Wide ✓</div>
							<div style={{fontSize: 12, color: Y.text2}}>{subscribed ? '3,200,001' : '3.2M'} subscribers</div>
						</div>
						<div
							style={{
								marginLeft: 12,
								display: 'flex',
								alignItems: 'center',
								gap: 8,
								height: 36,
								padding: '0 16px',
								borderRadius: 18,
								background: subscribed ? Y.ui3 : Y.text,
								color: subscribed ? Y.text : Y.ui,
								fontSize: 14,
								fontWeight: 500,
								transform: `scale(${subP})`,
							}}
						>
							{subscribed && <Icon name="bellRing" size={18} color={Y.text} style={{transform: `rotate(${Math.sin(t * 0.9) * 18 * Math.max(0, 1 - (t - 75) / 30)}deg)`}} />}
							{subscribed ? 'Subscribed' : 'Subscribe'}
						</div>
						<div style={{flex: 1}} />
						<div style={{display: 'flex', alignItems: 'center', height: 36, borderRadius: 18, background: Y.ui3, fontSize: 14, fontWeight: 500}}>
							<div style={{display: 'flex', alignItems: 'center', gap: 8, padding: '0 16px', borderRight: `1px solid ${Y.ui4}`, height: 24}}>
								<Icon name="like" size={20} color={liked ? '#fff' : Y.text2} style={{transform: `scale(${liked ? 1.15 : 1})`}} />
								{liked ? '96K' : '95K'}
							</div>
							<div style={{padding: '0 14px'}}>
								<Icon name="dislike" size={20} color={Y.text2} />
							</div>
						</div>
						<Pill>
							<Icon name="share" size={18} color={Y.text} /> Share
						</Pill>
						<Pill>
							<Icon name="download" size={18} color={Y.text} /> Download
						</Pill>
					</div>
					<div style={{marginTop: 14, background: Y.ui3, borderRadius: 12, padding: '10px 14px', fontSize: 14}}>
						<b>3.6M views • 1 month ago</b> &nbsp;#iceland #roadtrip #4k
						<div style={{color: Y.text, marginTop: 4}}>Ten days, one camper van and the most dramatic roads on the planet. Chapters below ↓</div>
					</div>
					<div style={{marginTop: 18, fontSize: 18, fontWeight: 700}}>12,408 Comments</div>
					{COMMENTS.map((c, i) => {
						const p = prog(t, commentsAt + i * 7.5, commentsAt + i * 7.5 + 14);
						return (
							<div key={i} style={{display: 'flex', gap: 14, marginTop: 16, opacity: p, transform: `translateY(${(1 - p) * 16}px)`}}>
								<ChAvatar c={c.c} size={40} />
								<div style={{fontSize: 14}}>
									<div>
										<b>{c.who}</b> <span style={{color: Y.text2}}>2 hours ago</span>
									</div>
									<div style={{marginTop: 2}}>{c.text}</div>
									<div style={{display: 'flex', gap: 10, alignItems: 'center', marginTop: 6, color: Y.text2}}>
										<Icon name="like" size={16} color={Y.text2} /> {c.likes}
									</div>
								</div>
							</div>
						);
					})}
				</div>
			</div>
			<div style={{flex: 1, display: 'flex', flexDirection: 'column', gap: 10, opacity: prog(enter, 0.5, 1)}}>
				<Chips t={0} active={0} />
				{upNext.map((i) => (
					<div key={i} style={{display: 'flex', gap: 8}}>
						<Thumb v={VIDEOS[i]} style={{width: 168, flexShrink: 0}} radius={8} />
						<div style={{fontSize: 14, lineHeight: 1.3}}>
							<div style={{fontWeight: 500, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden'}}>{VIDEOS[i].title}</div>
							<div style={{color: Y.text2, fontSize: 12, marginTop: 4}}>{CH[VIDEOS[i].ch].name}</div>
							<div style={{color: Y.text2, fontSize: 12}}>{VIDEOS[i].views}</div>
						</div>
					</div>
				))}
			</div>
		</div>
	);
};

/* live page: game stream + live chat with Super Chats */
export type ChatMsg = {c: ChKey; who: string; text: string; at: number; sc?: {amt: string; bg: string; head: string}};
export const LivePage: React.FC<{t: number; f: number; msgs: ChatMsg[]; watching: number}> = ({t, f, msgs, watching}) => (
	<div style={{display: 'flex', gap: 20, padding: '20px 20px 0', height: '100%'}}>
		<div style={{width: 960}}>
			<Player f={f} progress={1} live w={960}>
				<GameScene f={f} />
			</Player>
			<div style={{fontSize: 20, fontWeight: 700, marginTop: 12}}>🔴 WORLD RECORD ATTEMPTS — Neon Drift (all night!)</div>
			<div style={{display: 'flex', alignItems: 'center', gap: 12, marginTop: 10}}>
				<ChAvatar c="pixel" size={40} ring />
				<div style={{lineHeight: 1.25}}>
					<div style={{fontSize: 16, fontWeight: 500}}>PixelPro ✓</div>
					<div style={{fontSize: 12, color: Y.text2}}>1.4M subscribers</div>
				</div>
				<Pill bg={Y.text} color={Y.ui} style={{marginLeft: 12}}>
					Subscribe
				</Pill>
				<div style={{flex: 1}} />
				<Pill>
					<Icon name="eye" size={18} color={Y.text} /> {watching.toLocaleString('en-US')} watching now
				</Pill>
			</div>
		</div>
		<div style={{flex: 1, border: `1px solid ${Y.ui4}`, borderRadius: 12, display: 'flex', flexDirection: 'column', overflow: 'hidden'}}>
			<div style={{height: 48, display: 'flex', alignItems: 'center', padding: '0 14px', fontSize: 16, fontWeight: 500, borderBottom: `1px solid ${Y.ui4}`}}>
				Top chat <span style={{color: Y.text2, marginLeft: 6}}>▾</span>
			</div>
			<div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', padding: '8px 12px', gap: 8, overflow: 'hidden'}}>
				{msgs.map((m, i) => {
					const p = prog(t, m.at, m.at + 10);
					if (t < m.at) return null;
					if (m.sc)
						return (
							<div key={i} style={{borderRadius: 8, overflow: 'hidden', opacity: p, transform: `translateY(${(1 - p) * 20}px) scale(${lerp(0.9, 1, p)})`, flexShrink: 0}}>
								<div style={{background: m.sc.head, padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 10, color: '#fff'}}>
									<ChAvatar c={m.c} size={28} />
									<div style={{lineHeight: 1.2}}>
										<div style={{fontSize: 13, opacity: 0.85}}>{m.who}</div>
										<div style={{fontSize: 15, fontWeight: 700}}>{m.sc.amt}</div>
									</div>
								</div>
								<div style={{background: m.sc.bg, padding: '6px 12px 8px', fontSize: 14, color: '#fff'}}>{m.text}</div>
							</div>
						);
					return (
						<div key={i} style={{display: 'flex', gap: 10, fontSize: 14, alignItems: 'flex-start', opacity: p, flexShrink: 0}}>
							<ChAvatar c={m.c} size={24} />
							<div>
								<span style={{color: Y.text2, marginRight: 8}}>{m.who}</span>
								{m.text}
							</div>
						</div>
					);
				})}
			</div>
			<div style={{height: 52, display: 'flex', alignItems: 'center', gap: 10, padding: '0 12px', borderTop: `1px solid ${Y.ui4}`}}>
				<ChAvatar c="you" size={24} />
				<div style={{flex: 1, height: 32, borderRadius: 16, background: Y.ui3, display: 'flex', alignItems: 'center', padding: '0 12px', color: Y.text2, fontSize: 14}}>Chat…</div>
				<Icon name="dollar" size={24} color={Y.text2} />
			</div>
		</div>
	</div>
);

/* studio analytics */
const STUDIO_NAV: [Parameters<typeof Icon>[0]['name'], string][] = [
	['home', 'Dashboard'],
	['playlist', 'Content'],
	['chart', 'Analytics'],
	['comment', 'Comments'],
	['dollar', 'Earn'],
	['gear', 'Customisation'],
];
export const STUDIO_CHART = [8, 10, 9, 13, 12, 16, 15, 19, 22, 21, 26, 30, 29, 35, 41, 39, 46, 52, 58, 56, 64, 72, 80, 92];

export const StudioPage: React.FC<{t: number; draw: number; count: number}> = ({t, draw, count}) => {
	const W = 860;
	const H = 300;
	const max = 100;
	const pts = STUDIO_CHART.map((v, i) => [(i / (STUDIO_CHART.length - 1)) * W, H - (v / max) * H] as const);
	const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
	const metrics = [
		{l: 'Views', v: `${(1.24 * count).toFixed(2)}M`, d: '↑ 38%'},
		{l: 'Watch time (hours)', v: `${(84.3 * count).toFixed(1)}K`, d: '↑ 27%'},
		{l: 'Subscribers', v: `+${(12.4 * count).toFixed(1)}K`, d: '↑ 45%'},
		{l: 'Estimated revenue', v: `$${Math.round(8420 * count).toLocaleString('en-US')}`, d: '↑ 32%'},
	];
	return (
		<div style={{display: 'flex', height: '100%'}}>
			<div style={{width: 240, borderRight: `1px solid ${Y.ui4}`, padding: '18px 0'}}>
				<div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, paddingBottom: 18}}>
					<ChAvatar c="maya" size={88} />
					<div style={{fontSize: 14, fontWeight: 500}}>Your channel</div>
					<div style={{fontSize: 12, color: Y.text2}}>Maya Makes</div>
				</div>
				{STUDIO_NAV.map(([i, l]) => (
					<div key={l} style={{display: 'flex', alignItems: 'center', gap: 22, height: 46, padding: '0 22px', fontSize: 15, background: l === 'Analytics' ? Y.ui3 : undefined, borderLeft: l === 'Analytics' ? `4px solid ${Y.red}` : '4px solid transparent', color: l === 'Analytics' ? Y.red : Y.text}}>
						<Icon name={i} size={22} color={l === 'Analytics' ? Y.red : Y.text2} />
						{l}
					</div>
				))}
			</div>
			<div style={{flex: 1, padding: '22px 28px'}}>
				<div style={{fontSize: 24, fontWeight: 700}}>Channel analytics</div>
				<div style={{display: 'flex', gap: 26, marginTop: 14, borderBottom: `1px solid ${Y.ui4}`, fontSize: 15, fontWeight: 500}}>
					{['Overview', 'Content', 'Audience', 'Revenue', 'Trends'].map((x) => (
						<div key={x} style={{paddingBottom: 12, color: x === 'Overview' ? Y.text : Y.text2, borderBottom: x === 'Overview' ? `3px solid ${Y.text}` : '3px solid transparent'}}>
							{x}
						</div>
					))}
				</div>
				<div style={{fontSize: 22, fontWeight: 700, textAlign: 'center', margin: '20px 0 16px'}}>Your channel got {(1.24 * count).toFixed(2)}M views in the last 28 days</div>
				<div style={{border: `1px solid ${Y.ui4}`, borderRadius: 12, overflow: 'hidden'}}>
					<div style={{display: 'flex'}}>
						{metrics.map((m, i) => (
							<div key={m.l} style={{flex: 1, padding: '14px 16px', borderBottom: i === 0 ? `3px solid ${Y.blue}` : `1px solid ${Y.ui4}`, background: i === 0 ? Y.ui2 : undefined}}>
								<div style={{fontSize: 13, color: Y.text2}}>{m.l}</div>
								<div style={{fontSize: 26, fontWeight: 700, marginTop: 4}}>{m.v}</div>
								<div style={{fontSize: 13, color: '#2BA640', marginTop: 2}}>{m.d}</div>
							</div>
						))}
					</div>
					<div style={{padding: '24px 28px 18px'}}>
						<svg width={W} height={H + 30} style={{overflow: 'visible'}}>
							{[0, 1, 2, 3].map((g) => (
								<line key={g} x1={0} x2={W} y1={(g / 3) * H} y2={(g / 3) * H} stroke={Y.ui4} strokeWidth={1} />
							))}
							<path d={`${d} L${W} ${H} L0 ${H}Z`} fill="rgba(62,166,255,0.12)" style={{clipPath: `inset(0 ${(1 - draw) * 100}% 0 0)`}} />
							<path d={d} fill="none" stroke={Y.blue} strokeWidth={4} strokeLinejoin="round" pathLength={1} strokeDasharray={`${draw} 1`} />
							{draw > 0.98 && <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r={8} fill={Y.blue} stroke="#fff" strokeWidth={3} />}
							{['Oct 6', 'Oct 13', 'Oct 20', 'Oct 27', 'Nov 2'].map((x, i) => (
								<text key={x} x={(i / 4) * W} y={H + 26} fill={Y.text2} fontSize={13} fontFamily={YBODY} textAnchor={i === 0 ? 'start' : i === 4 ? 'end' : 'middle'}>
									{x}
								</text>
							))}
						</svg>
					</div>
				</div>
			</div>
		</div>
	);
};

/* ================================================================ mobile */
export const MobileTop: React.FC = () => (
	<div style={{height: 104, paddingTop: 54, display: 'flex', alignItems: 'center', padding: '54px 16px 0', gap: 18, background: Y.ui, flexShrink: 0}}>
		<PlayIcon h={20} />
		<span style={{fontWeight: 700, fontSize: 20, letterSpacing: '-0.06em', marginLeft: -14}}>YouTube</span>
		<div style={{flex: 1}} />
		<Icon name="tv" size={22} color={Y.text} />
		<Icon name="bell" size={22} color={Y.text} />
		<Icon name="search" size={22} color={Y.text} />
	</div>
);

export const MobileNav: React.FC<{active?: number}> = ({active = 0}) => (
	<div style={{height: 82, display: 'flex', justifyContent: 'space-around', alignItems: 'flex-start', paddingTop: 8, background: Y.ui, borderTop: `1px solid ${Y.ui3}`, flexShrink: 0}}>
		{([
			['home', 'Home'],
			['shorts', 'Shorts'],
			['plus', ''],
			['subs', 'Subscriptions'],
			['you', 'You'],
		] as const).map(([i, l], n) => (
			<div key={n} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, fontSize: 10, color: Y.text}}>
				{i === 'plus' ? (
					<div style={{width: 40, height: 40, borderRadius: 20, border: `1.5px solid ${Y.text}`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
						<Icon name="plus" size={22} color={Y.text} />
					</div>
				) : (
					<Icon name={i} size={24} color={n === active ? Y.text : Y.text2} />
				)}
				{l}
			</div>
		))}
	</div>
);

export const MobileHome: React.FC<{t: number}> = ({t}) => (
	<div style={{position: 'absolute', inset: 0, background: Y.ui, display: 'flex', flexDirection: 'column', fontFamily: YBODY, color: Y.text}}>
		<MobileTop />
		<div style={{transform: 'scale(0.86)', transformOrigin: '0 0', width: '116%', paddingLeft: 14}}>
			<Chips t={t} />
		</div>
		<div style={{flex: 1, overflow: 'hidden'}}>
			{[ICELAND, 0, 6].map((i) => (
				<div key={i} style={{marginBottom: 14}}>
					<Thumb v={VIDEOS[i]} radius={0} style={{width: '100%'}} />
					<div style={{display: 'flex', gap: 12, padding: '10px 12px'}}>
						<ChAvatar c={VIDEOS[i].ch} size={36} />
						<div style={{fontSize: 14, lineHeight: 1.3}}>
							<div style={{fontWeight: 500}}>{VIDEOS[i].title}</div>
							<div style={{color: Y.text2, fontSize: 12}}>
								{CH[VIDEOS[i].ch].name} • {VIDEOS[i].views}
							</div>
						</div>
					</div>
				</div>
			))}
		</div>
		<MobileNav />
	</div>
);

/** Shorts player with a swipe from one Short to the next and a double-tap heart */
export const ShortsPlayer: React.FC<{t: number; f: number; swipeAt: number; likeAt: number; first?: 'cook' | 'skate' | 'art'; second?: 'cook' | 'skate' | 'art'}> = ({t, f, swipeAt, likeAt, first = 'cook', second = 'skate'}) => {
	const sw = prog(t, swipeAt, swipeAt + 14, easeInOut);
	const liked = t >= likeAt;
	const heart = prog(t, likeAt, likeAt + 22);
	const Ui: React.FC<{c: ChKey; handle: string; likes: string; caption: string; isLiked: boolean}> = ({c, handle, likes, caption, isLiked}) => (
		<>
			<div style={{position: 'absolute', right: 10, bottom: 150, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18, color: '#fff', fontSize: 13, fontWeight: 500}}>
				{[
					{i: 'like' as const, l: isLiked ? (parseFloat(likes) + 0.1).toFixed(1) + 'M' : likes + 'M', on: isLiked},
					{i: 'dislike' as const, l: 'Dislike'},
					{i: 'comment' as const, l: '8.2K'},
					{i: 'share' as const, l: 'Share'},
					{i: 'remix' as const, l: 'Remix'},
				].map((b) => (
					<div key={b.i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4}}>
						<div style={{width: 48, height: 48, borderRadius: 24, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
							<Icon name={b.i} size={26} color={b.on ? Y.red : '#fff'} />
						</div>
						{b.l}
					</div>
				))}
				<div style={{width: 40, height: 40, borderRadius: 8, background: `linear-gradient(135deg, ${CH[c].g[0]}, ${CH[c].g[1]})`, border: '2px solid #fff'}} />
			</div>
			<div style={{position: 'absolute', left: 14, right: 80, bottom: 100, color: '#fff'}}>
				<div style={{display: 'flex', alignItems: 'center', gap: 10, fontSize: 15, fontWeight: 500}}>
					<ChAvatar c={c} size={32} /> {handle}
					<div style={{background: '#fff', color: Y.ui, borderRadius: 16, padding: '6px 12px', fontSize: 13, fontWeight: 700}}>Subscribe</div>
				</div>
				<div style={{fontSize: 14, marginTop: 8}}>{caption}</div>
				<div style={{fontSize: 13, marginTop: 6, display: 'flex', alignItems: 'center', gap: 6}}>
					<Icon name="music" size={14} color="#fff" /> original sound · {handle}
				</div>
			</div>
		</>
	);
	return (
		<div style={{position: 'absolute', inset: 0, background: '#000', fontFamily: YBODY, overflow: 'hidden'}}>
			<div style={{position: 'absolute', inset: 0, transform: `translateY(${-sw * 100}%)`}}>
				<ShortScene f={f} kind={first} />
				<Ui c="noodle" handle="@noodlelab" likes="1.2" caption="breakfast in 60 seconds 🥞 #shorts" isLiked={false} />
			</div>
			<div style={{position: 'absolute', inset: 0, transform: `translateY(${(1 - sw) * 100}%)`}}>
				<ShortScene f={f} kind={second} />
				<Ui c="pixel" handle="@skatepixel" likes="3.4" caption="300 tries later… 🛹 #kickflip" isLiked={liked} />
				{t >= likeAt && heart < 1 && (
					<div style={{position: 'absolute', left: '50%', top: '42%', transform: `translate(-50%, -50%) scale(${lerp(0.4, 1.6, heart)}) rotate(-10deg)`, opacity: 1 - prog(t, likeAt + 12, likeAt + 22)}}>
						<Icon name="heart" size={130} color={Y.red} />
					</div>
				)}
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, top: 54, display: 'flex', justifyContent: 'space-between', padding: '0 16px', color: '#fff', fontSize: 18, fontWeight: 700}}>
				<span style={{display: 'flex', alignItems: 'center', gap: 6}}>
					<Icon name="shorts" size={22} color={Y.red} /> Shorts
				</span>
				<Icon name="search" size={22} color="#fff" />
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, bottom: 0}}>
				<MobileNav active={1} />
			</div>
		</div>
	);
};

/** Shorts camera: create a Short */
export const ShortsCamera: React.FC<{t: number; f: number; recAt: number}> = ({t, f, recAt}) => {
	const rec = t >= recAt;
	const rp = prog(t, recAt, recAt + 90, (x) => x);
	return (
		<div style={{position: 'absolute', inset: 0, background: '#000', fontFamily: YBODY, color: '#fff', overflow: 'hidden'}}>
			<ShortScene f={f} kind="art" />
			<div style={{position: 'absolute', left: 14, right: 14, top: 58, height: 6, borderRadius: 3, background: 'rgba(255,255,255,0.35)'}}>
				<div style={{width: `${rp * 100}%`, height: '100%', borderRadius: 3, background: Y.red}} />
			</div>
			<div style={{position: 'absolute', left: '50%', top: 82, transform: 'translateX(-50%)', display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(0,0,0,0.45)', borderRadius: 18, padding: '8px 16px', fontSize: 15, fontWeight: 500}}>
				<Icon name="music" size={16} color="#fff" /> Add sound
			</div>
			<div style={{position: 'absolute', right: 14, top: 140, display: 'flex', flexDirection: 'column', gap: 22, alignItems: 'center', fontSize: 11}}>
				{(['flip', 'timer', 'sparkle', 'gear'] as const).map((i) => (
					<div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4}}>
						<Icon name={i} size={28} color="#fff" />
					</div>
				))}
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, bottom: 90, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 60}}>
				<div style={{width: 46, height: 46, borderRadius: 10, background: 'linear-gradient(135deg, #FFB347, #FF5E62)', border: '2px solid #fff'}} />
				<div style={{width: 86, height: 86, borderRadius: 43, border: '5px solid #fff', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
					<div style={{width: rec ? 36 : 64, height: rec ? 36 : 64, borderRadius: rec ? 8 : 32, background: Y.red}} />
				</div>
				<div style={{width: 46, height: 46, borderRadius: 23, background: Y.text, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: rec ? 1 : 0.4}}>
					<Icon name="check" size={24} color={Y.ui} />
				</div>
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, bottom: 44, display: 'flex', justifyContent: 'center', gap: 24, fontSize: 14, fontWeight: 500}}>
				<span style={{opacity: 0.6}}>Live</span>
				<span>Short</span>
				<span style={{opacity: 0.6}}>Video</span>
			</div>
		</div>
	);
};

/** YouTube Music now-playing */
export const MusicPlayer: React.FC<{t: number}> = ({t}) => {
	const p = 0.32 + ((t + 300) % 900) / 2400;
	return (
		<div style={{position: 'absolute', inset: 0, background: 'linear-gradient(180deg, #4A2A7A 0%, #1A0F2E 60%, #000 100%)', fontFamily: YBODY, color: '#fff', padding: '64px 26px 0'}}>
			<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 14, fontWeight: 500}}>
				<Icon name="next" size={20} color="#fff" style={{transform: 'rotate(90deg)'}} />
				<span style={{display: 'flex', gap: 6, alignItems: 'center'}}>
					<PlayIcon h={14} /> Music
				</span>
				<Icon name="more" size={20} color="#fff" />
			</div>
			<div style={{marginTop: 30, width: '100%', aspectRatio: '1', borderRadius: 14, background: 'linear-gradient(135deg, #C04CFD, #3D2BFF 60%, #00C2FF)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 30px 60px rgba(0,0,0,0.5)', position: 'relative', overflow: 'hidden'}}>
				<div style={{position: 'absolute', width: '150%', height: '150%', background: 'conic-gradient(from 0deg, transparent, rgba(255,255,255,0.18), transparent 40%)', transform: `rotate(${t * 2}deg)`}} />
				<Emoji e="🌙" size={130} />
			</div>
			<div style={{marginTop: 28, fontSize: 24, fontWeight: 700}}>Midnight Drive</div>
			<div style={{fontSize: 16, color: 'rgba(255,255,255,0.7)', marginTop: 4}}>Chill Station • Night Moves</div>
			<div style={{marginTop: 22, height: 4, borderRadius: 2, background: 'rgba(255,255,255,0.25)'}}>
				<div style={{width: `${p * 100}%`, height: '100%', borderRadius: 2, background: '#fff'}} />
			</div>
			<div style={{display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'rgba(255,255,255,0.7)', marginTop: 6}}>
				<span>1:{String(Math.floor(p * 60) % 60).padStart(2, '0')}</span>
				<span>3:42</span>
			</div>
			<div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 18}}>
				<Icon name="shuffle" size={24} color="#fff" />
				<Icon name="prev" size={30} color="#fff" />
				<div style={{width: 72, height: 72, borderRadius: 36, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
					<Icon name="pause" size={32} color="#000" />
				</div>
				<Icon name="next" size={30} color="#fff" />
				<Icon name="repeat" size={24} color="#fff" />
			</div>
		</div>
	);
};

/** mobile watch with a Download button that fills, then shows "Downloaded" */
export const MobileDownload: React.FC<{t: number; f: number; tapAt: number; doneAt: number}> = ({t, f, tapAt, doneAt}) => {
	const dl = prog(t, tapAt, doneAt, (x) => x);
	const done = t >= doneAt;
	return (
		<div style={{position: 'absolute', inset: 0, background: Y.ui, fontFamily: YBODY, color: Y.text, paddingTop: 54}}>
			<div style={{position: 'relative', width: '100%', aspectRatio: '16 / 9', overflow: 'hidden'}}>
				<IcelandScene f={f} />
				<div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 3, background: 'rgba(255,255,255,0.3)'}}>
					<div style={{width: '34%', height: '100%', background: Y.red}} />
				</div>
			</div>
			<div style={{padding: '12px 14px'}}>
				<div style={{fontSize: 17, fontWeight: 700, lineHeight: 1.3}}>{VIDEOS[ICELAND].title}</div>
				<div style={{fontSize: 12, color: Y.text2, marginTop: 4}}>3.6M views • 1mo</div>
				<div style={{display: 'flex', alignItems: 'center', gap: 10, marginTop: 12}}>
					<ChAvatar c="wander" size={32} />
					<span style={{fontSize: 14, fontWeight: 500, flex: 1}}>Wander Wide</span>
					<div style={{background: Y.ui3, borderRadius: 16, padding: '7px 12px', fontSize: 13, fontWeight: 500}}>Subscribed</div>
				</div>
				<div style={{display: 'flex', gap: 8, marginTop: 14}}>
					<div style={{background: Y.ui3, borderRadius: 16, padding: '8px 12px', fontSize: 13, display: 'flex', gap: 6, alignItems: 'center'}}>
						<Icon name="like" size={16} color={Y.text} /> 96K
					</div>
					<div
						style={{
							background: done ? Y.text : Y.ui3,
							color: done ? Y.ui : Y.text,
							borderRadius: 16,
							padding: '8px 12px',
							fontSize: 13,
							fontWeight: 500,
							display: 'flex',
							gap: 6,
							alignItems: 'center',
							transform: `scale(${t >= tapAt - 2 && t < tapAt + 5 ? 0.93 : 1})`,
						}}
					>
						{done ? (
							<Icon name="check" size={16} color={Y.ui} />
						) : t >= tapAt ? (
							<svg width="16" height="16" viewBox="0 0 16 16">
								<circle cx="8" cy="8" r="6" stroke={Y.ui4} strokeWidth="2.5" fill="none" />
								<circle cx="8" cy="8" r="6" stroke={Y.text} strokeWidth="2.5" fill="none" pathLength={1} strokeDasharray={`${dl} 1`} transform="rotate(-90 8 8)" />
							</svg>
						) : (
							<Icon name="download" size={16} color={Y.text} />
						)}
						{done ? 'Downloaded' : t >= tapAt ? `${Math.round(dl * 100)}%` : 'Download'}
					</div>
					<div style={{background: Y.ui3, borderRadius: 16, padding: '8px 12px', fontSize: 13, display: 'flex', gap: 6, alignItems: 'center'}}>
						<Icon name="share" size={16} color={Y.text} /> Share
					</div>
				</div>
			</div>
			<div style={{padding: '4px 14px'}}>
				{[0, 6].map((i) => (
					<div key={i} style={{display: 'flex', gap: 10, marginTop: 12}}>
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

/* ================================================================ TV */
export const TV: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => (
	<div style={{position: 'relative', width: 1640, height: 1010, ...style}}>
		<div style={{position: 'absolute', left: 0, top: 0, width: 1640, height: 940, borderRadius: 18, background: '#0B0B0B', padding: 14, boxShadow: `0 50px 100px ${Y.shadowStrong}, inset 0 0 0 2px #2A2A2A`}}>
			<div style={{position: 'relative', width: 1612, height: 912, borderRadius: 6, overflow: 'hidden', background: '#000'}}>
				{children}
				<div style={{position: 'absolute', inset: 0, background: 'linear-gradient(120deg, rgba(255,255,255,0.07), rgba(255,255,255,0) 40%)'}} />
			</div>
		</div>
		<div style={{position: 'absolute', left: 760, top: 940, width: 120, height: 50, background: 'linear-gradient(180deg, #2A2A2A, #111)', clipPath: 'polygon(25% 0, 75% 0, 100% 100%, 0 100%)'}} />
		<div style={{position: 'absolute', left: 600, top: 988, width: 440, height: 14, borderRadius: 7, background: '#1A1A1A'}} />
	</div>
);

export const TVHome: React.FC<{t: number; f: number}> = ({t, f}) => {
	const focus = Math.floor(((t + 600) / 30) % 4);
	return (
		<div style={{position: 'absolute', inset: 0, background: Y.ui, fontFamily: YBODY, color: Y.text}}>
			<div style={{position: 'absolute', inset: 0, height: 560}}>
				<IcelandScene f={f} />
				<div style={{position: 'absolute', inset: 0, background: 'linear-gradient(90deg, rgba(15,15,15,0.95) 0%, rgba(15,15,15,0.2) 60%), linear-gradient(0deg, #0F0F0F 0%, transparent 40%)'}} />
				<div style={{position: 'absolute', left: 120, top: 150, width: 620}}>
					<div style={{display: 'flex', alignItems: 'center', gap: 10, fontSize: 22, fontWeight: 500}}>
						<ChAvatar c="wander" size={40} /> Wander Wide
					</div>
					<div style={{fontSize: 52, fontWeight: 700, lineHeight: 1.1, marginTop: 14}}>Iceland in 4K — The Road Less Taken</div>
					<div style={{fontSize: 22, color: Y.text2, marginTop: 10}}>3.6M views • 15:30 • 4K HDR</div>
				</div>
			</div>
			<div style={{position: 'absolute', left: 120, top: 600, fontSize: 26, fontWeight: 700}}>Recommended</div>
			<div style={{position: 'absolute', left: 120, top: 650, display: 'flex', gap: 28}}>
				{[0, 6, 3, 7].map((i, n) => (
					<div key={i} style={{transform: `scale(${n === focus ? 1.08 : 1})`, transformOrigin: 'top left'}}>
						<Thumb v={VIDEOS[i]} style={{width: 320, boxShadow: n === focus ? `0 0 0 5px ${Y.text}` : undefined}} radius={10} />
					</div>
				))}
			</div>
			<div style={{position: 'absolute', left: 30, top: 160, display: 'flex', flexDirection: 'column', gap: 34}}>
				{(['search', 'home', 'shorts', 'subs', 'you'] as const).map((i, n) => (
					<Icon key={i} name={i} size={36} color={n === 1 ? Y.text : Y.text2} />
				))}
			</div>
		</div>
	);
};

export {interpolate, clamp, spr};
