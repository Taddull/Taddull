import {Easing, interpolate, spring} from 'remotion';
import '@fontsource-variable/archivo/wdth.css';
import '@fontsource/figtree/400.css';
import '@fontsource/figtree/500.css';
import '@fontsource/figtree/600.css';
import '@fontsource/figtree/700.css';
import '@fontsource/figtree/800.css';
import '@fontsource/jetbrains-mono/500.css';

export const FPS = 30;
export const W = 1920;
export const H = 1080;

// Discord brand palette + client UI greys
export const C = {
	blurple: '#5865F2',
	blurpleDeep: '#404EED',
	blurpleSoft: '#949CF7',
	green: '#57F287',
	yellow: '#FEE75C',
	fuchsia: '#EB459E',
	red: '#ED4245',
	white: '#FFFFFF',
	black: '#23272A',
	space: '#070818',
	space2: '#0E1030',
	rail: '#1E1F22',
	side: '#2B2D31',
	chat: '#313338',
	input: '#383A40',
	hover: '#35373C',
	floating: '#111214',
	userPanel: '#232428',
	text: '#F2F3F5',
	body: '#DBDEE1',
	muted: '#B5BAC1',
	faint: '#949BA4',
	channel: '#80848E',
	online: '#23A55A',
	idle: '#F0B232',
	dnd: '#F23F43',
	link: '#00A8FC',
	// one-take canvas theme: Discord Blurple world, white type, not-quite-black ink
	bg: '#5865F2',
	bgHi: '#7C86F6',
	bgLo: '#3F49C9',
	ink: '#23272A',
	shadow: 'rgba(16,20,82,0.45)',
};

// Discord's headline face is ABC Ginto Nord (wide, heavy grotesk) and UI face is gg sans.
// Both are proprietary, so we use the closest open equivalents:
//   Ginto Nord  -> Archivo, expanded width axis (125%), weight 800-900
//   gg sans     -> Figtree
export const DISPLAY = '"Archivo Variable", "Archivo", sans-serif';
export const BODY = 'Figtree, "Noto Sans", sans-serif';
export const MONO = '"JetBrains Mono", monospace';
export const EMOJI = '"Noto Color Emoji"';

export const display = (size: number, weight = 900): React.CSSProperties => ({
	fontFamily: DISPLAY,
	fontStretch: '125%',
	fontWeight: weight,
	fontSize: size,
	lineHeight: 0.98,
	letterSpacing: '-0.01em',
	textTransform: 'uppercase',
});

export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);
export const easeIn = Easing.bezier(0.7, 0, 0.84, 0);
export const backOut = Easing.bezier(0.34, 1.56, 0.64, 1);

/** 0..1 progress between frames a and b */
export const prog = (f: number, a: number, b: number, easing = easeOut) =>
	interpolate(f, [a, b], [0, 1], {...clamp, easing});

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export const spr = (
	f: number,
	delay: number,
	cfg: {damping?: number; stiffness?: number; mass?: number} = {},
) =>
	spring({
		frame: f - delay,
		fps: FPS,
		config: {damping: 14, stiffness: 140, mass: 0.9, ...cfg},
	});

/** in/out envelope: rises over [a,a+r], holds, falls over [b-r,b] */
export const env = (f: number, a: number, b: number, r = 10) =>
	Math.min(prog(f, a, a + r), 1 - prog(f, b - r, b, easeIn));
