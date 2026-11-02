import React from 'react';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame} from 'remotion';
import {prog} from '../youtube/kit';
import '../youtube/theme';
import {SCENES} from './film';
import {CarouselScene, HeroScene, IntroScene, LandScene, LogoScene, MoodsScene, PhoneScene} from './scenes';

/* Cinematic YouTube brand film: seven scenes joined by a dot-zoom, crossfades and circle wipes.
 * Timing, cameras, SFX and score live in ./film.ts. */
export const YouTubeFilm: React.FC = () => {
	const f = useCurrentFrame();
	const S = SCENES;
	const live = (from: number, to: number) => f >= from && f < to;
	return (
		<AbsoluteFill style={{background: '#050505', overflow: 'hidden'}}>
			<Audio src={staticFile('youtube-film-music.mp3')} />
			{live(S.intro.from, S.intro.to + 10) && (
				<AbsoluteFill style={{opacity: 1 - prog(f, S.intro.to, S.intro.to + 10)}}>
					<IntroScene f={f} />
				</AbsoluteFill>
			)}
			{live(S.hero.from, S.hero.to + 14) && (
				<AbsoluteFill style={{opacity: prog(f, S.hero.from, S.hero.from + 10) * (1 - prog(f, S.hero.to, S.hero.to + 14)), transform: `scale(${1 + prog(f, S.hero.to - 10, S.hero.to + 14) * 0.25})`}}>
					<HeroScene f={f} />
				</AbsoluteFill>
			)}
			{live(S.phone.from, S.moods.from + 16) && (
				<AbsoluteFill style={{opacity: prog(f, S.phone.from, S.phone.from + 14)}}>
					<PhoneScene f={f} />
				</AbsoluteFill>
			)}
			{live(S.moods.from, S.land.from + 16) && <MoodsScene f={f} />}
			{live(S.land.from, S.land.to + 14) && (
				<AbsoluteFill style={{opacity: 1 - prog(f, S.land.to, S.land.to + 14)}}>
					<LandScene f={f} />
				</AbsoluteFill>
			)}
			{live(S.carousel.from, S.carousel.to + 8) && (
				<AbsoluteFill style={{opacity: prog(f, S.carousel.from, S.carousel.from + 14) * (1 - prog(f, S.carousel.to, S.carousel.to + 8))}}>
					<CarouselScene f={f} />
				</AbsoluteFill>
			)}
			{live(S.logo.from, S.logo.to) && (
				<AbsoluteFill style={{opacity: prog(f, S.logo.from - 2, S.logo.from + 6)}}>
					<LogoScene f={f} />
				</AbsoluteFill>
			)}
		</AbsoluteFill>
	);
};
