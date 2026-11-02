import React from 'react';
import {AbsoluteFill, interpolate, random, useCurrentFrame} from 'remotion';
import {Avatar, Body, Callout, Clyde, Emoji, Eyebrow, GRAD, Icon, Reveal, SpaceBg, Sparkle, USERS, UserKey} from './primitives';
import {BODY, C, MONO, clamp, display, easeIn, easeInOut, easeOut, lerp, prog, spr} from './theme';
import {IPad, IPhone, MacBook} from './devices';
import {
	Bar,
	CamTile,
	ChannelSidebar,
	ChatHeader,
	DesktopShell,
	GameScene,
	InputBar,
	MobileChat,
	MobileHome,
	MobileInput,
	Msg,
	ServerRail,
	Typing,
} from './ui';
import {MAIN_ROWS, MEMBERS} from './scenes1';
import {talk} from './scenes2';

/* ================================================================ 9. APPS & ACTIVITIES (78-88s) */
const CMDS = [
	{c: '/poll', d: 'Ask the server a question', app: 'Discord', bg: C.blurple, e: '📊'},
	{c: '/play', d: 'Queue a song in voice', app: 'DJ Bot', bg: C.fuchsia, e: '🎵'},
	{c: '/remind', d: 'Set a reminder for later', app: 'Remindy', bg: '#00A8FC', e: '⏰'},
	{c: '/giveaway', d: 'Start a giveaway', app: 'GiftBot', bg: C.green, e: '🎁'},
];
const POLL = [
	{t: 'Neon Drift', e: '🏎️', v: 46},
	{t: 'Block Party', e: '🧱', v: 31},
	{t: 'Space Pals', e: '🚀', v: 23},
];

export const Apps: React.FC = () => {
	const f = useCurrentFrame();
	const enter = spr(f, 0, {damping: 18, stiffness: 70});
	const ph = spr(f, 20, {damping: 16, stiffness: 80});
	const cam = prog(f, 0, 300, easeInOut);
	const typed = '/poll';
	const tn = Math.floor(interpolate(f, [20, 40], [0, typed.length], clamp));
	const popup = f >= 26 && f < 92;
	const popP = prog(f, 26, 36);
	const sel = Math.min(3, Math.floor(interpolate(f, [44, 70], [0, 3], clamp)));
	const selIdx = f < 78 ? sel : 0;
	const pollAt = 96;
	const pollP = prog(f, pollAt + 20, pollAt + 90, easeInOut);
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 2340} a={C.blurple} b="#00A8FC" />
			<div style={{position: 'absolute', left: 110, top: 70, width: 1700}}>
				<Eyebrow f={f} start={2} num="07" label="Apps & Activities" icon="apps" color="#00A8FC" />
				<div style={{height: 26}} />
				<Reveal text="PLAY. BUILD. AUTOMATE." f={f} start={8} stagger={5} hl={['AUTOMATE']} style={{...display(76), color: '#fff'}} hlBg="linear-gradient(92deg, #00A8FC, #5865F2)" />
			</div>
			<div style={{position: 'absolute', inset: 0, perspective: 2400}}>
				<div
					style={{
						position: 'absolute',
						left: 70,
						top: 270,
						transformOrigin: '0 0',
						transform: `translateY(${(1 - enter) * 800}px) scale(${lerp(0.7, 0.72, cam)}) rotateY(${lerp(8, 4, cam)}deg)`,
					}}
				>
					<MacBook>
						<DesktopShell
							rail={<ServerRail f={f} selected={0} />}
							sidebar={<ChannelSidebar f={f} rows={MAIN_ROWS} />}
							main={
								<>
									<ChatHeader name="general" topic="the place to hang out ✨ be nice, have fun" />
									<div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', overflow: 'hidden'}}>
										<Msg f={f} u="luna">
											ok but what are we playing tonight
										</Msg>
										<Msg f={f} u="kai">
											let's vote 🗳️
										</Msg>
										<Msg f={f} u="you" at={pollAt} h={420}>
											<div style={{marginTop: 6, width: 520, background: C.side, borderRadius: 12, padding: '16px 18px', border: '1px solid #3F4147'}}>
												<div style={{fontWeight: 800, fontSize: 19, color: '#fff'}}>What should we play tonight?</div>
												<div style={{fontSize: 13.5, color: C.faint, marginTop: 2, marginBottom: 12}}>Select one answer</div>
												{POLL.map((o, i) => {
													const v = Math.round(o.v * pollP);
													return (
														<div key={o.t} style={{position: 'relative', height: 48, borderRadius: 8, background: '#383A40', marginBottom: 8, overflow: 'hidden', border: i === 0 && f > pollAt + 30 ? `2px solid ${C.blurple}` : '2px solid transparent'}}>
															<div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${v}%`, background: i === 0 ? 'rgba(88,101,242,0.45)' : 'rgba(255,255,255,0.08)'}} />
															<div style={{position: 'relative', display: 'flex', alignItems: 'center', gap: 10, height: '100%', padding: '0 14px', fontWeight: 700, fontSize: 17, color: C.text}}>
																<Emoji e={o.e} size={22} />
																<span style={{flex: 1}}>{o.t}</span>
																<span style={{color: C.muted}}>{v}%</span>
															</div>
														</div>
													);
												})}
												<div style={{fontSize: 13.5, color: C.faint, marginTop: 4}}>{Math.round(248 * pollP)} votes · 23h left</div>
											</div>
										</Msg>
									</div>
									<div style={{position: 'relative'}}>
										{popup && (
											<div
												style={{
													position: 'absolute',
													left: 18,
													right: 18,
													bottom: 8,
													background: C.side,
													borderRadius: 10,
													padding: 8,
													boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
													opacity: popP,
													transform: `translateY(${(1 - popP) * 20}px)`,
												}}
											>
												<div style={{fontSize: 12.5, fontWeight: 800, color: C.faint, letterSpacing: '0.04em', padding: '4px 8px 8px'}}>COMMANDS MATCHING /</div>
												{CMDS.map((c, i) => (
													<div key={c.c} style={{display: 'flex', alignItems: 'center', gap: 12, padding: '10px 10px', borderRadius: 6, background: i === selIdx ? '#404249' : undefined}}>
														<div style={{width: 34, height: 34, borderRadius: '50%', background: c.bg, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
															<Emoji e={c.e} size={18} />
														</div>
														<span style={{fontFamily: MONO, fontWeight: 500, fontSize: 16.5, color: '#fff'}}>{c.c}</span>
														<span style={{fontSize: 15, color: C.muted, flex: 1}}>{c.d}</span>
														<span style={{fontSize: 13.5, color: C.faint, fontWeight: 700}}>{c.app}</span>
													</div>
												))}
											</div>
										)}
									</div>
									<Typing f={f} text="mila" />
									<InputBar f={f} placeholder="Message #general" text={f >= 18 && f < pollAt ? typed.slice(0, tn) : undefined} />
								</>
							}
						/>
					</MacBook>
				</div>
				<div
					style={{
						position: 'absolute',
						left: 1390,
						top: 230,
						transformOrigin: '0 0',
						transform: `translateY(${(1 - ph) * 900 + Math.sin(f / 30) * 8}px) scale(0.86) rotateY(-12deg) rotateZ(2deg)`,
					}}
				>
					<IPhone>
						<ActivitiesPhone f={f} />
					</IPhone>
				</div>
			</div>
			<Callout f={f} start={150} float={1} style={{left: 1190, top: 820}}>
				<div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '12px 18px'}}>
					<div style={{width: 40, height: 40, borderRadius: 12, background: C.green, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
						<Emoji e="🎁" size={22} />
					</div>
					<div style={{lineHeight: 1.2}}>
						<div style={{fontWeight: 800, fontSize: 18}}>Thousands of apps</div>
						<div style={{fontSize: 15, color: C.muted}}>Add bots & games to any server</div>
					</div>
				</div>
			</Callout>
		</AbsoluteFill>
	);
};

const ACTS = [
	{t: 'Chess Club', e: '♟️', g: ['#23A55A', '#0E5E33'], p: '2–8 players'},
	{t: 'Poker Night', e: '🃏', g: ['#ED4245', '#7A1214'], p: '2–8 players'},
	{t: 'Doodle Duel', e: '🖍️', g: ['#FEE75C', '#FF8A4C'], p: 'Up to 16'},
	{t: 'Watch Together', e: '🍿', g: ['#5865F2', '#2A2F8F'], p: 'Unlimited'},
	{t: 'Word Snacks', e: '🔤', g: ['#EB459E', '#8C2A6A'], p: 'Up to 8'},
	{t: 'Putt Party', e: '⛳', g: ['#00A8FC', '#0B4F7A'], p: 'Up to 8'},
];

const ActivitiesPhone: React.FC<{f: number}> = ({f}) => (
	<div style={{position: 'absolute', inset: 0, background: '#111214', fontFamily: BODY, color: C.text, paddingTop: 60}}>
		<div style={{padding: '6px 18px 4px', fontWeight: 900, fontSize: 26}}>Activities</div>
		<div style={{padding: '0 18px 12px', fontSize: 14.5, color: C.muted}}>Play games together in 🔊 Lounge</div>
		<div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, padding: '4px 14px'}}>
			{ACTS.map((a, i) => {
				const s = spr(f, 30 + i * 6, {damping: 13});
				const hot = i === 0 && f > 150;
				return (
					<div key={a.t} style={{borderRadius: 16, overflow: 'hidden', background: '#1E1F22', transform: `scale(${s * (hot ? 1.04 : 1)})`, boxShadow: hot ? `0 0 0 3px ${C.blurple}` : undefined}}>
						<div style={{height: 108, background: `linear-gradient(135deg, ${a.g[0]}, ${a.g[1]})`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
							<Emoji e={a.e} size={52} style={{transform: `rotate(${Math.sin((f + i * 20) / 18) * 8}deg)`}} />
						</div>
						<div style={{padding: '8px 10px 10px'}}>
							<div style={{fontWeight: 800, fontSize: 15.5}}>{a.t}</div>
							<div style={{fontSize: 12.5, color: C.faint}}>{a.p}</div>
						</div>
					</div>
				);
			})}
		</div>
		<div style={{position: 'absolute', left: 14, right: 14, bottom: 34, height: 54, borderRadius: 14, background: C.blurple, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 18, opacity: prog(f, 150, 165), transform: `translateY(${(1 - prog(f, 150, 170)) * 30}px)`}}>
			Start Chess Club ▶
		</div>
	</div>
);

/* ================================================================ 10. NITRO (88-96s) */
const PERKS = [
	{t: 'Custom emoji anywhere', e: '😎', c: C.fuchsia},
	{t: 'HD video & streaming', e: '📺', c: C.blurple},
	{t: 'Bigger file uploads', e: '📁', c: '#00A8FC'},
	{t: 'Profile themes & effects', e: '🎨', c: '#F47FFF'},
	{t: 'Super Reactions', e: '💥', c: C.yellow},
	{t: 'Server Boosts', e: '💎', c: '#FF73FA'},
];

const NitroProfile: React.FC<{f: number}> = ({f}) => {
	const hue = (f * 1.2) % 360;
	return (
		<div
			style={{
				position: 'absolute',
				inset: 0,
				fontFamily: BODY,
				color: C.text,
				background: `linear-gradient(180deg, #4A2C8F 0%, #2A1A5E 45%, #5A1F4F 100%)`,
			}}
		>
			<div style={{height: 230, background: `linear-gradient(${120 + Math.sin(f / 30) * 30}deg, ${C.fuchsia}, ${C.blurple}, #00A8FC)`, position: 'relative', overflow: 'hidden'}}>
				{[0, 1, 2, 3, 4, 5].map((i) => (
					<Sparkle key={i} size={16 + (i % 3) * 10} color="rgba(255,255,255,0.8)" style={{position: 'absolute', left: 30 + i * 60, top: 70 + ((i * 47) % 110), transform: `rotate(${f * 2 + i * 40}deg) scale(${0.6 + 0.4 * Math.sin(f / 10 + i)})`}} />
				))}
			</div>
			<div style={{position: 'absolute', left: 22, top: 160}}>
				<div style={{position: 'relative', width: 128, height: 128}}>
					<div style={{position: 'absolute', inset: -8, borderRadius: '50%', background: `conic-gradient(from ${hue}deg, ${C.fuchsia}, ${C.yellow}, ${C.green}, #00A8FC, ${C.blurple}, ${C.fuchsia})`}} />
					<div style={{position: 'absolute', inset: -2, borderRadius: '50%', background: '#2A1A5E'}} />
					<Avatar u="ava" size={124} style={{position: 'absolute', left: 2, top: 2}} />
				</div>
			</div>
			<div style={{position: 'absolute', right: 18, top: 248, display: 'flex', gap: 6}}>
				{['💎', '🚀', '🏆'].map((b) => (
					<div key={b} style={{width: 34, height: 34, borderRadius: 10, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
						<Emoji e={b} size={20} />
					</div>
				))}
			</div>
			<div style={{position: 'absolute', left: 16, right: 16, top: 312, background: 'rgba(0,0,0,0.35)', borderRadius: 18, padding: '16px 18px'}}>
				<div style={{fontWeight: 900, fontSize: 26}}>ava ✨</div>
				<div style={{fontSize: 15, color: '#E3D5FF'}}>ava.draws · she/her</div>
				<div style={{height: 1, background: 'rgba(255,255,255,0.15)', margin: '14px 0'}} />
				<div style={{fontSize: 13, fontWeight: 800, letterSpacing: '0.05em', color: '#E3D5FF'}}>ABOUT ME</div>
				<div style={{fontSize: 15.5, marginTop: 6, lineHeight: 1.4}}>digital artist 🎨 · commissions open · come hang in #art-showcase</div>
				<div style={{fontSize: 13, fontWeight: 800, letterSpacing: '0.05em', color: '#E3D5FF', marginTop: 14}}>NITRO MEMBER SINCE</div>
				<div style={{fontSize: 15.5, marginTop: 4, display: 'flex', alignItems: 'center', gap: 8}}>
					<Icon name="gem" size={18} color="#FF73FA" /> Mar 12, 2021
				</div>
			</div>
			<div style={{position: 'absolute', left: 16, right: 16, bottom: 36, height: 52, borderRadius: 14, background: '#fff', color: '#2A1A5E', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: 18}}>
				Edit Profile
			</div>
		</div>
	);
};

export const Nitro: React.FC = () => {
	const f = useCurrentFrame();
	const ph = spr(f, 4, {damping: 15, stiffness: 80});
	const burst = prog(f, 120, 160);
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 2640} a={C.fuchsia} b="#8C54FF" />
			<AbsoluteFill style={{background: `radial-gradient(50% 60% at 50% 60%, ${C.fuchsia}33, transparent)`}} />
			<AbsoluteFill style={{alignItems: 'center'}}>
				<div style={{marginTop: 56, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
					<Eyebrow f={f} start={2} num="08" label="Discord Nitro" icon="gem" color={C.fuchsia} />
					<div style={{height: 22}} />
					<Reveal text="LEVEL UP WITH NITRO" f={f} start={8} stagger={4} hl={['NITRO']} align="center" style={{...display(84), color: '#fff'}} hlBg={`linear-gradient(92deg, #FF73FA, ${C.fuchsia} 40%, #8C54FF)`} />
				</div>
			</AbsoluteFill>
			<div style={{position: 'absolute', inset: 0, perspective: 2000}}>
				<div
					style={{
						position: 'absolute',
						left: 960 - (427 * 0.84) / 2,
						top: 250,
						transformOrigin: '0 0',
						transform: `translateY(${(1 - ph) * 900 + Math.sin(f / 26) * 8}px) scale(0.84) rotateY(${Math.sin(f / 50) * 8}deg)`,
					}}
				>
					<IPhone frame="blurple">
						<NitroProfile f={f} />
					</IPhone>
				</div>
			</div>
			{/* super reaction burst */}
			<div style={{position: 'absolute', left: 1180, top: 300}}>
				{f >= 120 &&
					new Array(14).fill(0).map((_, i) => {
						const a = (i / 14) * Math.PI * 2;
						const d = 40 + burst * 150;
						return (
							<div key={i} style={{position: 'absolute', left: Math.cos(a) * d, top: Math.sin(a) * d, opacity: 1 - burst, transform: `scale(${1 - burst * 0.5})`}}>
								<Emoji e={i % 2 ? '💜' : '✨'} size={28} />
							</div>
						);
					})}
				<div style={{position: 'absolute', left: -40, top: -40, transform: `scale(${spr(f, 112, {damping: 8, stiffness: 200}) * (1 + 0.15 * Math.sin(f / 5))})`}}>
					<Emoji e="🔥" size={80} />
				</div>
			</div>
			{PERKS.map((p, i) => {
				const left = i < 3;
				const row = i % 3;
				const s = spr(f, 30 + i * 7, {damping: 14});
				return (
					<div
						key={p.t}
						style={{
							position: 'absolute',
							left: left ? 150 : 1320,
							top: 370 + row * 180,
							width: 450,
							transform: `translateX(${(1 - s) * (left ? -500 : 500)}px) translateY(${Math.sin((f + i * 20) / 30) * 6}px)`,
							opacity: Math.min(1, s * 1.4),
						}}
					>
						<div style={{display: 'flex', alignItems: 'center', gap: 18, padding: '20px 24px', borderRadius: 22, background: 'rgba(20,12,40,0.7)', border: `1.5px solid ${p.c}66`, boxShadow: `0 20px 50px rgba(0,0,0,0.4), inset 0 0 30px ${p.c}22`}}>
							<div style={{width: 64, height: 64, borderRadius: 18, background: `linear-gradient(135deg, ${p.c}, ${p.c}88)`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
								<Emoji e={p.e} size={34} />
							</div>
							<div style={{fontFamily: BODY, fontWeight: 800, fontSize: 25, color: '#fff', lineHeight: 1.2}}>{p.t}</div>
						</div>
					</div>
				);
			})}
		</AbsoluteFill>
	);
};

/* ================================================================ 11. EVERY DEVICE (96-104s) */
export const Devices: React.FC = () => {
	const f = useCurrentFrame();
	const cam = prog(f, 0, 240, easeInOut);
	const mb = spr(f, 0, {damping: 18, stiffness: 70});
	const pad = spr(f, 10, {damping: 18, stiffness: 70});
	const p1 = spr(f, 18, {damping: 16, stiffness: 80});
	const p2 = spr(f, 26, {damping: 16, stiffness: 80});
	const platforms = ['macOS', 'Windows', 'Linux', 'iOS', 'Android', 'Web', 'Xbox', 'PlayStation'];
	const sendAt = 120;
	const pulse = prog(f, sendAt, sendAt + 30);
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 2880} />
			<AbsoluteFill style={{alignItems: 'center'}}>
				<div style={{marginTop: 60, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
					<Eyebrow f={f} start={2} num="09" label="Cross-platform" icon="globe" />
					<div style={{height: 22}} />
					<Reveal text="ON EVERY DEVICE" f={f} start={8} stagger={4} hl={['EVERY', 'DEVICE']} align="center" style={{...display(88), color: '#fff'}} />
					<div style={{display: 'flex', gap: 12, marginTop: 26}}>
						{platforms.map((p, i) => {
							const s = spr(f, 30 + i * 4, {damping: 13});
							return (
								<div key={p} style={{transform: `scale(${s})`, padding: '8px 18px', borderRadius: 999, background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.14)', fontFamily: BODY, fontWeight: 700, fontSize: 20, color: '#E3E5FF'}}>
									{p}
								</div>
							);
						})}
					</div>
				</div>
			</AbsoluteFill>
			<div style={{position: 'absolute', inset: 0, perspective: 2600, transform: `scale(${lerp(1, 1.05, cam)})`, transformOrigin: '50% 80%'}}>
				{/* iPad left */}
				<div style={{position: 'absolute', left: 30, top: 440, transformOrigin: '0 0', transform: `translateY(${(1 - pad) * 800}px) scale(0.5) rotateY(18deg)`}}>
					<IPad>
						<div style={{position: 'absolute', inset: 0, display: 'flex', background: '#000'}}>
							<div style={{flex: 1, position: 'relative', containerType: 'inline-size'}}>
								<GameScene f={f} />
							</div>
							<div style={{width: 300, display: 'flex', flexDirection: 'column', gap: 8, padding: 8, background: '#0E0F12'}}>
								{(['luna', 'zed', 'nova'] as UserKey[]).map((u, i) => (
									<CamTile key={u} f={f} u={u} seed={i} speaking={talk(f, i + 2)} style={{flex: 1}} />
								))}
							</div>
						</div>
					</IPad>
				</div>
				{/* MacBook center */}
				<div style={{position: 'absolute', left: 880 - 840 * 0.62, top: 370, transformOrigin: '0 0', transform: `translateY(${(1 - mb) * 800}px) scale(0.62)`}}>
					<MacBook>
						<DesktopShell
							rail={<ServerRail f={f} selected={0} />}
							sidebar={<ChannelSidebar f={f} rows={MAIN_ROWS} />}
							main={
								<>
									<ChatHeader name="general" topic="the place to hang out ✨" />
									<div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', overflow: 'hidden'}}>
										<Msg f={f} u="kai">gg that was insane</Msg>
										<Msg f={f} u="nova">same time tomorrow? 🙌</Msg>
										<Msg f={f} u="luna" at={sendAt + 18} h={110} reactions={[{e: '💜', n: 3, at: sendAt + 40, me: true}]}>
											omw home, I'll catch you all on mobile 📱
										</Msg>
									</div>
									<InputBar f={f} placeholder="Message #general" />
								</>
							}
							members={undefined}
						/>
					</MacBook>
				</div>
				{/* iPhone duo right */}
				<div style={{position: 'absolute', left: 1390, top: 380, transformOrigin: '0 0', transform: `translateY(${(1 - p1) * 800 + Math.sin(f / 30) * 6}px) scale(0.62) rotateY(-16deg) rotateZ(-3deg)`}}>
					<IPhone frame="black">
						<MobileHome f={f} />
					</IPhone>
				</div>
				<div style={{position: 'absolute', left: 1600, top: 430, transformOrigin: '0 0', transform: `translateY(${(1 - p2) * 800 + Math.sin(f / 30 + 1) * 6}px) scale(0.62) rotateY(-16deg) rotateZ(4deg)`}}>
					<IPhone>
						<MobileChat title="general" sub="Pixel Party" input={<MobileInput f={f} text={f < sendAt ? "omw home, I'll catch you all on mobile 📱".slice(0, Math.floor(interpolate(f, [60, sendAt - 6], [0, 42], clamp))) : undefined} />}>
							<Msg f={f} u="kai" scale={0.85}>gg that was insane</Msg>
							<Msg f={f} u="nova" scale={0.85}>same time tomorrow? 🙌</Msg>
							<Msg f={f} u="luna" scale={0.85} at={sendAt} h={110}>
								omw home, I'll catch you all on mobile 📱
							</Msg>
						</MobileChat>
					</IPhone>
				</div>
				{/* sync pulse from phone to laptop */}
				{f >= sendAt && f < sendAt + 34 && (
					<svg width="1920" height="1080" style={{position: 'absolute', inset: 0}}>
						<defs>
							<linearGradient id="sync" x1="1" x2="0">
								<stop offset="0" stopColor={C.green} />
								<stop offset="1" stopColor={C.blurple} />
							</linearGradient>
						</defs>
						<path d="M1760 880 C 1560 600, 1320 620, 1120 790" stroke="url(#sync)" strokeWidth="5" fill="none" strokeDasharray="900" strokeDashoffset={900 * (1 - pulse)} strokeLinecap="round" opacity={1 - prog(f, sendAt + 22, sendAt + 34)} />
					</svg>
				)}
			</div>
		</AbsoluteFill>
	);
};

/* ================================================================ 12. STATS (104-108s) */
export const Stats: React.FC = () => {
	const f = useCurrentFrame();
	const stats = [
		{v: 200, suf: 'M+', l: 'people every month', c: C.blurple},
		{v: 19, suf: 'M+', l: 'active servers each week', c: C.green},
		{v: 4, suf: 'B+', l: 'minutes of conversation a day', c: C.fuchsia},
	];
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 3120} />
			<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
				<Reveal text="LOVED BY COMMUNITIES EVERYWHERE" f={f} start={0} stagger={3} hl={['EVERYWHERE']} align="center" style={{...display(46, 800), color: '#E3E5FF'}} />
				<div style={{display: 'flex', gap: 30, marginTop: 70}}>
					{stats.map((s, i) => {
						const p = prog(f, 8 + i * 8, 70 + i * 8, easeOut);
						const sc = spr(f, 6 + i * 8, {damping: 14});
						return (
							<div key={i} style={{width: 540, textAlign: 'center', transform: `scale(${sc})`}}>
								<div style={{...display(124), color: '#fff', letterSpacing: '-0.03em'}}>
									{Math.round(s.v * p)}
									<span style={{color: s.c}}>{s.suf}</span>
								</div>
								<div style={{height: 6, width: 120 * p, background: s.c, borderRadius: 3, margin: '24px auto 18px', boxShadow: `0 0 20px ${s.c}`}} />
								<div style={{fontFamily: BODY, fontWeight: 600, fontSize: 28, color: '#B9BEE8'}}>{s.l}</div>
							</div>
						);
					})}
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

/* ================================================================ 13. BENTO RECAP (108-114s) */
const TILES: {t: string; d: string; icon: Parameters<typeof Icon>[0]['name']; c: string; col: string; row: string}[] = [
	{t: 'Servers & Channels', d: 'A home for every group', icon: 'users', c: C.blurple, col: '1 / 3', row: '1 / 2'},
	{t: 'Text Chat', d: 'Threads, replies, reactions', icon: 'chat', c: C.fuchsia, col: '3 / 4', row: '1 / 2'},
	{t: 'Voice', d: 'Always-on hangouts', icon: 'speaker', c: C.green, col: '4 / 5', row: '1 / 3'},
	{t: 'Video & Go Live', d: 'Stream in up to 4K', icon: 'video', c: C.red, col: '1 / 2', row: '2 / 3'},
	{t: 'Stage & Events', d: 'Q&As, AMAs, game nights', icon: 'stage', c: C.yellow, col: '2 / 4', row: '2 / 3'},
	{t: 'Roles & AutoMod', d: 'Safe by design', icon: 'shield', c: C.green, col: '1 / 2', row: '3 / 4'},
	{t: 'Apps & Activities', d: 'Bots, polls & games', icon: 'apps', c: '#00A8FC', col: '2 / 3', row: '3 / 4'},
	{t: 'Nitro', d: 'Level up your profile', icon: 'gem', c: '#FF73FA', col: '3 / 4', row: '3 / 4'},
	{t: 'Every Device', d: 'Desktop, mobile, web, console', icon: 'globe', c: C.blurpleSoft, col: '4 / 5', row: '3 / 4'},
];

export const Bento: React.FC = () => {
	const f = useCurrentFrame();
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 3240} />
			<div style={{position: 'absolute', left: 110, top: 70}}>
				<Reveal text="EVERYTHING YOUR COMMUNITY NEEDS" f={f} start={0} stagger={3} hl={['COMMUNITY']} style={{...display(64), color: '#fff'}} />
			</div>
			<div style={{position: 'absolute', left: 110, right: 110, top: 200, bottom: 80, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gridTemplateRows: 'repeat(3, 1fr)', gap: 22, perspective: 1800}}>
				{TILES.map((t, i) => {
					const s = spr(f, 8 + i * 4, {damping: 15, stiffness: 120});
					const big = t.col === '1 / 3' || t.row === '1 / 3' || t.col === '2 / 4';
					return (
						<div
							key={t.t}
							style={{
								gridColumn: t.col,
								gridRow: t.row,
								position: 'relative',
								borderRadius: 28,
								overflow: 'hidden',
								background: `linear-gradient(150deg, ${t.c}30 0%, rgba(22,24,52,0.85) 55%)`,
								border: `1.5px solid ${t.c}55`,
								boxShadow: `inset 0 1px 0 rgba(255,255,255,0.08), 0 20px 50px rgba(0,0,0,0.35)`,
								transform: `rotateX(${(1 - s) * 50}deg) translateY(${(1 - s) * 80}px) scale(${lerp(0.85, 1, s)})`,
								opacity: Math.min(1, s * 1.5),
								padding: 30,
								display: 'flex',
								flexDirection: 'column',
								justifyContent: 'flex-end',
							}}
						>
							<div style={{position: 'absolute', right: -40, top: -40, width: 220, height: 220, borderRadius: '50%', background: `radial-gradient(closest-side, ${t.c}55, transparent)`}} />
							<div style={{position: 'absolute', left: 30, top: 30, width: 66, height: 66, borderRadius: 20, background: t.c, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 10px 30px ${t.c}66`}}>
								<Icon name={t.icon} size={36} color={t.c === C.yellow || t.c === C.green ? C.black : '#fff'} />
							</div>
							{big && <BentoArt i={i} f={f} />}
							<div style={{...display(big ? 34 : 26, 800), color: '#fff', lineHeight: 1.05}}>{t.t}</div>
							<div style={{fontFamily: BODY, fontWeight: 600, fontSize: 21, color: '#B9BEE8', marginTop: 8}}>{t.d}</div>
						</div>
					);
				})}
			</div>
		</AbsoluteFill>
	);
};

const BentoArt: React.FC<{i: number; f: number}> = ({i, f}) => {
	if (i === 0)
		return (
			<div style={{position: 'absolute', right: 30, top: 34, display: 'flex', gap: 12}}>
				{['🎮', '🎨', '🎧', '📚', '🚀'].map((e, k) => (
					<div key={e} style={{width: 64, height: 64, borderRadius: k === 0 ? 20 : 32, background: ['#5865F2', '#EB459E', '#23A55A', '#F0B232', '#ED4245'][k], display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `translateY(${Math.sin((f + k * 10) / 14) * 6}px)`}}>
						<Emoji e={e} size={32} />
					</div>
				))}
			</div>
		);
	if (i === 2)
		return (
			<div style={{position: 'absolute', left: 30, right: 30, top: 120, display: 'flex', flexDirection: 'column', gap: 10}}>
				{(['nova', 'kai', 'luna', 'zed'] as UserKey[]).map((u, k) => (
					<div key={u} style={{display: 'flex', alignItems: 'center', gap: 12}}>
						<Avatar u={u} size={40} speaking={talk(f, k)} />
						<span style={{fontFamily: BODY, fontWeight: 700, fontSize: 21, color: '#fff'}}>{USERS[u].name}</span>
					</div>
				))}
				<div style={{display: 'flex', gap: 5, alignItems: 'center', height: 44, marginTop: 4}}>
					{new Array(18).fill(0).map((_, k) => (
						<div key={k} style={{flex: 1, borderRadius: 4, background: C.green, height: 6 + Math.abs(Math.sin(f * 0.2 + k * 0.7)) * 36}} />
					))}
				</div>
			</div>
		);
	if (i === 4)
		return (
			<div style={{position: 'absolute', right: 30, top: 30, display: 'flex'}}>
				{(['nova', 'ava', 'kai', 'luna', 'rio'] as UserKey[]).map((u, k) => (
					<Avatar key={u} u={u} size={60} speaking={k === 0 ? talk(f, 9) : 0} style={{marginLeft: k ? -14 : 0, boxShadow: '0 0 0 4px #1b1d3c', borderRadius: '50%'}} />
				))}
			</div>
		);
	return null;
};

/* ================================================================ 14. OUTRO (114-120s) */
export const Outro: React.FC = () => {
	const f = useCurrentFrame();
	const logo = spr(f, 4, {damping: 11, stiffness: 120});
	const fadeOut = prog(f, 160, 180, easeIn);
	const confetti = new Array(40).fill(0).map((_, i) => ({
		x: random(`cx${i}`) * 1920,
		vy: 2 + random(`cv${i}`) * 4,
		r: random(`cr${i}`) * 360,
		c: [C.blurple, C.fuchsia, C.green, C.yellow, '#fff'][i % 5],
		s: 10 + random(`cs${i}`) * 14,
		d: random(`cd${i}`) * 40,
	}));
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 3420} />
			{confetti.map((c, i) => {
				const t = Math.max(0, f - 20 - c.d);
				return (
					<Sparkle
						key={i}
						size={c.s}
						color={c.c}
						style={{position: 'absolute', left: c.x + Math.sin(t / 12 + i) * 30, top: -40 + t * c.vy, transform: `rotate(${c.r + t * 4}deg)`, opacity: f > 20 + c.d ? 0.85 : 0}}
					/>
				);
			})}
			<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
				<div style={{display: 'flex', alignItems: 'center', gap: 40, transform: `scale(${logo})`}}>
					<div style={{width: 170, height: 170, borderRadius: 48, background: `linear-gradient(140deg, #7983F5, ${C.blurple} 45%, ${C.blurpleDeep})`, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 0 90px ${C.blurple}aa`}}>
						<Clyde size={108} style={{transform: `translateY(${Math.sin(f / 9) * 3}px)`}} />
					</div>
					<div style={{...display(150), color: '#fff'}}>DISCORD</div>
				</div>
				<div style={{height: 40}} />
				<Reveal text="IMAGINE A PLACE." f={f} start={18} stagger={4} hl={['PLACE']} align="center" style={{...display(56, 800), color: '#E3E5FF'}} />
				<div style={{display: 'flex', gap: 24, marginTop: 56}}>
					{[
						{t: 'Download for Mac', bg: '#fff', fg: C.black, icon: 'download' as const},
						{t: 'Open Discord in your browser', bg: C.black, fg: '#fff', icon: 'globe' as const},
					].map((b, i) => {
						const s = spr(f, 36 + i * 6, {damping: 12});
						return (
							<div
								key={b.t}
								style={{
									transform: `scale(${s})`,
									display: 'flex',
									alignItems: 'center',
									gap: 14,
									padding: '22px 38px',
									borderRadius: 40,
									background: b.bg,
									color: b.fg,
									fontFamily: BODY,
									fontWeight: 800,
									fontSize: 26,
									boxShadow: i === 0 ? '0 18px 50px rgba(88,101,242,0.45)' : '0 18px 50px rgba(0,0,0,0.4)',
								}}
							>
								<Icon name={b.icon} size={28} color={b.fg} />
								{b.t}
							</div>
						);
					})}
				</div>
				<div style={{marginTop: 46, fontFamily: BODY, fontWeight: 700, fontSize: 28, color: '#9EA6F7', letterSpacing: '0.08em', opacity: prog(f, 56, 76)}}>discord.com</div>
			</AbsoluteFill>
			<AbsoluteFill style={{background: '#000', opacity: fadeOut}} />
		</AbsoluteFill>
	);
};

export {GRAD, Bar, Callout, Body, MONO, clamp, easeOut, IPad};
