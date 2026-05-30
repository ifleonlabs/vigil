"""Convenience entry point so you can run vigil without installing.

    python main.py init
    python main.py create-user alice
    python main.py run          # web + scheduler + worker in one process
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from vigil.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
