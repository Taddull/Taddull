import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Avatar, Body, Callout, Clyde, Emoji, Eyebrow, GRAD, Icon, Reveal, SpaceBg, Sparkle} from './primitives';
import {BODY, C, clamp, display, easeIn, easeInOut, easeOut, lerp, prog, spr} from './theme';
import {IPhone, MacBook} from './devices';
import {
	ChannelSidebar,
	ChatHeader,
	DesktopShell,
	InputBar,
	MemberList,
	Mention,
	MobileChat,
	MobileHome,
	MobileInput,
	Msg,
	Row,
	ServerRail,
	Typing,
} from './ui';

/* ================================================================ 1. INTRO (0-8s) */
export const Intro: React.FC = () => {
	const f = useCurrentFrame();
	const words = ['IMAGINE', 'A', 'PLACE…'];
	// phase A: kinetic words 0-110 ; phase B: logo reveal 105-240
	const outA = prog(f, 100, 116, easeIn);
	const burst = spr(f, 116, {damping: 11, stiffness: 120});
	const ring = prog(f, 114, 160);
	const logoY = interpolate(prog(f, 158, 183, easeInOut), [0, 1], [0, -70]);
	return (
		<AbsoluteFill>
			<SpaceBg f={f} />
			{/* Phase A — slam words, one per beat */}
			<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', opacity: 1 - outA, transform: `scale(${1 + outA * 0.5})`}}>
				<div style={{display: 'flex', gap: 46, alignItems: 'baseline'}}>
					{words.map((w, i) => {
						const at = 13 + i * 15;
						const s = spr(f, at, {damping: 10, stiffness: 200, mass: 0.6});
						const o = interpolate(f, [at, at + 3], [0, 1], clamp);
						return (
							<div
								key={w}
								style={{
									...display(138),
									color: i === 2 ? 'transparent' : '#fff',
									backgroundImage: i === 2 ? GRAD : undefined,
									WebkitBackgroundClip: i === 2 ? 'text' : undefined,
									backgroundClip: i === 2 ? 'text' : undefined,
									opacity: o,
									transform: `scale(${lerp(2.2, 1, s)}) translateY(${(1 - s) * -30}px)`,
									filter: `blur(${(1 - Math.min(1, s)) * 18}px)`,
								}}
							>
								{w}
							</div>
						);
					})}
				</div>
				<div
					style={{
						marginTop: 34,
						fontFamily: BODY,
						fontWeight: 600,
						fontSize: 34,
						color: '#C9CDFB',
						letterSpacing: '0.02em',
						opacity: prog(f, 60, 76),
						transform: `translateY(${(1 - prog(f, 60, 80)) * 20}px)`,
					}}
				>
					…where you belong, with the people who get you.
				</div>
			</AbsoluteFill>

			{/* shockwave rings */}
			{[0, 1, 2].map((i) => {
				const r = prog(f, 117 + i * 5, 163 + i * 5, easeOut);
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: 960,
							top: 540,
							width: 2400 * r,
							height: 2400 * r,
							marginLeft: -1200 * r,
							marginTop: -1200 * r,
							borderRadius: '50%',
							border: `${6 - i * 1.5}px solid ${[C.blurple, C.fuchsia, C.green][i]}`,
							opacity: (1 - r) * (f > 117 ? 1 : 0),
						}}
					/>
				);
			})}
			{/* Phase B — logo */}
			<AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
				<div style={{transform: `translateY(${logoY}px)`, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
					<div
						style={{
							position: 'relative',
							width: 260,
							height: 260,
							borderRadius: lerp(130, 72, prog(f, 128, 158)),
							background: `linear-gradient(140deg, #7983F5, ${C.blurple} 45%, ${C.blurpleDeep})`,
							display: 'flex',
							alignItems: 'center',
							justifyContent: 'center',
							transform: `scale(${burst}) rotate(${(1 - burst) * -40}deg)`,
							boxShadow: `0 0 ${120 * ring}px ${C.blurple}, 0 30px 80px rgba(0,0,0,0.5)`,
							opacity: f >= 116 ? 1 : 0,
						}}
					>
						<Clyde size={160} style={{transform: `translateY(${Math.sin(f / 9) * 3}px)`}} />
						{[0, 1, 2, 3].map((i) => {
							const sp = spr(f, 130 + i * 4, {damping: 12});
							const ang = (i / 4) * Math.PI * 2 + 0.6;
							return (
								<Sparkle
									key={i}
									size={[34, 22, 28, 18][i]}
									color={[C.yellow, C.green, '#fff', C.fuchsia][i]}
									style={{
										position: 'absolute',
										left: 130 + Math.cos(ang) * 175 * sp - 15,
										top: 130 + Math.sin(ang) * 175 * sp - 15,
										transform: `scale(${sp}) rotate(${f * 2}deg)`,
									}}
								/>
							);
						})}
					</div>
					<div style={{display: 'flex', marginTop: 46, height: 150, alignItems: 'center'}}>
						{'DISCORD'.split('').map((ch, i) => {
							const p = prog(f, 146 + i * 2.5, 168 + i * 2.5);
							return (
								<span
									key={i}
									style={{
										...display(150),
										color: '#fff',
										display: 'inline-block',
										opacity: p,
										transform: `translateY(${(1 - p) * 60}px) scale(${lerp(0.6, 1, p)})`,
										filter: `blur(${(1 - p) * 12}px)`,
									}}
								>
									{ch}
								</span>
							);
						})}
					</div>
					<div style={{marginTop: 26, overflow: 'hidden'}}>
						<Reveal
							text="GROUP CHAT THAT'S ALL FUN & GAMES"
							f={f}
							start={178}
							stagger={2.5}
							hl={['FUN', 'GAMES']}
							style={{...display(40, 800), color: '#E3E5FF', letterSpacing: '0.02em'}}
						/>
					</div>
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

/* ================================================================ shared app content */
export const MAIN_ROWS: Row[] = [
	{type: 'ch', name: 'welcome', icon: 'hash'},
	{type: 'ch', name: 'announcements', unread: true, badge: 2},
	{type: 'ch', name: 'events', icon: 'calendar'},
	{type: 'cat', label: 'Text Channels'},
	{type: 'ch', name: 'general', active: true},
	{type: 'ch', name: 'memes', unread: true},
	{type: 'ch', name: 'clips-and-highlights'},
	{type: 'ch', name: 'art-showcase'},
	{type: 'cat', label: 'Voice Channels'},
	{type: 'voice', name: 'Lounge', users: [{u: 'nova', speaking: 1}, {u: 'kai'}, {u: 'mila', muted: true}]},
	{type: 'voice', name: 'Gaming'},
	{type: 'voice', name: 'Game Night', icon: 'stage'},
];

export const MEMBERS = [
	{label: 'Admin', users: ['nova'] as const},
	{label: 'Moderators', users: ['kai', 'jun'] as const},
	{label: 'Artists', users: ['mila', 'ava'] as const},
	{label: 'Online', users: ['zed', 'luna', 'rio', 'ozzy'] as const},
].map((g) => ({...g, users: [...g.users]}));

const HeroChat: React.FC<{f: number}> = ({f}) => (
	<>
		<ChatHeader name="general" topic="the place to hang out ✨ be nice, have fun" />
		<div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', overflow: 'hidden'}}>
			<Msg f={f} u="rio" time="Today at 9:02 PM">
				just dropped the new map pack in <Mention># announcements</Mention> 🗺️
			</Msg>
			<Msg f={f} u="jun" time="Today at 9:05 PM" reactions={[{e: '😂', n: 4}]}>
				finally, my squad has been waiting all week
			</Msg>
			<Msg f={f} u="luna" time="Today at 9:12 PM">
				who's up for some games tonight?? 🎮
			</Msg>
			<Msg f={f} u="kai" reactions={[{e: '🔥', n: 6, me: true}, {e: '🙌', n: 3}]}>
				me!! just finished my homework
			</Msg>
			<Msg f={f} u="mila" at={40}>
				save me a spot, joining <Mention># Lounge</Mention> in 5
			</Msg>
			<Msg f={f} u="nova" at={70} reactions={[{e: '🎉', n: 12, me: true, at: 100}, {e: '💜', n: 8, at: 108}]}>
				Server just hit 10,000 members!! thank you all 💜
			</Msg>
		</div>
		<Typing f={f} text="zed" />
		<InputBar f={f} placeholder="Message #general" />
	</>
);

/* ================================================================ 2. HERO (8-18s) */
export const Hero: React.FC = () => {
	const f = useCurrentFrame();
	const enter = spr(f, 0, {damping: 18, stiffness: 70});
	const phone = spr(f, 24, {damping: 16, stiffness: 80});
	const cam = prog(f, 0, 300, easeInOut);
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 240} />
			<AbsoluteFill style={{alignItems: 'center'}}>
				<div style={{marginTop: 70, textAlign: 'center'}}>
					<Reveal text="YOUR PLACE TO TALK" f={f} start={6} stagger={4} hl={['TALK']} align="center" style={{...display(96), color: '#fff'}} />
					<div style={{height: 22}} />
					<Body f={f} start={26} w={1100} size={28} align="center">
						Whether you're part of a school club, a gaming group, or a worldwide art community — Discord makes it easy to talk every day and hang out more often.
					</Body>
				</div>
			</AbsoluteFill>
			<div style={{position: 'absolute', inset: 0, perspective: 2400}}>
				<div
					style={{
						position: 'absolute',
						left: 960 - 840,
						top: 330,
						transformOrigin: '50% 0%',
						transform: `translateY(${(1 - enter) * 700}px) scale(${0.6 + cam * 0.03}) rotateX(${(1 - enter) * 30 + 3}deg) rotateY(${lerp(-5, 3, cam)}deg)`,
					}}
				>
					<MacBook>
						<DesktopShell
							rail={<ServerRail f={f} selected={0} badges={{2: 4, 4: 12}} />}
							sidebar={<ChannelSidebar f={f} rows={MAIN_ROWS} />}
							main={<HeroChat f={f} />}
							members={<MemberList groups={MEMBERS} />}
						/>
					</MacBook>
				</div>
				<div
					style={{
						position: 'absolute',
						left: 1380,
						top: 410,
						transform: `translateY(${(1 - phone) * 800 + Math.sin(f / 30) * 10}px) scale(0.68) rotateY(${lerp(-18, -8, cam)}deg) rotateZ(${(1 - phone) * 10 + 2}deg)`,
						transformOrigin: '0% 0%',
					}}
				>
					<IPhone>
						<MobileHome f={f} />
					</IPhone>
				</div>
				<div
					style={{
						position: 'absolute',
						left: 250,
						top: 480,
						transform: `translateY(${(1 - spr(f, 40)) * 700 + Math.sin(f / 28 + 2) * 10}px) scale(0.6) rotateY(16deg) rotateZ(-4deg)`,
						transformOrigin: '0% 0%',
					}}
				>
					<IPhone frame="blurple">
						<MobileChat title="general" sub="Pixel Party" input={<MobileInput f={f} />}>
							<Msg f={f} u="ava" scale={0.9}>
								look what I made 👀
							</Msg>
							<div style={{margin: '4px 16px 8px 70px', height: 210, borderRadius: 12, background: `linear-gradient(135deg, ${C.fuchsia}, ${C.blurple})`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
								<Emoji e="🎨" size={90} />
							</div>
							<Msg f={f} u="rio" scale={0.9} reactions={[{e: '😍', n: 9, me: true}]}>
								that's insane omg
							</Msg>
						</MobileChat>
					</IPhone>
				</div>
			</div>
			<Callout f={f} start={70} float={1} style={{left: 1500, top: 330}}>
				<div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '14px 20px'}}>
					<div style={{width: 12, height: 12, borderRadius: 6, background: C.online, boxShadow: `0 0 12px ${C.online}`}} />
					<span style={{fontWeight: 700, fontSize: 22}}>1,248 online</span>
				</div>
			</Callout>
			<Callout f={f} start={95} float={2} style={{left: 90, top: 390}}>
				<div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '12px 18px'}}>
					<Avatar u="nova" size={40} />
					<div style={{lineHeight: 1.2}}>
						<div style={{fontWeight: 800, fontSize: 18}}>nova joined</div>
						<div style={{fontSize: 15, color: C.muted}}>🔊 Lounge</div>
					</div>
				</div>
			</Callout>
		</AbsoluteFill>
	);
};

/* ================================================================ 3. SERVERS (18-28s) */
export const Servers: React.FC = () => {
	const f = useCurrentFrame();
	const zoom = prog(f, 0, 300, easeInOut);
	const morph = prog(f, 120, 140);
	const sel = f < 120 ? 2 : 0;
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 540} a={C.blurple} b={C.green} />
			<div style={{position: 'absolute', left: 110, top: 250, width: 720}}>
				<Eyebrow f={f} start={4} num="01" label="Servers & Channels" icon="users" />
				<div style={{height: 34}} />
				<Reveal text={'A HOME FOR\nEVERY SQUAD'} f={f} start={10} stagger={4} hl={['SQUAD']} style={{...display(84), color: '#fff'}} />
				<div style={{height: 30}} />
				<Body f={f} start={34} w={640}>
					Spin up an invite-only server in seconds. Organise topics into text channels, drop into voice when you're free.
				</Body>
				<div style={{display: 'flex', gap: 14, marginTop: 40, flexWrap: 'wrap', width: 640}}>
					{['# general', '# memes', '🔊 Lounge', '# art-showcase', '📅 events', '🎙 Stage'].map((t, i) => {
						const s = spr(f, 60 + i * 5, {damping: 12});
						return (
							<div
								key={t}
								style={{
									transform: `scale(${s})`,
									padding: '10px 18px',
									borderRadius: 12,
									background: 'rgba(255,255,255,0.07)',
									border: '1px solid rgba(255,255,255,0.12)',
									fontFamily: BODY,
									fontWeight: 700,
									fontSize: 22,
									color: '#E3E5FF',
								}}
							>
								{t}
							</div>
						);
					})}
				</div>
			</div>
			{/* zoomed-in MacBook: crop on rail + sidebar */}
			<div style={{position: 'absolute', left: 900, top: 90, width: 960, height: 900, perspective: 2000}}>
				<div
					style={{
						position: 'absolute',
						left: 0,
						top: 0,
						transformOrigin: '0 0',
						transform: `translate(${lerp(40, 0, spr(f, 0, {damping: 20, stiffness: 60}))}px, ${(1 - spr(f, 0, {damping: 20, stiffness: 60})) * 300}px) scale(${lerp(0.82, 0.9, zoom)}) rotateY(${lerp(-14, -8, zoom)}deg)`,
					}}
				>
					<MacBook>
						<DesktopShell
							rail={<ServerRail f={f} start={8} selected={sel} morph={f < 120 ? prog(f, 20, 36) : morph} badges={{4: 12, 6: 3}} />}
							sidebar={<ChannelSidebar f={f} rows={MAIN_ROWS} start={40} />}
							main={<HeroChat f={f + 200} />}
						/>
					</MacBook>
				</div>
			</div>
			{/* floating server card */}
			<Callout f={f} start={150} float={0} style={{left: 1470, top: 150}}>
				<div style={{width: 340, overflow: 'hidden', borderRadius: 18}}>
					<div style={{height: 90, background: `linear-gradient(120deg, ${C.blurple}, ${C.fuchsia})`}} />
					<div style={{padding: '0 20px 20px', marginTop: -36}}>
						<div style={{width: 72, height: 72, borderRadius: 20, background: `linear-gradient(135deg, #5865F2, #8C54FF)`, border: `5px solid #1E1F22`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
							<Emoji e="🎮" size={38} />
						</div>
						<div style={{fontWeight: 800, fontSize: 24, marginTop: 10}}>Pixel Party</div>
						<div style={{display: 'flex', gap: 16, fontSize: 16, color: C.muted, marginTop: 6}}>
							<span>
								<span style={{color: C.online}}>●</span> 1,248 Online
							</span>
							<span>
								<span style={{color: C.faint}}>●</span> 10,000 Members
							</span>
						</div>
						<div style={{marginTop: 16, height: 44, borderRadius: 8, background: C.online, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 17}}>
							Join Server
						</div>
					</div>
				</div>
			</Callout>
		</AbsoluteFill>
	);
};

/* ================================================================ 4. CHAT (28-40s) */
export const Chat: React.FC = () => {
	const f = useCurrentFrame();
	const enter = spr(f, 0, {damping: 18, stiffness: 70});
	const cam = prog(f, 0, 360, easeInOut);
	const typed = 'gg everyone, same time tomorrow?';
	const tn = Math.floor(interpolate(f, [235, 290], [0, typed.length], clamp));
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 840} a={C.fuchsia} b={C.blurple} />
			<div style={{position: 'absolute', inset: 0, perspective: 2200}}>
				<div
					style={{
						position: 'absolute',
						left: 700 - 840,
						top: 40,
						transformOrigin: '50% 50%',
						transform: `translateX(${(1 - enter) * -900}px) scale(${lerp(0.66, 0.7, cam)}) rotateY(${lerp(14, 8, cam)}deg)`,
					}}
				>
					<MacBook>
						<DesktopShell
							rail={<ServerRail f={f} selected={0} badges={{2: 4}} />}
							sidebar={<ChannelSidebar f={f} rows={MAIN_ROWS} />}
							main={
								<>
									<ChatHeader name="general" topic="the place to hang out ✨ be nice, have fun" />
									<div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', overflow: 'hidden'}}>
										<Msg f={f} u="kai" time="Today at 9:30 PM">
											ok who's carrying tonight
										</Msg>
										<Msg f={f} u="luna" at={30} h={130}>
											not me, I'm still recovering from last night 😭
										</Msg>
										<Msg f={f} u="zed" at={60} h={150} reply={{u: 'luna', text: "not me, I'm still recovering…"}} reactions={[{e: '😂', n: 7, at: 80}, {e: '💀', n: 4, at: 86}]}>
											skill issue tbh
										</Msg>
										<Msg f={f} u="ava" at={100} h={360} reactions={[{e: '🔥', n: 23, me: true, at: 150}, {e: '🏆', n: 11, at: 156}, {e: '👏', n: 6, at: 162}]}>
											clip of the year incoming 👇
											<div style={{marginTop: 8, width: 420, height: 236, borderRadius: 10, overflow: 'hidden', position: 'relative'}}>
												<div style={{position: 'absolute', inset: 0, background: `linear-gradient(135deg, #2a0845, #6441A5)`}} />
												<div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
													<div style={{width: 70, height: 70, borderRadius: '50%', background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
														<svg width="30" height="30" viewBox="0 0 24 24">
															<path d="M7 4l13 8-13 8z" fill="#fff" />
														</svg>
													</div>
												</div>
												<div style={{position: 'absolute', left: 10, bottom: 8, fontSize: 13, color: '#fff', fontWeight: 700}}>clutch_1v4.mp4 · 0:27</div>
											</div>
										</Msg>
										<Msg f={f} u="nova" at={190} h={130} mention>
											<Mention>@everyone</Mention> game night starts in 10 — grab a seat in 🔊 Lounge
										</Msg>
									</div>
									<Typing f={f} text={f < 235 ? 'kai.exe and mila' : 'you'} />
									<InputBar f={f} placeholder="Message #general" text={f >= 235 ? typed.slice(0, tn) : undefined} />
								</>
							}
						/>
					</MacBook>
				</div>
			</div>
			<div style={{position: 'absolute', left: 1300, top: 270, width: 600}}>
				<Eyebrow f={f} start={4} num="02" label="Text Chat" icon="chat" color={C.fuchsia} />
				<div style={{height: 34}} />
				<Reveal text={'CHAT THAT\nKEEPS UP'} f={f} start={10} stagger={4} hl={['KEEPS', 'UP']} style={{...display(80), color: '#fff'}} />
				<div style={{height: 30}} />
				<Body f={f} start={34} w={560} size={26}>
					Replies, threads, reactions, GIFs, file sharing and mentions — conversation flows as fast as your friends do.
				</Body>
			</div>
			{/* break-out floating elements */}
			<Callout f={f} start={120} float={0} style={{left: 960, top: 120}}>
				<div style={{display: 'flex', gap: 10, padding: '12px 16px', alignItems: 'center'}}>
					{['😂', '🔥', '💜', '👀', '🎉'].map((e, i) => (
						<Emoji key={e} e={e} size={40} style={{transform: `translateY(${Math.sin((f + i * 8) / 8) * 4}px)`}} />
					))}
				</div>
			</Callout>
			<Callout f={f} start={175} float={2} style={{left: 1010, top: 770}}>
				<div style={{display: 'flex', gap: 14, padding: '14px 20px', alignItems: 'center'}}>
					<div style={{width: 44, height: 44, borderRadius: 12, background: C.blurple, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
						<Icon name="thread" size={26} color="#fff" />
					</div>
					<div style={{lineHeight: 1.25}}>
						<div style={{fontWeight: 800, fontSize: 19}}>Thread: game night strats</div>
						<div style={{fontSize: 15, color: C.muted}}>24 messages · 6 people</div>
					</div>
				</div>
			</Callout>
		</AbsoluteFill>
	);
};
