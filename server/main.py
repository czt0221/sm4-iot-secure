from __future__ import annotations

import argparse
import logging
from pathlib import Path

from server.receive import UDPServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SM4 IoT secure server")
    parser.add_argument("--host", default="0.0.0.0", help="bind host")
    parser.add_argument("--port", default=9999, type=int, help="bind UDP port")
    parser.add_argument(
        "--server-dir",
        default=Path(__file__).resolve().parent,
        type=Path,
        help="directory containing id_masterkey and data files",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="logging level",
    )
    parser.add_argument(
        "--max-time-skew",
        default=30,
        type=int,
        help="maximum allowed timestamp skew in seconds",
    )
    parser.add_argument(
        "--replay-ttl",
        default=None,
        type=int,
        help="replay cache TTL in seconds; defaults to max(10, 2 * max-time-skew)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    server = UDPServer(
        host=args.host,
        port=args.port,
        server_dir=args.server_dir,
        max_time_skew=args.max_time_skew,
        replay_ttl=args.replay_ttl,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
