"""Command-line interface for soar-app-linter."""

import argparse
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
    "abuseipdb",
    "alienvaultotx",
    "awsathena",
    "awscloudtrail",
    "awsdynamodb",
    "awsguardduty",
    "awslambda",
    "awss3",
    "awssecurityhub",
    "awssts",
    "awswafv2",
    "azuread",
    "azuredevops",
    "bigfix",
    "bigquery",
    "bmcremedy",
    "carbonblackappcontrol",
    "carbonblackdefense",
    "carbonblackdefensev2",
    "censys",
    "checkpointfirewall",
    "ciscoesa",
    "ciscosma",
    "ciscotalosintelligence",
    "ciscoumbrella",
    "ciscoumbrellainvestigate",
    "ciscowebex",
    "cloudconvert",
    "cloudpassagehalo",
    "cofenseintelligence",
    "confluence",
    "connector-template",
    "crits",
    "csvimport",
    "cylance",
    "dshield",
    "elasticsearch",
    "fidelisnetwork",
    "fortigate",
    "googleworkspacefordrive",
    "grrrapidresponse",
    "haveibeenpwned",
    "honeydb",
    "http",
    "ibmwatsonv3",
    "imap",
    "ipinfo",
    "ipstack",
    "isitphishing",
    "ivantiitsm",
    "junipersrx",
    "koodous",
    "malshare",
    "maxmind",
    "mcafeeepo",
    "metadefender",
    "metasponse",
    "microsoft365defender",
    "microsoftadldap",
    "microsoftazuresql",
    "microsoftsccm",
    "microsoftscom",
    "microsoftsqlserver",
    "mimecast",
    "misp",
    "mongodb",
    "mxtoolbox",
    "mysql",
    "nessus",
    "netwitnessendpoint",
    "nginx",
    "nmap",
    "paloaltonetworksfirewall",
    "phantom",
    "phishinginitiative",
    "phishlabs",
    "phishtank",
    "postgresql",
    "qradar",
    "qualys_ssllabs",
    "remedyforce",
    "rest_ingest",
    "ripe",
    "rsasecureidam",
    "safebrowsing",
    "salesforce",
    "screenshotmachine",
    "signalfx",
    "smtp",
    "splunkattackanalyzer",
    "splunkitsi",
    "splunkoncall",
    "sqlite",
    "ssh",
    "statuspage",
    "symantecdlp",
    "symantecmessaginggateway",
    "symantecsa",
    "taniumrest",
    "tenableio",
    "thehive",
    "threatcrowd",
    "timer",
    "tufinsecuretrack",
    "twilio",
    "virustotalv3",
    "vsphere",
    "whois",
    "whoisrdap",
    "wigle",
    "wildfire",
    "wmi",
    "zendesk",
    "zscaler",
]

IGNORED_REPOS = [
    "alibabaram",
    "virustotal",
    "wwt_cisco_firepower",
    "frictionless_connector_repo",
]


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


def main() -> int:
    """Main entry point for the CLI."""
    args = parse_args()

    if not os.path.exists(args.target):
        logger.error(f"Error: Target '{args.target}' does not exist")
        return 1

    # Check if target is a directory with subdirectories (multiple repos)
    if os.path.isdir(args.target):
        subdirs = [d for d in os.listdir(args.target) 
                  if os.path.isdir(os.path.join(args.target, d)) and not d.startswith('.')]
        
        if subdirs:
            logger.info(f"Found {len(subdirs)} repositories in {args.target}")
            overall_exit_code = 0
            failed_repos = []
            skipped_repos = []
            processed_repos = []
            error_free_repos = []  # Track repos with no errors
            already_error_free_repos = []  # Track repos skipped due to ERROR_FREE_REPOS
            ignored_repos = []  # Track repos skipped due to IGNORED_REPOS
            error_summary: Dict[str, set] = defaultdict(set)
            repo_error_messages: Dict[str, List[str]] = {}  # Track error messages per repo
            
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
                
                # Check if we should process this repo based on publisher
                if not should_process_app(repo_path):
                    skipped_repos.append(subdir)
                    continue
                
                processed_repos.append(subdir)
                exit_code, error_codes, error_messages = process_single_repo(repo_path, args)
                
                # Store error messages for this repo
                repo_error_messages[subdir] = error_messages
                
                # Collect error codes for this repo
                for error_code in error_codes:
                    error_summary[error_code].add(subdir)
                
                # Track repos with no errors
                if not error_codes:
                    error_free_repos.append(subdir)
                
                if exit_code != 0:
                    overall_exit_code = exit_code
                    failed_repos.append(subdir)
            
            # Report results
            logger.info(f"Processed {len(processed_repos)} Splunk apps, skipped {len(skipped_repos)} non-Splunk apps, skipped {len(already_error_free_repos)} known error-free apps, ignored {len(ignored_repos)} repos")
            
            if failed_repos:
                logger.error(f"Linting failed for {len(failed_repos)} repositories: {', '.join(failed_repos)}")
            elif processed_repos:
                logger.info("All processed repositories passed linting")
            
            # Print error summary
            if error_summary:
                print("\n=== Error Summary ===")
                for error_code in sorted(error_summary.keys()):
                    repos_with_error = error_summary[error_code]
                    print(f"{error_code}: {len(repos_with_error)} repositories")
                    if args.verbose:
                        print(f"  Repositories: {', '.join(sorted(repos_with_error))}")
            
            # Print error-free repositories for future skipping
            if error_free_repos:
                print(f"\n=== Error-Free Repositories ({len(error_free_repos)}) ===")
                print("# Add these to your skip list for future runs:")
                print("ERROR_FREE_REPOS = [")
                for repo in sorted(error_free_repos):
                    print(f'    "{repo}",')
                print("]")
            
            return overall_exit_code
    
    # Process single target (file or directory)
    exit_code, error_codes, error_messages = process_single_repo(args.target, args)
    
    # For single repo, show error summary if there are errors
    if error_codes:
        print("\n=== Error Summary ===")
        error_counts = defaultdict(int)
        for error_code in error_codes:
            error_counts[error_code] += 1
        
        for error_code in sorted(error_counts.keys()):
            print(f"{error_code}: {error_counts[error_code]} occurrences")
            
        print("\n=== Detailed Error Messages ===")
        for error_msg in error_messages:
            print(error_msg)
    else:
        print("\n=== No errors found in this repository ===")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
