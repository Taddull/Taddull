import '@fontsource-variable/roboto-flex/full.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';
import '@fontsource/roboto/900.css';

/* YouTube brand red + near-black, YouTube dark-theme UI greys, and a light "studio" canvas */
export const Y = {
	red: '#FF0000',
	redDeep: '#CC0000',
	ink: '#0F0F0F',
	almostBlack: '#282828',
	ui: '#0F0F0F',
	ui2: '#212121',
	ui3: '#272727',
	ui4: '#3F3F3F',
	text: '#F1F1F1',
	text2: '#AAAAAA',
	blue: '#3EA6FF',
	white: '#FFFFFF',
	canvas: '#F4F4F4',
	canvasHi: '#FFFFFF',
	canvasLo: '#E4E4E4',
	body: '#3A3A3A',
	shadow: 'rgba(15,15,15,0.16)',
	shadowStrong: 'rgba(15,15,15,0.28)',
};

// YouTube's brand face (YouTube Sans) is proprietary: Roboto Flex (heavy, slightly condensed) stands in
// for headlines, and Roboto — YouTube's actual UI font — is used for the interface.
export const YDISPLAY = '"Roboto Flex Variable", Roboto, sans-serif';
export const YBODY = 'Roboto, sans-serif';

export const ydisplay = (size: number, weight = 900): React.CSSProperties => ({
	fontFamily: YDISPLAY,
	fontWeight: weight,
	fontSize: size,
	fontStretch: '88%',
	letterSpacing: '-0.02em',
	lineHeight: 0.98,
	textTransform: 'uppercase',
	color: Y.ink,
});
