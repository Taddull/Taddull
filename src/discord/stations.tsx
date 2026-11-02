import React from 'react';
import {interpolate} from 'remotion';
import {Avatar, Body, Card, Clyde, Emoji, Eyebrow, Icon, Reveal, Sparkle, USERS, UserKey} from './primitives';
import {BODY, C, MONO, clamp, display, easeIn, easeInOut, lerp, prog, spr} from './theme';
import {IPad, IPhone, MacBook} from './devices';
import {
	CamTile,
	CallControls,
	ChannelSidebar,
	ChatHeader,
	DesktopShell,
	GameScene,
	InputBar,
	MemberList,
	Mention,
	MobileChat,
	MobileHome,
	MobileInput,
	Msg,
	Row,
	ServerRail,
	Toggle,
	Typing,
} from './ui';
import {Cursor} from './world';
import {CHAT_ARRIVE, CUES, STATIONS} from './timeline';

/* ================================================================ shared */
export const talk = (f: number, seed: number) => {
	const a = Math.sin(f * 0.11 + seed * 2.3) * Math.sin(f * 0.047 + seed * 1.7);
	return interpolate(a, [0.15, 0.45], [0, 1], clamp);
};

const rise = (t: number, at: number, dist = 700) => (1 - spr(t, at, {damping: 18, stiffness: 75})) * dist;

const MAIN_ROWS: Row[] = [
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

const MEMBERS = [
	{label: 'Admin', users: ['nova'] as UserKey[]},
	{label: 'Moderators', users: ['kai', 'jun'] as UserKey[]},
	{label: 'Artists', users: ['mila', 'ava'] as UserKey[]},
	{label: 'Online', users: ['zed', 'luna', 'rio', 'ozzy'] as UserKey[]},
];

const H1 = (size: number): React.CSSProperties => ({...display(size), color: '#fff'});

/* ================================================================ 1. INTRO */
export const Intro: React.FC<{f: number}> = ({f}) => {
	const I = CUES.intro;
	const t = f - STATIONS.intro.arrive;
	const out = prog(t, I.wordsOut, I.wordsOut + 16, easeIn);
	const burst = spr(t, I.logo, {damping: 11, stiffness: 130});
	const words = ['IMAGINE', 'A', 'PLACE…'];
	const chip = prog(t, I.words[2] + 12, I.words[2] + 26, easeInOut);
	return (
		<>
			<div
				style={{
					position: 'absolute',
					inset: 0,
					display: 'flex',
					flexDirection: 'column',
					alignItems: 'center',
					justifyContent: 'center',
					opacity: 1 - out,
					transform: `translateZ(${90 + out * 260}px) translateY(${-out * 160}px) scale(${1 - out * 0.35})`,
				}}
			>
				<div style={{display: 'flex', gap: 44, alignItems: 'center'}}>
					{words.map((w, i) => {
						const s = spr(t, I.words[i], {damping: 10, stiffness: 210, mass: 0.6});
						const isChip = i === 2;
						return (
							<div
								key={w}
								style={{
									...H1(140),
									position: 'relative',
									opacity: interpolate(t, [I.words[i], I.words[i] + 3], [0, 1], clamp),
									transform: `scale(${lerp(2.1, 1, s)})`,
									filter: s < 0.98 ? `blur(${(1 - Math.min(1, s)) * 14}px)` : undefined,
									padding: isChip ? '0.06em 0.16em 0.08em' : undefined,
								}}
							>
								{isChip && (
									<div style={{position: 'absolute', inset: 0, borderRadius: 22, background: '#fff', transform: `scaleX(${chip})`, transformOrigin: 'left'}} />
								)}
								<span style={{position: 'relative'}}>
									{w}
									{isChip && <span style={{position: 'absolute', left: 0, top: 0, color: C.bg, clipPath: `inset(-10% ${(1 - chip) * 100}% -10% 0)`}}>{w}</span>}
								</span>
							</div>
						);
					})}
				</div>
				<div style={{marginTop: 40, fontFamily: BODY, fontWeight: 600, fontSize: 34, color: 'rgba(255,255,255,0.9)', opacity: prog(t, I.sub, I.sub + 14), transform: `translateY(${(1 - prog(t, I.sub, I.sub + 18)) * 20}px)`}}>
					…where you belong, with the people who get you.
				</div>
			</div>
			{/* shock rings */}
			{[0, 1, 2].map((i) => {
				const r = prog(t, I.logo + i * 5, I.logo + 46 + i * 5);
				if (t < I.logo) return null;
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							left: 960 - 1100 * r,
							top: 400 - 1100 * r,
							width: 2200 * r,
							height: 2200 * r,
							borderRadius: '50%',
							border: `${7 - i * 2}px solid rgba(255,255,255,${0.8 - i * 0.2})`,
							opacity: 1 - r,
						}}
					/>
				);
			})}
			<div style={{position: 'absolute', left: 0, right: 0, top: 285, display: 'flex', flexDirection: 'column', alignItems: 'center', transform: 'translateZ(70px)'}}>
				<div
					style={{
						position: 'relative',
						width: 230,
						height: 230,
						borderRadius: lerp(115, 64, prog(t, I.logo + 10, I.logo + 34)),
						background: '#fff',
						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',
						transform: `scale(${burst}) rotate(${(1 - burst) * -40}deg)`,
						boxShadow: `0 30px 80px ${C.shadow}`,
						opacity: t >= I.logo ? 1 : 0,
					}}
				>
					<Clyde size={145} color={C.bg} style={{transform: `translateY(${Math.sin(t / 9) * 3}px)`}} />
					{[0, 1, 2, 3].map((i) => {
						const sp = spr(t, I.logo + 14 + i * 4, {damping: 12});
						const ang = (i / 4) * Math.PI * 2 + 0.6;
						return (
							<Sparkle
								key={i}
								size={[34, 22, 28, 18][i]}
								color={[C.yellow, C.green, '#fff', C.fuchsia][i]}
								style={{position: 'absolute', left: 115 + Math.cos(ang) * 165 * sp - 15, top: 115 + Math.sin(ang) * 165 * sp - 15, transform: `scale(${sp}) rotate(${t * 2}deg)`}}
							/>
						);
					})}
				</div>
				<div style={{display: 'flex', marginTop: 40, height: 140, alignItems: 'center'}}>
					{'DISCORD'.split('').map((ch, i) => {
						const p = prog(t, I.wordmark + i * 2.5, I.wordmark + 20 + i * 2.5);
						return (
							<span key={i} style={{...H1(140), display: 'inline-block', opacity: p, transform: `translateY(${(1 - p) * 60}px) scale(${lerp(0.6, 1, p)})`}}>
								{ch}
							</span>
						);
					})}
				</div>
				<Reveal text="GROUP CHAT THAT'S ALL FUN & GAMES" f={t} start={I.tagline} stagger={2.2} hl={['FUN', 'GAMES']} align="center" style={{...H1(40), marginTop: 30}} />
			</div>
		</>
	);
};

/* ================================================================ 2. HERO */
export const Hero: React.FC<{f: number}> = ({f}) => {
	const H = CUES.hero;
	const t = f - STATIONS.hero.arrive;
	return (
		<>
			<div style={{position: 'absolute', left: 0, right: 0, top: 70, display: 'flex', flexDirection: 'column', alignItems: 'center', transform: 'translateZ(120px)'}}>
				<Reveal text="YOUR PLACE TO TALK" f={t} start={H.title} stagger={4} hl={['TALK']} align="center" style={H1(92)} />
				<div style={{height: 22}} />
				<Body f={t} start={H.title + 16} w={1200} size={27} align="center">
					From school clubs to gaming squads to worldwide art communities — talk every day and hang out more often.
				</Body>
			</div>
			<div style={{position: 'absolute', inset: 0, transformStyle: 'preserve-3d'}}>
				<div style={{position: 'absolute', left: 120, top: 330, transformOrigin: '50% 0%', transform: `translateY(${rise(t, H.mac)}px) scale(0.6) rotateX(3deg)`}}>
					<MacBook>
						<DesktopShell
							rail={<ServerRail f={t} selected={0} badges={{2: 4, 4: 12}} />}
							sidebar={<ChannelSidebar f={t} rows={MAIN_ROWS} />}
							main={
								<>
									<ChatHeader name="general" topic="the place to hang out ✨ be nice, have fun" />
									<div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', overflow: 'hidden'}}>
										<Msg f={t} u="rio" time="Today at 9:02 PM">
											just dropped the new map pack in <Mention># announcements</Mention> 🗺️
										</Msg>
										<Msg f={t} u="jun" time="Today at 9:05 PM" reactions={[{e: '😂', n: 4}]}>
											finally, my squad has been waiting all week
										</Msg>
										<Msg f={t} u="luna" time="Today at 9:12 PM">
											who's up for some games tonight?? 🎮
										</Msg>
										<Msg f={t} u="kai" reactions={[{e: '🔥', n: 6, me: true}, {e: '🙌', n: 3}]}>
											me!! just finished my homework
										</Msg>
										<Msg f={t} u="nova" at={H.msg} reactions={[{e: '🎉', n: 12, me: true, at: H.react[0]}, {e: '💜', n: 8, at: H.react[1]}]}>
											Server just hit 10,000 members!! thank you all 💜
										</Msg>
									</div>
									<Typing f={t} text="zed" />
									<InputBar f={t} placeholder="Message #general" />
								</>
							}
							members={<MemberList groups={MEMBERS} />}
						/>
					</MacBook>
				</div>
				<div style={{position: 'absolute', left: 1390, top: 410, transformOrigin: '0 0', transform: `translateY(${rise(t, H.phoneR, 800) + Math.sin(t / 30) * 8}px) scale(0.66) rotateY(-10deg) rotateZ(2deg)`}}>
					<IPhone>
						<MobileHome f={t} />
					</IPhone>
				</div>
				<div style={{position: 'absolute', left: 250, top: 480, transformOrigin: '0 0', transform: `translateY(${rise(t, H.phoneL, 800) + Math.sin(t / 28 + 2) * 8}px) scale(0.58) rotateY(14deg) rotateZ(-4deg)`}}>
					<IPhone frame="black">
						<MobileChat title="general" sub="Pixel Party" input={<MobileInput f={t} />}>
							<Msg f={t} u="ava" scale={0.9}>
								look what I made 👀
							</Msg>
							<div style={{margin: '4px 16px 8px 70px', height: 210, borderRadius: 12, background: `linear-gradient(135deg, ${C.fuchsia}, ${C.blurple})`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
								<Emoji e="🎨" size={90} />
							</div>
							<Msg f={t} u="rio" scale={0.9} reactions={[{e: '😍', n: 9, me: true}]}>
								that's insane omg
							</Msg>
						</MobileChat>
					</IPhone>
				</div>
			</div>
			<Card f={t} at={H.online} x={1500} y={330} float={1} radius={999}>
				<div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '14px 24px'}}>
					<div style={{width: 13, height: 13, borderRadius: 7, background: C.online, boxShadow: `0 0 0 5px rgba(35,165,90,0.2)`}} />
					<span style={{fontWeight: 800, fontSize: 22}}>1,248 online</span>
				</div>
			</Card>
			<Card f={t} at={H.joined} x={80} y={400} float={2}>
				<div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '12px 20px 12px 12px'}}>
					<Avatar u="nova" size={44} />
					<div style={{lineHeight: 1.2}}>
						<div style={{fontWeight: 800, fontSize: 19}}>nova joined</div>
						<div style={{fontSize: 15, color: '#5C5E66', display: 'flex', alignItems: 'center', gap: 5}}>
							<Icon name="speaker" size={15} color="#5C5E66" /> Lounge
						</div>
					</div>
				</div>
			</Card>
		</>
	);
};

/* ================================================================ 3. SERVERS + CHAT (one MacBook, camera pans across it) */
export const AppStation: React.FC<{f: number}> = ({f}) => {
	const S = CUES.servers;
	const Ch = CUES.chat;
	const t = f - STATIONS.app.arrive;
	const tc = f - CHAT_ARRIVE;
	const typed = 'gg everyone, same time tomorrow?';
	const tn = Math.floor(interpolate(tc, [Ch.typeFrom, Ch.typeTo], [0, typed.length], clamp));
	const joined = t >= S.click;
	return (
		<>
			<div style={{position: 'absolute', inset: 0, transformStyle: 'preserve-3d'}}>
				<div style={{position: 'absolute', left: 418, top: 190, transformOrigin: '0 0', transform: `translateY(${rise(t, S.mac, 600)}px) scale(0.74)`}}>
					<MacBook>
						<DesktopShell
							rail={<ServerRail f={t} start={S.rail} selected={0} morph={prog(t, S.rail + 34, S.rail + 46)} badges={{4: 12, 6: 3}} />}
							sidebar={<ChannelSidebar f={t} rows={MAIN_ROWS} start={S.rows} />}
							main={
								<>
									<ChatHeader name="general" topic="the place to hang out ✨ be nice, have fun" />
									<div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', overflow: 'hidden'}}>
										<Msg f={tc} u="kai" time="Today at 9:30 PM">
											ok who's carrying tonight
										</Msg>
										<Msg f={tc} u="luna">
											not me, I'm still recovering from last night 😭
										</Msg>
										<Msg f={tc} u="zed" at={Ch.msgs[0]} h={150} reply={{u: 'luna', text: "not me, I'm still recovering…"}} reactions={[{e: '😂', n: 7, at: Ch.reacts[0]}, {e: '💀', n: 4, at: Ch.reacts[1]}]}>
											skill issue tbh
										</Msg>
										<Msg f={tc} u="ava" at={Ch.msgs[1]} h={360} reactions={[{e: '🔥', n: 23, me: true, at: Ch.reacts[2]}, {e: '🏆', n: 11, at: Ch.reacts[3]}, {e: '👏', n: 6, at: Ch.reacts[4]}]}>
											clip of the year incoming 👇
											<div style={{marginTop: 8, width: 400, height: 225, borderRadius: 10, overflow: 'hidden', position: 'relative', containerType: 'inline-size'}}>
												<GameScene f={f} />
												<div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
													<div style={{width: 64, height: 64, borderRadius: '50%', background: 'rgba(0,0,0,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
														<svg width="28" height="28" viewBox="0 0 24 24">
															<path d="M7 4l13 8-13 8z" fill="#fff" />
														</svg>
													</div>
												</div>
											</div>
										</Msg>
										<Msg f={tc} u="nova" at={Ch.msgs[2]} h={130} mention>
											<Mention>@everyone</Mention> game night starts in 10 — grab a seat in 🔊 Lounge
										</Msg>
										<Msg f={tc} u="you" at={Ch.send + 2} h={90}>
											{typed}
										</Msg>
									</div>
									<Typing f={tc} text={tc < Ch.typeFrom ? 'kai.exe and mila' : 'you'} />
									<InputBar f={tc} placeholder="Message #general" text={tc >= Ch.typeFrom && tc < Ch.send ? typed.slice(0, tn) : undefined} />
								</>
							}
							members={<MemberList groups={MEMBERS} />}
						/>
					</MacBook>
				</div>
			</div>
			{/* servers copy (left of the laptop) */}
			<div style={{position: 'absolute', left: -230, top: 250, width: 640, transform: 'translateZ(120px)'}}>
				<Eyebrow f={t} start={S.eyebrow} num="01" label="Servers & Channels" icon="users" />
				<div style={{height: 30}} />
				<Reveal text={'A HOME FOR\nEVERY SQUAD'} f={t} start={S.title} stagger={4} hl={['SQUAD']} style={H1(66)} />
				<div style={{height: 26}} />
				<Body f={t} start={S.title + 18} w={560} size={24}>
					Invite-only spaces for your people. Organise topics into channels and drop into voice when you're free.
				</Body>
			</div>
			<Card f={t} at={S.card} x={1030} y={130} float={0}>
				<div style={{width: 340}}>
					<div style={{height: 80, background: `linear-gradient(120deg, ${C.blurple}, ${C.fuchsia})`}} />
					<div style={{padding: '0 20px 20px', marginTop: -32}}>
						<div style={{width: 64, height: 64, borderRadius: 18, background: 'linear-gradient(135deg, #5865F2, #8C54FF)', border: '5px solid #fff', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
							<Emoji e="🎮" size={32} />
						</div>
						<div style={{fontWeight: 900, fontSize: 24, marginTop: 8}}>Pixel Party</div>
						<div style={{display: 'flex', gap: 14, fontSize: 15, color: '#5C5E66', marginTop: 4}}>
							<span>
								<span style={{color: C.online}}>●</span> 1,248 Online
							</span>
							<span>● 10,000 Members</span>
						</div>
						<div
							style={{
								marginTop: 14,
								height: 44,
								borderRadius: 10,
								background: joined ? C.ink : C.online,
								color: '#fff',
								display: 'flex',
								alignItems: 'center',
								justifyContent: 'center',
								gap: 8,
								fontWeight: 800,
								fontSize: 17,
								transform: `scale(${t >= S.click - 2 && t < S.click + 5 ? 0.95 : 1})`,
							}}
						>
							{joined ? (
								<>
									<Icon name="check" size={18} color={C.green} /> Joined
								</>
							) : (
								'Join Server'
							)}
						</div>
					</div>
				</div>
			</Card>
			<Cursor
				t={t}
				path={[
					{t: S.cursorIn, x: 1290, y: 640},
					{t: S.click - 4, x: 1192, y: 352},
					{t: S.click + 10, x: 1202, y: 372},
				]}
				clicks={[S.click]}
				z={242}
			/>
			{/* chat copy (right of the laptop) */}
			<div style={{position: 'absolute', left: 1730, top: 270, width: 560, transform: 'translateZ(120px)'}}>
				<Eyebrow f={tc} start={Ch.eyebrow} num="02" label="Text Chat" icon="chat" />
				<div style={{height: 30}} />
				<Reveal text={'CHAT THAT\nKEEPS UP'} f={tc} start={Ch.title} stagger={4} hl={['KEEPS', 'UP']} style={H1(62)} />
				<div style={{height: 26}} />
				<Body f={tc} start={Ch.title + 18} w={500} size={23}>
					Replies, threads, reactions, GIFs and clips — conversation flows as fast as your friends do.
				</Body>
			</div>
			<Card f={tc} at={Ch.emojiBar} x={1290} y={120} float={1} radius={999}>
				<div style={{display: 'flex', gap: 10, padding: '10px 18px', alignItems: 'center'}}>
					{['😂', '🔥', '💜', '👀', '🎉'].map((e, i) => (
						<Emoji key={e} e={e} size={38} style={{transform: `translateY(${Math.sin((tc + i * 8) / 8) * 4}px)`}} />
					))}
				</div>
			</Card>
		</>
	);
};

/* ================================================================ 4. VOICE */
const VoiceGrid: React.FC<{t: number}> = ({t}) => {
	const V = CUES.voice;
	const people: UserKey[] = ['nova', 'kai', 'mila', 'luna', 'zed', 'you'];
	return (
		<div style={{position: 'absolute', inset: 0, background: '#0E0F12', fontFamily: BODY, color: C.text, display: 'flex', flexDirection: 'column'}}>
			<div style={{padding: '62px 18px 10px', display: 'flex', alignItems: 'center', gap: 10}}>
				<Icon name="chevron" size={26} color={C.muted} />
				<div style={{flex: 1, lineHeight: 1.15}}>
					<div style={{fontWeight: 800, fontSize: 19, display: 'flex', alignItems: 'center', gap: 6}}>
						<Icon name="speaker" size={18} color={C.muted} /> Lounge
					</div>
					<div style={{fontSize: 13, color: C.faint}}>Pixel Party · 6 connected</div>
				</div>
			</div>
			<div style={{flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, padding: '6px 10px'}}>
				{people.map((u, i) => {
					const s = spr(t, V.tiles + i * V.tileStep, {damping: 13});
					const sp = u === 'you' ? 0 : talk(t, i);
					return (
						<div
							key={u}
							style={{
								borderRadius: 16,
								background: `linear-gradient(160deg, ${USERS[u].g[0]}33, #1E1F22 70%)`,
								display: 'flex',
								flexDirection: 'column',
								alignItems: 'center',
								justifyContent: 'center',
								gap: 10,
								transform: `scale(${s})`,
								boxShadow: sp > 0.05 ? `inset 0 0 0 3px rgba(35,165,90,${sp})` : undefined,
							}}
						>
							<Avatar u={u} size={78} speaking={sp} />
							<div style={{fontWeight: 700, fontSize: 15}}>{USERS[u].name}</div>
						</div>
					);
				})}
			</div>
			<div style={{background: '#1E1F22', borderRadius: '26px 26px 0 0', padding: '18px 18px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
				{(['video', 'mic', 'speaker', 'screen'] as const).map((n) => (
					<div key={n} style={{width: 56, height: 56, borderRadius: 28, background: '#2B2D31', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
						<Icon name={n} size={26} color="#fff" />
					</div>
				))}
				<div style={{width: 56, height: 56, borderRadius: 28, background: C.dnd, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
					<Icon name="hangup" size={28} color="#fff" />
				</div>
			</div>
		</div>
	);
};

export const Voice: React.FC<{f: number}> = ({f}) => {
	const V = CUES.voice;
	const t = f - STATIONS.voice.arrive;
	const bars = new Array(44).fill(0).map((_, i) => Math.abs(Math.sin(t * 0.21 + i * 0.6) * Math.sin(t * 0.09 + i * 0.25)) * (0.4 + 0.6 * Math.abs(Math.sin(i * 0.3))));
	const rows: Row[] = [
		{type: 'cat', label: 'Voice Channels'},
		{
			type: 'voice',
			name: 'Lounge',
			active: true,
			users: [
				{u: 'nova', speaking: talk(t, 0)},
				{u: 'kai', speaking: talk(t, 1)},
				{u: 'mila', muted: true},
				{u: 'luna', speaking: talk(t, 3)},
				{u: 'zed', speaking: talk(t, 4)},
				{u: 'you'},
			],
			userStart: [-200, -200, ...V.joins],
		},
		{type: 'voice', name: 'Gaming', users: [{u: 'jun', live: true}, {u: 'rio', video: true}]},
		{type: 'voice', name: 'Study Room', users: [{u: 'ava'}]},
		{type: 'voice', name: 'AFK'},
	];
	return (
		<>
			<div style={{position: 'absolute', left: 860, top: 390, width: 1000, height: 300, display: 'flex', alignItems: 'center', gap: 9, opacity: 0.35 * prog(t, -10, 20), transform: 'translateZ(-40px)'}}>
				{bars.map((v, i) => (
					<div key={i} style={{flex: 1, height: 20 + v * 280, borderRadius: 10, background: '#fff'}} />
				))}
			</div>
			<div style={{position: 'absolute', left: 110, top: 250, width: 720, transform: 'translateZ(120px)'}}>
				<Eyebrow f={t} start={V.eyebrow} num="03" label="Voice Channels" icon="speaker" />
				<div style={{height: 32}} />
				<Reveal text={'HOP IN.\nHANG OUT.'} f={t} start={V.title} stagger={5} hl={['HANG', 'OUT']} style={H1(96)} />
				<div style={{height: 28}} />
				<Body f={t} start={V.title + 18} w={600}>
					Voice channels are always on. No calls, no scheduling — just drop in when you're free.
				</Body>
				<div style={{display: 'flex', gap: 14, marginTop: 34}}>
					{[
						{x: 'Crystal-clear audio', i: 'headphones' as const},
						{x: 'Noise suppression', i: 'mic' as const},
					].map((c, i) => (
						<div key={c.x} style={{transform: `scale(${spr(t, V.title + 30 + i * 6, {damping: 13})})`, display: 'flex', alignItems: 'center', gap: 10, padding: '12px 20px', borderRadius: 999, background: '#fff', color: C.ink, fontFamily: BODY, fontWeight: 800, fontSize: 20, boxShadow: `0 16px 40px ${C.shadow}`}}>
							<Icon name={c.i} size={22} color={C.bg} />
							{c.x}
						</div>
					))}
				</div>
			</div>
			<div style={{position: 'absolute', inset: 0, transformStyle: 'preserve-3d'}}>
				<div style={{position: 'absolute', left: 900, top: 130, transformOrigin: '0 0', transform: `translateY(${rise(t, V.phoneA, 900) + Math.sin(t / 30) * 8}px) scale(0.92) rotateY(10deg) rotateZ(-3deg)`}}>
					<IPhone frame="black">
						<div style={{position: 'absolute', inset: 0, background: C.side, fontFamily: BODY, color: C.text, paddingTop: 54, display: 'flex', flexDirection: 'column'}}>
							<div style={{transform: 'scale(1.08)', transformOrigin: 'top left', width: '92.6%', flex: 1, display: 'flex', flexDirection: 'column'}}>
								<ChannelSidebar f={t} rows={rows} banner={false} />
							</div>
						</div>
					</IPhone>
				</div>
				<div style={{position: 'absolute', left: 1340, top: 90, transformOrigin: '0 0', transform: `translateY(${rise(t, V.phoneB, 900) + Math.sin(t / 30 + 1.5) * 8}px) scale(0.98) rotateY(-10deg) rotateZ(3deg)`}}>
					<IPhone>
						<VoiceGrid t={t} />
					</IPhone>
				</div>
			</div>
			<Card f={t} at={V.callout} x={720} y={780} float={1}>
				<div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '12px 20px 12px 12px'}}>
					<Avatar u="luna" size={44} />
					<div style={{lineHeight: 1.2}}>
						<div style={{fontWeight: 800, fontSize: 19}}>luna joined Lounge</div>
						<div style={{fontSize: 15, color: C.online, fontWeight: 700}}>● Voice Connected</div>
					</div>
				</div>
			</Card>
		</>
	);
};

/* ================================================================ 5. GO LIVE + EVENTS */
const LiveBadge: React.FC<{scale?: number}> = ({scale = 1}) => (
	<span style={{background: C.dnd, color: '#fff', fontWeight: 900, fontSize: 13 * scale, padding: `${3 * scale}px ${7 * scale}px`, borderRadius: 5 * scale, letterSpacing: '0.05em'}}>LIVE</span>
);

export const Live: React.FC<{f: number}> = ({f}) => {
	const L = CUES.live;
	const t = f - STATIONS.live.arrive;
	const viewers = Math.floor(interpolate(t, [0, 150], [212, 1284], clamp));
	const q = t >= L.click4k ? 2 : 1;
	const fps = t >= L.click60 ? 1 : 0;
	const going = t >= L.interested;
	const interested = Math.floor(interpolate(t, [L.event, 150], [1180, 2481], clamp)) + (going ? 1 : 0);
	const rows: Row[] = [
		{type: 'cat', label: 'Text Channels'},
		{type: 'ch', name: 'general'},
		{type: 'ch', name: 'clips-and-highlights', unread: true},
		{type: 'cat', label: 'Voice Channels'},
		{type: 'voice', name: 'Lounge', users: [{u: 'nova'}, {u: 'mila', muted: true}]},
		{
			type: 'voice',
			name: 'Gaming',
			active: true,
			users: [
				{u: 'kai', live: true, speaking: talk(t, 1)},
				{u: 'luna', video: true, speaking: talk(t, 3)},
				{u: 'zed', video: true, speaking: talk(t, 4)},
				{u: 'jun', speaking: talk(t, 5)},
				{u: 'you'},
			],
		},
	];
	const chip = (on: boolean): React.CSSProperties => ({
		flex: 1,
		textAlign: 'center',
		padding: '8px 0',
		borderRadius: 8,
		fontWeight: 800,
		fontSize: 16,
		background: on ? C.bg : '#EBEDEF',
		color: on ? '#fff' : C.ink,
	});
	return (
		<>
			<div style={{position: 'absolute', left: 0, right: 0, top: 56, display: 'flex', flexDirection: 'column', alignItems: 'center', transform: 'translateZ(120px)'}}>
				<Eyebrow f={t} start={L.eyebrow} num="04" label="Video, Go Live & Events" icon="video" />
				<div style={{height: 24}} />
				<Reveal text="STREAM. SHARE. GO LIVE." f={t} start={L.title} stagger={4} hl={['LIVE']} align="center" style={H1(84)} />
			</div>
			<div style={{position: 'absolute', inset: 0, transformStyle: 'preserve-3d'}}>
				<div style={{position: 'absolute', left: 900 - 840, top: 300, transformOrigin: '50% 0%', transform: `translateY(${rise(t, L.mac)}px) scale(0.62) rotateX(3deg)`}}>
					<MacBook>
						<DesktopShell
							rail={<ServerRail f={t} selected={0} />}
							sidebar={<ChannelSidebar f={t} rows={rows} voice="Gaming" />}
							main={
								<div style={{position: 'absolute', inset: 0, background: '#000', display: 'flex', flexDirection: 'column'}}>
									<div style={{height: 54, display: 'flex', alignItems: 'center', gap: 10, padding: '0 18px'}}>
										<Icon name="speaker" size={22} color={C.muted} />
										<span style={{fontWeight: 800, fontSize: 17}}>Gaming</span>
										<LiveBadge />
										<span style={{color: C.muted, fontSize: 15, display: 'flex', alignItems: 'center', gap: 6}}>
											<Icon name="eye" size={18} color={C.muted} /> {viewers.toLocaleString('en-US')}
										</span>
									</div>
									<div style={{flex: 1, display: 'flex', gap: 10, padding: '0 14px'}}>
										<div style={{flex: 1, position: 'relative', borderRadius: 12, overflow: 'hidden', containerType: 'inline-size', boxShadow: `inset 0 0 0 3px rgba(35,165,90,${talk(t, 1)})`}}>
											<GameScene f={f} />
											<div style={{position: 'absolute', left: 12, bottom: 12, background: 'rgba(0,0,0,0.65)', borderRadius: 6, padding: '4px 10px', fontSize: 14, fontWeight: 700, display: 'flex', gap: 8, alignItems: 'center'}}>
												<LiveBadge scale={0.85} /> kai.exe — Neon Drift · {q === 2 ? '4K' : '1080p'} {fps ? '60' : '30'}FPS
											</div>
										</div>
										<div style={{width: 250, display: 'flex', flexDirection: 'column', gap: 10}}>
											{(['luna', 'zed', 'jun'] as UserKey[]).map((u, i) => (
												<CamTile key={u} f={t} u={u} cam={u !== 'jun'} seed={i} speaking={talk(t, [3, 4, 5][i])} scale={0.7} style={{flex: 1}} />
											))}
										</div>
									</div>
									<div style={{padding: '14px 0 18px'}}>
										<CallControls f={t} scale={0.9} />
									</div>
								</div>
							}
						/>
					</MacBook>
				</div>
				<div style={{position: 'absolute', left: 1450, top: 360, transformOrigin: '0 0', transform: `translateY(${rise(t, L.phone, 900) + Math.sin(t / 30) * 8}px) scale(0.72) rotateY(-12deg) rotateZ(2deg)`}}>
					<IPhone>
						<MobileChat title="Gaming" sub="Watching kai.exe" input={<MobileInput f={t} placeholder="Message #Gaming" />}>
							<div style={{position: 'absolute', top: 112, left: 0, right: 0, height: 230, containerType: 'inline-size'}}>
								<GameScene f={f} />
								<div style={{position: 'absolute', left: 10, top: 10}}>
									<LiveBadge scale={0.9} />
								</div>
							</div>
							<Msg f={t} u="luna" at={30} h={90} scale={0.85}>
								that drift was CLEAN 😮
							</Msg>
							<Msg f={t} u="zed" at={70} h={90} scale={0.85} reactions={[{e: '🏎️', n: 5, at: 90}]}>
								new pb incoming
							</Msg>
						</MobileChat>
					</IPhone>
				</div>
			</div>
			<Card f={t} at={L.picker} x={70} y={440} float={0}>
				<div style={{padding: '16px 20px', width: 300}}>
					<div style={{display: 'flex', alignItems: 'center', gap: 10, fontWeight: 900, fontSize: 19}}>
						<Icon name="screen" size={24} color={C.bg} /> Stream Quality
					</div>
					<div style={{display: 'flex', gap: 8, marginTop: 12}}>
						{['720p', '1080p', '4K'].map((x, i) => (
							<div key={x} style={chip(i === q)}>
								{x}
							</div>
						))}
					</div>
					<div style={{display: 'flex', gap: 8, marginTop: 8}}>
						{['30 FPS', '60 FPS'].map((x, i) => (
							<div key={x} style={chip(i === fps)}>
								{x}
							</div>
						))}
					</div>
				</div>
			</Card>
			<Card f={t} at={L.event} x={70} y={660} float={2}>
				<div style={{width: 540}}>
					<div style={{height: 100, position: 'relative', background: `linear-gradient(120deg, ${C.yellow}, #FF8A4C 45%, ${C.fuchsia})`}}>
						<Emoji e="🕹️" size={74} style={{position: 'absolute', right: 26, top: 12, transform: 'rotate(12deg)'}} />
						<div style={{position: 'absolute', left: 18, top: 16, background: 'rgba(0,0,0,0.35)', color: '#fff', borderRadius: 999, padding: '4px 12px', fontSize: 13, fontWeight: 800, display: 'flex', gap: 6, alignItems: 'center'}}>
							<Icon name="stage" size={15} color="#fff" /> STAGE EVENT
						</div>
					</div>
					<div style={{padding: '14px 22px 18px'}}>
						<div style={{display: 'flex', alignItems: 'center', gap: 8, color: '#C27C0E', fontWeight: 800, fontSize: 15}}>
							<Icon name="calendar" size={17} color="#C27C0E" /> FRI, NOV 14 · 8:00 PM
						</div>
						<div style={{fontWeight: 900, fontSize: 26, marginTop: 4}}>Community Game Night</div>
						<div style={{display: 'flex', alignItems: 'center', gap: 12, marginTop: 12}}>
							<div style={{display: 'flex'}}>
								{(['nova', 'kai', 'luna', 'zed'] as UserKey[]).map((u, i) => (
									<Avatar key={u} u={u} size={32} style={{marginLeft: i ? -10 : 0, boxShadow: '0 0 0 3px #fff', borderRadius: '50%'}} />
								))}
							</div>
							<span style={{color: '#5C5E66', fontSize: 16, fontWeight: 700, flex: 1}}>{interested.toLocaleString('en-US')} interested</span>
							<div
								style={{
									width: 150,
									height: 42,
									borderRadius: 10,
									background: going ? C.online : C.bg,
									color: '#fff',
									fontWeight: 800,
									fontSize: 16,
									display: 'flex',
									gap: 6,
									alignItems: 'center',
									justifyContent: 'center',
									transform: `scale(${t >= L.interested - 2 && t < L.interested + 5 ? 0.94 : 1})`,
								}}
							>
								<Icon name={going ? 'check' : 'bell'} size={16} color="#fff" />
								{going ? 'Going!' : 'Interested'}
							</div>
						</div>
					</div>
				</div>
			</Card>
			<Cursor
				t={t}
				path={[
					{t: L.picker + 10, x: 470, y: 760},
					{t: L.click4k - 4, x: 322, y: 522},
					{t: L.click60 - 4, x: 300, y: 566},
					{t: L.interested - 6, x: 528, y: 880},
					{t: L.interested + 14, x: 540, y: 896},
				]}
				clicks={[L.click4k, L.click60, L.interested]}
				z={242}
			/>
		</>
	);
};

/* ================================================================ 6. EVERY DEVICE */
export const Devices: React.FC<{f: number}> = ({f}) => {
	const D = CUES.devices;
	const t = f - STATIONS.devices.arrive;
	const platforms = ['macOS', 'Windows', 'Linux', 'iOS', 'Android', 'Web', 'Xbox', 'PlayStation'];
	const msg = "omw home, catch you all on mobile 📱";
	const tn = Math.floor(interpolate(t, [D.typeFrom, D.typeTo], [0, msg.length], clamp));
	const pulse = prog(t, D.send, D.arrive, easeInOut);
	return (
		<>
			<div style={{position: 'absolute', left: 0, right: 0, top: 56, display: 'flex', flexDirection: 'column', alignItems: 'center', transform: 'translateZ(120px)'}}>
				<Eyebrow f={t} start={D.eyebrow} num="05" label="Cross-platform" icon="globe" />
				<div style={{height: 22}} />
				<Reveal text="ON EVERY DEVICE" f={t} start={D.title} stagger={4} hl={['EVERY', 'DEVICE']} align="center" style={H1(88)} />
				<div style={{display: 'flex', gap: 12, marginTop: 26}}>
					{platforms.map((p, i) => (
						<div key={p} style={{transform: `scale(${spr(t, D.chips + i * D.chipStep, {damping: 13})})`, padding: '8px 18px', borderRadius: 999, background: '#fff', color: C.ink, fontFamily: BODY, fontWeight: 800, fontSize: 19, boxShadow: `0 10px 26px ${C.shadow}`}}>
							{p}
						</div>
					))}
				</div>
			</div>
			<div style={{position: 'absolute', inset: 0, transformStyle: 'preserve-3d'}}>
				<div style={{position: 'absolute', left: 30, top: 440, transformOrigin: '0 0', transform: `translateY(${rise(t, D.rise[0], 800)}px) scale(0.5) rotateY(18deg)`}}>
					<IPad>
						<div style={{position: 'absolute', inset: 0, display: 'flex', background: '#000'}}>
							<div style={{flex: 1, position: 'relative', containerType: 'inline-size'}}>
								<GameScene f={f} />
							</div>
							<div style={{width: 300, display: 'flex', flexDirection: 'column', gap: 8, padding: 8, background: '#0E0F12'}}>
								{(['luna', 'zed', 'nova'] as UserKey[]).map((u, i) => (
									<CamTile key={u} f={t} u={u} seed={i} speaking={talk(t, i + 2)} style={{flex: 1}} />
								))}
							</div>
						</div>
					</IPad>
				</div>
				<div style={{position: 'absolute', left: 880 - 840 * 0.62, top: 370, transformOrigin: '0 0', transform: `translateY(${rise(t, D.rise[1], 800)}px) scale(0.62)`}}>
					<MacBook>
						<DesktopShell
							rail={<ServerRail f={t} selected={0} />}
							sidebar={<ChannelSidebar f={t} rows={MAIN_ROWS} />}
							main={
								<>
									<ChatHeader name="general" topic="the place to hang out ✨" />
									<div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', overflow: 'hidden'}}>
										<Msg f={t} u="kai">gg that was insane</Msg>
										<Msg f={t} u="nova">same time tomorrow? 🙌</Msg>
										<Msg f={t} u="luna" at={D.arrive} h={110} reactions={[{e: '💜', n: 3, at: D.arrive + 10, me: true}]}>
											{msg}
										</Msg>
									</div>
									<InputBar f={t} placeholder="Message #general" />
								</>
							}
						/>
					</MacBook>
				</div>
				<div style={{position: 'absolute', left: 1390, top: 380, transformOrigin: '0 0', transform: `translateY(${rise(t, D.rise[2], 800) + Math.sin(t / 30) * 6}px) scale(0.62) rotateY(-14deg) rotateZ(-3deg)`}}>
					<IPhone frame="black">
						<MobileHome f={t} />
					</IPhone>
				</div>
				<div style={{position: 'absolute', left: 1600, top: 430, transformOrigin: '0 0', transform: `translateY(${rise(t, D.rise[3], 800) + Math.sin(t / 30 + 1) * 6}px) scale(0.62) rotateY(-14deg) rotateZ(4deg)`}}>
					<IPhone>
						<MobileChat title="general" sub="Pixel Party" input={<MobileInput f={t} text={t >= D.typeFrom && t < D.send ? msg.slice(0, tn) : undefined} />}>
							<Msg f={t} u="kai" scale={0.85}>gg that was insane</Msg>
							<Msg f={t} u="nova" scale={0.85}>same time tomorrow? 🙌</Msg>
							<Msg f={t} u="luna" scale={0.85} at={D.send} h={110}>
								{msg}
							</Msg>
						</MobileChat>
					</IPhone>
				</div>
				{t >= D.send && t < D.arrive + 16 && (
					<svg width="1920" height="1080" style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
						<path
							d="M1760 880 C 1560 600, 1320 620, 1120 790"
							stroke="#fff"
							strokeWidth="6"
							fill="none"
							strokeDasharray="900"
							strokeDashoffset={900 * (1 - pulse)}
							strokeLinecap="round"
							opacity={1 - prog(t, D.arrive, D.arrive + 16)}
						/>
					</svg>
				)}
			</div>
		</>
	);
};

/* ================================================================ 7. APPS + NITRO */
const CMDS = [
	{c: '/play', d: 'Queue a song in voice', app: 'DJ Bot', bg: C.fuchsia, e: '🎵'},
	{c: '/remind', d: 'Set a reminder for later', app: 'Remindy', bg: '#00A8FC', e: '⏰'},
	{c: '/poll', d: 'Ask the server a question', app: 'Discord', bg: C.blurple, e: '📊'},
	{c: '/giveaway', d: 'Start a giveaway', app: 'GiftBot', bg: C.green, e: '🎁'},
];
const POLL = [
	{t: 'Neon Drift', e: '🏎️', v: 46},
	{t: 'Block Party', e: '🧱', v: 31},
	{t: 'Space Pals', e: '🚀', v: 23},
];
const PERKS = [
	{t: 'Custom emoji anywhere', e: '😎'},
	{t: 'HD video & streaming', e: '📺'},
	{t: 'Bigger file uploads', e: '📁'},
	{t: 'Profile themes', e: '🎨'},
];

const NitroProfile: React.FC<{t: number}> = ({t}) => {
	const hue = (t * 1.2) % 360;
	return (
		<div style={{position: 'absolute', inset: 0, fontFamily: BODY, color: C.text, background: 'linear-gradient(180deg, #4A2C8F 0%, #2A1A5E 45%, #5A1F4F 100%)'}}>
			<div style={{height: 230, background: `linear-gradient(${120 + Math.sin(t / 30) * 30}deg, ${C.fuchsia}, ${C.blurple}, #00A8FC)`, position: 'relative', overflow: 'hidden'}}>
				{[0, 1, 2, 3, 4, 5].map((i) => (
					<Sparkle key={i} size={16 + (i % 3) * 10} color="rgba(255,255,255,0.8)" style={{position: 'absolute', left: 30 + i * 60, top: 70 + ((i * 47) % 110), transform: `rotate(${t * 2 + i * 40}deg) scale(${0.6 + 0.4 * Math.sin(t / 10 + i)})`}} />
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

export const Apps: React.FC<{f: number}> = ({f}) => {
	const P = CUES.apps;
	const t = f - STATIONS.apps.arrive;
	const typed = '/poll';
	const tn = Math.floor(interpolate(t, [P.typeFrom, P.typeTo], [0, typed.length], clamp));
	const popup = t >= P.popup && t < P.enter + 2;
	const popP = prog(t, P.popup, P.popup + 8);
	const sel = t < P.sel[0] ? 0 : t < P.sel[1] ? 1 : 2;
	const fill = prog(t, P.fillFrom, P.fillTo, easeInOut);
	const burst = prog(t, P.superReact, P.superReact + 36);
	return (
		<>
			<div style={{position: 'absolute', left: 110, top: 64, transform: 'translateZ(120px)'}}>
				<Eyebrow f={t} start={P.eyebrow} num="06" label="Apps, Activities & Nitro" icon="apps" />
				<div style={{height: 24}} />
				<Reveal text="PLAY. BUILD. LEVEL UP." f={t} start={P.title} stagger={4} hl={['LEVEL', 'UP']} style={H1(76)} />
			</div>
			<div style={{position: 'absolute', inset: 0, transformStyle: 'preserve-3d'}}>
				<div style={{position: 'absolute', left: 60, top: 270, transformOrigin: '0 0', transform: `translateY(${rise(t, P.mac, 800)}px) scale(0.66) rotateY(5deg)`}}>
					<MacBook>
						<DesktopShell
							rail={<ServerRail f={t} selected={0} />}
							sidebar={<ChannelSidebar f={t} rows={MAIN_ROWS} />}
							main={
								<>
									<ChatHeader name="general" topic="the place to hang out ✨ be nice, have fun" />
									<div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', overflow: 'hidden'}}>
										<Msg f={t} u="luna">ok but what are we playing tonight</Msg>
										<Msg f={t} u="kai">let's vote 🗳️</Msg>
										<Msg f={t} u="you" at={P.poll} h={420}>
											<div style={{marginTop: 6, width: 520, background: C.side, borderRadius: 12, padding: '16px 18px', border: '1px solid #3F4147'}}>
												<div style={{fontWeight: 800, fontSize: 19, color: '#fff'}}>What should we play tonight?</div>
												<div style={{fontSize: 13.5, color: C.faint, marginTop: 2, marginBottom: 12}}>Select one answer</div>
												{POLL.map((o, i) => {
													const v = Math.round(o.v * fill);
													return (
														<div key={o.t} style={{position: 'relative', height: 48, borderRadius: 8, background: '#383A40', marginBottom: 8, overflow: 'hidden', border: i === 0 && fill > 0.3 ? `2px solid ${C.blurple}` : '2px solid transparent'}}>
															<div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: `${v}%`, background: i === 0 ? 'rgba(88,101,242,0.5)' : 'rgba(255,255,255,0.08)'}} />
															<div style={{position: 'relative', display: 'flex', alignItems: 'center', gap: 10, height: '100%', padding: '0 14px', fontWeight: 700, fontSize: 17, color: C.text}}>
																<Emoji e={o.e} size={22} />
																<span style={{flex: 1}}>{o.t}</span>
																<span style={{color: C.muted}}>{v}%</span>
															</div>
														</div>
													);
												})}
												<div style={{fontSize: 13.5, color: C.faint, marginTop: 4}}>{Math.round(248 * fill)} votes · 23h left</div>
											</div>
										</Msg>
									</div>
									<div style={{position: 'relative'}}>
										{popup && (
											<div style={{position: 'absolute', left: 18, right: 18, bottom: 8, background: C.side, borderRadius: 10, padding: 8, boxShadow: '0 10px 40px rgba(0,0,0,0.5)', opacity: popP, transform: `translateY(${(1 - popP) * 20}px)`}}>
												<div style={{fontSize: 12.5, fontWeight: 800, color: C.faint, letterSpacing: '0.04em', padding: '4px 8px 8px'}}>APP COMMANDS</div>
												{CMDS.map((c, i) => (
													<div key={c.c} style={{display: 'flex', alignItems: 'center', gap: 12, padding: '10px 10px', borderRadius: 6, background: i === sel ? '#404249' : undefined}}>
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
									<Typing f={t} text="mila" />
									<InputBar f={t} placeholder="Message #general" text={t >= P.typeFrom - 2 && t < P.enter ? typed.slice(0, tn) : undefined} />
								</>
							}
						/>
					</MacBook>
				</div>
				<div style={{position: 'absolute', left: 1450, top: 150, transformOrigin: '0 0', transform: `translateY(${rise(t, P.nitro, 900) + Math.sin(t / 26) * 8}px) scale(0.86) rotateY(-10deg) rotateZ(2deg)`}}>
					<IPhone frame="blurple">
						<NitroProfile t={t} />
					</IPhone>
				</div>
			</div>
			{PERKS.map((p, i) => {
				const s = spr(t, P.perks + i * P.perkStep, {damping: 14});
				return (
					<div
						key={p.t}
						style={{
							position: 'absolute',
							left: 1110,
							top: 330 + i * 92,
							transform: `translateZ(${200 + i * 30}px) translateX(${(1 - s) * 260}px) translateY(${Math.sin((t + i * 20) / 30) * 5}px)`,
							opacity: Math.min(1, s * 1.4),
						}}
					>
						<div style={{display: 'flex', alignItems: 'center', gap: 14, padding: '12px 20px 12px 12px', borderRadius: 18, background: '#fff', color: C.ink, boxShadow: `0 16px 40px ${C.shadow}`}}>
							<div style={{width: 46, height: 46, borderRadius: 14, background: `linear-gradient(135deg, ${C.fuchsia}, ${C.bg})`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
								<Emoji e={p.e} size={26} />
							</div>
							<div style={{fontFamily: BODY, fontWeight: 800, fontSize: 20}}>{p.t}</div>
						</div>
					</div>
				);
			})}
			<div style={{position: 'absolute', left: 1820, top: 170, transform: 'translateZ(260px)'}}>
				{t >= P.superReact &&
					new Array(14).fill(0).map((_, i) => {
						const a = (i / 14) * Math.PI * 2;
						const d = 30 + burst * 140;
						return (
							<div key={i} style={{position: 'absolute', left: Math.cos(a) * d, top: Math.sin(a) * d, opacity: 1 - burst, transform: `scale(${1 - burst * 0.5})`}}>
								<Emoji e={i % 2 ? '💜' : '✨'} size={26} />
							</div>
						);
					})}
				<div style={{position: 'absolute', left: -40, top: -40, transform: `scale(${spr(t, P.superReact - 4, {damping: 8, stiffness: 200}) * (1 + 0.12 * Math.sin(t / 5))})`}}>
					<Emoji e="🔥" size={80} />
				</div>
			</div>
		</>
	);
};

/* ================================================================ 8. ROLES & SAFETY */
const ROLES = [
	{n: 'Admin', c: '#FF6B6B', m: 3},
	{n: 'Moderator', c: C.green, m: 12},
	{n: 'Artist', c: '#F47FFF', m: 48},
	{n: 'VIP', c: C.yellow, m: 120},
	{n: 'Gamer', c: '#00A8FC', m: 2310},
	{n: 'Member', c: '#A5B4FF', m: 10000},
];
const PERMS = [
	{n: 'Manage Messages', d: 'Delete or pin messages from other members.'},
	{n: 'Timeout Members', d: 'Temporarily stop members from chatting.'},
	{n: 'Kick Members', d: 'Remove members from the server.'},
	{n: 'Manage Events', d: 'Create, edit and cancel events.'},
	{n: 'Mention @everyone', d: 'Notify everyone in the server.'},
];
// toggle centres in station-local px (MacBook at 80,190 scaled 0.66; see SettingsView layout)
export const TOGGLE_POS = (i: number) => ({x: 1074, y: 354 + i * 58});

const SettingsView: React.FC<{t: number}> = ({t}) => {
	const R = CUES.roles;
	return (
		<div style={{position: 'absolute', inset: 0, display: 'flex', fontFamily: BODY, color: C.text}}>
			<div style={{width: 300, background: C.side, padding: '60px 14px 0 40px'}}>
				<div style={{fontSize: 13, fontWeight: 800, color: C.faint, letterSpacing: '0.05em', padding: '0 10px 8px'}}>PIXEL PARTY</div>
				{['Overview', 'Roles', 'Emoji', 'Stickers', 'Widget', 'Server Template'].map((n) => (
					<div key={n} style={{padding: '8px 10px', borderRadius: 6, fontSize: 16.5, fontWeight: 600, color: n === 'Roles' ? '#fff' : C.muted, background: n === 'Roles' ? '#404249' : undefined, marginBottom: 2}}>
						{n}
					</div>
				))}
				<div style={{fontSize: 13, fontWeight: 800, color: C.faint, letterSpacing: '0.05em', padding: '18px 10px 8px'}}>MODERATION</div>
				{['Safety Setup', 'AutoMod', 'Audit Log', 'Bans'].map((n) => (
					<div key={n} style={{padding: '8px 10px', borderRadius: 6, fontSize: 16.5, fontWeight: 600, color: C.muted, marginBottom: 2}}>
						{n}
					</div>
				))}
			</div>
			<div style={{flex: 1, background: C.chat, display: 'flex'}}>
				<div style={{width: 250, padding: '60px 16px 0', borderRight: '1px solid #3F4147'}}>
					<div style={{fontSize: 13, fontWeight: 800, color: C.faint, letterSpacing: '0.05em', marginBottom: 10}}>ROLES — 6</div>
					{ROLES.map((r, i) => {
						const p = prog(t, R.list + i * 3, R.list + 14 + i * 3);
						return (
							<div key={r.n} style={{display: 'flex', alignItems: 'center', gap: 10, padding: '9px 10px', borderRadius: 6, background: i === 1 ? '#404249' : undefined, marginBottom: 3, opacity: p, transform: `translateX(${(1 - p) * -20}px)`}}>
								<div style={{width: 13, height: 13, borderRadius: '50%', background: r.c}} />
								<span style={{fontWeight: 700, fontSize: 16.5, color: i === 1 ? '#fff' : C.muted, flex: 1}}>{r.n}</span>
								<span style={{fontSize: 13, color: C.faint}}>{r.m.toLocaleString('en-US')}</span>
							</div>
						);
					})}
				</div>
				<div style={{flex: 1, padding: '56px 36px 0'}}>
					<div style={{fontSize: 22, fontWeight: 800}}>
						EDIT ROLE — <span style={{color: C.green}}>Moderator</span>
					</div>
					<div style={{display: 'flex', gap: 22, marginTop: 16, borderBottom: '1px solid #3F4147'}}>
						{['Display', 'Permissions', 'Links', 'Manage Members'].map((x) => (
							<div key={x} style={{paddingBottom: 12, fontWeight: 700, fontSize: 16, color: x === 'Permissions' ? '#fff' : C.muted, borderBottom: x === 'Permissions' ? `3px solid ${C.blurple}` : '3px solid transparent'}}>
								{x}
							</div>
						))}
					</div>
					{PERMS.map((p, i) => {
						const at = R.toggles[i];
						const on = at === undefined ? 0 : prog(t, at, at + 7);
						return (
							<div key={p.n} style={{display: 'flex', alignItems: 'center', gap: 18, height: 86, borderBottom: '1px solid #3F4147'}}>
								<div style={{flex: 1}}>
									<div style={{fontWeight: 700, fontSize: 18}}>{p.n}</div>
									<div style={{fontSize: 14.5, color: C.faint, marginTop: 3}}>{p.d}</div>
								</div>
								<Toggle on={on} />
							</div>
						);
					})}
				</div>
			</div>
		</div>
	);
};

export const Roles: React.FC<{f: number}> = ({f}) => {
	const R = CUES.roles;
	const t = f - STATIONS.roles.arrive;
	const path = [{t: R.toggles[0] - 26, x: 1240, y: 760}, ...R.toggles.map((c, i) => ({t: c - 5, ...TOGGLE_POS(i)})), {t: R.toggles[3] + 14, x: TOGGLE_POS(3).x + 14, y: TOGGLE_POS(3).y + 20}];
	return (
		<>
			<div style={{position: 'absolute', inset: 0, transformStyle: 'preserve-3d'}}>
				<div style={{position: 'absolute', left: 80, top: 230, transformOrigin: '0 0', transform: `translateX(${-rise(t, R.mac, 1300)}px) scale(0.66)`}}>
					<MacBook>
						<div style={{position: 'absolute', inset: 0, background: C.chat}}>
							<SettingsView t={t} />
							<div style={{position: 'absolute', left: 0, top: 0, height: 34, display: 'flex', alignItems: 'center', padding: '0 16px', gap: 9}}>
								{['#FF5F57', '#FEBC2E', '#28C840'].map((c) => (
									<div key={c} style={{width: 13, height: 13, borderRadius: '50%', background: c}} />
								))}
							</div>
						</div>
					</MacBook>
				</div>
			</div>
			<div style={{position: 'absolute', left: 1300, top: 300, width: 600, transform: 'translateZ(120px)'}}>
				<Eyebrow f={t} start={R.eyebrow} num="07" label="Roles & Safety" icon="shield" />
				<div style={{height: 30}} />
				<Reveal text={"YOU'RE IN\nCONTROL"} f={t} start={R.title} stagger={4} hl={['CONTROL']} style={H1(80)} />
				<div style={{height: 26}} />
				<Body f={t} start={R.title + 18} w={560} size={25}>
					Custom roles, granular permissions and AutoMod keep your space safe and exactly how you like it.
				</Body>
			</div>
			<Card f={t} at={R.automod} x={720} y={120} float={0} dark>
				<div style={{width: 470, padding: '16px 18px', borderLeft: `5px solid ${C.dnd}`}}>
					<div style={{display: 'flex', alignItems: 'center', gap: 12}}>
						<Icon name="shield" size={34} color={C.blurple} />
						<div style={{lineHeight: 1.25}}>
							<div style={{fontWeight: 800, fontSize: 19}}>
								AutoMod <span style={{background: C.blurple, fontSize: 11, padding: '1px 5px', borderRadius: 4, verticalAlign: 'middle'}}>✓ APP</span>
							</div>
							<div style={{fontSize: 15, color: C.muted}}>Blocked a message in #general</div>
						</div>
					</div>
					<div style={{marginTop: 10, padding: '8px 12px', borderRadius: 8, background: 'rgba(237,66,69,0.14)', fontSize: 15, color: '#FFB3B4', fontFamily: MONO}}>
						Rule: Block spam links · Action: Timeout 10m
					</div>
				</div>
			</Card>
			<Cursor t={t} path={path} clicks={R.toggles} z={2} />
		</>
	);
};

/* ================================================================ 9. CTA (+ overview title) */
export const Cta: React.FC<{f: number; camZ: number}> = ({f, camZ}) => {
	const T = CUES.cta;
	const O = CUES.overview;
	const t = f - STATIONS.cta.arrive;
	const logo = spr(t, T.logo, {damping: 11, stiffness: 130});
	const done = t >= T.done;
	const titleO = prog(f, O.title, O.title + 16) * (1 - prog(f, O.dive, O.dive + 12)) * interpolate(camZ, [0.32, 0.5], [1, 0], clamp);
	const conf = new Array(36).fill(0).map((_, i) => ({
		a: (i / 36) * Math.PI * 2 + (i % 3) * 0.2,
		v: 260 + ((i * 53) % 220),
		c: [C.yellow, C.green, '#fff', C.fuchsia][i % 4],
		s: 14 + ((i * 7) % 16),
	}));
	const cp = prog(t, T.click, T.click + 50);
	return (
		<>
			{/* giant overview title, sized for the zoomed-out camera */}
			{titleO > 0.01 && (
				<div style={{position: 'absolute', left: -2000, right: -2000, top: 540 - 320, opacity: titleO, display: 'flex', justifyContent: 'center', transform: 'translateZ(900px)'}}>
					<Reveal text={'ALL IN\nONE PLACE.'} f={f} start={O.title} stagger={4} hl={['ONE', 'PLACE']} align="center" style={{...H1(280), lineHeight: 1.05, textShadow: `0 30px 80px ${C.shadow}`}} />
				</div>
			)}
			<div style={{position: 'absolute', left: 0, right: 0, top: 250, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 40, transform: `translateZ(90px) scale(${logo})`, opacity: t >= T.logo - 1 ? 1 : 0}}>
				<div style={{width: 180, height: 180, borderRadius: 52, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: `0 30px 80px ${C.shadow}`}}>
					<Clyde size={116} color={C.bg} style={{transform: `translateY(${Math.sin(t / 9) * 3}px)`}} />
				</div>
				<div style={{...H1(150)}}>
					{'DISCORD'.split('').map((ch, i) => {
						const p = prog(t, T.wordmark + i * 2, T.wordmark + 16 + i * 2);
						return (
							<span key={i} style={{display: 'inline-block', opacity: p, transform: `translateY(${(1 - p) * 40}px)`}}>
								{ch}
							</span>
						);
					})}
				</div>
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, top: 500, display: 'flex', justifyContent: 'center', transform: 'translateZ(60px)'}}>
				<Reveal text="IMAGINE A PLACE." f={t} start={T.line} stagger={4} hl={['PLACE']} align="center" style={H1(58)} />
			</div>
			<div style={{position: 'absolute', left: 538, top: 640, display: 'flex', gap: 24, transform: 'translateZ(40px)'}}>
				{[
					{x: done ? 'Downloading…' : 'Download for Mac', bg: '#fff', fg: C.ink, icon: (done ? 'check' : 'download') as 'check' | 'download', w: 340},
					{x: 'Open Discord in your browser', bg: C.ink, fg: '#fff', icon: 'globe' as const, w: 480},
				].map((b, i) => {
					const s = spr(t, T.buttons[i], {damping: 12});
					const press = i === 0 && t >= T.click - 2 && t < T.click + 5 ? 0.95 : 1;
					return (
						<div
							key={i}
							style={{
								width: b.w,
								height: 76,
								transform: `scale(${s * press})`,
								display: 'flex',
								alignItems: 'center',
								justifyContent: 'center',
								gap: 14,
								borderRadius: 40,
								background: b.bg,
								color: b.fg,
								fontFamily: BODY,
								fontWeight: 800,
								fontSize: 25,
								boxShadow: `0 18px 50px ${C.shadow}`,
							}}
						>
							<Icon name={b.icon} size={28} color={i === 0 && done ? C.online : b.fg} />
							{b.x}
						</div>
					);
				})}
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, top: 770, transform: 'translateZ(40px)', textAlign: 'center', fontFamily: BODY, fontWeight: 800, fontSize: 30, color: '#fff', letterSpacing: '0.08em', opacity: prog(t, T.url, T.url + 14)}}>discord.com</div>
			<Cursor
				t={t}
				path={[
					{t: T.cursorIn, x: 1240, y: 980},
					{t: T.click - 4, x: 700, y: 682},
					{t: 236, x: 712, y: 700},
				]}
				clicks={[T.click]}
				z={42}
			/>
			{t >= T.click &&
				conf.map((c, i) => (
					<Sparkle
						key={i}
						size={c.s}
						color={c.c}
						style={{
							position: 'absolute',
							left: 708 + Math.cos(c.a) * c.v * cp,
							top: 678 + Math.sin(c.a) * c.v * cp + cp * cp * 160,
							opacity: 1 - prog(t, T.click + 30, T.click + 60),
							transform: `translateZ(${60 + (i % 5) * 40}px) rotate(${t * 6 + i * 20}deg)`,
						}}
					/>
				))}
		</>
	);
};
