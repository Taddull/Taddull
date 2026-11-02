import React from 'react';
import {BODY} from './theme';

/* MacBook Pro — screen content is authored at 1440x900 */
export const MB = {w: 1680, h: 1000, screenW: 1440, screenH: 900};

export const MacBook: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => (
	<div style={{position: 'relative', width: MB.w, height: MB.h, ...style}}>
		{/* floor shadow */}
		<div
			style={{
				position: 'absolute',
				left: 40,
				right: 40,
				top: 940,
				height: 70,
				background: 'radial-gradient(50% 50% at 50% 50%, rgba(0,0,0,0.75), rgba(0,0,0,0))',
			}}
		/>
		{/* lid */}
		<div
			style={{
				position: 'absolute',
				left: 98,
				top: 0,
				width: 1484,
				height: 950,
				borderRadius: '36px 36px 10px 10px',
				background: 'linear-gradient(180deg, #121215, #070708)',
				boxShadow:
					'0 0 0 2px #5c5e66, 0 0 0 4px #1c1d21, 0 40px 90px rgba(0,0,0,0.6), inset 0 0 0 1.5px #26272c',
			}}
		>
			<div
				style={{
					position: 'absolute',
					left: 22,
					top: 22,
					width: 1440,
					height: 900,
					borderRadius: '14px 14px 2px 2px',
					overflow: 'hidden',
					background: '#000',
				}}
			>
				{children}
				<div
					style={{
						position: 'absolute',
						inset: 0,
						background: 'linear-gradient(118deg, rgba(255,255,255,0.09) 0%, rgba(255,255,255,0.02) 30%, rgba(255,255,255,0) 45%)',
						pointerEvents: 'none',
					}}
				/>
			</div>
			{/* notch */}
			<div
				style={{
					position: 'absolute',
					left: 742 - 100,
					top: 20,
					width: 200,
					height: 32,
					background: '#070708',
					borderRadius: '0 0 14px 14px',
				}}
			>
				<div style={{position: 'absolute', left: 94, top: 11, width: 11, height: 11, borderRadius: '50%', background: '#1a1c28', boxShadow: 'inset 0 0 3px #3a4a7a'}} />
			</div>
		</div>
		{/* hinge */}
		<div
			style={{
				position: 'absolute',
				left: 160,
				top: 948,
				width: 1360,
				height: 8,
				background: 'linear-gradient(180deg, #2b2c30, #515359)',
			}}
		/>
		{/* base */}
		<div
			style={{
				position: 'absolute',
				left: 0,
				top: 954,
				width: 1680,
				height: 30,
				borderRadius: '3px 3px 40px 40px / 3px 3px 26px 26px',
				background: 'linear-gradient(180deg, #f2f3f6 0%, #c9cbd1 28%, #9a9ca3 70%, #5d5f66 100%)',
				boxShadow: 'inset 0 1px 0 #ffffff',
			}}
		>
			<div
				style={{
					position: 'absolute',
					left: 840 - 130,
					top: 0,
					width: 260,
					height: 13,
					borderRadius: '0 0 16px 16px',
					background: 'linear-gradient(180deg, #8f9198, #c3c5cb)',
				}}
			/>
		</div>
	</div>
);

/* iPhone — screen content is authored at 393x852 */
export const IP = {w: 393 + 34, h: 852 + 34, screenW: 393, screenH: 852};

export const IPhone: React.FC<{
	children: React.ReactNode;
	style?: React.CSSProperties;
	frame?: 'titanium' | 'blurple' | 'black';
	time?: string;
}> = ({children, style, frame = 'titanium', time = '9:41'}) => {
	const frames = {
		titanium: 'linear-gradient(135deg, #8d8e93 0%, #3a3b3f 22%, #6d6e73 48%, #2a2b2e 76%, #7c7d82 100%)',
		blurple: 'linear-gradient(135deg, #b9bff9 0%, #4752c4 30%, #8b94f7 55%, #3a43a8 80%, #a5acf8 100%)',
		black: 'linear-gradient(135deg, #4a4a4e 0%, #111 30%, #333 60%, #0b0b0c 100%)',
	};
	return (
		<div style={{position: 'relative', width: IP.w, height: IP.h, ...style}}>
			{/* side buttons */}
			{[
				{l: -4, t: 170, h: 30},
				{l: -4, t: 228, h: 62},
				{l: -4, t: 302, h: 62},
				{r: -4, t: 260, h: 96},
			].map((b, i) => (
				<div
					key={i}
					style={{
						position: 'absolute',
						left: b.l,
						right: b.r,
						top: b.t,
						width: 6,
						height: b.h,
						borderRadius: 3,
						background: frames[frame],
					}}
				/>
			))}
			<div
				style={{
					position: 'absolute',
					inset: 0,
					borderRadius: 72,
					background: frames[frame],
					padding: 3,
					boxShadow: '0 50px 100px rgba(0,0,0,0.6), 0 20px 40px rgba(0,0,0,0.4)',
				}}
			>
				<div style={{width: '100%', height: '100%', borderRadius: 69, background: '#030303', padding: 14}}>
					<div
						style={{
							position: 'relative',
							width: IP.screenW,
							height: IP.screenH,
							borderRadius: 56,
							overflow: 'hidden',
							background: '#000',
						}}
					>
						{children}
						{/* status bar */}
						<div
							style={{
								position: 'absolute',
								top: 0,
								left: 0,
								right: 0,
								height: 54,
								display: 'flex',
								alignItems: 'center',
								justifyContent: 'space-between',
								padding: '6px 34px 0 50px',
								fontFamily: BODY,
								fontWeight: 700,
								fontSize: 17,
								color: '#fff',
								pointerEvents: 'none',
							}}
						>
							<span>{time}</span>
							<span style={{display: 'flex', gap: 6, alignItems: 'center'}}>
								<svg width="18" height="12" viewBox="0 0 18 12">
									{[0, 1, 2, 3].map((i) => (
										<rect key={i} x={i * 4.6} y={9 - i * 3} width="3.2" height={3 + i * 3} rx="1" fill="#fff" />
									))}
								</svg>
								<svg width="17" height="12" viewBox="0 0 17 12">
									<path d="M8.5 11.5 6 8.8a3.6 3.6 0 0 1 5 0zM3.6 6.4a7 7 0 0 1 9.8 0l1.6-1.7a9.4 9.4 0 0 0-13 0zM.2 3.1a11.8 11.8 0 0 1 16.6 0" fill="#fff" stroke="#fff" strokeWidth="0.6" />
								</svg>
								<svg width="27" height="13" viewBox="0 0 27 13">
									<rect x="0.5" y="0.5" width="23" height="12" rx="3.5" fill="none" stroke="rgba(255,255,255,0.5)" />
									<rect x="2.5" y="2.5" width="19" height="8" rx="2" fill="#fff" />
									<rect x="24.5" y="4.5" width="2" height="4" rx="1" fill="rgba(255,255,255,0.5)" />
								</svg>
							</span>
						</div>
						{/* dynamic island */}
						<div
							style={{
								position: 'absolute',
								top: 11,
								left: (IP.screenW - 124) / 2,
								width: 124,
								height: 36,
								borderRadius: 20,
								background: '#000',
							}}
						/>
						{/* home indicator */}
						<div
							style={{
								position: 'absolute',
								bottom: 8,
								left: (IP.screenW - 136) / 2,
								width: 136,
								height: 5,
								borderRadius: 3,
								background: 'rgba(255,255,255,0.85)',
							}}
						/>
						<div
							style={{
								position: 'absolute',
								inset: 0,
								background: 'linear-gradient(125deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0) 38%)',
								pointerEvents: 'none',
							}}
						/>
					</div>
				</div>
			</div>
		</div>
	);
};

/* iPad Pro — landscape screen authored at 1180x820 */
export const PAD = {w: 1180 + 60, h: 820 + 60, screenW: 1180, screenH: 820};

export const IPad: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => (
	<div style={{position: 'relative', width: PAD.w, height: PAD.h, ...style}}>
		<div
			style={{
				position: 'absolute',
				inset: 0,
				borderRadius: 54,
				background: 'linear-gradient(135deg, #9a9ba0 0%, #3b3c40 25%, #707176 55%, #2a2b2e 80%, #85868b 100%)',
				padding: 3,
				boxShadow: '0 50px 110px rgba(0,0,0,0.6)',
			}}
		>
			<div style={{width: '100%', height: '100%', borderRadius: 51, background: '#050505', padding: 27}}>
				<div style={{position: 'relative', width: PAD.screenW, height: PAD.screenH, borderRadius: 24, overflow: 'hidden', background: '#000'}}>
					{children}
					<div
						style={{
							position: 'absolute',
							inset: 0,
							background: 'linear-gradient(120deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0) 40%)',
							pointerEvents: 'none',
						}}
					/>
				</div>
			</div>
		</div>
		<div style={{position: 'absolute', left: PAD.w / 2 - 5, top: 11, width: 10, height: 10, borderRadius: '50%', background: '#1a1c28'}} />
	</div>
);
