import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Avatar, Body, Callout, Emoji, Eyebrow, Icon, Reveal, SpaceBg, USERS, UserKey} from './primitives';
import {BODY, C, MONO, clamp, display, easeInOut, lerp, prog, spr} from './theme';
import {IPad, IPhone, MacBook} from './devices';
import {
	CallControls,
	CamTile,
	ChannelSidebar,
	ChatHeader,
	DesktopShell,
	GameScene,
	MobileChat,
	MobileInput,
	Msg,
	Row,
	ServerRail,
	Toggle,
	UserPanel,
} from './ui';

/* deterministic "who is talking" envelope */
export const talk = (f: number, seed: number) => {
	const a = Math.sin(f * 0.11 + seed * 2.3) * Math.sin(f * 0.047 + seed * 1.7);
	return interpolate(a, [0.15, 0.45], [0, 1], clamp);
};

/* ================================================================ 5. VOICE (40-50s) */
const VoiceGrid: React.FC<{f: number}> = ({f}) => {
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
				<div style={{width: 36, height: 36, borderRadius: 18, background: '#2B2D31', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
					<Icon name="users" size={20} color={C.muted} />
				</div>
			</div>
			<div style={{flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, padding: '6px 10px'}}>
				{people.map((u, i) => {
					const at = 10 + i * 6;
					const s = spr(f, at, {damping: 13});
					const sp = u === 'you' ? 0 : talk(f, i);
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
							<div style={{fontWeight: 700, fontSize: 15, display: 'flex', gap: 5, alignItems: 'center'}}>
								{USERS[u].name}
								{u === 'mila' && <Icon name="micOff" size={14} color={C.dnd} />}
							</div>
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

const VoiceSidebarPhone: React.FC<{f: number}> = ({f}) => {
	const rows: Row[] = [
		{type: 'cat', label: 'Voice Channels'},
		{
			type: 'voice',
			name: 'Lounge',
			active: true,
			users: [
				{u: 'nova', speaking: talk(f, 0)},
				{u: 'kai', speaking: talk(f, 1)},
				{u: 'mila', muted: true},
				{u: 'luna', speaking: talk(f, 3)},
				{u: 'zed', speaking: talk(f, 4)},
				{u: 'you'},
			],
			userStart: [-100, -100, 30, 60, 90, 120],
		},
		{type: 'voice', name: 'Gaming', users: [{u: 'jun', live: true}, {u: 'rio', video: true}]},
		{type: 'voice', name: 'Study Room', users: [{u: 'ava'}]},
		{type: 'voice', name: 'AFK'},
	];
	return (
		<div style={{position: 'absolute', inset: 0, background: C.side, fontFamily: BODY, color: C.text, paddingTop: 54, display: 'flex', flexDirection: 'column'}}>
			<div style={{transform: 'scale(1.08)', transformOrigin: 'top left', width: '92.6%', flex: 1, display: 'flex', flexDirection: 'column'}}>
				<ChannelSidebar f={f} rows={rows} banner={false} />
			</div>
		</div>
	);
};

export const Voice: React.FC = () => {
	const f = useCurrentFrame();
	const p1 = spr(f, 0, {damping: 16, stiffness: 70});
	const p2 = spr(f, 12, {damping: 16, stiffness: 70});
	const cam = prog(f, 0, 300, easeInOut);
	// audio bars
	const bars = new Array(48).fill(0).map((_, i) => {
		const v = Math.abs(Math.sin(f * 0.21 + i * 0.6) * Math.sin(f * 0.09 + i * 0.25)) * (0.4 + 0.6 * Math.abs(Math.sin(i * 0.3)));
		return v;
	});
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 1200} a={C.green} b={C.blurple} />
			{/* waveform behind phones */}
			<div style={{position: 'absolute', left: 860, top: 540, width: 1000, height: 300, marginTop: -150, display: 'flex', alignItems: 'center', gap: 9, opacity: 0.55 * prog(f, 10, 40)}}>
				{bars.map((v, i) => (
					<div key={i} style={{flex: 1, height: 20 + v * 280, borderRadius: 10, background: `linear-gradient(180deg, ${C.green}, ${C.blurple})`}} />
				))}
			</div>
			<div style={{position: 'absolute', left: 110, top: 250, width: 700}}>
				<Eyebrow f={f} start={4} num="03" label="Voice Channels" icon="speaker" color={C.green} />
				<div style={{height: 34}} />
				<Reveal text={'HOP IN.\nHANG OUT.'} f={f} start={10} stagger={5} hl={['HANG', 'OUT']} style={{...display(96), color: '#fff'}} hlBg={`linear-gradient(92deg, ${C.green}, #00A8FC)`} />
				<div style={{height: 30}} />
				<Body f={f} start={34} w={620}>
					Voice channels are always on. No calls, no scheduling — just drop in when you're free and pick up where you left off.
				</Body>
				<div style={{display: 'flex', gap: 14, marginTop: 36}}>
					{[
						{t: 'Crystal-clear audio', i: 'headphones' as const},
						{t: 'Noise suppression', i: 'mic' as const},
					].map((x, i) => {
						const s = spr(f, 70 + i * 8, {damping: 13});
						return (
							<div key={x.t} style={{transform: `scale(${s})`, display: 'flex', alignItems: 'center', gap: 10, padding: '12px 18px', borderRadius: 14, background: 'rgba(87,242,135,0.1)', border: '1px solid rgba(87,242,135,0.4)', fontFamily: BODY, fontWeight: 700, fontSize: 21, color: '#D7FBE3'}}>
								<Icon name={x.i} size={22} color={C.green} />
								{x.t}
							</div>
						);
					})}
				</div>
			</div>
			<div style={{position: 'absolute', inset: 0, perspective: 2000}}>
				<div
					style={{
						position: 'absolute',
						left: 900,
						top: 130,
						transformOrigin: '0 0',
						transform: `translateY(${(1 - p1) * 900 + Math.sin(f / 30) * 8}px) scale(0.92) rotateY(${lerp(16, 10, cam)}deg) rotateZ(-3deg)`,
					}}
				>
					<IPhone frame="black">
						<VoiceSidebarPhone f={f} />
					</IPhone>
				</div>
				<div
					style={{
						position: 'absolute',
						left: 1340,
						top: 90,
						transformOrigin: '0 0',
						transform: `translateY(${(1 - p2) * 900 + Math.sin(f / 30 + 1.5) * 8}px) scale(0.98) rotateY(${lerp(-16, -10, cam)}deg) rotateZ(3deg)`,
					}}
				>
					<IPhone>
						<VoiceGrid f={f} />
					</IPhone>
				</div>
			</div>
			<Callout f={f} start={140} float={1} style={{left: 760, top: 760}}>
				<div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '12px 18px'}}>
					<Avatar u="luna" size={42} speaking={talk(f, 3)} />
					<div style={{lineHeight: 1.2}}>
						<div style={{fontWeight: 800, fontSize: 18}}>luna joined Lounge</div>
						<div style={{fontSize: 15, color: C.green}}>● Voice Connected</div>
					</div>
				</div>
			</Callout>
		</AbsoluteFill>
	);
};

/* ================================================================ 6. VIDEO & GO LIVE (50-60s) */
const LiveBadge: React.FC<{scale?: number}> = ({scale = 1}) => (
	<span style={{background: C.dnd, color: '#fff', fontWeight: 900, fontSize: 13 * scale, padding: `${3 * scale}px ${7 * scale}px`, borderRadius: 5 * scale, letterSpacing: '0.05em'}}>LIVE</span>
);

export const GoLive: React.FC = () => {
	const f = useCurrentFrame();
	const enter = spr(f, 0, {damping: 18, stiffness: 70});
	const ph = spr(f, 30, {damping: 16, stiffness: 80});
	const cam = prog(f, 0, 300, easeInOut);
	const viewers = Math.floor(interpolate(f, [40, 260], [12, 1284], clamp));
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
				{u: 'kai', live: true, speaking: talk(f, 1)},
				{u: 'luna', video: true, speaking: talk(f, 3)},
				{u: 'zed', video: true, speaking: talk(f, 4)},
				{u: 'jun', speaking: talk(f, 5)},
				{u: 'you'},
			],
		},
	];
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 1500} a={C.red} b={C.blurple} />
			<AbsoluteFill style={{alignItems: 'center'}}>
				<div style={{marginTop: 64, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
					<Eyebrow f={f} start={2} num="04" label="Video & Go Live" icon="video" color={C.red} />
					<div style={{height: 26}} />
					<Reveal text="STREAM. SHARE. GO LIVE." f={f} start={8} stagger={5} hl={['LIVE']} align="center" style={{...display(84), color: '#fff'}} hlBg={`linear-gradient(92deg, ${C.red}, ${C.fuchsia})`} />
					<div style={{height: 18}} />
					<Body f={f} start={28} w={1100} size={26} align="center">
						Turn on your camera, share your screen or stream your game to friends in a click.
					</Body>
				</div>
			</AbsoluteFill>
			<div style={{position: 'absolute', inset: 0, perspective: 2400}}>
				<div
					style={{
						position: 'absolute',
						left: 900 - 840,
						top: 350,
						transformOrigin: '50% 0%',
						transform: `translateY(${(1 - enter) * 700}px) scale(${lerp(0.6, 0.63, cam)}) rotateX(4deg) rotateY(${lerp(6, 2, cam)}deg)`,
					}}
				>
					<MacBook>
						<DesktopShell
							rail={<ServerRail f={f} selected={0} />}
							sidebar={<ChannelSidebar f={f} rows={rows} voice="Gaming" />}
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
										<div style={{flex: 1, position: 'relative', borderRadius: 12, overflow: 'hidden', containerType: 'inline-size', boxShadow: `inset 0 0 0 3px rgba(35,165,90,${talk(f, 1)})`}}>
											<GameScene f={f} />
											<div style={{position: 'absolute', left: 12, bottom: 12, background: 'rgba(0,0,0,0.65)', borderRadius: 6, padding: '4px 10px', fontSize: 14, fontWeight: 700, display: 'flex', gap: 8, alignItems: 'center'}}>
												<LiveBadge scale={0.85} /> kai.exe — Neon Drift
											</div>
										</div>
										<div style={{width: 250, display: 'flex', flexDirection: 'column', gap: 10}}>
											{(['luna', 'zed', 'jun'] as UserKey[]).map((u, i) => (
												<CamTile key={u} f={f} u={u} cam={u !== 'jun'} seed={i} speaking={talk(f, [3, 4, 5][i])} scale={0.7} style={{flex: 1, transform: `scale(${spr(f, 20 + i * 8)})`}} />
											))}
										</div>
									</div>
									<div style={{padding: '14px 0 18px'}}>
										<CallControls f={f} scale={0.9} />
									</div>
								</div>
							}
						/>
					</MacBook>
				</div>
				<div
					style={{
						position: 'absolute',
						left: 1440,
						top: 380,
						transformOrigin: '0 0',
						transform: `translateY(${(1 - ph) * 900 + Math.sin(f / 30) * 8}px) scale(0.72) rotateY(-14deg) rotateZ(2deg)`,
					}}
				>
					<IPhone>
						<MobileChat title="Gaming" sub="Watching kai.exe" input={<MobileInput f={f} placeholder="Message #Gaming" />}>
							<div style={{position: 'absolute', top: 112, left: 0, right: 0, height: 230, containerType: 'inline-size'}}>
								<GameScene f={f} />
								<div style={{position: 'absolute', left: 10, top: 10}}>
									<LiveBadge scale={0.9} />
								</div>
							</div>
							<Msg f={f} u="luna" at={60} h={90} scale={0.85}>
								that drift was CLEAN 😮
							</Msg>
							<Msg f={f} u="zed" at={110} h={90} scale={0.85} reactions={[{e: '🏎️', n: 5, at: 130}]}>
								new pb incoming
							</Msg>
						</MobileChat>
					</IPhone>
				</div>
			</div>
			<Callout f={f} start={90} float={0} style={{left: 110, top: 470}}>
				<div style={{padding: '16px 20px', width: 300}}>
					<div style={{display: 'flex', alignItems: 'center', gap: 10, fontWeight: 800, fontSize: 19}}>
						<Icon name="screen" size={24} color={C.blurple} /> Screen Share
					</div>
					<div style={{display: 'flex', gap: 8, marginTop: 12}}>
						{['720p', '1080p', '4K'].map((q, i) => (
							<div key={q} style={{flex: 1, textAlign: 'center', padding: '8px 0', borderRadius: 8, fontWeight: 800, fontSize: 16, background: i === Math.min(2, Math.floor(interpolate(f, [100, 160], [0, 3], clamp))) ? C.blurple : '#2B2D31'}}>
								{q}
							</div>
						))}
					</div>
					<div style={{display: 'flex', gap: 8, marginTop: 8}}>
						{['30 FPS', '60 FPS'].map((q, i) => (
							<div key={q} style={{flex: 1, textAlign: 'center', padding: '8px 0', borderRadius: 8, fontWeight: 800, fontSize: 16, background: i === (f > 175 ? 1 : 0) ? C.blurple : '#2B2D31'}}>
								{q}
							</div>
						))}
					</div>
				</div>
			</Callout>
		</AbsoluteFill>
	);
};

/* ================================================================ 7. STAGE & EVENTS (60-68s) */
const StageView: React.FC<{f: number}> = ({f}) => {
	const speakers: UserKey[] = ['nova', 'ava', 'kai'];
	const audience: UserKey[] = ['luna', 'zed', 'rio', 'jun', 'ozzy', 'mila', 'you', 'luna', 'rio', 'zed', 'jun', 'ozzy', 'mila', 'kai', 'ava', 'nova', 'zed', 'luna', 'you', 'rio', 'ozzy', 'jun'];
	const hand = spr(f, 120, {damping: 9});
	return (
		<div style={{position: 'absolute', inset: 0, background: '#0E0F12', fontFamily: BODY, color: C.text, display: 'flex', flexDirection: 'column'}}>
			<div style={{height: 64, display: 'flex', alignItems: 'center', gap: 12, padding: '0 26px', borderBottom: '1px solid #232428'}}>
				<Icon name="stage" size={26} color={C.green} />
				<span style={{fontWeight: 800, fontSize: 20}}>Game Night Q&A</span>
				<span style={{color: C.faint, fontSize: 16}}>· Pixel Party</span>
				<div style={{flex: 1}} />
				<span style={{display: 'flex', alignItems: 'center', gap: 6, color: C.muted, fontSize: 16}}>
					<Icon name="users" size={20} color={C.muted} /> {Math.floor(interpolate(f, [0, 200], [214, 1032], clamp)).toLocaleString('en-US')} listening
				</span>
			</div>
			<div style={{padding: '22px 30px 0', fontSize: 14, fontWeight: 800, letterSpacing: '0.06em', color: C.faint}}>SPEAKERS</div>
			<div style={{display: 'flex', gap: 22, padding: '14px 30px'}}>
				{speakers.map((u, i) => {
					const sp = talk(f, i + 7);
					return (
						<div key={u} style={{flex: 1, height: 230, borderRadius: 18, background: `linear-gradient(160deg, ${USERS[u].g[0]}40, #1E1F22 75%)`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, boxShadow: sp > 0.05 ? `inset 0 0 0 3px rgba(35,165,90,${sp})` : undefined, transform: `scale(${spr(f, 10 + i * 6)})`}}>
							<Avatar u={u} size={96} speaking={sp} />
							<div style={{fontWeight: 800, fontSize: 18, display: 'flex', gap: 6, alignItems: 'center'}}>
								{i === 0 && <Icon name="crown" size={18} color={C.yellow} />}
								{USERS[u].name}
							</div>
						</div>
					);
				})}
			</div>
			<div style={{padding: '18px 30px 0', fontSize: 14, fontWeight: 800, letterSpacing: '0.06em', color: C.faint}}>AUDIENCE</div>
			<div style={{display: 'flex', flexWrap: 'wrap', gap: 20, padding: '14px 30px'}}>
				{audience.map((u, i) => (
					<div key={i} style={{position: 'relative', transform: `scale(${spr(f, 30 + i * 2)})`}}>
						<Avatar u={u} size={74} />
						{i === 3 && (
							<div style={{position: 'absolute', right: -12, top: -14, transform: `scale(${hand}) rotate(${Math.sin(f / 4) * 14}deg)`}}>
								<Emoji e="✋" size={30} />
							</div>
						)}
					</div>
				))}
			</div>
			<div style={{flex: 1}} />
			<div style={{display: 'flex', justifyContent: 'center', gap: 14, paddingBottom: 26}}>
				<div style={{padding: '14px 26px', borderRadius: 28, background: '#2B2D31', fontWeight: 800, fontSize: 17, display: 'flex', gap: 10, alignItems: 'center'}}>
					<Icon name="hand" size={22} color="#fff" /> Request to Speak
				</div>
				<div style={{padding: '14px 26px', borderRadius: 28, background: C.dnd, fontWeight: 800, fontSize: 17}}>Leave Quietly</div>
			</div>
		</div>
	);
};

export const Stage: React.FC = () => {
	const f = useCurrentFrame();
	const enter = spr(f, 0, {damping: 18, stiffness: 70});
	const cam = prog(f, 0, 240, easeInOut);
	const interested = Math.floor(interpolate(f, [60, 220], [120, 2481], clamp));
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 1800} a={C.yellow} b={C.blurple} />
			<div style={{position: 'absolute', left: 110, top: 150, width: 760}}>
				<Eyebrow f={f} start={2} num="05" label="Stage & Events" icon="stage" color={C.yellow} />
				<div style={{height: 34}} />
				<Reveal text={'HOST EVENTS\nTHAT FEEL LIVE'} f={f} start={8} stagger={4} hl={['LIVE']} style={{...display(68), color: '#fff'}} hlBg={`linear-gradient(92deg, ${C.yellow}, #FF8A4C)`} />
				<div style={{height: 26}} />
				<Body f={f} start={30} w={600} size={26}>
					Run Q&As, watch parties and AMAs on Stage, and schedule events your whole community can RSVP to.
				</Body>
			</div>
			<div style={{position: 'absolute', inset: 0, perspective: 2200}}>
				<div
					style={{
						position: 'absolute',
						left: 900,
						top: 190,
						transformOrigin: '0 0',
						transform: `translateX(${(1 - enter) * 1000}px) scale(${lerp(0.68, 0.71, cam)}) rotateY(${lerp(-14, -9, cam)}deg)`,
					}}
				>
					<IPad>
						<StageView f={f} />
					</IPad>
				</div>
			</div>
			{/* event card */}
			<Callout f={f} start={40} float={1} style={{left: 160, top: 610}}>
				<div style={{width: 560, borderRadius: 18, overflow: 'hidden'}}>
					<div style={{height: 120, position: 'relative', background: `linear-gradient(120deg, ${C.yellow}, #FF8A4C 40%, ${C.fuchsia})`}}>
						<Emoji e="🕹️" size={84} style={{position: 'absolute', right: 26, top: 16, transform: 'rotate(12deg)'}} />
					</div>
					<div style={{padding: '18px 22px 22px'}}>
						<div style={{display: 'flex', alignItems: 'center', gap: 8, color: C.yellow, fontWeight: 800, fontSize: 16}}>
							<Icon name="calendar" size={18} color={C.yellow} /> FRI, NOV 14 · 8:00 PM
						</div>
						<div style={{fontWeight: 900, fontSize: 28, marginTop: 6}}>Community Game Night</div>
						<div style={{display: 'flex', alignItems: 'center', gap: 14, marginTop: 14}}>
							<div style={{display: 'flex'}}>
								{(['nova', 'kai', 'luna', 'zed'] as UserKey[]).map((u, i) => (
									<Avatar key={u} u={u} size={34} style={{marginLeft: i ? -10 : 0, boxShadow: '0 0 0 3px #1E1F22', borderRadius: '50%'}} />
								))}
							</div>
							<span style={{color: C.muted, fontSize: 17, fontWeight: 600}}>{interested.toLocaleString('en-US')} interested</span>
							<div style={{flex: 1}} />
							<div style={{padding: '10px 18px', borderRadius: 8, background: f > 150 ? C.online : C.blurple, fontWeight: 800, fontSize: 16, display: 'flex', gap: 6, alignItems: 'center'}}>
								{f > 150 ? <Icon name="check" size={16} color="#fff" /> : <Icon name="bell" size={16} color="#fff" />}
								Interested
							</div>
						</div>
					</div>
				</div>
			</Callout>
		</AbsoluteFill>
	);
};

/* ================================================================ 8. ROLES & MODERATION (68-78s) */
const ROLES = [
	{n: 'Admin', c: '#FF6B6B', m: 3},
	{n: 'Moderator', c: C.green, m: 12},
	{n: 'Artist', c: '#F47FFF', m: 48},
	{n: 'VIP', c: C.yellow, m: 120},
	{n: 'Gamer', c: '#00A8FC', m: 2310},
	{n: 'Member', c: '#A5B4FF', m: 10000},
];
const PERMS = [
	{n: 'Manage Messages', d: 'Delete or pin messages from other members.', on: 60},
	{n: 'Timeout Members', d: 'Temporarily stop members from chatting.', on: 80},
	{n: 'Kick Members', d: 'Remove members from the server.', on: 100},
	{n: 'Manage Events', d: 'Create, edit and cancel events.', on: 120},
	{n: 'Mention @everyone', d: 'Notify everyone in the server.', on: -1},
];

const SettingsView: React.FC<{f: number}> = ({f}) => {
	const sel = 1;
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
						const p = prog(f, 10 + i * 4, 26 + i * 4);
						return (
							<div key={r.n} style={{display: 'flex', alignItems: 'center', gap: 10, padding: '9px 10px', borderRadius: 6, background: i === sel ? '#404249' : undefined, marginBottom: 3, opacity: p, transform: `translateX(${(1 - p) * -20}px)`}}>
								<div style={{width: 13, height: 13, borderRadius: '50%', background: r.c}} />
								<span style={{fontWeight: 700, fontSize: 16.5, color: i === sel ? '#fff' : C.muted, flex: 1}}>{r.n}</span>
								<span style={{fontSize: 13, color: C.faint}}>{r.m.toLocaleString('en-US')}</span>
							</div>
						);
					})}
				</div>
				<div style={{flex: 1, padding: '56px 36px 0'}}>
					<div style={{fontSize: 22, fontWeight: 800, display: 'flex', gap: 10, alignItems: 'center'}}>
						EDIT ROLE — <span style={{color: C.green}}>Moderator</span>
					</div>
					<div style={{display: 'flex', gap: 22, marginTop: 16, borderBottom: '1px solid #3F4147'}}>
						{['Display', 'Permissions', 'Links', 'Manage Members'].map((t) => (
							<div key={t} style={{paddingBottom: 12, fontWeight: 700, fontSize: 16, color: t === 'Permissions' ? '#fff' : C.muted, borderBottom: t === 'Permissions' ? `3px solid ${C.blurple}` : '3px solid transparent'}}>
								{t}
							</div>
						))}
					</div>
					{PERMS.map((p) => {
						const on = p.on < 0 ? 0 : prog(f, p.on, p.on + 8);
						return (
							<div key={p.n} style={{display: 'flex', alignItems: 'center', gap: 18, padding: '18px 0', borderBottom: '1px solid #3F4147'}}>
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

export const Roles: React.FC = () => {
	const f = useCurrentFrame();
	const enter = spr(f, 0, {damping: 18, stiffness: 70});
	const cam = prog(f, 0, 300, easeInOut);
	return (
		<AbsoluteFill>
			<SpaceBg f={f + 2040} a={C.green} b={C.blurple} />
			<div style={{position: 'absolute', inset: 0, perspective: 2400}}>
				<div
					style={{
						position: 'absolute',
						left: 80,
						top: 180,
						transformOrigin: '0 0',
						transform: `translateX(${(1 - enter) * -1000}px) scale(${lerp(0.64, 0.67, cam)}) rotateY(${lerp(14, 9, cam)}deg)`,
					}}
				>
					<MacBook>
						<div style={{position: 'absolute', inset: 0, background: C.chat}}>
							<SettingsView f={f} />
							<div style={{position: 'absolute', left: 0, top: 0, right: 0}}>
								<div style={{height: 34, display: 'flex', alignItems: 'center', padding: '0 16px', gap: 9}}>
									{['#FF5F57', '#FEBC2E', '#28C840'].map((c) => (
										<div key={c} style={{width: 13, height: 13, borderRadius: '50%', background: c}} />
									))}
								</div>
							</div>
						</div>
					</MacBook>
				</div>
			</div>
			<div style={{position: 'absolute', left: 1290, top: 250, width: 600}}>
				<Eyebrow f={f} start={4} num="06" label="Roles & Safety" icon="shield" color={C.green} />
				<div style={{height: 34}} />
				<Reveal text={"YOU'RE IN\nCONTROL"} f={f} start={10} stagger={4} hl={['CONTROL']} style={{...display(80), color: '#fff'}} hlBg={`linear-gradient(92deg, ${C.green}, #00A8FC)`} />
				<div style={{height: 26}} />
				<Body f={f} start={32} w={560} size={26}>
					Custom roles, granular permissions and AutoMod keep your space safe, organised and exactly how you like it.
				</Body>
			</div>
			<Callout f={f} start={150} float={0} style={{left: 760, top: 110}}>
				<div style={{width: 470, padding: '16px 18px', borderLeft: `4px solid ${C.dnd}`, borderRadius: 18}}>
					<div style={{display: 'flex', alignItems: 'center', gap: 12}}>
						<Icon name="shield" size={34} color={C.blurple} />
						<div style={{lineHeight: 1.25}}>
							<div style={{fontWeight: 800, fontSize: 19}}>
								AutoMod <span style={{background: C.blurple, fontSize: 11, padding: '1px 5px', borderRadius: 4, verticalAlign: 'middle'}}>✓ APP</span>
							</div>
							<div style={{fontSize: 15, color: C.muted}}>Blocked a message in #general</div>
						</div>
					</div>
					<div style={{marginTop: 10, padding: '8px 12px', borderRadius: 8, background: 'rgba(237,66,69,0.12)', fontSize: 15, color: '#FFB3B4', fontFamily: MONO}}>
						Rule: Block spam links · Action: Timeout 10m
					</div>
				</div>
			</Callout>
			<Callout f={f} start={185} float={2} style={{left: 1290, top: 760}}>
				<div style={{padding: '16px 18px', width: 520}}>
					<div style={{fontSize: 13, fontWeight: 800, color: C.faint, letterSpacing: '0.05em', marginBottom: 10}}>ROLES</div>
					<div style={{display: 'flex', flexWrap: 'wrap', gap: 8}}>
						{ROLES.map((r, i) => (
							<div key={r.n} style={{display: 'flex', alignItems: 'center', gap: 7, padding: '6px 12px', borderRadius: 8, background: '#2B2D31', fontWeight: 700, fontSize: 16, transform: `scale(${spr(f, 195 + i * 4, {damping: 12})})`}}>
								<div style={{width: 11, height: 11, borderRadius: '50%', background: r.c}} />
								{r.n}
							</div>
						))}
					</div>
				</div>
			</Callout>
		</AbsoluteFill>
	);
};

export {UserPanel, ChatHeader};
