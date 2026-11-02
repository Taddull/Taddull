/* Single source of truth for the 3D one-take: camera path, per-station animation cues and the SFX
 * list. Pure TS with no imports so scripts/make_audio.py can load it via `node`.
 * 30 fps, 120 BPM -> 1 beat = 15 frames, 8th = 7.5, 16th = 3.75, 1 bar = 60 frames.
 * Every audible cue sits on the 8th/16th-note grid so SFX land in time with the music. */

export const FPS = 30;
export const DURATION = 1800; // 60 s
export const PERSPECTIVE = 1600; // CSS perspective (px) -> ~62° horizontal FOV
export const SX = 2200; // station spacing on the gallery wall
export const SY = 1250;

export type StationId = 'intro' | 'hero' | 'app' | 'voice' | 'live' | 'devices' | 'apps' | 'roles' | 'cta';

/* arrive = frame the camera reaches the station (multiples of 15 = on the beat) */
export const STATIONS: Record<StationId, {col: number; row: number; arrive: number}> = {
	intro: {col: 0, row: 0, arrive: 0},
	hero: {col: 1, row: 0, arrive: 195},
	app: {col: 2, row: 0, arrive: 375},
	voice: {col: 2, row: 1, arrive: 750},
	live: {col: 2, row: 2, arrive: 930},
	devices: {col: 1, row: 2, arrive: 1050}, // built while the camera flies past
	apps: {col: 0, row: 2, arrive: 1170},
	roles: {col: 0, row: 1, arrive: 1320},
	cta: {col: 1, row: 1, arrive: 1560},
};
export const CHAT_ARRIVE = 555; // second half of the app station (same MacBook)

export const center = (id: StationId) => ({x: STATIONS[id].col * SX, y: STATIONS[id].row * SY});

/* ---------------------------------------------------------------- cues (frames relative to arrival) */
export const CUES = {
	intro: {words: [15, 30, 45], sub: 60, wordsOut: 75, logo: 90, wordmark: 105, tagline: 120},
	hero: {title: -30, mac: -30, phoneL: -15, phoneR: -8, online: 30, joined: 52.5, msg: 75, react: [90, 97.5]},
	servers: {mac: -45, eyebrow: -30, title: -22, rail: 0, railStep: 3.75, rows: 30, card: 75, cursorIn: 90, click: 120},
	chat: {eyebrow: -22, title: -15, msgs: [15, 45, 75], reacts: [30, 37.5, 90, 97.5, 105], emojiBar: 60, typeFrom: 105, typeTo: 135, send: 142.5},
	voice: {eyebrow: -30, title: -22, phoneA: -45, phoneB: -30, tiles: 0, tileStep: 3.75, joins: [15, 37.5, 60, 82.5], callout: 97.5},
	live: {eyebrow: -30, title: -22, mac: -45, phone: -15, picker: 15, click4k: 45, click60: 67.5, event: 60, interested: 120},
	devices: {rise: [-34, -28, -22, -16], eyebrow: -22, title: -18, chips: 8, chipStep: 3, typeFrom: 18, typeTo: 48, send: 54, arrive: 70},
	apps: {mac: -45, eyebrow: -30, title: -22, typeFrom: 0, typeTo: 15, popup: 22.5, sel: [30, 37.5], enter: 52.5, poll: 60, fillFrom: 67.5, fillTo: 127.5, nitro: -30, perks: 75, perkStep: 7.5, superReact: 105},
	roles: {mac: -45, eyebrow: -30, title: -22, list: 0, toggles: [30, 45, 60, 75], automod: 90},
	overview: {start: 1410, title: 1440, settle: 1470, dive: 1515},
	cta: {logo: -45, wordmark: -37.5, line: 0, land: 0, buttons: [15, 22.5], url: 37.5, cursorIn: 52, click: 90, done: 97.5},
};

/* ---------------------------------------------------------------- 3D orbit camera
 * The camera orbits a target point T at distance d, azimuth yaw (deg, + = camera to the right),
 * elevation pitch (deg, + = camera above) and roll. Keys are joined with monotone cubic splines
 * (C1-continuous, no overshoot) so the camera never stops dead and never wobbles past a key. */
export type CamKey = {f: number; x: number; y: number; z?: number; d: number; yaw: number; pitch: number; roll?: number};

export const CAMERA: CamKey[] = [
	{f: 0, x: 60, y: -20, d: 1950, yaw: -9, pitch: 6, roll: -2},
	{f: 75, x: 20, y: -10, d: 1800, yaw: -4, pitch: 3, roll: -1},
	{f: 150, x: 0, y: 40, d: 1550, yaw: 10, pitch: 2, roll: 1},
	// hero: approach from the left, orbit to the right, push in
	{f: 190, x: 2150, y: -30, d: 1800, yaw: -18, pitch: 6},
	{f: 255, x: 2200, y: -10, d: 1650, yaw: -5, pitch: 4},
	{f: 330, x: 2260, y: 140, d: 1300, yaw: 10, pitch: 5},
	// servers: wide, then dive into the server rail + channel menu, glide down it, up to the invite card
	{f: 385, x: 4120, y: 0, d: 1400, yaw: 16, pitch: 3, roll: 1},
	{f: 430, x: 4072, y: -40, d: 860, yaw: 22, pitch: 4, roll: 1},
	{f: 468, x: 4090, y: 120, d: 820, yaw: 18, pitch: 1},
	{f: 498, x: 4600, y: -220, d: 980, yaw: 6, pitch: -4},
	// chat: wide with headline, close on the messages, down to the composer
	{f: 560, x: 5000, y: 10, d: 1350, yaw: -10, pitch: 2, roll: -1},
	{f: 640, x: 4520, y: 90, d: 960, yaw: -18, pitch: 4, roll: -1},
	{f: 700, x: 4600, y: 230, d: 1000, yaw: -10, pitch: 8},
	// voice
	{f: 760, x: 4500, y: 1260, d: 1550, yaw: -14, pitch: 4},
	{f: 830, x: 4989, y: 1270, d: 1200, yaw: -20, pitch: 2, roll: -1},
	{f: 885, x: 4900, y: 1250, d: 1100, yaw: -8, pitch: 4},
	// go live + events: close on the quality picker for the clicks, then the event card
	{f: 940, x: 4300, y: 2420, d: 1500, yaw: 12, pitch: 6, roll: 1},
	{f: 978, x: 3680, y: 2475, d: 760, yaw: 20, pitch: 4, roll: 1},
	{f: 1040, x: 3940, y: 2800, d: 920, yaw: 12, pitch: 9},
	{f: 1078, x: 4080, y: 2560, d: 1450, yaw: 0, pitch: 5},
	// fly past the "every device" station
	{f: 1125, x: 2200, y: 2520, d: 1800, yaw: -12, pitch: 5, roll: 2},
	// apps + nitro
	{f: 1180, x: 100, y: 2480, d: 1500, yaw: 10, pitch: 5},
	{f: 1228, x: -340, y: 2640, d: 860, yaw: 18, pitch: 7, roll: 1},
	{f: 1278, x: 600, y: 2500, d: 1050, yaw: -14, pitch: 3, roll: -1},
	// roles: wide, then close on the permission toggles
	{f: 1328, x: 220, y: 1200, d: 1400, yaw: -12, pitch: 2},
	{f: 1368, x: 114, y: 1151, d: 780, yaw: 18, pitch: 4, roll: 1},
	{f: 1402, x: 150, y: 1190, d: 850, yaw: 24, pitch: 6, roll: 1},
	// crane back for the overview, slow orbit, dive into the CTA
	{f: 1470, x: 2385, y: 1300, d: 6400, yaw: 26, pitch: 12, roll: -2},
	{f: 1512, x: 2385, y: 1300, d: 6100, yaw: 20, pitch: 9, roll: -1},
	{f: 1560, x: 2200, y: 1250, d: 1600, yaw: 0, pitch: 0},
	{f: 1680, x: 2200, y: 1260, d: 1500, yaw: -4, pitch: 2},
	{f: DURATION, x: 2200, y: 1250, d: 1420, yaw: 3, pitch: 1},
];

/* Fritsch–Carlson monotone cubic interpolation over non-uniform keys */
const monotone = (xs: number[], ys: number[]) => {
	const n = xs.length;
	const h = xs.slice(1).map((x, i) => x - xs[i]);
	const dl = h.map((hi, i) => (ys[i + 1] - ys[i]) / hi);
	const m = new Array(n).fill(0);
	for (let i = 1; i < n - 1; i++) {
		if (dl[i - 1] * dl[i] <= 0) continue;
		const w1 = 2 * h[i] + h[i - 1];
		const w2 = h[i] + 2 * h[i - 1];
		m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i]);
	}
	return (x: number) => {
		if (x <= xs[0]) return ys[0];
		if (x >= xs[n - 1]) return ys[n - 1];
		let i = 0;
		while (xs[i + 1] < x) i++;
		const t = (x - xs[i]) / h[i];
		const t2 = t * t;
		const t3 = t2 * t;
		return (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1];
	};
};

const fs = CAMERA.map((k) => k.f);
const S = {
	x: monotone(fs, CAMERA.map((k) => k.x)),
	y: monotone(fs, CAMERA.map((k) => k.y)),
	z: monotone(fs, CAMERA.map((k) => k.z ?? 0)),
	ld: monotone(fs, CAMERA.map((k) => Math.log(k.d))),
	yaw: monotone(fs, CAMERA.map((k) => k.yaw)),
	pitch: monotone(fs, CAMERA.map((k) => k.pitch)),
	roll: monotone(fs, CAMERA.map((k) => k.roll ?? 0)),
};

export type Cam = {x: number; y: number; z: number; d: number; yaw: number; pitch: number; roll: number};
export const sampleCam = (f: number): Cam => ({
	x: S.x(f),
	y: S.y(f),
	z: S.z(f),
	d: Math.exp(S.ld(f)),
	yaw: S.yaw(f),
	pitch: S.pitch(f),
	roll: S.roll(f),
});

/* approximate on-screen motion (px/frame) — drives the "air" whoosh layer in the audio */
export const CAM_SPEED: number[] = (() => {
	const out: number[] = [];
	for (let f = 0; f < DURATION; f++) {
		const a = sampleCam(f);
		const b = sampleCam(f + 1);
		const pan = (Math.hypot(b.x - a.x, b.y - a.y) * PERSPECTIVE) / a.d;
		const ang = ((Math.abs(b.yaw - a.yaw) + Math.abs(b.pitch - a.pitch) + Math.abs(b.roll - a.roll)) * Math.PI) / 180 * PERSPECTIVE * 0.6;
		const zoom = Math.abs(Math.log(b.d) - Math.log(a.d)) * 960;
		out.push(pan + ang + zoom);
	}
	return out;
})();

/* ---------------------------------------------------------------- SFX (sparse, soft, tuned) */
export type Sfx = {f: number; type: string; gain?: number; pan?: number; step?: number; dur?: number};

const A = (id: StationId) => STATIONS[id].arrive;

const buildSfx = (): Sfx[] => {
	const s: Sfx[] = [];
	// step = scale degree offset used to pick a chord tone, so repeated UI sounds form little melodies
	const add = (f: number, type: string, o: Omit<Sfx, 'f' | 'type'> = {}) => s.push({f, type, ...o});

	const I = CUES.intro;
	I.words.forEach((w, i) => add(w, 'thump', {step: i}));
	add(I.logo - 30, 'riser', {dur: 1});
	add(I.logo, 'impact');
	add(I.wordmark, 'shimmer', {gain: 0.6});

	const H = CUES.hero;
	const h = A('hero');
	add(h + H.online, 'pop', {step: 0, pan: 0.4});
	add(h + H.joined, 'chime', {pan: -0.4});
	add(h + H.msg, 'ding');
	add(h + H.react[0], 'pop', {step: 2});

	const Sv = CUES.servers;
	const a = A('app');
	for (let i = 0; i < 10; i++) add(a + Sv.rail + i * Sv.railStep, 'pluck', {step: i, pan: -0.3, gain: 0.8});
	add(a + Sv.card, 'pop', {step: 1, pan: 0.3});
	add(a + Sv.click, 'click', {pan: 0.3});
	add(a + Sv.click + 7.5, 'chime', {pan: 0.3});

	const Ch = CUES.chat;
	const c = CHAT_ARRIVE;
	Ch.msgs.forEach((m, i) => add(c + m, 'ding', {step: i}));
	add(c + Ch.reacts[0], 'pop', {step: 2});
	add(c + Ch.emojiBar, 'pop', {step: 4, pan: 0.3});
	add(c + Ch.reacts[2], 'pop', {step: 3});
	add(c + Ch.send, 'send');

	const V = CUES.voice;
	const v = A('voice');
	V.joins.forEach((j, i) => add(v + j, 'chime', {step: i, pan: -0.2}));
	add(v + V.callout, 'pop', {step: 1, pan: -0.3});

	const L = CUES.live;
	const l = A('live');
	add(l + L.picker, 'pop', {step: 0, pan: -0.4});
	add(l + L.click4k, 'click', {pan: -0.4});
	add(l + L.event, 'pop', {step: 2, pan: -0.2});
	add(l + L.click60, 'click', {pan: -0.4});
	add(l + L.interested, 'click', {pan: -0.1});
	add(l + L.interested + 7.5, 'chime', {pan: -0.1});

	const P = CUES.apps;
	const p = A('apps');
	add(p + P.popup, 'pop', {step: 0, pan: -0.3});
	P.sel.forEach((t) => add(p + t, 'tick', {pan: -0.3}));
	add(p + P.enter, 'click', {pan: -0.3});
	add(p + P.poll, 'ding', {step: 1, pan: -0.3});
	for (let i = 0; i < 4; i++) add(p + P.perks + i * P.perkStep, 'pluck', {step: i + 2, pan: 0.4, gain: 0.8});
	add(p + P.superReact, 'shimmer', {pan: 0.4, gain: 0.7});

	const R = CUES.roles;
	const r = A('roles');
	R.toggles.forEach((t, i) => add(r + t, 'toggle', {step: i}));
	add(r + R.automod, 'alert', {pan: 0.2});

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
