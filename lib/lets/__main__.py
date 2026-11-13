"""`python3 lib/lets/__main__.py`: what bin/lets runs. Old syntax up to the version check, so any python3 can say
what's needed."""

import os
import sys

if sys.version_info < (3, 11):  # noqa: UP036  (this check is for older Pythons)
    sys.stderr.write(
        "LETS needs Python 3.11 or newer; this is %d.%d. Install a newer one:\n"
        "  Ubuntu or Debian: sudo apt install python3.12   (or newer)\n"
        "  macOS:            brew install python\n" % sys.version_info[:2]
    )
    sys.exit(1)
if not __package__:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from lets.cli import main  # noqa: E402

main()
