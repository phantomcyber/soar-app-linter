"""Command-line interface for soar-app-linter."""

import argparse
import json
import logging
import os
import sys
import re
from typing import List, Dict
from collections import defaultdict

from .app_validation import validate_app_json, should_process_app
from .pylint_runner import MessageLevel, run_pylint
from .dependency_utils import install_dependencies

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ERROR_FREE_REPOS = [
        "abnormalsecurity",
    "archer",
    "awsathena",
    "awssystemsmanager",
    "checkpointfirewall",
    "confluence",
    "dns",
    "git",
    "ibmwatsonv3",
    "insightvm",
    "ivantiitsm",
    "junipersrx",
    "kafka",
    "office365",
    "rsasecureidam",
    "snowflake",
    "splunkattackanalyzer",
    "symantecdlp",
    "symantecmessaginggateway",
    "tenableio",
]

IGNORED_REPOS = [
    "alibabaram",
    "virustotal",
    "wwt_cisco_firepower",
    "frictionless_connector_repo",
]

# Repos that only have pudb import errors (E0401: Unable to import 'pudb')
PUDB_ONLY_ERROR_REPOS = [
    "abuseipdb",
    "alienvaultotx",
    "awscloudtrail",
    "awsdynamodb",
    "awsguardduty",
    "awslambda",
    "awss3",
    "awssecurityhub",
    "awssts",
    "awswafv2",
    "carbonblackdefense",
    "carbonblackdefensev2",
    "censys",
    "ciscoumbrella",
    "ciscoumbrellainvestigate",
    "cloudpassagehalo",
    "cofenseintelligence",
    "connector-template",
    "crits",
    "cylance",
    "dshield",
    "fortigate",
    "grrrapidresponse",
    "haveibeenpwned",
    "honeydb",
    "ipinfo",
    "ipstack",
    "isitphishing",
    "koodous",
    "malshare",
    "mcafeeepo",
    "metadefender",
    "microsoftsccm",
    "microsoftscom",
    "misp",
    "mongodb",
    "mxtoolbox",
    "mysql",
    "nessus",
    "netwitnessendpoint",
    "nginx",
    "paloaltonetworksfirewall",
    "phantom",
    "phishinginitiative",
    "phishlabs",
    "phishtank",
    "qradar",
    "qualys_ssllabs",
    "remedyforce",
    "ripe",
    "safebrowsing",
    "signalfx",
    "splunkitsi",
    "splunkoncall",
    "sqlite",
    "ssh",
    "statuspage",
    "symantecsa",
    "thehive",
    "threatcrowd",
    "timer",
    "tufinsecuretrack",
    "twilio",
    "virustotalv3",
    "vsphere",
    "whoisrdap",
    "wigle",
    "zendesk",
    "zscaler",
]

# Repos with suspected namespace conflicts (repo name conflicts with module name)
NAMESPACE_CONFLICT_REPOS = [
    # Will be populated after running linter
]

# Packages already included in the platform - exclude from E0401 filtering
PLATFORM_PACKAGES = {
    "beautifulsoup4", "bs4",  # beautifulsoup4 imports as bs4
    "soupsieve",
    "parse",
    "python_dateutil", "dateutil",  # python_dateutil imports as dateutil
    "six",
    "requests",
    "certifi",
    "charset_normalizer",
    "idna",
    "urllib3",
    "sh",
    "xmltodict",
    "simplejson",
    "python-dateutil",
    "python-magic", "magic",  # python-magic imports as magic
    "distro",
    "django",
    "requests-pkcs12", "requests_pkcs12",  # requests-pkcs12 can import as requests_pkcs12
    "pynacl", "nacl",  # pynacl imports as nacl
    "psycopg2",
    "PyYAML", "yaml",  # PyYAML imports as yaml
    "hvac",
    "pylint",
    "pudb",
    # Add alternative names and common variations
    "lxml",
    "defusedxml",
    "html5lib",
    "webencodings",
    "phantom_common",
    "encryption_helper",
}


def parse_args(args: List[str] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Lint Python code for Splunk SOAR apps.")
    
    parser.add_argument(
        "target",
        help="Directory or file to lint (if directory contains subdirectories, will lint each subdirectory)"
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
        help="Minimum message level to show: 'info' or 'error' (default: info)"
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
    
    parser.add_argument(
        "--single-repo",
        action="store_true",
        help="Treat target as a single repository instead of scanning for multiple repositories"
    )
    
    parser.add_argument(
        "--filter-e0401",
        action="store_true",
        help="Show only E0401 (import errors) and their unique messages"
    )
    
    parser.add_argument(
        "--json-failures",
        action="store_true",
        help="Output JSON with repositories as keys and their error messages as values (excludes error-free, pudb-only, and ignored repos)"
    )
    
    return parser.parse_args(args)


def extract_error_codes(output: str) -> List[str]:
    """Extract pylint error codes from output."""
    # Match patterns like "E0606", "W0613", "C0103", "I1101", "S101", etc.
    # E=Error, W=Warning, C=Convention, R=Refactor, F=Fatal, I=Info, S=Security
    error_pattern = r'\b[EWCRFIS]\d{4}\b'
    return re.findall(error_pattern, output)


def extract_error_messages(output: str) -> List[str]:
    """Extract detailed pylint error messages from output."""
    # Match patterns like "file.py:line:col: CODE: message"
    error_lines = []
    for line in output.split('\n'):
        if re.search(r':\d+:\d+:\s+[EWCRFIS]\d{4}:', line):
            error_lines.append(line.strip())
    return error_lines


def is_platform_package_error(error_message: str) -> bool:
    """Check if an error message is about a platform package."""
    for package in PLATFORM_PACKAGES:
        # Check for various patterns:
        # - "Unable to import 'package'"
        # - "Unable to import \"package\""
        # - "No module named 'package'"
        # - "No module named \"package\""
        # - Submodule imports like 'package.submodule'
        # - Just the package name in the message
        if (f"'{package}'" in error_message or 
            f'"{package}"' in error_message or
            f"'{package}." in error_message or  # submodule imports
            f'"{package}.' in error_message or  # submodule imports
            f"import '{package}'" in error_message or
            f'import "{package}"' in error_message or
            f"import '{package}." in error_message or  # submodule imports
            f'import "{package}.' in error_message or  # submodule imports
            f"named '{package}'" in error_message or
            f'named "{package}"' in error_message or
            f"named '{package}." in error_message or  # submodule imports
            f'named "{package}.' in error_message or  # submodule imports
            f" {package} " in error_message or
            f" {package}." in error_message or  # submodule imports
            error_message.endswith(f" {package}") or
            error_message.startswith(f"{package} ") or
            error_message.startswith(f"{package}.")):  # submodule imports
            return True
    return False


def extract_e0401_messages_by_repo(output: str, repo_name: str) -> Dict[str, List[str]]:
    """Extract E0401 error messages for a specific repository, excluding platform packages."""
    repo_errors = []
    
    for line in output.split('\n'):
        if 'E0401:' in line:
            # Extract just the error message part after "E0401:"
            match = re.search(r'E0401:\s*(.+)$', line)
            if match:
                error_message = match.group(1).strip()
                
                # Only add non-platform package errors
                if not is_platform_package_error(error_message):
                    repo_errors.append(error_message)
    
    # Return repo name as key with unique error messages as value
    return {repo_name: list(set(repo_errors))} if repo_errors else {}


def process_single_repo(repo_path: str, args: argparse.Namespace) -> tuple[int, List[str], List[str]]:
    """Process a single repository and return its exit code, error codes, and error messages."""
    logger.info(f"Processing repository: {repo_path}")
    
    # Check if we should process this app based on publisher
    if not should_process_app(repo_path):
        logger.info(f"Skipping {os.path.basename(repo_path)} - not a Splunk app")
        return 0, [], []  # Return success for skipped apps with no errors
    
    # Validate app.json if not disabled
    if not args.disable_app_json_validation and not validate_app_json(repo_path):
        return 1, [], []
    
    if not args.no_deps and not install_dependencies(repo_path):
        return 1, [], []
    
    # Run pylint
    exit_code, output = run_pylint(
        target=repo_path,
        output_format=args.output_format,
        verbose=args.verbose,
        message_level=args.message_level,
        no_deps=args.no_deps,
    )

    # Extract error codes and messages from output
    error_codes = extract_error_codes(output) if output else []
    error_messages = extract_error_messages(output) if output else []

    if output:
        print(f"\n=== Results for {os.path.basename(repo_path)} ===")
        print(output, end="")

    return exit_code, error_codes, error_messages


def has_only_pudb_import_errors(error_messages: List[str]) -> bool:
    """Check if the only errors in the list are pudb import errors."""
    if not error_messages:
        return False
    
    for error_msg in error_messages:
        # Check if this is an E0401 error about pudb
        if 'E0401:' in error_msg and 'pudb' in error_msg.lower():
            continue
        else:
            # Found a non-pudb error
            return False
    
    # All errors are pudb-related
    return True


def has_namespace_conflict(repo_name: str, error_messages: List[str]) -> bool:
    """Check if the repo has import errors that match the repository name, indicating a namespace conflict."""
    if not error_messages:
        return False
    
    # Look for E0401 import errors that mention the repo name
    for error_msg in error_messages:
        if 'E0401:' in error_msg:
            # Check if the error message contains the repo name as an import
            # Common patterns: "Unable to import 'reponame'" or 'Unable to import "reponame"'
            if (f"'{repo_name}'" in error_msg or 
                f'"{repo_name}"' in error_msg or
                f"import '{repo_name}'" in error_msg or
                f'import "{repo_name}"' in error_msg):
                return True
    
    return False


def main() -> int:
    """Main entry point for the CLI."""
    args = parse_args()

    if not os.path.exists(args.target):
        logger.error(f"Error: Target '{args.target}' does not exist")
        return 1

    # Check if we should treat target as a single repo or scan for multiple repos
    if args.single_repo or not os.path.isdir(args.target):
        # Process single repository or file
        return _process_single_target(args)
    
    # Check if target is a directory with subdirectories (multiple repos)
    if os.path.isdir(args.target):
        subdirs = [d for d in os.listdir(args.target) 
                  if os.path.isdir(os.path.join(args.target, d)) and not d.startswith('.')]
        
        if subdirs:
            return _process_multiple_repos(args, subdirs)
        else:
            # No subdirectories found, treat as single target
            return _process_single_target(args)


def _process_single_target(args) -> int:
    """Process a single target (file or directory)."""
    exit_code, error_codes, error_messages = process_single_repo(args.target, args)
    
    # Handle --json-failures for single repo
    if args.json_failures:
        repo_name = os.path.basename(args.target)
        failures_json = {}
        
        if error_messages:
            # Filter out platform package errors from the messages
            filtered_messages = []
            for message in error_messages:
                if 'E0401:' in message and is_platform_package_error(message):
                    continue  # Skip platform package errors
                filtered_messages.append(message)
            
            # Only include repo if it still has errors after filtering
            if filtered_messages:
                failures_json[repo_name] = filtered_messages
        
        print(json.dumps(failures_json, indent=2, sort_keys=True))
        return exit_code
    
    # For single repo, show error summary if there are errors
    if error_codes:
        if args.filter_e0401:
            repo_name = os.path.basename(args.target)
            e0401_messages_by_repo = extract_e0401_messages_by_repo('\n'.join(error_messages), repo_name)
            if e0401_messages_by_repo:
                print(f"\n=== E0401 Import Errors by Repository ({len(e0401_messages_by_repo)} repositories) ===")
                print(json.dumps(e0401_messages_by_repo, indent=2, sort_keys=True))
                
                # Count how many times each import failure occurs (same as multi-repo)
                import_failure_counts = defaultdict(int)
                for repo, errors in e0401_messages_by_repo.items():
                    for error in errors:
                        import_failure_counts[error] += 1
                
                print("\n=== Import Failure Counts ===")
                for error_msg in sorted(import_failure_counts.keys()):
                    count = import_failure_counts[error_msg]
                    print(f"{count} occurrences: {error_msg}")
            else:
                print("\n=== No E0401 errors found ===")
        else:
            print("\n=== Error Summary ===")
            error_counts = defaultdict(int)
            for error_code in error_codes:
                error_counts[error_code] += 1
            
            for error_code in sorted(error_counts.keys()):
                print(f"{error_code}: {error_counts[error_code]} occurrences")
            
            # Add comprehensive error summary by error code (same as multi-repo)
            error_summary: Dict[str, set] = defaultdict(set)
            repo_name = os.path.basename(args.target)
            for error_code in error_codes:
                error_summary[error_code].add(repo_name)
            
            if args.verbose:
                print("\n=== Comprehensive Error Summary ===")
                for error_code in sorted(error_summary.keys()):
                    repos_with_error = error_summary[error_code]
                    print(f"{error_code}: {len(repos_with_error)} repositories")
                    print(f"  Repositories: {', '.join(sorted(repos_with_error))}")
                
            print("\n=== Detailed Error Messages ===")
            for error_msg in error_messages:
                print(error_msg)
    else:
        print("\n=== No errors found in this repository ===")
    
    return exit_code


def _process_multiple_repos(args, subdirs) -> int:
    """Process multiple repositories in a directory."""
    logger.info(f"Found {len(subdirs)} repositories in {args.target}")
    overall_exit_code = 0
    failed_repos = []
    skipped_repos = []
    processed_repos = []
    error_free_repos = []  # Track repos with no errors
    pudb_only_repos = []  # Track repos with only pudb import errors
    namespace_conflict_repos = []  # Track repos with suspected namespace conflicts
    already_error_free_repos = []  # Track repos skipped due to ERROR_FREE_REPOS
    already_pudb_only_repos = []  # Track repos skipped due to PUDB_ONLY_ERROR_REPOS
    ignored_repos = []  # Track repos skipped due to IGNORED_REPOS
    error_summary: Dict[str, set] = defaultdict(set)
    repo_error_messages: Dict[str, List[str]] = {}  # Track error messages per repo
    all_e0401_messages = {}  # Track E0401 messages by repo across all repos
    
    for subdir in sorted(subdirs):
        repo_path = os.path.join(args.target, subdir)
        
        # Skip repos that are in the ignored list
        if subdir in IGNORED_REPOS:
            ignored_repos.append(subdir)
            continue
        
        # Skip repos that are already known to be error-free
        if subdir in ERROR_FREE_REPOS:
            already_error_free_repos.append(subdir)
            continue
        
        # Skip repos that only have pudb import errors (essentially clean)
        if subdir in PUDB_ONLY_ERROR_REPOS:
            already_pudb_only_repos.append(subdir)
            continue
        
        # Check if we should process this repo based on publisher
        if not should_process_app(repo_path):
            logger.info(f"Skipping {subdir} - not a Splunk app")
            skipped_repos.append(subdir)
            continue
        
        processed_repos.append(subdir)
        exit_code, error_codes, error_messages = process_single_repo(repo_path, args)
        
        # Store error messages for this repo
        repo_error_messages[subdir] = error_messages
        
        # Collect E0401 messages if filtering is enabled
        if args.filter_e0401:
            e0401_messages_by_repo = extract_e0401_messages_by_repo('\n'.join(error_messages), subdir)
            all_e0401_messages.update(e0401_messages_by_repo)
        
        # Collect error codes for this repo
        for error_code in error_codes:
            error_summary[error_code].add(subdir)
        
        # Track repos with no errors or only pudb errors
        if not error_codes:
            error_free_repos.append(subdir)
        elif has_only_pudb_import_errors(error_messages):
            pudb_only_repos.append(subdir)
        elif has_namespace_conflict(subdir, error_messages):
            namespace_conflict_repos.append(subdir)
        
        if exit_code != 0:
            overall_exit_code = exit_code
            failed_repos.append(subdir)
    
    # Report results
    logger.info(f"Processed {len(processed_repos)} Splunk apps, skipped {len(skipped_repos)} non-Splunk apps, skipped {len(already_error_free_repos)} known error-free apps, skipped {len(already_pudb_only_repos)} known pudb-only apps, ignored {len(ignored_repos)} repos")
    
    if failed_repos:
        logger.error(f"Linting failed for {len(failed_repos)} repositories: {', '.join(failed_repos)}")
    elif processed_repos:
        logger.info("All processed repositories passed linting")
    
    # Print E0401 summary if filtering is enabled
    if args.filter_e0401 and all_e0401_messages:
        print(f"\n=== E0401 Import Errors by Repository ({len(all_e0401_messages)} repositories) ===")
        print(json.dumps(all_e0401_messages, indent=2, sort_keys=True))
        
        # Count how many repos have each import failure
        import_failure_counts = defaultdict(int)
        for repo, errors in all_e0401_messages.items():
            for error in errors:
                import_failure_counts[error] += 1
        
        print("\n=== Import Failure Counts ===")
        for error_msg in sorted(import_failure_counts.keys()):
            count = import_failure_counts[error_msg]
            print(f"{count} repos: {error_msg}")
    
    # Print error summary (unless filtering for E0401 only)
    if error_summary and not args.filter_e0401:
        print("\n=== Error Summary ===")
        for error_code in sorted(error_summary.keys()):
            repos_with_error = error_summary[error_code]
            print(f"{error_code}: {len(repos_with_error)} repositories")
            if args.verbose:
                print(f"  Repositories: {', '.join(sorted(repos_with_error))}")
    
    # Print error-free repositories for future skipping
    if error_free_repos and not args.filter_e0401:
        print(f"\n=== Error-Free Repositories ({len(error_free_repos)}) ===")
        print("# Add these to your skip list for future runs:")
        print("ERROR_FREE_REPOS = [")
        for repo in sorted(error_free_repos):
            print(f'    "{repo}",')
        print("]")
    
    # Print pudb-only repositories for future reference
    if pudb_only_repos and not args.filter_e0401:
        print(f"\n=== Repositories with Only PUDB Import Errors ({len(pudb_only_repos)}) ===")
        print("# These repos only have 'Unable to import pudb' errors:")
        print("PUDB_ONLY_ERROR_REPOS = [")
        for repo in sorted(pudb_only_repos):
            print(f'    "{repo}",')
        print("]")
    
    # Print namespace conflict repositories for future reference
    if namespace_conflict_repos and not args.filter_e0401:
        print(f"\n=== Repositories with Suspected Namespace Conflicts ({len(namespace_conflict_repos)}) ===")
        print("# These repos have import errors that match their repository name:")
        print("NAMESPACE_CONFLICT_REPOS = [")
        for repo in sorted(namespace_conflict_repos):
            print(f'    "{repo}",')
        print("]")
    
    # Output JSON failures if requested
    if args.json_failures:
        failures_json = {}
        for repo, messages in repo_error_messages.items():
            # Only include repos that have errors and are not in our skip lists
            if (messages and 
                repo not in ERROR_FREE_REPOS and 
                repo not in PUDB_ONLY_ERROR_REPOS and 
                repo not in IGNORED_REPOS and
                repo not in error_free_repos and
                repo not in pudb_only_repos):
                
                # Filter out platform package errors from the messages
                filtered_messages = []
                for message in messages:
                    if 'E0401:' in message and is_platform_package_error(message):
                        continue  # Skip platform package errors
                    filtered_messages.append(message)
                
                # Only include repos that still have errors after filtering
                if filtered_messages:
                    failures_json[repo] = filtered_messages
        
        print(json.dumps(failures_json, indent=2, sort_keys=True))
    
    return overall_exit_code


if __name__ == "__main__":
    sys.exit(main())
