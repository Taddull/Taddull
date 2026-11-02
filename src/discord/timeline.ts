/* Single source of truth for the one-take camera, the per-station animation cues and the
 * SFX track. Pure TS with no imports so scripts/make_audio.py can load it via `node`.
 * 30 fps, 120 BPM -> 1 beat = 15 frames, 1 bar = 60 frames. */

export const FPS = 30;
export const DURATION = 1800; // 60 s
export const SX = 2200; // world spacing between stations
export const SY = 1250;

export type StationId = 'intro' | 'hero' | 'app' | 'voice' | 'live' | 'devices' | 'apps' | 'roles' | 'cta';

/* arrive = frame the camera settles on the station */
export const STATIONS: Record<StationId, {col: number; row: number; arrive: number}> = {
	intro: {col: 0, row: 0, arrive: 0},
	hero: {col: 1, row: 0, arrive: 180},
	app: {col: 2, row: 0, arrive: 360},
	voice: {col: 2, row: 1, arrive: 660},
	live: {col: 2, row: 2, arrive: 810},
	devices: {col: 1, row: 2, arrive: 990},
	apps: {col: 0, row: 2, arrive: 1110},
	roles: {col: 0, row: 1, arrive: 1290},
	cta: {col: 1, row: 1, arrive: 1560},
};
export const CHAT_ARRIVE = 510; // camera pans across the same MacBook from servers to chat

export const center = (id: StationId) => ({x: STATIONS[id].col * SX, y: STATIONS[id].row * SY});

/* ---------------------------------------------------------------- camera */
export type Ease = 'drift' | 'move' | 'zoom';
export type Key = {f: number; x: number; y: number; z: number; ease?: Ease};

const c = center;
export const CAMERA: Key[] = [
	{f: 0, ...c('intro'), z: 1},
	{f: 144, ...c('intro'), z: 1.06, ease: 'drift'},
	{f: 180, ...c('hero'), z: 1, ease: 'move'},
	{f: 324, ...c('hero'), z: 1.05, ease: 'drift'},
	{f: 360, x: c('app').x - 440, y: 0, z: 1.06, ease: 'move'},
	{f: 474, x: c('app').x - 420, y: 0, z: 1.09, ease: 'drift'},
	{f: CHAT_ARRIVE, x: c('app').x + 420, y: 0, z: 1.08, ease: 'move'},
	{f: 624, x: c('app').x + 400, y: 0, z: 1.11, ease: 'drift'},
	{f: 660, ...c('voice'), z: 1, ease: 'move'},
	{f: 774, ...c('voice'), z: 1.05, ease: 'drift'},
	{f: 810, ...c('live'), z: 1, ease: 'move'},
	{f: 954, ...c('live'), z: 1.04, ease: 'drift'},
	{f: 990, ...c('devices'), z: 1, ease: 'move'},
	{f: 1074, ...c('devices'), z: 1.03, ease: 'drift'},
	{f: 1110, ...c('apps'), z: 1, ease: 'move'},
	{f: 1254, ...c('apps'), z: 1.04, ease: 'drift'},
	{f: 1290, ...c('roles'), z: 1, ease: 'move'},
	{f: 1404, ...c('roles'), z: 1.04, ease: 'drift'},
	{f: 1470, x: SX + 185, y: SY, z: 0.27, ease: 'zoom'},
	{f: 1520, x: SX + 185, y: SY, z: 0.282, ease: 'drift'},
	{f: 1560, ...c('cta'), z: 1, ease: 'zoom'},
	{f: DURATION, ...c('cta'), z: 1.07, ease: 'drift'},
];

/* ---------------------------------------------------------------- cues (frames relative to arrival) */
export const CUES = {
	intro: {words: [15, 30, 45], sub: 55, wordsOut: 76, logo: 90, wordmark: 100, tagline: 116},
	hero: {title: -22, mac: -32, phoneL: -18, phoneR: -10, online: 40, joined: 62, msg: 70, react: [95, 102]},
	servers: {mac: -34, eyebrow: -20, title: -14, rail: 6, railStep: 3, rows: 30, card: 58, cursorIn: 62, click: 96},
	chat: {eyebrow: -16, title: -12, msgs: [8, 34, 60], reacts: [24, 28, 80, 86, 92], emojiBar: 40, typeFrom: 66, typeTo: 96, send: 104},
	voice: {eyebrow: -20, title: -16, phoneA: -32, phoneB: -24, tiles: 6, tileStep: 5, joins: [12, 30, 48, 66], callout: 76},
	live: {eyebrow: -22, title: -18, mac: -32, phone: -8, picker: 40, click4k: 70, click60: 92, event: 56, interested: 112},
	devices: {rise: [-34, -28, -22, -16], eyebrow: -22, title: -18, chips: 8, chipStep: 3, typeFrom: 18, typeTo: 48, send: 54, arrive: 70},
	apps: {mac: -32, eyebrow: -22, title: -18, typeFrom: 4, typeTo: 18, popup: 22, sel: [34, 44], enter: 58, poll: 62, fillFrom: 70, fillTo: 128, nitro: -20, perks: 26, perkStep: 6, superReact: 104},
	roles: {mac: -34, eyebrow: -22, title: -18, list: 4, toggles: [30, 48, 66, 84], automod: 98},
	overview: {start: 1404, title: 1438, settle: 1470, dive: 1520},
	cta: {logo: -32, wordmark: -24, line: -4, land: 0, buttons: [10, 16], url: 28, cursorIn: 46, click: 92, done: 98},
};

/* ---------------------------------------------------------------- SFX track */
export type Sfx = {f: number; type: string; gain?: number; pan?: number; pitch?: number; dur?: number};

const A = (id: StationId) => STATIONS[id].arrive;

const buildSfx = (): Sfx[] => {
	const s: Sfx[] = [];
	const add = (f: number, type: string, o: Omit<Sfx, 'f' | 'type'> = {}) => s.push({f: Math.round(f), type, ...o});

	// camera moves: whoosh peaking on arrival, panned in the direction of travel
	for (let i = 1; i < CAMERA.length; i++) {
		const k = CAMERA[i];
		const p = CAMERA[i - 1];
		if (k.ease === 'move') add(p.f, 'whoosh', {dur: (k.f - p.f) / FPS, pan: Math.sign(k.x - p.x) * 0.6, gain: 0.9});
	}

	// intro
	const I = CUES.intro;
	I.words.forEach((w, i) => add(w, 'thump', {pitch: 1 + i * 0.12}));
	add(I.sub - 4, 'swish', {gain: 0.5});
	add(I.logo - 42, 'riser', {dur: 42 / FPS, gain: 0.7});
	add(I.logo, 'impact');
	add(I.wordmark, 'swish', {gain: 0.7});
	add(I.wordmark + 6, 'shimmer', {gain: 0.6});
	add(I.tagline, 'swish', {gain: 0.45, pan: 0.2});

	// hero
	const H = CUES.hero;
	const h = A('hero');
	add(h + H.title, 'swish', {gain: 0.5});
	add(h + H.phoneL, 'swish', {gain: 0.45, pan: -0.5});
	add(h + H.phoneR, 'swish', {gain: 0.45, pan: 0.5});
	add(h + H.online, 'pop', {pitch: 1.1});
	add(h + H.joined, 'join', {pan: -0.4});
	add(h + H.msg, 'ding', {gain: 0.55});
	H.react.forEach((r, i) => add(h + r, 'pop', {pitch: 1.2 + i * 0.15, gain: 0.7}));

	// servers
	const S = CUES.servers;
	const a = A('app');
	add(a + S.eyebrow, 'pop', {pitch: 0.9, pan: -0.3});
	add(a + S.title, 'swish', {gain: 0.5, pan: -0.3});
	for (let i = 0; i < 10; i++) add(a + S.rail + i * S.railStep, 'pop', {pitch: 0.8 + i * 0.07, gain: 0.55, pan: -0.2});
	add(a + S.rows, 'swish', {gain: 0.35});
	add(a + S.card, 'pop', {pitch: 1.0, pan: 0.4});
	add(a + S.click, 'click', {pan: 0.4});
	add(a + S.click + 4, 'ding', {gain: 0.6, pan: 0.4});

	// chat
	const Ch = CUES.chat;
	const ch = CHAT_ARRIVE;
	add(ch + Ch.eyebrow, 'pop', {pitch: 0.9, pan: 0.4});
	add(ch + Ch.title, 'swish', {gain: 0.5, pan: 0.4});
	Ch.msgs.forEach((m) => add(ch + m, 'ding', {gain: 0.6}));
	Ch.reacts.forEach((r, i) => add(ch + r, 'pop', {pitch: 1.1 + (i % 3) * 0.12, gain: 0.6}));
	add(ch + Ch.emojiBar, 'pop', {pitch: 1.3, pan: -0.4});
	for (let t = Ch.typeFrom; t < Ch.typeTo; t += 2.2) add(ch + t, 'key', {gain: 0.5, pitch: 0.9 + ((t * 7) % 5) / 10});
	add(ch + Ch.send, 'click', {gain: 0.7});
	add(ch + Ch.send + 2, 'send');

	// voice
	const V = CUES.voice;
	const v = A('voice');
	add(v + V.eyebrow, 'pop', {pitch: 0.9, pan: -0.4});
	add(v + V.title, 'swish', {gain: 0.5, pan: -0.4});
	for (let i = 0; i < 6; i++) add(v + V.tiles + i * V.tileStep, 'pop', {pitch: 0.9 + i * 0.08, gain: 0.45, pan: 0.5});
	V.joins.forEach((j, i) => add(v + j, 'join', {pan: 0.2, pitch: 1 + i * 0.05}));
	add(v + V.callout, 'pop', {pitch: 1.15});

	// live
	const L = CUES.live;
	const l = A('live');
	add(l + L.title, 'swish', {gain: 0.5});
	add(l + L.phone, 'swish', {gain: 0.4, pan: 0.6});
	add(l + L.picker, 'pop', {pan: -0.6});
	add(l + L.click4k, 'click', {pan: -0.6});
	add(l + L.click60, 'click', {pan: -0.6});
	add(l + L.event, 'pop', {pitch: 1.05, pan: 0.5});
	add(l + L.interested, 'click', {pan: 0.5});
	add(l + L.interested + 3, 'ding', {gain: 0.55, pan: 0.5});

	// devices
	const D = CUES.devices;
	const d = A('devices');
	add(d + D.title, 'swish', {gain: 0.5});
	for (let i = 0; i < 8; i++) add(d + D.chips + i * D.chipStep, 'pop', {pitch: 0.85 + i * 0.07, gain: 0.45, pan: -0.6 + i * 0.17});
	for (let t = D.typeFrom; t < D.typeTo; t += 2.4) add(d + t, 'key', {gain: 0.45, pan: 0.6, pitch: 0.9 + ((t * 7) % 5) / 10});
	add(d + D.send, 'send', {pan: 0.6});
	add(d + D.arrive, 'ding', {gain: 0.6, pan: -0.2});

	// apps + nitro
	const P = CUES.apps;
	const p = A('apps');
	add(p + P.title, 'swish', {gain: 0.5});
	for (let t = P.typeFrom; t < P.typeTo; t += 3) add(p + t, 'key', {gain: 0.55, pan: -0.3});
	add(p + P.popup, 'pop', {pitch: 1.0, pan: -0.3});
	P.sel.forEach((t) => add(p + t, 'tick', {pan: -0.3}));
	add(p + P.enter, 'click', {pan: -0.3});
	add(p + P.poll, 'ding', {gain: 0.55, pan: -0.3});
	add(p + P.fillFrom, 'fill', {dur: (P.fillTo - P.fillFrom) / FPS, gain: 0.5, pan: -0.3});
	add(p + P.nitro, 'swish', {gain: 0.4, pan: 0.6});
	for (let i = 0; i < 4; i++) add(p + P.perks + i * P.perkStep, 'pop', {pitch: 1.0 + i * 0.1, gain: 0.5, pan: 0.6});
	add(p + P.superReact, 'shimmer', {pan: 0.6});
	add(p + P.superReact, 'pop', {pitch: 0.7, pan: 0.6});

	// roles
	const R = CUES.roles;
	const r = A('roles');
	add(r + R.title, 'swish', {gain: 0.5, pan: 0.4});
	add(r + R.list, 'swish', {gain: 0.3, pan: -0.3});
	R.toggles.forEach((t, i) => {
		add(r + t, 'click', {gain: 0.6, pan: -0.1});
		add(r + t + 1, 'toggle', {pitch: 1 + i * 0.06, pan: -0.1});
	});
	add(r + R.automod, 'alert', {pan: 0.3});

	// overview + dive
	const O = CUES.overview;
	add(O.start, 'whooshBig', {dur: (O.settle - O.start) / FPS});
	add(O.title, 'swish', {gain: 0.6});
	add(O.settle, 'shimmer', {gain: 0.8});
	add(O.dive - 30, 'riser', {dur: (A('cta') - O.dive + 30) / FPS, gain: 0.8});
	add(O.dive, 'whoosh', {dur: (A('cta') - O.dive) / FPS, gain: 1});

	// cta
	const T = CUES.cta;
	const t = A('cta');
	add(t + T.logo, 'pop', {pitch: 0.8});
	add(t + T.land, 'impact');
	add(t + T.wordmark, 'swish', {gain: 0.6});
	add(t + T.line, 'swish', {gain: 0.45});
	T.buttons.forEach((b, i) => add(t + b, 'pop', {pitch: 1 + i * 0.15, pan: i ? 0.3 : -0.3}));
	add(t + T.url, 'tick');
	add(t + T.click, 'click', {pan: -0.3});
	add(t + T.done, 'ding', {pan: -0.3});
	add(t + T.click, 'shimmer', {gain: 0.7});
	return s.sort((x, y) => x.f - y.f);
};

export const SFX = buildSfx();
