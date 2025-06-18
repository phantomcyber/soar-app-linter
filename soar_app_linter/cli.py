"""Command-line interface for soar-app-linter."""

import argparse
import logging
import os
import sys
from typing import List

from .app_validation import validate_app_json
from .pylint_runner import MessageLevel, run_pylint
from .dependency_utils import install_dependencies

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args(args: List[str] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Lint Python code for Splunk SOAR apps.")
    
    parser.add_argument(
        "target",
        help="Directory or file to lint"
    )
    
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--message-level",
        type=MessageLevel,
        choices=list(MessageLevel),
        default=MessageLevel.INFO,
        help="Minimum message level to show (default: info)"
    )
    
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="Skip dependency installation and ignore import errors"
    )
    
    parser.add_argument(
        "--disable-app-json-validation",
        action="store_true",
        help="Skip app.json validation"
    )
    
    return parser.parse_args(args)


def main() -> int:
    """Main entry point for the CLI."""
    args = parse_args()

    if not os.path.exists(args.target):
        logger.error(f"Error: Target '{args.target}' does not exist")
        return 1

    # Validate app.json if not disabled
    if not args.disable_app_json_validation and not validate_app_json(args.target):
        return 1
    
    if not args.no_deps and not install_dependencies(args.target):
        return 1
    
    # Run pylint
    exit_code, output = run_pylint(
        target=args.target,
        output_format=args.output_format,
        verbose=args.verbose,
        message_level=args.message_level,
        no_deps=args.no_deps,
    )

    if output:
        print(output, end="")

    return exit_code

if __name__ == "__main__":
    sys.exit(main())
