#!/usr/bin/env python3
"""End-to-end demonstration without DaVinci Resolve.

Creates a synthetic 60-second 1080p "documentary" master (H.264 + AAC, 2 s
GOP), revises 5 seconds of picture and sound on the synthetic timeline, runs a
Verified Patch and prints the verification report.

    python3 demo.py [work_dir]
"""

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from srx.events import Emitter  # noqa: E402
from srx.exporter import ExportOptions, Exporter  # noqa: E402
from srx.plan import Revision  # noqa: E402
from srx.render import SyntheticRenderSource  # noqa: E402
from srx.synthetic import AudioChange, SynthTimeline, VideoChange  # noqa: E402


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="srx-demo-")
    os.makedirs(work, exist_ok=True)
    tl = SynthTimeline(width=1920, height=1080, fps="30000/1001", frames=1798, start_frame=107892)
    master = os.path.join(work, "demo_master.mp4")
    if not os.path.exists(master):
        print(f"Rendering synthetic 60 s 1080p master -> {master}")
        tl.render_master(master, gop=60, bframes=3, preset="veryfast", crf=20)
    a, b = 900, 1050  # 00:00:30;00 .. 00:00:35;00
    revised = tl.revised([VideoChange(a, b)], [AudioChange(a, b)])
    out = os.path.join(work, f"demo_master_rev_{int(time.time())}.mp4")
    opts = ExportOptions(mode="verified", timeline_offset=tl.start_frame, preset="slow",
                         job_root=os.path.join(work, "jobs"), cache_dir=os.path.join(work, "cache"),
                         project_root=os.path.join(work, "projects"))
    res = Exporter(Emitter()).smart_export(master, out, [Revision(a, b, label="5 s revision")],
                                           SyntheticRenderSource(revised), opts)
    print()
    print(open(res["report_md"]).read())
    print(json.dumps(res["summary"], indent=2))


if __name__ == "__main__":
    main()
