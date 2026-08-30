"""CLI entry point for the stretch (search-and-score) buyer agent."""

from __future__ import annotations

import argparse
import logging
import sys

from .stretch.agent import run_stretch_agent


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="buyer_agent_stretch",
        description="Search-and-score buyer agent — finds the best item using web reviews.",
    )
    parser.add_argument(
        "goal",
        help='Purchase goal, e.g. "buy the best biriyani under ₹500"',
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print each tool call and result",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the LLM model (ignores .env LLM_MODEL)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(message)s",
    )

    if args.model:
        import os
        os.environ["LLM_MODEL"] = args.model

    result = run_stretch_agent(args.goal, verbose=args.verbose)
    print(f"\n{result}")
    sys.exit(0)
