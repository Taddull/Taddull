"""MaxTrace+ computer-vision and output-generation engine.

The engine runs as an isolated worker process (its own Python virtual
environment) so OpenCV never has to be installed into DaVinci Resolve's
embedded interpreter. The Fusion-side Lua launcher talks to it through job
files on disk; see ``worker.py``.
"""

__version__ = "1.0.0"
