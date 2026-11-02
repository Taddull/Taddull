import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame} from 'remotion';
import {C} from './theme';
import {sampleCam} from './timeline';
import {Decor, Environment, Journey, Scene3D, Sky, Station, Vignette} from './world';
import {AppStation, Apps, Cta, Devices, Hero, Intro, Live, Roles, Voice} from './stations';

/* One continuous 3D camera: it orbits, dollies and tilts across a gallery wall of feature stations,
 * diving into menus and UI details, with no cuts. Camera path, cues and SFX live in ./timeline.ts. */
export const DiscordPromo: React.FC = () => {
	const f = useCurrentFrame();
	const cam = sampleCam(f);
	return (
		<AbsoluteFill style={{background: C.bg, overflow: 'hidden'}}>
			<Audio src={staticFile('discord-promo-music.mp3')} />
			<Sky />
			<Scene3D cam={cam}>
				<Environment f={f} />
				<Journey cam={cam} />
				<Station id="intro" cam={cam}>
					<Intro f={f} />
				</Station>
				<Station id="hero" cam={cam}>
					<Hero f={f} />
				</Station>
				<Station id="app" cam={cam}>
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
				<Station id="cta" cam={cam}>
					<Cta f={f} camZ={1600 / cam.d} />
				</Station>
				<Decor f={f} />
			</Scene3D>
			<Vignette />
		</AbsoluteFill>
	);
};
