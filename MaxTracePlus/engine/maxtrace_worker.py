#!/usr/bin/env python3
"""Entry point launched by the Fusion script: ``python -I maxtrace_worker.py <job_dir>``.

Running with ``-I`` keeps the interpreter isolated from user site-packages
and environment variables; this file puts the engine package on the path.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from maxtrace.worker import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
