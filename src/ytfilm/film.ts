/* YouTube brand film (cinematic, scene-based) — timing for scenes, per-scene cameras, cues, SFX and
 * music arrangement. Loaded by Remotion and by scripts/make_audio.py (via `node`).
 * 30 fps, 120 BPM: beat = 15 frames, bar = 60 frames. Scene changes and audible cues sit on the grid. */
import {type CamKey, type Cam, cameraSpeed, createCamera} from '../engine/camera.ts';

export const FPS = 30;
export const DURATION = 1800;
export const PERSPECTIVE = 1600;

export const SCENES = {
	intro: {from: 0, to: 150},
	hero: {from: 150, to: 390},
	phone: {from: 390, to: 630},
	moods: {from: 630, to: 930},
	land: {from: 930, to: 1290},
	carousel: {from: 1290, to: 1560},
	logo: {from: 1560, to: 1800},
};
export type SceneId = keyof typeof SCENES;

export const MOODS = [
	{id: 'gaming', word: 'GAMING', label: 'Your Gaming Feed', bg: '#3A1CFF', ink: '#E9FF5B', outline: 'rgba(233,255,91,0.16)', at: 630},
	{id: 'music', word: 'MUSIC', label: 'Your Music Mix', bg: '#F45DA4', ink: '#3B0A2A', outline: 'rgba(59,10,42,0.14)', at: 705},
	{id: 'learn', word: 'LEARN', label: 'Learn Something New', bg: '#C8F25A', ink: '#1F2366', outline: 'rgba(31,35,102,0.14)', at: 780},
	{id: 'night', word: 'LATE\nNIGHT', label: 'Late Night Binge', bg: '#1C2A5E', ink: '#FFD36B', outline: 'rgba(255,211,107,0.12)', at: 855},
] as const;
export const MOOD_LEN = 75;

/* cues: absolute frames */
export const CUE = {
	intro: {dot: 12, rings: 18, words: [36, 48, 60, 72, 84], land: 105, out: 128},
	hero: {enter: 150, fan: 270, fanStep: 3.75, title: 285, out: 360},
	phone: {enter: 390, title: 450, ring: 480, tap: 495, out: 612},
	land: {title: 942, tilt: 990, counter: 1050, counterTo: 1110, words: [1140, 1170, 1200], all: 1230},
	carousel: {title: 1320, collapse: 1500},
	logo: {flatten: 1620, tri: 1642.5, wordmark: 1665, tagline: 1695, button: 1717.5},
};

/* ---------------------------------------------------------------- per-scene cameras (scene-local world) */
const K = (keys: CamKey[]) => createCamera(keys);
export const CAMS: Record<SceneId, (f: number) => Cam> = {
	intro: K([
		{f: 0, x: 0, y: 0, d: 1700, yaw: 0, pitch: 0},
		{f: 150, x: 0, y: 0, d: 1500, yaw: 2, pitch: 1},
	]),
	hero: K([
		{f: 150, x: 0, y: 0, d: 520, yaw: -28, pitch: 12, roll: -6},
		{f: 210, x: 0, y: 0, d: 1150, yaw: -16, pitch: 8, roll: -3},
		{f: 270, x: -60, y: 0, d: 1600, yaw: -8, pitch: 4},
		{f: 330, x: -20, y: -10, d: 1800, yaw: 5, pitch: 3},
		{f: 390, x: 120, y: 0, d: 1150, yaw: 12, pitch: 2},
	]),
	phone: K([
		{f: 390, x: 240, y: 0, d: 1050, yaw: 24, pitch: 6, roll: 3},
		{f: 470, x: 0, y: 0, d: 1550, yaw: 8, pitch: 3, roll: 1},
		{f: 540, x: -40, y: 20, d: 1500, yaw: 0, pitch: 2},
		{f: 630, x: 240, y: -262, d: 820, yaw: -8, pitch: 2},
	]),
	moods: K([
		{f: 630, x: 0, y: 0, d: 1600, yaw: 0, pitch: 0},
		{f: 930, x: 0, y: 0, d: 1600, yaw: 0, pitch: 0},
	]),
	land: K([
		{f: 930, x: 0, y: -40, d: 1600, yaw: 0, pitch: 0},
		{f: 990, x: 0, y: -40, d: 1600, yaw: 0, pitch: 0},
		{f: 1060, x: 0, y: -260, d: 1500, yaw: -8, pitch: 28},
		{f: 1170, x: 260, y: -220, d: 1250, yaw: -22, pitch: 22, roll: -2},
		{f: 1290, x: 520, y: -160, d: 1050, yaw: -34, pitch: 16, roll: -3},
	]),
	carousel: K([
		{f: 1290, x: 0, y: 40, d: 2300, yaw: 0, pitch: 10},
		{f: 1420, x: 0, y: 20, d: 2050, yaw: 0, pitch: 7},
		{f: 1560, x: 0, y: 0, d: 1700, yaw: 0, pitch: 3},
	]),
	logo: K([
		{f: 1560, x: 0, y: 0, d: 1600, yaw: 0, pitch: 0},
		{f: 1800, x: 0, y: 0, d: 1480, yaw: 0, pitch: 0},
	]),
};
export const sceneAt = (f: number): SceneId => (Object.keys(SCENES) as SceneId[]).find((k) => f >= SCENES[k].from && f < SCENES[k].to) ?? 'logo';
const combined = (f: number) => CAMS[sceneAt(f)](f);
export const CAM_SPEED = cameraSpeed(combined, DURATION, PERSPECTIVE).map((v, f) => (Object.values(SCENES).some((s) => f === s.from - 1) ? 0 : v));

/* ---------------------------------------------------------------- music: Am – F – C – G, scored per bar */
export const MUSIC = {
	chords: [
		[[57, 60, 64, 69], 33],
		[[57, 60, 65, 69], 41],
		[[55, 60, 64, 67], 36],
		[[55, 59, 62, 67], 43],
	],
	// one entry per 2 s bar: intro (pads) → build (pads + arp) → A (beat) → B (beat + extras) → break → end
	sections: [
		'intro', 'intro', 'intro', 'intro',
		'break', 'break', 'break', 'break', 'break', 'break',
		'A', 'A', 'A', 'A', 'A',
		'B', 'B', 'B', 'B', 'B', 'B',
		'break', 'break', 'break', 'break', 'break',
		'B', 'B', 'B',
		'end',
	],
	endChord: 2, // resolve on C
};

/* ---------------------------------------------------------------- SFX */
export type Sfx = {f: number; type: string; gain?: number; pan?: number; step?: number; dur?: number};
const buildSfx = (): Sfx[] => {
	const s: Sfx[] = [];
	const add = (f: number, type: string, o: Omit<Sfx, 'f' | 'type'> = {}) => s.push({f, type, ...o});
	const I = CUE.intro;
	add(I.dot, 'pop', {step: 0, gain: 0.8});
	I.words.forEach((w, i) => add(w, 'pluck', {step: i, gain: 0.75}));
	add(I.land, 'chime', {step: 0});
	add(I.out, 'swell', {dur: (SCENES.hero.from - I.out) / FPS});
	const H = CUE.hero;
	add(H.enter, 'impact', {gain: 0.8});
	for (let i = 0; i < 6; i++) add(H.fan + i * H.fanStep, 'pluck', {step: i + 1, gain: 0.7, pan: 0.15 * i});
	add(H.title, 'shimmer', {gain: 0.6});
	add(H.out, 'swell', {dur: (SCENES.phone.from - H.out) / FPS});
	const P = CUE.phone;
	add(P.title, 'pluck', {step: 2, gain: 0.7});
	add(P.ring, 'swell', {dur: 0.5, gain: 0.6});
	add(P.tap, 'click');
	add(P.tap + 3.75, 'chime', {step: 1});
	add(SCENES.moods.from - 30, 'riser', {dur: 1});
	MOODS.forEach((m, i) => {
		add(m.at, 'impact', {gain: 0.55});
		add(m.at, 'chime', {step: i + 1, gain: 0.8});
		add(m.at + 7.5, 'swipe', {gain: 0.7});
	});
	add(SCENES.land.from, 'impact', {gain: 0.5});
	const L = CUE.land;
	add(L.title, 'pluck', {step: 0, gain: 0.7});
	add(L.tilt, 'swell', {dur: 2});
	for (let t = L.counter; t < L.counterTo; t += 7.5) add(t, 'tick', {gain: 0.8});
	add(L.counterTo, 'pop', {step: 2});
	L.words.forEach((w, i) => add(w, 'pop', {step: i + 3}));
	add(L.all, 'shimmer', {gain: 0.7});
	const C = CUE.carousel;
	add(C.title, 'chime', {step: 2});
	add(C.title, 'shimmer', {gain: 0.5});
	add(C.collapse, 'riser', {dur: (SCENES.logo.from - C.collapse) / FPS});
	const G = CUE.logo;
	add(SCENES.logo.from, 'impact');
	add(G.flatten, 'pop', {step: 0});
	add(G.tri, 'pluck', {step: 4});
	add(G.wordmark, 'swipe', {gain: 0.8});
	add(G.tagline, 'chime', {step: 0});
	add(G.button, 'pop', {step: 2});
	add(G.button, 'shimmer', {gain: 0.5});
	return s.sort((a, b) => a.f - b.f);
};
export const SFX = buildSfx();
