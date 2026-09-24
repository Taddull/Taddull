import React from 'react';
import {Composition} from 'remotion';
import {PassengerChart} from './PassengerChart';

export const RemotionRoot: React.FC = () => (
	<Composition
		id="PassengerChart"
		component={PassengerChart}
		durationInFrames={300}
		fps={30}
		width={1920}
		height={1080}
	/>
);
