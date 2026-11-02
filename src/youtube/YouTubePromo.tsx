import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame} from 'remotion';
import {Decor, Environment, Journey, Scene3D, StationFrame, placeDecor} from '../engine/scene3d';
import {Spark, Sticker} from './kit';
import {Cta, Devices, Hero, HomeStation, Intro, Live, Premium, Shorts, Studio} from './stations';
import {ORDER, PERSPECTIVE, SX, SY, StationId, center, sampleCam} from './timeline';
import {Y} from './theme';

const ENV = {dot: 'rgba(15,15,15,0.13)', floorDot: 'rgba(15,15,15,0.16)', glow: 'rgba(255,0,0,0.05)', wallZ: -520};
const POINTS = ORDER.map((id) => center(id));
const DECOR = placeDecor(POINTS, ['▶', '🎬', '🔔', '❤️', '👍', '🎧', '🍿', '📺', '🎮', '🔥', '💬', '🎸'], 'yt');

const STATIONS: [StationId, React.FC<{f: number}>][] = [
	['intro', Intro],
	['hero', Hero],
	['home', HomeStation],
	['shorts', Shorts],
	['live', Live],
	['devices', Devices],
	['studio', Studio],
	['premium', Premium],
];

/* YouTube commercial: one continuous 3D camera across a gallery wall of feature stations.
 * Camera path, cues, SFX and harmony live in ./timeline.ts. */
export const YouTubePromo: React.FC = () => {
	const f = useCurrentFrame();
	const cam = sampleCam(f);
	return (
		<AbsoluteFill style={{background: Y.canvas, overflow: 'hidden'}}>
			<Audio src={staticFile('youtube-promo-music.mp3')} />
			<AbsoluteFill style={{background: `radial-gradient(120% 90% at 30% 0%, ${Y.canvasHi} 0%, ${Y.canvas} 50%, ${Y.canvasLo} 100%)`}} />
			<Scene3D cam={cam} perspective={PERSPECTIVE}>
				<Environment f={f} theme={ENV} x0={-2600} y0={-1900} w={10600} h={6400} floorY={2 * SY + 950} />
				<Journey cam={cam} points={POINTS} color="rgba(255,0,0,0.45)" z={-480} />
				{STATIONS.map(([id, C]) => {
					const c = center(id);
					return (
						<StationFrame key={id} x={c.x} y={c.y} cam={cam} perspective={PERSPECTIVE}>
							<C f={f} />
						</StationFrame>
					);
				})}
				<StationFrame x={center('cta').x} y={center('cta').y} cam={cam} perspective={PERSPECTIVE}>
					<Cta f={f} scale={PERSPECTIVE / cam.d} />
				</StationFrame>
				<Decor f={f} items={DECOR} sticker={Sticker} spark={Spark} />
			</Scene3D>
			<AbsoluteFill style={{background: 'radial-gradient(85% 80% at 50% 50%, transparent 60%, rgba(15,15,15,0.14) 100%)'}} />
		</AbsoluteFill>
	);
};

export {SX};
