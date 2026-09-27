import React from 'react';
import {Composition} from 'remotion';
import {PassengerChart} from './PassengerChart';
import {RealityKicksIn} from './RealityKicksIn';

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
			id="RealityKicksIn"
			component={RealityKicksIn}
			durationInFrames={240}
			fps={24}
			width={1920}
			height={1080}
		/>
	</>
);
