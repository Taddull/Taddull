# Smart Revision Exporter - verification report

**Result: PASSED**  
Mode: verified (verification level: full)  
Output: `<work>/demo_master_rev_1793561561.mp4`  
Output SHA-256: `76096043d0a499f65f0f1f5126aba87f71d3652394fc585a45c15ee59a4791bd`  
Master SHA-256: `e049ad8f7e3097cba62ccf85197b92a7339cc05724d508b409a2a51e27990e40`  
Engine version: 1.0.0

## Video

| Metric | Value |
|---|---|
| Master frames | 1798 |
| Output frames | 1798 |
| Unchanged frames compared | 1618 |
| Unchanged frames pixel-identical | 1618 |
| Re-encoded frames | 180 |
|   of which boundary frames (unchanged content) | 30 |
| Encode fidelity, luma PSNR min/mean (dB) | 50.08 / 51.45 |
| Boundary render vs master, luma PSNR min (dB) | 44.61 |
| Guard render vs master, luma PSNR min (dB) | 44.36 |

### Segments

| Kind | Master frames | Output frames | Revised (output) | Boundary |
|---|---|---|---|---|
| copy | 0-899 | 0-899 |  | 0 |
| render | 900-1079 | 900-1079 | [(900, 1050)] | 30 |
| copy | 1080-1797 | 1080-1797 |  | 0 |

## Audio

- Track 0: **splice** - AAC-LC packet splice with overlap guard frames

## Checks

| Check | Status | Detail |
|---|---|---|
| container | PASS | output parsed (ISO-BMFF structure valid) |
| frame_count | PASS | 1798 frames (expected 1798) |
| frame_rate | PASS | 30000/1001 fps, timescale 30000 |
| dimensions | PASS | 1920x1080 yuv420p |
| color_metadata | PASS | colour metadata identical (container + VUI): color_range=tv, color_space=bt709, color_transfer=bt709, color_primaries=bt709 |
| splice_points | PASS | 2 splice point(s) on IDR/clean-cut boundaries |
| parameter_sets | PASS | output carries SPS ids [0, 1] / PPS ids [0, 1] |
| timestamps | PASS | constant-frame-rate composition timestamps, no duplicates or gaps; first composition time identical to master |
| decoded_frame_count | PASS | decoder produced exactly 1798 frames |
| decoder_errors | PASS | no decoder errors or warnings in decoded ranges |
| pixel_identity | PASS | all 1618 preserved frames are pixel-identical to the master (SHA-256 of decoded yuv420p frames) |
| encode_fidelity | PASS | 180 re-encoded frames vs fresh render: luma PSNR min 50.08 dB / mean 51.45 dB; worst plane 48.75 dB |
| black_frames | PASS | no unintended black frames in re-encoded regions |
| unchanged_content | PASS | 30 boundary + 6 guard frame(s) rendered fresh match the master (min PSNR over Y/U/V 43.32 dB) |
| seams | PASS | 8 copied frames adjacent to splice points decode identically |
| audio0_packets | PASS | 2574 AAC packets byte-identical; 240 packets replaced in 1 splice(s) |
| audio0_pcm_identity | PASS | decoded audio outside the splice regions is bit-identical (2633728 samples) |
| audio0_splice | PASS | transition blocks at codec-noise level (no clicks); replaced audio aligned (lag 0): splice [1406, 1646]: start 35.08 dB, end 59.28 dB, lag 0 |

## Encoding

- Patch encoder: libx264, preset slow, CRF 16.0
- x264 parameters: `sps-id=1:repeat-headers=1:open-gop=0:force-cfr=1:cabac=1:8x8dct=1:bframes=3:b-pyramid=normal:ref=4:keyint=60:min-keyint=15:colorprim=bt709:transfer=bt709:colormatrix=bt709:range=tv:sar=1/1:vbv-maxrate=23750:vbv-bufsize=29687`
- Output parameter sets: {'sps_ids': [0, 1], 'pps_ids': [0, 1], 'count': 2}
- Audio encoder: aac

## Processing cost

- analyze: 0.22 s
- render: 119.36 s
- encode: 10.51 s
- audio: 0.74 s
- assemble: 0.15 s
- verify: 35.78 s
- frames decoded for verification: 3596 (full decode (no cache))

