import React from 'react';
import {CLYDE_PATH} from '../discord/primitives';
import {Extrude} from '../ytfilm/objects';

/* rounded-square app badge (24x24 box) with Clyde centred inside it */
export const BADGE_D = 'M6 0h12a6 6 0 0 1 6 6v12a6 6 0 0 1-6 6H6a6 6 0 0 1-6-6V6a6 6 0 0 1 6-6z';
export const CLYDE_IN_BADGE = 'translate(4.2 4.26) scale(0.65)';

export const Badge3D: React.FC<{w: number; sheen: number; clyde?: number}> = ({w, sheen, clyde = 1}) => (
	<Extrude
		id="dcb"
		w={w}
		h={w}
		viewBox="0 0 24 24"
		d={BADGE_D}
		depth={w * 0.13}
		layers={26}
		front={['#8C95FF', '#4752C4']}
		side={['#3A44B0', '#0E1240']}
		sheen={sheen}
		inlayDepth={w * 0.03}
		inlay={
			<g style={{transform: `scale(${clyde})`, transformOrigin: '12px 12px'}}>
				<path d={CLYDE_PATH} fill="rgba(10,14,60,0.35)" transform={`translate(0.3 0.4) ${CLYDE_IN_BADGE}`} />
				<path d={CLYDE_PATH} fill="#fff" transform={CLYDE_IN_BADGE} />
			</g>
		}
	/>
);

const BOOK_D = 'M50 14 C38 5 20 3 4 7 V64 C20 60 38 62 50 70 Z M50 14 C62 5 80 3 96 7 V64 C80 60 62 62 50 70 Z';
export const Book3D: React.FC<{w: number; sheen: number}> = ({w, sheen}) => (
	<Extrude
		id="book"
		w={w}
		h={(w * 72) / 100}
		viewBox="0 0 100 72"
		d={BOOK_D}
		depth={w * 0.12}
		front={['#FFFFFF', '#D9DCF8']}
		side={['#5865F2', '#1A2070']}
		sheen={sheen}
		inlayDepth={1.5}
		inlay={
			<g stroke="#5865F2" strokeWidth="2.2" strokeLinecap="round" fill="none" opacity={0.75}>
				<path d="M14 20 C24 18 34 19 42 23 M14 30 C24 28 34 29 42 33 M14 40 C24 38 34 39 42 43 M14 50 C22 48 30 49 36 52" />
				<path d="M58 23 C66 19 76 18 86 20 M58 33 C66 29 76 28 86 30 M58 43 C66 39 76 38 86 40" />
				<path d="M50 15 V69" stroke="#9AA2FA" />
			</g>
		}
	/>
);

const PALETTE_D =
	'M50 2 C80 2 100 22 98 46 C96 62 82 64 74 60 C66 56 60 62 64 70 C68 80 60 88 46 88 C20 88 2 70 2 44 C2 20 22 2 50 2 Z M30 58 A7 7 0 1 0 30 72 A7 7 0 1 0 30 58 Z';
export const Palette3D: React.FC<{w: number; sheen: number}> = ({w, sheen}) => (
	<Extrude
		id="pal"
		w={w}
		h={(w * 90) / 100}
		viewBox="0 0 100 90"
		d={PALETTE_D}
		evenodd
		depth={w * 0.1}
		front={['#FFE9BF', '#EDB96B']}
		side={['#C98A3A', '#4A2A08']}
		sheen={sheen}
		inlayDepth={3}
		inlay={
			<g>
				{[
					[30, 24, '#5865F2'],
					[52, 16, '#EB459E'],
					[74, 26, '#FEE75C'],
					[82, 46, '#57F287'],
					[20, 42, '#ED4245'],
				].map(([x, y, c], i) => (
					<g key={i}>
						<circle cx={x as number} cy={y as number} r="7.5" fill={c as string} />
						<circle cx={(x as number) - 2.4} cy={(y as number) - 2.4} r="2.2" fill="rgba(255,255,255,0.55)" />
					</g>
				))}
			</g>
		}
	/>
);

const BOLT_D = 'M38 0 L4 58 H28 L20 100 L56 38 H32 Z';
export const Bolt3D: React.FC<{w: number; sheen: number}> = ({w, sheen}) => (
	<Extrude id="bolt" w={w} h={(w * 100) / 60} viewBox="0 0 60 100" d={BOLT_D} depth={w * 0.22} front={['#A3AAFF', '#5865F2']} side={['#4752C4', '#141A5E']} sheen={sheen} />
);
