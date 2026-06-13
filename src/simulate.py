#!/usr/bin/env python3
"""CLI-Einstiegspunkt für die kooperative Transportlogistik (AOT Aufgabenblatt 2).

Beispiele:
    python3 src/simulate.py --world config/world_balanced.json --protocol cnp
    python3 src/simulate.py --world config/world_overhang.json --protocol ecnp
    python3 src/simulate.py --world config/world_balanced.json --protocol both --quiet
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cnp
import ecnp
from model import load_world


def main() -> int:
    ap = argparse.ArgumentParser(description="Kooperative Transportlogistik: CNP / eCNP")
    ap.add_argument("--world", required=True, help="Pfad zur Welt-JSON")
    ap.add_argument("--protocol", choices=["cnp", "ecnp", "both"], default="both")
    ap.add_argument("--quiet", action="store_true",
                    help="kein Nachrichten-Log, nur Ergebniszusammenfassung")
    args = ap.parse_args()

    world = load_world(args.world)
    verbose = not args.quiet

    runners = []
    if args.protocol in ("cnp", "both"):
        runners.append(cnp.run)
    if args.protocol in ("ecnp", "both"):
        runners.append(ecnp.run)

    results = []
    for run in runners:
        res = run(world, verbose=verbose)
        print("-" * 48)
        print(res.summary())
        print("-" * 48)
        results.append(res)

    if len(results) == 2:
        a, b = results
        print("\n### Vergleich CNP vs. eCNP ###")
        print(f"  Gesamtenergie  CNP={a.total_energy:.1f}  eCNP={b.total_energy:.1f}"
              f"  Delta={a.total_energy - b.total_energy:+.1f}")
        print(f"  Nachrichten    CNP={a.messages}      eCNP={b.messages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
