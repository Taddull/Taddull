import React from 'react';
import {AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {C, clamp, easeIn, easeOut, prog} from './theme';
import {Chat, Hero, Intro, Servers} from './scenes1';
import {GoLive, Roles, Stage, Voice} from './scenes2';
import {Apps, Bento, Devices, Nitro, Outro, Stats} from './scenes3';

const TAIL = 14; // overlap frames for cross transitions

type SceneDef = {id: string; from: number; to: number; C: React.FC};
export const SCENES: SceneDef[] = [
	{id: 'intro', from: 0, to: 240, C: Intro},
	{id: 'hero', from: 240, to: 540, C: Hero},
	{id: 'servers', from: 540, to: 840, C: Servers},
	{id: 'chat', from: 840, to: 1200, C: Chat},
	{id: 'voice', from: 1200, to: 1500, C: Voice},
	{id: 'golive', from: 1500, to: 1800, C: GoLive},
	{id: 'stage', from: 1800, to: 2040, C: Stage},
	{id: 'roles', from: 2040, to: 2340, C: Roles},
	{id: 'apps', from: 2340, to: 2640, C: Apps},
	{id: 'nitro', from: 2640, to: 2880, C: Nitro},
	{id: 'devices', from: 2880, to: 3120, C: Devices},
	{id: 'stats', from: 3120, to: 3240, C: Stats},
	{id: 'bento', from: 3240, to: 3420, C: Bento},
	{id: 'outro', from: 3420, to: 3600, C: Outro},
];

/* zoom-blur crossfade wrapper */
const Shell: React.FC<{dur: number; children: React.ReactNode; first?: boolean; last?: boolean}> = ({dur, children, first, last}) => {
	const f = useCurrentFrame();
	const inP = first ? 1 : prog(f, 0, TAIL, easeOut);
	const outP = last ? 0 : prog(f, dur, dur + TAIL, easeIn);
	const scale = (1 - inP) * -0.06 + 1 + outP * 0.12;
	const blur = (1 - inP) * 14 + outP * 18;
	return (
		<AbsoluteFill
			style={{
				opacity: Math.min(inP, 1 - outP),
				transform: `scale(${scale})`,
				filter: blur > 0.3 ? `blur(${blur}px)` : undefined,
			}}
		>
			{children}
		</AbsoluteFill>
	);
};

/* diagonal brand-colour shutter that sweeps across a cut */
const Shutter: React.FC<{at: number}> = ({at}) => {
	const f = useCurrentFrame();
	const colors = [C.blurple, C.fuchsia, '#0B0D2E'];
	if (f < at - 14 || f > at + 16) return null;
	return (
		<AbsoluteFill style={{overflow: 'hidden', pointerEvents: 'none'}}>
			{colors.map((c, i) => {
				const p = interpolate(f, [at - 12 + i * 2, at + 12 + i * 2], [0, 1], {...clamp, easing: easeOut});
				const x = interpolate(p, [0, 1], [-2600, 2600]);
				return (
					<div
						key={i}
						style={{
							position: 'absolute',
							top: -400,
							left: 0,
							width: 1100 - i * 250,
							height: 1900,
							background: c,
							transform: `translateX(${x}px) rotate(18deg)`,
						}}
					/>
				);
			})}
		</AbsoluteFill>
	);
};

export const SHUTTERS = [540, 1200, 1800, 2340, 2880, 3420];

export const DiscordPromo: React.FC = () => {
	return (
		<AbsoluteFill style={{background: C.space}}>
			<Audio src={staticFile('discord-promo-music.mp3')} />
			{SCENES.map((s, i) => (
				<Sequence key={s.id} from={s.from} durationInFrames={s.to - s.from + TAIL} name={s.id}>
					<Shell dur={s.to - s.from} first={i === 0} last={i === SCENES.length - 1}>
						<s.C />
					</Shell>
				</Sequence>
			))}
			{SHUTTERS.map((at) => (
				<Shutter key={at} at={at} />
			))}
		</AbsoluteFill>
	);
};
