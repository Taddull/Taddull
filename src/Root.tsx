import React from 'react';
import {Composition} from 'remotion';
import {PassengerChart} from './PassengerChart';
import {NIGHTLY_SEARCH_DURATION, NightlySearch} from './NightlySearch';
import {WINTER_NIGHTS_DURATION, WinterNights} from './WinterNights';

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
			id="NightlySearch"
			component={NightlySearch}
			durationInFrames={NIGHTLY_SEARCH_DURATION}
			fps={30}
			width={1920}
			height={1080}
		/>
		<Composition
			id="WinterNights"
			component={WinterNights}
			durationInFrames={WINTER_NIGHTS_DURATION}
			fps={30}
			width={1920}
			height={1080}
		/>
	</>
);
