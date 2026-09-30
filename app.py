"""Desktop UI for the nida package.

    python app.py           # look up people by National ID
    python app.py --demo    # offline preview with generated sample records

What it does
    * Enter a 20-digit National ID (NIN) and see the holder's full details.
    * Every fetched record is cached to nida_history.json, so afterwards you
      can search your own history BY NAME to recover the NIN.

Note: NIDA publishes no "search people by name" endpoint, so the name search
only covers records this machine has already fetched. Only look up IDs you
have permission or consent to check - this returns real personal data.
"""

from __future__ import annotations

import argparse
import sys

from nidaui.app import main


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NIDA Lookup - Tanzania National ID desktop app.")
    parser.add_argument("--demo", action="store_true",
                        help="use offline sample data instead of the NIDA service")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    try:
        main(offline=args.demo)
    except ImportError as exc:  # e.g. pillow without the ImageTk extra
        sys.exit(f"Missing dependency: {exc}\n"
                 "Install everything with:  pip install -r requirements.txt")
