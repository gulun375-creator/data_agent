"""Application entry point."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Data Agent - AI-powered data analysis assistant",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to settings YAML file (default: config/settings.yaml)",
    )
    parser.add_argument(
        "--schema",
        type=str,
        default=None,
        help="Path to schema directory (overrides config)",
    )
    args = parser.parse_args()

    from data_agent.config.settings import load_config

    config = load_config(args.config)

    if args.schema:
        config.schema_dir = args.schema

    if not config.openai_api_key:
        print(
            "错误: 未设置 OPENAI_API_KEY。\n"
            "请在 .env 文件或环境变量中设置 OPENAI_API_KEY。",
            file=sys.stderr,
        )
        sys.exit(1)

    from data_agent.cli.app import run_cli

    run_cli(config)


if __name__ == "__main__":
    main()
