import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame} from 'remotion';
import {C} from './theme';
import {Backdrop, Foreground, Journey, Layer, Station, camAt} from './world';
import {AppStation, Apps, Cta, Devices, Hero, Intro, Live, Roles, Voice} from './stations';

/* One continuous camera move across a single Blurple canvas — no cuts.
 * Camera path, cues and SFX all live in ./timeline.ts. */
export const DiscordPromo: React.FC = () => {
	const f = useCurrentFrame();
	const cam = camAt(f);
	return (
		<AbsoluteFill style={{background: C.bg, overflow: 'hidden'}}>
			<Audio src={staticFile('discord-promo-music.mp3')} />
			<Backdrop cam={cam} f={f} />
			<Layer cam={cam}>
				<Journey cam={cam} />
				<Station id="intro" cam={cam}>
					<Intro f={f} />
				</Station>
				<Station id="hero" cam={cam}>
					<Hero f={f} />
				</Station>
				<Station id="app" cam={cam} hw={1800}>
					<AppStation f={f} />
				</Station>
				<Station id="voice" cam={cam}>
					<Voice f={f} />
				</Station>
				<Station id="live" cam={cam}>
					<Live f={f} />
				</Station>
				<Station id="devices" cam={cam}>
					<Devices f={f} />
				</Station>
				<Station id="apps" cam={cam}>
					<Apps f={f} />
				</Station>
				<Station id="roles" cam={cam}>
					<Roles f={f} />
				</Station>
				<Station id="cta" cam={cam} hw={2600}>
					<Cta f={f} camZ={cam.z} />
				</Station>
			</Layer>
			<Foreground cam={cam} f={f} />
		</AbsoluteFill>
	);
};
