import React from 'react';
import {interpolate} from 'remotion';
import {Reveal} from '../discord/primitives';
import {IPad, IPhone, MacBook} from '../discord/devices';
import {Cursor} from '../engine/scene3d';
import {GameScene} from '../discord/ui';
import {Body, CH, ChAvatar, Card, Emoji, Eyebrow, ICELAND, Icon, IcelandScene, PlayIcon, Sparkle, VIDEOS, clamp, easeInOut, lerp, prog, spr} from './kit';
import {Browser, ChatMsg, HomeFeed, LivePage, MobileHome, MobileNav, MusicPlayer, MobileDownload, Player, ShortsCamera, ShortsPlayer, StudioPage, TV, TVHome, TopBar, WatchPage} from './ui';
import {CUES, STATIONS, WATCH_ARRIVE} from './timeline';
import {Y, YBODY, ydisplay} from './theme';

const H1 = (size: number): React.CSSProperties => ydisplay(size);
const rise = (t: number, at: number, dist = 700) => (1 - spr(t, at, {damping: 18, stiffness: 75})) * dist;
const preserve: React.CSSProperties = {position: 'absolute', inset: 0, transformStyle: 'preserve-3d'};
const lift = (z = 120): React.CSSProperties => ({transform: `translateZ(${z}px)`});
const chip = {chipColor: Y.red, chipText: '#fff'};
const cur = {fill: Y.ink, stroke: '#fff', shadow: Y.shadowStrong, ring: Y.red};

/* ================================================================ 1. INTRO */
export const Intro: React.FC<{f: number}> = ({f}) => {
	const I = CUES.intro;
	const t = f - STATIONS.intro.arrive;
	const out = prog(t, I.wordsOut, I.wordsOut + 16);
	const burst = spr(t, I.logo, {damping: 11, stiffness: 130});
	const words = ['WATCH.', 'CREATE.', 'SHARE.'];
	const c = prog(t, I.words[2] + 12, I.words[2] + 26, easeInOut);
	return (
		<>
			<div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 40, opacity: 1 - out, transform: `translateZ(${90 + out * 260}px) translateY(${-out * 160}px) scale(${1 - out * 0.35})`}}>
				{words.map((w, i) => {
					const s = spr(t, I.words[i], {damping: 10, stiffness: 210, mass: 0.6});
					const isChip = i === 2;
					return (
						<div
							key={w}
							style={{
								...H1(150),
								position: 'relative',
								padding: isChip ? '0.04em 0.14em 0.06em' : undefined,
								opacity: interpolate(t, [I.words[i], I.words[i] + 3], [0, 1], clamp),
								transform: `scale(${lerp(2.1, 1, s)})`,
								filter: s < 0.98 ? `blur(${(1 - Math.min(1, s)) * 14}px)` : undefined,
							}}
						>
							{isChip && <div style={{position: 'absolute', inset: 0, borderRadius: 18, background: Y.red, transform: `scaleX(${c})`, transformOrigin: 'left'}} />}
							<span style={{position: 'relative'}}>
								{w}
								{isChip && <span style={{position: 'absolute', left: 0, top: 0, color: '#fff', clipPath: `inset(-10% ${(1 - c) * 100}% -10% 0)`}}>{w}</span>}
							</span>
						</div>
					);
				})}
			</div>
			{[0, 1, 2].map((i) => {
				const r = prog(t, I.logo + i * 5, I.logo + 46 + i * 5);
				if (t < I.logo) return null;
				return <div key={i} style={{position: 'absolute', left: 960 - 1100 * r, top: 390 - 1100 * r, width: 2200 * r, height: 2200 * r, borderRadius: '50%', border: `${7 - i * 2}px solid ${i === 1 ? Y.ink : Y.red}`, opacity: (1 - r) * 0.8}} />;
			})}
			<div style={{position: 'absolute', left: 0, right: 0, top: 260, display: 'flex', flexDirection: 'column', alignItems: 'center', ...lift(70)}}>
				<div style={{position: 'relative', transform: `scale(${burst}) rotate(${(1 - burst) * -30}deg)`, opacity: t >= I.logo ? 1 : 0, filter: `drop-shadow(0 30px 50px rgba(255,0,0,0.35))`}}>
					<PlayIcon h={230} />
					{[0, 1, 2, 3].map((i) => {
						const sp = spr(t, I.logo + 14 + i * 4, {damping: 12});
						const ang = (i / 4) * Math.PI * 2 + 0.6;
						return (
							<Sparkle key={i} size={[34, 22, 28, 18][i]} color={[Y.red, '#FFB800', Y.ink, Y.blue][i]} style={{position: 'absolute', left: 161 + Math.cos(ang) * 230 * sp - 15, top: 115 + Math.sin(ang) * 180 * sp - 15, transform: `scale(${sp}) rotate(${t * 2}deg)`}} />
						);
					})}
				</div>
				<div style={{display: 'flex', marginTop: 34, height: 150, alignItems: 'center'}}>
					{'YouTube'.split('').map((ch, i) => {
						const p = prog(t, I.wordmark + i * 2.5, I.wordmark + 20 + i * 2.5);
						return (
							<span key={i} style={{fontFamily: YBODY, fontWeight: 700, fontSize: 150, letterSpacing: '-0.06em', color: Y.ink, display: 'inline-block', opacity: p, transform: `translateY(${(1 - p) * 60}px) scale(${lerp(0.6, 1, p)})`}}>
								{ch}
							</span>
						);
					})}
				</div>
				<Reveal text="THE WORLD IS WATCHING" f={t} start={I.tagline} stagger={2.5} hl={['WATCHING']} align="center" style={{...H1(46), marginTop: 26}} {...chip} />
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
			<div style={{position: 'absolute', left: 0, right: 0, top: 70, display: 'flex', flexDirection: 'column', alignItems: 'center', ...lift()}}>
				<Reveal text="EVERYTHING YOU LOVE TO WATCH" f={t} start={H.title} stagger={4} hl={['WATCH']} align="center" style={H1(88)} {...chip} />
				<div style={{height: 20}} />
				<Body f={t} start={H.title + 16} w={1200} size={27} align="center">
					Music, gaming, cooking, learning, live streams and Shorts — from creators everywhere, all in one place.
				</Body>
			</div>
			<div style={preserve}>
				<div style={{position: 'absolute', left: 120, top: 330, transformOrigin: '50% 0%', transform: `translateY(${rise(t, H.mac)}px) scale(0.6) rotateX(3deg)`}}>
					<MacBook>
						<Browser>
							<TopBar />
							<div style={{height: 'calc(100% - 56px)'}}>
								<HomeFeed t={200} />
							</div>
						</Browser>
					</MacBook>
				</div>
				<div style={{position: 'absolute', left: 1390, top: 410, transformOrigin: '0 0', transform: `translateY(${rise(t, H.phoneR, 800) + Math.sin(t / 30) * 8}px) scale(0.66) rotateY(-10deg) rotateZ(2deg)`}}>
					<IPhone>
						<MobileHome t={t} />
					</IPhone>
				</div>
				<div style={{position: 'absolute', left: 250, top: 480, transformOrigin: '0 0', transform: `translateY(${rise(t, H.phoneL, 800) + Math.sin(t / 28 + 2) * 8}px) scale(0.58) rotateY(14deg) rotateZ(-4deg)`}}>
					<IPhone frame="black">
						<ShortsPlayer t={t} f={f} swipeAt={1e9} likeAt={1e9} />
					</IPhone>
				</div>
			</div>
			<Card f={t} at={H.views} x={1490} y={330} float={1} radius={999}>
				<div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '14px 24px'}}>
					<PlayIcon h={20} />
					<span style={{fontWeight: 700, fontSize: 22}}>2.4M views</span>
				</div>
			</Card>
			<Card f={t} at={H.notify} x={40} y={390} float={2} dark>
				<div style={{display: 'flex', alignItems: 'center', gap: 14, padding: '12px 16px 12px 14px', width: 430}}>
					<Icon name="bellRing" size={26} color={Y.text} />
					<ChAvatar c="maya" size={40} />
					<div style={{lineHeight: 1.3, fontSize: 15, flex: 1}}>
						<b>Maya Makes</b> uploaded: I Built a Tiny Cabin in 7 Days
						<div style={{fontSize: 13, color: Y.text2}}>just now</div>
					</div>
				</div>
			</Card>
			<Card f={t} at={H.react} x={1600} y={830} float={0} radius={999}>
				<div style={{display: 'flex', alignItems: 'center', gap: 10, padding: '12px 22px'}}>
					<Icon name="like" size={24} color={Y.ink} />
					<span style={{fontWeight: 700, fontSize: 20}}>96K</span>
				</div>
			</Card>
		</>
	);
};

/* ================================================================ 3. HOME -> WATCH (one MacBook, camera pans across it) */
// station-local px of the Iceland card / Like / Subscribe on the 0.74-scaled MacBook (see ui.tsx layout)
const HOME_CLICK = {x: 1097, y: 633};
const LIKE = {x: 988, y: 760};
const SUBSCRIBE = {x: 725, y: 760};

export const HomeStation: React.FC<{f: number}> = ({f}) => {
	const Hm = CUES.home;
	const W = CUES.watch;
	const t = f - STATIONS.home.arrive;
	const tw = f - WATCH_ARRIVE;
	const onWatch = t >= Hm.click + 2;
	const enter = prog(t, Hm.click + 2, Hm.click + 26, easeInOut);
	const liked = tw >= W.like;
	const subscribed = tw >= W.subscribe;
	const subP = tw >= W.subscribe - 2 && tw < W.subscribe + 5 ? 0.93 : 1;
	return (
		<>
			<div style={preserve}>
				<div style={{position: 'absolute', left: 418, top: 190, transformOrigin: '0 0', transform: `translateY(${rise(t, Hm.mac, 600)}px) scale(0.74)`}}>
					<MacBook>
						<Browser url={onWatch ? 'youtube.com/watch?v=iceland4k' : 'youtube.com'}>
							<TopBar />
							<div style={{height: 'calc(100% - 56px)', position: 'relative'}}>
								{enter < 1 && (
									<div style={{position: 'absolute', inset: 0, opacity: 1 - prog(enter, 0.15, 0.6)}}>
										<HomeFeed t={t} chipStart={Hm.chips} gridStart={Hm.grid} hot={ICELAND} hotP={prog(t, Hm.hover, Hm.hover + 8)} />
									</div>
								)}
								{onWatch && (
									<div style={{position: 'absolute', inset: 0}}>
										<WatchPage t={tw} f={f} liked={liked} subscribed={subscribed} subP={subP} enter={enter} commentsAt={W.comments} />
									</div>
								)}
							</div>
						</Browser>
					</MacBook>
				</div>
			</div>
			<div style={{position: 'absolute', left: -230, top: 250, width: 640, ...lift()}}>
				<Eyebrow f={t} start={Hm.eyebrow} num="01" label="Home & Discovery" icon="home" />
				<div style={{height: 30}} />
				<Reveal text={'FIND YOUR\nNEXT OBSESSION'} f={t} start={Hm.title} stagger={4} hl={['OBSESSION']} style={H1(70)} {...chip} />
				<div style={{height: 24}} />
				<Body f={t} start={Hm.title + 18} w={560} size={24}>
					A feed that learns what you love — from the creators you follow and the ones you haven't found yet.
				</Body>
			</div>
			<Cursor t={t} path={[{t: Hm.cursorIn, x: 1330, y: 860}, {t: Hm.hover - 4, x: HOME_CLICK.x, y: HOME_CLICK.y}, {t: Hm.click + 14, x: HOME_CLICK.x + 10, y: HOME_CLICK.y + 14}]} clicks={[Hm.click]} z={2} {...cur} />
			<div style={{position: 'absolute', left: 1730, top: 270, width: 560, ...lift()}}>
				<Eyebrow f={tw} start={W.eyebrow} num="02" label="Watch & Subscribe" icon="play" />
				<div style={{height: 30}} />
				<Reveal text={'WATCH. LIKE.\nSUBSCRIBE.'} f={tw} start={W.title} stagger={4} hl={['SUBSCRIBE']} style={H1(66)} {...chip} />
				<div style={{height: 24}} />
				<Body f={tw} start={W.title + 18} w={500} size={23}>
					Up to 4K playback, chapters and comments — and one tap to follow the creators you love.
				</Body>
			</div>
			<Cursor
				t={tw}
				path={[
					{t: W.like - 22, x: 1080, y: 930},
					{t: W.like - 4, x: LIKE.x, y: LIKE.y},
					{t: W.subscribe - 4, x: SUBSCRIBE.x, y: SUBSCRIBE.y},
					{t: W.subscribe + 18, x: SUBSCRIBE.x + 12, y: SUBSCRIBE.y + 16},
				]}
				clicks={[W.like, W.subscribe]}
				z={2}
				{...cur}
			/>
			<Card f={tw} at={W.toast} x={1240} y={290} float={1} dark>
				<div style={{display: 'flex', alignItems: 'center', gap: 14, padding: '14px 20px 14px 16px', width: 420}}>
					<div style={{width: 44, height: 44, borderRadius: 22, background: Y.red, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
						<Icon name="bellRing" size={24} color="#fff" />
					</div>
					<div style={{lineHeight: 1.3}}>
						<div style={{fontWeight: 700, fontSize: 18}}>Subscribed to Wander Wide</div>
						<div style={{fontSize: 14, color: Y.text2}}>You'll be notified about new videos</div>
					</div>
				</div>
			</Card>
		</>
	);
};

/* ================================================================ 4. SHORTS */
export const Shorts: React.FC<{f: number}> = ({f}) => {
	const S = CUES.shorts;
	const t = f - STATIONS.shorts.arrive;
	return (
		<>
			<div style={{position: 'absolute', left: 110, top: 200, width: 720, ...lift()}}>
				<Eyebrow f={t} start={S.eyebrow} num="03" label="Shorts" icon="shorts" />
				<div style={{height: 30}} />
				<Reveal text={'SWIPE.\nWATCH.\nREPEAT.'} f={t} start={S.title} stagger={5} hl={['REPEAT']} style={H1(104)} {...chip} />
				<div style={{height: 26}} />
				<Body f={t} start={S.title + 18} w={600}>
					Bite-sized vertical videos that never run out — and a Shorts camera to make your own in seconds.
				</Body>
				<div style={{display: 'flex', gap: 14, marginTop: 30}}>
					{[
						{x: 'Vertical video', i: 'phone' as const},
						{x: 'Remix & reply', i: 'remix' as const},
					].map((c, i) => (
						<div key={c.x} style={{transform: `scale(${spr(t, S.title + 30 + i * 6, {damping: 13})})`, display: 'flex', alignItems: 'center', gap: 10, padding: '12px 20px', borderRadius: 999, background: '#fff', color: Y.ink, fontFamily: YBODY, fontWeight: 700, fontSize: 20, boxShadow: `0 16px 40px ${Y.shadow}`}}>
							<Icon name={c.i} size={22} color={Y.red} />
							{c.x}
						</div>
					))}
				</div>
			</div>
			<div style={preserve}>
				<div style={{position: 'absolute', left: 900, top: 130, transformOrigin: '0 0', transform: `translateY(${rise(t, S.phoneA, 900) + Math.sin(t / 30) * 8}px) scale(0.92) rotateY(10deg) rotateZ(-3deg)`}}>
					<IPhone frame="black">
						<ShortsPlayer t={t} f={f} swipeAt={S.swipe} likeAt={S.like} />
					</IPhone>
				</div>
				<div style={{position: 'absolute', left: 1340, top: 90, transformOrigin: '0 0', transform: `translateY(${rise(t, S.phoneB, 900) + Math.sin(t / 30 + 1.5) * 8}px) scale(0.98) rotateY(-10deg) rotateZ(3deg)`}}>
					<IPhone>
						<ShortsCamera t={t} f={f} recAt={S.rec} />
					</IPhone>
				</div>
			</div>
			<Card f={t} at={S.callout} x={700} y={790} float={1} radius={999}>
				<div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '12px 22px'}}>
					<Icon name="heart" size={26} color={Y.red} />
					<span style={{fontWeight: 700, fontSize: 20}}>3.4M likes · #kickflip trending</span>
				</div>
			</Card>
		</>
	);
};

/* ================================================================ 5. LIVE + SUPER CHAT */
const SC20 = {amt: '$20.00', head: '#E65100', bg: '#F57C00'};
const SC50 = {amt: '$50.00', head: '#C2185B', bg: '#E91E63'};

export const Live: React.FC<{f: number}> = ({f}) => {
	const L = CUES.live;
	const t = f - STATIONS.live.arrive;
	const picked = t >= L.pick;
	const sent = t >= L.send;
	const watching = Math.floor(interpolate(t, [0, 150], [9840, 12481], clamp));
	const msgs: ChatMsg[] = [
		{c: 'maya', who: '@mayamakes', text: 'LETS GOOO 🔥🔥', at: L.chat[0]},
		{c: 'taste', who: '@tastetrip', text: 'that last corner was insane', at: L.chat[1]},
		{c: 'cosmo', who: '@cosmoclips', text: 'new PB incoming 👀', at: L.chat[2]},
		{c: 'noodle', who: '@noodlelab', text: 'hi from Tokyo 🇯🇵', at: L.chat[3]},
		{c: 'you', who: '@you', text: 'Love the stream!! 🔥', at: L.superchat, sc: SC20},
		{c: 'strum', who: '@strumschool', text: 'GG!!', at: L.chat[4]},
		{c: 'maya', who: '@mayamakes', text: 'World record or bust 🏆', at: L.superchat2, sc: SC50},
		{c: 'pixel', who: '@pixelpro', text: 'thank you all ❤️', at: L.chat[5]},
	];
	const amt = (on: boolean): React.CSSProperties => ({flex: 1, textAlign: 'center', padding: '9px 0', borderRadius: 10, fontWeight: 700, fontSize: 16, background: on ? SC20.bg : '#F0F0F0', color: on ? '#fff' : Y.ink});
	return (
		<>
			<div style={{position: 'absolute', left: 0, right: 0, top: 56, display: 'flex', flexDirection: 'column', alignItems: 'center', ...lift()}}>
				<Eyebrow f={t} start={L.eyebrow} num="04" label="Live & Super Chat" icon="live" />
				<div style={{height: 24}} />
				<Reveal text="GO LIVE TO THE WORLD" f={t} start={L.title} stagger={4} hl={['LIVE']} align="center" style={H1(88)} {...chip} />
			</div>
			<div style={preserve}>
				<div style={{position: 'absolute', left: 900 - 840, top: 300, transformOrigin: '50% 0%', transform: `translateY(${rise(t, L.mac)}px) scale(0.62) rotateX(3deg)`}}>
					<MacBook>
						<Browser url="youtube.com/live/neon-drift">
							<TopBar />
							<div style={{height: 'calc(100% - 56px)'}}>
								<LivePage t={t} f={f} msgs={msgs} watching={watching} />
							</div>
						</Browser>
					</MacBook>
				</div>
				<div style={{position: 'absolute', left: 1450, top: 360, transformOrigin: '0 0', transform: `translateY(${rise(t, L.phone, 900) + Math.sin(t / 30) * 8}px) scale(0.72) rotateY(-12deg) rotateZ(2deg)`}}>
					<IPhone>
						<div style={{position: 'absolute', inset: 0, background: Y.ui, fontFamily: YBODY, color: Y.text, paddingTop: 54, display: 'flex', flexDirection: 'column'}}>
							<div style={{position: 'relative', width: '100%', aspectRatio: '16 / 9', containerType: 'inline-size', overflow: 'hidden'}}>
								<GameScene f={f} />
								<div style={{position: 'absolute', left: 8, top: 8, background: Y.red, fontSize: 12, fontWeight: 700, padding: '2px 6px', borderRadius: 3}}>LIVE</div>
							</div>
							<div style={{padding: '10px 12px', fontSize: 15, fontWeight: 700}}>World record attempts 🔴</div>
							<div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 8, padding: '0 12px 12px', overflow: 'hidden'}}>
								{msgs.slice(0, 6).filter((m) => t >= m.at).map((m, i) =>
									m.sc ? (
										<div key={i} style={{borderRadius: 8, background: m.sc.bg, padding: '6px 10px', fontSize: 13, flexShrink: 0}}>
											<b>{m.who}</b> · {m.sc.amt}
											<div>{m.text}</div>
										</div>
									) : (
										<div key={i} style={{display: 'flex', gap: 8, fontSize: 13, flexShrink: 0}}>
											<ChAvatar c={m.c} size={20} />
											<span>
												<span style={{color: Y.text2}}>{m.who}</span> {m.text}
											</span>
										</div>
									),
								)}
							</div>
							<MobileNav />
						</div>
					</IPhone>
				</div>
			</div>
			<Card f={t} at={L.composer} x={70} y={440} float={0}>
				<div style={{padding: '18px 18px', width: 320}}>
					<div style={{display: 'flex', alignItems: 'center', gap: 10, fontWeight: 900, fontSize: 20}}>
						<Icon name="dollar" size={26} color={SC20.bg} /> Super Chat
					</div>
					<div style={{display: 'flex', gap: 8, marginTop: 12}}>
						{['$2', '$5', '$10', '$20'].map((x, i) => (
							<div key={x} style={amt(picked ? i === 3 : i === 1)}>
								{x}
							</div>
						))}
					</div>
					<div style={{marginTop: 10, height: 40, borderRadius: 10, border: '1px solid #DDD', display: 'flex', alignItems: 'center', padding: '0 12px', fontSize: 15, color: picked ? Y.ink : '#999'}}>{picked ? 'Love the stream!! 🔥' : 'Say something nice…'}</div>
					<div style={{marginTop: 10, height: 40, borderRadius: 10, background: sent ? Y.ink : Y.blue, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, fontWeight: 700, fontSize: 16, transform: `scale(${t >= L.send - 2 && t < L.send + 5 ? 0.95 : 1})`}}>
						{sent ? (
							<>
								<Icon name="check" size={18} color="#fff" /> Sent
							</>
						) : (
							`Buy and send · ${picked ? '$20' : '$5'}`
						)}
					</div>
				</div>
			</Card>
			<Card f={t} at={L.viewers} x={70} y={720} float={2}>
				<div style={{display: 'flex', alignItems: 'center', gap: 14, padding: '14px 20px', width: 320}}>
					<div style={{width: 44, height: 44, borderRadius: 22, background: '#FFE5E5', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
						<Icon name="eye" size={24} color={Y.red} />
					</div>
					<div style={{lineHeight: 1.2}}>
						<div style={{fontWeight: 900, fontSize: 24}}>{watching.toLocaleString('en-US')}</div>
						<div style={{fontSize: 14, color: '#666'}}>watching now · peak 14.2K</div>
					</div>
				</div>
			</Card>
			<Cursor
				t={t}
				path={[
					{t: L.composer + 10, x: 470, y: 760},
					{t: L.pick - 4, x: 342, y: 517},
					{t: L.send - 4, x: 230, y: 616},
					{t: L.send + 18, x: 244, y: 632},
				]}
				clicks={[L.pick, L.send]}
				z={242}
				{...cur}
			/>
		</>
	);
};

/* ================================================================ 6. WATCH ANYWHERE */
export const Devices: React.FC<{f: number}> = ({f}) => {
	const D = CUES.devices;
	const t = f - STATIONS.devices.arrive;
	const chips = ['Smart TV', 'Desktop', 'Mobile', 'Tablet', 'Console', 'Web'];
	return (
		<>
			<div style={{position: 'absolute', left: 0, right: 0, top: 50, display: 'flex', flexDirection: 'column', alignItems: 'center', ...lift()}}>
				<Eyebrow f={t} start={D.eyebrow} num="05" label="Every screen" icon="tv" />
				<div style={{height: 22}} />
				<Reveal text="WATCH ANYWHERE" f={t} start={D.title} stagger={4} hl={['ANYWHERE']} align="center" style={H1(92)} {...chip} />
				<div style={{display: 'flex', gap: 12, marginTop: 24}}>
					{chips.map((p, i) => (
						<div key={p} style={{transform: `scale(${spr(t, D.chips + i * D.chipStep, {damping: 13})})`, padding: '8px 18px', borderRadius: 999, background: '#fff', color: Y.ink, fontFamily: YBODY, fontWeight: 700, fontSize: 19, boxShadow: `0 10px 26px ${Y.shadow}`}}>
							{p}
						</div>
					))}
				</div>
			</div>
			<div style={preserve}>
				<div style={{position: 'absolute', left: 40, top: 520, transformOrigin: '0 0', transform: `translateY(${rise(t, D.rise[0], 800)}px) scale(0.42) rotateY(18deg)`}}>
					<IPad>
						<div style={{position: 'absolute', inset: 0, background: Y.ui, padding: 0}}>
							<Player f={f} progress={0.34} w={1180}>
								<IcelandScene f={f} />
							</Player>
							<div style={{padding: '14px 20px', fontFamily: YBODY, color: Y.text, fontSize: 24, fontWeight: 700}}>{VIDEOS[ICELAND].title}</div>
						</div>
					</IPad>
				</div>
				<div style={{position: 'absolute', left: 960 - 1640 * 0.27, top: 330, transformOrigin: '0 0', transform: `translateY(${rise(t, D.rise[1], 800)}px) scale(0.54)`}}>
					<TV>
						<TVHome t={t} f={f} />
					</TV>
				</div>
				<div style={{position: 'absolute', left: 1500, top: 440, transformOrigin: '0 0', transform: `translateY(${rise(t, D.rise[2], 800) + Math.sin(t / 30) * 6}px) scale(0.6) rotateY(-14deg) rotateZ(3deg)`}}>
					<IPhone>
						<ShortsPlayer t={t} f={f} swipeAt={1e9} likeAt={1e9} first="art" />
					</IPhone>
				</div>
			</div>
		</>
	);
};

/* ================================================================ 7. STUDIO */
export const Studio: React.FC<{f: number}> = ({f}) => {
	const S = CUES.studio;
	const t = f - STATIONS.studio.arrive;
	const draw = prog(t, S.drawFrom, S.drawTo, easeInOut);
	const metrics = [
		{i: 'eye' as const, l: 'Views', v: `${(1.24 * draw).toFixed(2)}M`},
		{i: 'users' as const, l: 'New subscribers', v: `+${(12.4 * draw).toFixed(1)}K`},
		{i: 'clock' as const, l: 'Watch time', v: `${(84.3 * draw).toFixed(1)}K hrs`},
		{i: 'dollar' as const, l: 'Estimated revenue', v: `$${Math.round(8420 * draw).toLocaleString('en-US')}`},
	];
	const burst = prog(t, S.milestone, S.milestone + 36);
	return (
		<>
			<div style={{position: 'absolute', left: 110, top: 64, ...lift()}}>
				<Eyebrow f={t} start={S.eyebrow} num="06" label="YouTube Studio" icon="chart" />
				<div style={{height: 24}} />
				<Reveal text="GROW YOUR CHANNEL" f={t} start={S.title} stagger={4} hl={['GROW']} style={H1(80)} {...chip} />
			</div>
			<div style={preserve}>
				<div style={{position: 'absolute', left: 60, top: 270, transformOrigin: '0 0', transform: `translateY(${rise(t, S.mac, 800)}px) scale(0.66) rotateY(5deg)`}}>
					<MacBook>
						<Browser url="studio.youtube.com">
							<div style={{height: 56, display: 'flex', alignItems: 'center', gap: 16, padding: '0 16px', borderBottom: `1px solid ${Y.ui4}`}}>
								<Icon name="menu" size={24} color={Y.text} />
								<PlayIcon h={20} />
								<span style={{fontWeight: 700, fontSize: 20, marginLeft: -10, letterSpacing: '-0.04em'}}>Studio</span>
								<div style={{flex: 1, display: 'flex', justifyContent: 'center'}}>
									<div style={{width: 560, height: 40, borderRadius: 8, border: `1px solid ${Y.ui4}`, display: 'flex', alignItems: 'center', gap: 10, padding: '0 14px', color: '#888', fontSize: 15}}>
										<Icon name="search" size={18} color="#888" /> Search across your channel
									</div>
								</div>
								<div style={{display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 6, border: `1px solid ${Y.ui4}`, fontSize: 14, fontWeight: 500}}>
									<Icon name="create" size={18} color={Y.red} /> CREATE
								</div>
								<ChAvatar c="maya" size={32} />
							</div>
							<div style={{height: 'calc(100% - 57px)'}}>
								<StudioPage t={t} draw={draw} count={draw} />
							</div>
						</Browser>
					</MacBook>
				</div>
			</div>
			{metrics.map((m, i) => {
				const s = spr(t, S.metrics + i * S.metricStep, {damping: 14});
				return (
					<div key={m.l} style={{position: 'absolute', left: 1190, top: 290 + i * 112, opacity: Math.min(1, s * 1.4), transform: `translateZ(${200 + i * 30}px) translateX(${(1 - s) * 260}px) translateY(${Math.sin((t + i * 20) / 30) * 5}px)`}}>
						<div style={{display: 'flex', alignItems: 'center', gap: 16, padding: '14px 24px 14px 14px', borderRadius: 18, background: '#fff', boxShadow: `0 16px 40px ${Y.shadow}`, width: 330}}>
							<div style={{width: 52, height: 52, borderRadius: 14, background: '#FFE5E5', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
								<Icon name={m.i} size={28} color={Y.red} />
							</div>
							<div style={{lineHeight: 1.2, fontFamily: YBODY}}>
								<div style={{fontSize: 15, color: '#666'}}>{m.l}</div>
								<div style={{fontSize: 28, fontWeight: 900, color: Y.ink}}>{m.v}</div>
							</div>
							<div style={{marginLeft: 'auto', color: '#2BA640', fontWeight: 700, fontSize: 15}}>↑</div>
						</div>
					</div>
				);
			})}
			<div style={{position: 'absolute', left: 1580, top: 150, transform: 'translateZ(280px)'}}>
				{t >= S.milestone &&
					new Array(16).fill(0).map((_, i) => {
						const a = (i / 16) * Math.PI * 2;
						const d = 30 + burst * 170;
						return (
							<div key={i} style={{position: 'absolute', left: 140 + Math.cos(a) * d, top: 40 + Math.sin(a) * d, opacity: 1 - burst}}>
								<Sparkle size={22} color={[Y.red, '#FFB800', Y.blue, Y.ink][i % 4]} />
							</div>
						);
					})}
				<div style={{transform: `scale(${spr(t, S.milestone - 4, {damping: 9, stiffness: 200})})`, transformOrigin: '140px 40px'}}>
					<div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '14px 22px', borderRadius: 999, background: Y.ink, color: '#fff', fontFamily: YBODY, fontWeight: 700, fontSize: 20, whiteSpace: 'nowrap', boxShadow: `0 20px 40px ${Y.shadowStrong}`}}>
						<Emoji e="🎉" size={26} /> 100K subscribers!
					</div>
				</div>
			</div>
		</>
	);
};

/* ================================================================ 8. PREMIUM + MUSIC */
export const Premium: React.FC<{f: number}> = ({f}) => {
	const P = CUES.premium;
	const t = f - STATIONS.premium.arrive;
	const welcome = t >= P.welcome;
	const perks = [
		{i: 'noad' as const, l: 'Ad-free videos'},
		{i: 'bgplay' as const, l: 'Background play'},
		{i: 'download' as const, l: 'Downloads'},
		{i: 'music' as const, l: 'YouTube Music Premium'},
	];
	return (
		<>
			<div style={preserve}>
				<div style={{position: 'absolute', left: 150, top: 110, transformOrigin: '0 0', transform: `translateX(${-rise(t, P.phones, 1400)}px) translateY(${Math.sin(t / 30) * 8}px) scale(0.95) rotateY(12deg) rotateZ(-2deg)`}}>
					<IPhone frame="black">
						<MusicPlayer t={t} />
					</IPhone>
				</div>
				<div style={{position: 'absolute', left: 560, top: 160, transformOrigin: '0 0', transform: `translateX(${-rise(t, P.phones + 8, 1600)}px) translateY(${Math.sin(t / 30 + 1.4) * 8}px) scale(0.9) rotateY(6deg) rotateZ(2deg)`}}>
					<IPhone>
						<MobileDownload t={t} f={f} tapAt={P.tap} doneAt={P.done} />
					</IPhone>
				</div>
			</div>
			<div style={{position: 'absolute', left: 1060, top: 110, width: 800, ...lift()}}>
				<Eyebrow f={t} start={P.eyebrow} num="07" label="Premium & Music" icon="music" />
				<div style={{height: 24}} />
				<Reveal text="NO ADS. JUST PLAY." f={t} start={P.title} stagger={4} hl={['PLAY']} style={H1(84)} {...chip} />
				<div style={{height: 18}} />
				<Body f={t} start={P.title + 16} w={720} size={24}>
					Ad-free videos, background play, downloads for the road and all the music you love.
				</Body>
			</div>
			<Card f={t} at={P.card} x={1060} y={470} float={0}>
				<div style={{width: 520, padding: '20px 24px 22px'}}>
					<div style={{display: 'flex', alignItems: 'center', gap: 8}}>
						<PlayIcon h={22} />
						<span style={{fontWeight: 700, fontSize: 24, letterSpacing: '-0.04em'}}>Premium</span>
					</div>
					{perks.map((p, i) => {
						const s = prog(t, P.perks + i * P.perkStep, P.perks + i * P.perkStep + 12);
						return (
							<div key={p.l} style={{display: 'flex', alignItems: 'center', gap: 14, height: 44, opacity: s, transform: `translateX(${(1 - s) * 20}px)`, fontSize: 18, fontWeight: 500}}>
								<Icon name={p.i} size={24} color={Y.ink} />
								<span style={{flex: 1}}>{p.l}</span>
								<Icon name="check" size={20} color="#2BA640" />
							</div>
						);
					})}
					<div style={{marginTop: 14, height: 52, borderRadius: 26, background: welcome ? Y.ink : Y.red, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, fontWeight: 700, fontSize: 18, transform: `scale(${t >= P.click - 2 && t < P.click + 5 ? 0.95 : 1})`}}>
						{welcome ? (
							<>
								<Icon name="check" size={20} color="#fff" /> Welcome to Premium
							</>
						) : (
							'Try it free'
						)}
					</div>
				</div>
			</Card>
			<Cursor t={t} path={[{t: P.cursorIn, x: 1580, y: 980}, {t: P.click - 4, x: 1318, y: 740}, {t: P.click + 16, x: 1330, y: 756}]} clicks={[P.click]} z={242} {...cur} />
		</>
	);
};

/* ================================================================ 9. CTA (+ overview title) */
export const Cta: React.FC<{f: number; scale: number}> = ({f, scale}) => {
	const T = CUES.cta;
	const O = CUES.overview;
	const t = f - STATIONS.cta.arrive;
	const logo = spr(t, T.logo, {damping: 11, stiffness: 130});
	const done = t >= T.done;
	const titleO = prog(f, O.title, O.title + 16) * (1 - prog(f, O.dive, O.dive + 12)) * interpolate(scale, [0.32, 0.5], [1, 0], clamp);
	const cp = prog(t, T.click, T.click + 50);
	return (
		<>
			{titleO > 0.01 && (
				<div style={{position: 'absolute', left: -2000, right: -2000, top: 540 - 320, opacity: titleO, display: 'flex', justifyContent: 'center', transform: 'translateZ(900px)'}}>
					<Reveal text={'PRESS PLAY ON\nEVERYTHING.'} f={f} start={O.title} stagger={4} hl={['EVERYTHING']} align="center" style={{...H1(280), lineHeight: 1.05}} {...chip} />
				</div>
			)}
			<div style={{position: 'absolute', left: 0, right: 0, top: 260, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 34, transform: `translateZ(90px) scale(${logo})`, opacity: t >= T.logo - 1 ? 1 : 0}}>
				<PlayIcon h={150} style={{filter: 'drop-shadow(0 24px 40px rgba(255,0,0,0.35))'}} />
				<div style={{fontFamily: YBODY, fontWeight: 700, fontSize: 170, letterSpacing: '-0.06em', color: Y.ink, lineHeight: 1}}>
					{'YouTube'.split('').map((ch, i) => {
						const p = prog(t, T.wordmark + i * 2, T.wordmark + 16 + i * 2);
						return (
							<span key={i} style={{display: 'inline-block', opacity: p, transform: `translateY(${(1 - p) * 40}px)`}}>
								{ch}
							</span>
						);
					})}
				</div>
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, top: 500, display: 'flex', justifyContent: 'center', ...lift(60)}}>
				<Reveal text="BROADCAST YOURSELF." f={t} start={T.line} stagger={4} hl={['YOURSELF']} align="center" style={H1(64)} {...chip} />
			</div>
			<div style={{position: 'absolute', left: 618, top: 640, display: 'flex', gap: 24, ...lift(40)}}>
				{[
					{x: done ? 'Opening…' : 'Open YouTube', bg: Y.red, fg: '#fff', icon: (done ? 'check' : 'play') as 'check' | 'play', w: 340},
					{x: 'Get the app', bg: Y.ink, fg: '#fff', icon: 'phone' as const, w: 320},
				].map((b, i) => {
					const s = spr(t, T.buttons[i], {damping: 12});
					const press = i === 0 && t >= T.click - 2 && t < T.click + 5 ? 0.95 : 1;
					return (
						<div key={i} style={{width: b.w, height: 76, transform: `scale(${s * press})`, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14, borderRadius: 40, background: b.bg, color: b.fg, fontFamily: YBODY, fontWeight: 700, fontSize: 26, boxShadow: `0 18px 50px ${i === 0 ? 'rgba(255,0,0,0.35)' : Y.shadowStrong}`}}>
							<Icon name={b.icon} size={26} color={b.fg} />
							{b.x}
						</div>
					);
				})}
			</div>
			<div style={{position: 'absolute', left: 0, right: 0, top: 770, textAlign: 'center', fontFamily: YBODY, fontWeight: 700, fontSize: 30, color: Y.ink, letterSpacing: '0.06em', opacity: prog(t, T.url, T.url + 14), ...lift(40)}}>youtube.com</div>
			<Cursor t={t} path={[{t: T.cursorIn, x: 1240, y: 980}, {t: T.click - 4, x: 780, y: 682}, {t: 236, x: 792, y: 700}]} clicks={[T.click]} z={42} {...cur} />
			{t >= T.click &&
				new Array(36).fill(0).map((_, i) => {
					const a = (i / 36) * Math.PI * 2 + (i % 3) * 0.2;
					const v = 260 + ((i * 53) % 220);
					return (
						<Sparkle
							key={i}
							size={14 + ((i * 7) % 16)}
							color={[Y.red, '#FFB800', Y.ink, Y.blue][i % 4]}
							style={{position: 'absolute', left: 788 + Math.cos(a) * v * cp, top: 678 + Math.sin(a) * v * cp + cp * cp * 160, opacity: 1 - prog(t, T.click + 30, T.click + 60), transform: `translateZ(${60 + (i % 5) * 40}px) rotate(${t * 6 + i * 20}deg)`}}
						/>
					);
				})}
		</>
	);
};

export {CH};
