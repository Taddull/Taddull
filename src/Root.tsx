import React from 'react';
import {Composition} from 'remotion';
import {PassengerChart} from './PassengerChart';
import {DiscordPromo} from './discord/DiscordPromo';
import {YouTubePromo} from './youtube/YouTubePromo';

export const RemotionRoot: React.FC = () => (
	<>
		<Composition
			id="PassengerChart"
			component={PassengerChart}
			durationInFrames={300}
			fps={30}
			width={1920}
			height={1080}
		/>
		<Composition
			id="DiscordPromo"
			component={DiscordPromo}
			durationInFrames={1800}
			fps={30}
			width={1920}
			height={1080}
		/>
		<Composition
			id="YouTubePromo"
			component={YouTubePromo}
			durationInFrames={1800}
			fps={30}
			width={1920}
			height={1080}
		/>
	</>
);
