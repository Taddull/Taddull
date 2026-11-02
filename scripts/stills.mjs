// Usage: [COMP=YouTubePromo] node scripts/stills.mjs <outDir> <frame> [frame...]
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'node:path';

const [outDir, ...frames] = process.argv.slice(2);
const browserExecutable = '/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell';
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const composition = await selectComposition({serveUrl, id: process.env.COMP ?? 'DiscordPromo', browserExecutable});
for (const fr of frames) {
	const out = path.join(outDir, `f${String(fr).padStart(4, '0')}.jpg`);
	await renderStill({serveUrl, composition, frame: Number(fr), output: out, imageFormat: 'jpeg', jpegQuality: 85, browserExecutable});
	console.log('wrote', out);
}
