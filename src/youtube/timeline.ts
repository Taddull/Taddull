/* YouTube promo — single source of truth for the 3D one-take: camera path, per-station cues, SFX and
 * music harmony. Loaded by Remotion and by scripts/make_audio.py (via `node`).
 * 30 fps, 120 BPM -> beat = 15 frames, 8th = 7.5, 16th = 3.75, bar = 60. Cues sit on that grid. */
import {type CamKey, cameraSpeed, createCamera} from '../engine/camera.ts';

export const FPS = 30;
export const DURATION = 1800;
export const PERSPECTIVE = 1600;
export const SX = 2200;
export const SY = 1250;

export type StationId = 'intro' | 'hero' | 'home' | 'shorts' | 'live' | 'devices' | 'studio' | 'premium' | 'cta';
export const STATIONS: Record<StationId, {col: number; row: number; arrive: number}> = {
	intro: {col: 0, row: 0, arrive: 0},
	hero: {col: 1, row: 0, arrive: 195},
	home: {col: 2, row: 0, arrive: 375},
	shorts: {col: 2, row: 1, arrive: 750},
	live: {col: 2, row: 2, arrive: 930},
	devices: {col: 1, row: 2, arrive: 1050},
	studio: {col: 0, row: 2, arrive: 1170},
	premium: {col: 0, row: 1, arrive: 1320},
	cta: {col: 1, row: 1, arrive: 1560},
};
export const WATCH_ARRIVE = 555; // second half of the home station: same MacBook, now on the watch page
export const ORDER: StationId[] = ['intro', 'hero', 'home', 'shorts', 'live', 'devices', 'studio', 'premium', 'cta'];
export const center = (id: StationId) => ({x: STATIONS[id].col * SX, y: STATIONS[id].row * SY});

/* ---------------------------------------------------------------- cues (frames relative to arrival) */
export const CUES = {
	intro: {words: [15, 30, 45], wordsOut: 75, logo: 90, wordmark: 105, tagline: 120},
	hero: {title: -30, mac: -30, phoneL: -15, phoneR: -8, views: 30, notify: 52.5, react: 90},
	home: {mac: -45, eyebrow: -30, title: -22, chips: 0, chipStep: 3.75, grid: 22.5, cursorIn: 75, hover: 105, click: 120},
	watch: {enter: -45, eyebrow: -22, title: -15, like: 45, subscribe: 75, toast: 82.5, comments: 97.5},
	shorts: {eyebrow: -30, title: -22, phoneA: -45, phoneB: -30, swipe: 30, like: 60, rec: 105, callout: 75},
	live: {eyebrow: -30, title: -22, mac: -45, phone: -15, composer: 15, pick: 45, send: 67.5, chat: [0, 22.5, 37.5, 52.5, 90, 112.5], superchat: 75, superchat2: 105, viewers: 30},
	devices: {rise: [-34, -28, -22, -16], eyebrow: -22, title: -18, chips: 8, chipStep: 3},
	studio: {mac: -45, eyebrow: -30, title: -22, drawFrom: 15, drawTo: 75, metrics: 60, metricStep: 7.5, milestone: 105},
	premium: {phones: -45, eyebrow: -30, title: -22, tap: 22.5, done: 52.5, card: 45, perks: 52.5, perkStep: 7.5, cursorIn: 60, click: 82.5, welcome: 90},
	overview: {start: 1410, title: 1440, settle: 1470, dive: 1515},
	cta: {logo: -45, wordmark: -37.5, line: 0, land: 0, buttons: [15, 22.5], url: 37.5, cursorIn: 52, click: 90, done: 97.5},
};

/* ---------------------------------------------------------------- 3D camera */
export const CAMERA: CamKey[] = [
	{f: 0, x: 60, y: -20, d: 1950, yaw: -9, pitch: 6, roll: -2},
	{f: 75, x: 20, y: -10, d: 1800, yaw: -4, pitch: 3, roll: -1},
	{f: 150, x: 0, y: 40, d: 1550, yaw: 10, pitch: 2, roll: 1},
	// hero
	{f: 190, x: 2150, y: -30, d: 1800, yaw: -18, pitch: 6},
	{f: 255, x: 2200, y: -10, d: 1650, yaw: -5, pitch: 4},
	{f: 330, x: 2260, y: 140, d: 1300, yaw: 10, pitch: 5},
	// home: wide, dive onto the chips + feed, glide down to the Iceland card and click it
	{f: 385, x: 4120, y: 0, d: 1400, yaw: 16, pitch: 3, roll: 1},
	{f: 430, x: 4330, y: -150, d: 880, yaw: 20, pitch: 4, roll: 1},
	{f: 470, x: 4470, y: 60, d: 860, yaw: 14, pitch: 1},
	{f: 498, x: 4560, y: 60, d: 1000, yaw: 6, pitch: -2},
	// watch: wide, close on Like + Subscribe, then comments + toast
	{f: 560, x: 4820, y: 0, d: 1350, yaw: -10, pitch: 2, roll: -1},
	{f: 615, x: 4330, y: 200, d: 900, yaw: -16, pitch: 4, roll: -1},
	{f: 700, x: 4640, y: 80, d: 1080, yaw: -8, pitch: 6},
	// shorts: wide, close on the swipe + like, then the Shorts camera
	{f: 760, x: 4500, y: 1260, d: 1550, yaw: -14, pitch: 4},
	{f: 805, x: 4560, y: 1260, d: 1200, yaw: -18, pitch: 2, roll: -1},
	{f: 855, x: 4989, y: 1270, d: 1200, yaw: -8, pitch: 4},
	// live: wide, close on the Super Chat composer for the clicks, then the live chat
	{f: 940, x: 4300, y: 2420, d: 1500, yaw: 12, pitch: 6, roll: 1},
	{f: 978, x: 3680, y: 2475, d: 760, yaw: 20, pitch: 4, roll: 1},
	{f: 1035, x: 4640, y: 2560, d: 950, yaw: -6, pitch: 5},
	{f: 1078, x: 4080, y: 2560, d: 1450, yaw: 0, pitch: 5},
	// fly past "watch anywhere"
	{f: 1125, x: 2200, y: 2520, d: 1800, yaw: -12, pitch: 5, roll: 2},
	// studio: wide, close on the growth chart, then the metric cards
	{f: 1180, x: 100, y: 2480, d: 1500, yaw: 10, pitch: 5},
	{f: 1228, x: -266, y: 2600, d: 860, yaw: 18, pitch: 7, roll: 1},
	{f: 1278, x: 380, y: 2470, d: 1050, yaw: -14, pitch: 3, roll: -1},
	// premium: wide, close on the download, then the "Try it free" click
	{f: 1328, x: 150, y: 1220, d: 1450, yaw: -10, pitch: 2},
	{f: 1352, x: -208, y: 1269, d: 950, yaw: 14, pitch: 4, roll: 1},
	{f: 1398, x: 340, y: 1470, d: 900, yaw: 20, pitch: 6, roll: 1},
	// overview + dive into the CTA
	{f: 1470, x: 2385, y: 1300, d: 6400, yaw: 26, pitch: 12, roll: -2},
	{f: 1512, x: 2385, y: 1300, d: 6100, yaw: 20, pitch: 9, roll: -1},
	{f: 1560, x: 2200, y: 1250, d: 1600, yaw: 0, pitch: 0},
	{f: 1680, x: 2200, y: 1260, d: 1500, yaw: -4, pitch: 2},
	{f: DURATION, x: 2200, y: 1250, d: 1420, yaw: 3, pitch: 1},
];
export const sampleCam = createCamera(CAMERA);
export const CAM_SPEED = cameraSpeed(sampleCam, DURATION, PERSPECTIVE);

/* ---------------------------------------------------------------- music: G – D – Em – C (I–V–vi–IV) */
export const MUSIC = {
	chords: [
		[[55, 59, 62, 67], 31],
		[[57, 62, 66, 69], 38],
		[[55, 59, 64, 67], 40],
		[[55, 60, 64, 67], 36],
	],
};

/* ---------------------------------------------------------------- SFX (sparse, soft, tuned) */
export type Sfx = {f: number; type: string; gain?: number; pan?: number; step?: number; dur?: number};
const A = (id: StationId) => STATIONS[id].arrive;

const buildSfx = (): Sfx[] => {
	const s: Sfx[] = [];
	const add = (f: number, type: string, o: Omit<Sfx, 'f' | 'type'> = {}) => s.push({f, type, ...o});

	const I = CUES.intro;
	I.words.forEach((w, i) => add(w, 'thump', {step: i}));
	add(I.logo - 30, 'riser', {dur: 1});
	add(I.logo, 'impact');
	add(I.wordmark, 'shimmer', {gain: 0.6});

	const H = CUES.hero;
	const h = A('hero');
	add(h + H.views, 'pop', {step: 0, pan: 0.4});
	add(h + H.notify, 'bell', {pan: -0.4});
	add(h + H.react, 'pop', {step: 2});

	const Hm = CUES.home;
	const m = A('home');
	for (let i = 0; i < 9; i++) add(m + Hm.chips + i * Hm.chipStep, 'pluck', {step: i, pan: -0.2, gain: 0.8});
	add(m + Hm.click, 'click', {pan: 0.2});
	add(m + Hm.click + 3.75, 'swipe', {gain: 0.8});

	const W = CUES.watch;
	const w = 555;
	add(w + W.like, 'click', {pan: -0.2});
	add(w + W.like + 3.75, 'pop', {step: 2, pan: -0.2});
	add(w + W.subscribe, 'click', {pan: -0.3});
	add(w + W.toast, 'bell', {pan: 0.3});
	add(w + W.comments, 'pluck', {step: 1, gain: 0.7});
	add(w + W.comments + 7.5, 'pluck', {step: 2, gain: 0.7});
	add(w + W.comments + 15, 'pluck', {step: 3, gain: 0.7});

	const Sh = CUES.shorts;
	const sh = A('shorts');
	add(sh + Sh.swipe, 'swipe', {pan: -0.2});
	add(sh + Sh.like, 'pop', {step: 4, pan: -0.2});
	add(sh + Sh.like + 3.75, 'shimmer', {gain: 0.45, pan: -0.2});
	add(sh + Sh.callout, 'pop', {step: 1, pan: -0.4});
	add(sh + Sh.rec, 'click', {pan: 0.3});
	add(sh + Sh.rec + 3.75, 'tick', {pan: 0.3});

	const L = CUES.live;
	const l = A('live');
	add(l + L.composer, 'pop', {step: 0, pan: -0.4});
	add(l + L.pick, 'click', {pan: -0.4});
	add(l + L.send, 'click', {pan: -0.4});
	add(l + L.superchat, 'coin', {pan: 0.3});
	add(l + L.superchat2, 'coin', {step: 2, pan: 0.3, gain: 0.8});

	const St = CUES.studio;
	const st = A('studio');
	add(st + St.drawFrom, 'riser', {dur: (St.drawTo - St.drawFrom) / FPS, gain: 0.5});
	for (let i = 0; i < 4; i++) add(st + St.metrics + i * St.metricStep, 'pluck', {step: i + 1, pan: 0.4, gain: 0.8});
	add(st + St.milestone, 'chime', {pan: 0.4});
	add(st + St.milestone, 'shimmer', {pan: 0.4, gain: 0.6});

	const P = CUES.premium;
	const p = A('premium');
	add(p + P.tap, 'click', {pan: -0.3});
	add(p + P.done, 'chime', {pan: -0.3});
	add(p + P.card, 'pop', {step: 0, pan: 0.3});
	add(p + P.click, 'click', {pan: 0.3});
	add(p + P.welcome, 'chime', {step: 2, pan: 0.3});

	const O = CUES.overview;
	add(O.start, 'swell', {dur: (O.title - O.start) / FPS});
	add(O.settle, 'shimmer', {gain: 0.8});
	add(O.dive - 15, 'riser', {dur: (A('cta') - O.dive + 15) / FPS});

	const T = CUES.cta;
	const t = A('cta');
	add(t + T.land, 'impact');
	T.buttons.forEach((b, i) => add(t + b, 'pop', {step: i * 2, pan: i ? 0.3 : -0.3}));
	add(t + T.click, 'click', {pan: -0.3});
	add(t + T.done, 'chime', {pan: -0.3});
	add(t + T.click, 'shimmer', {gain: 0.6});
	return s.sort((x, y) => x.f - y.f);
};
export const SFX = buildSfx();
