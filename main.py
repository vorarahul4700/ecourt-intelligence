#!/usr/bin/env python3
"""
CLI entrypoint for eCourts India Services Scraper.
Supports interactive prompt or CLI flags, formats output (rich tables, JSON, CSV),
and optionally inspects initial DOM hidden input elements.
"""

import sys
import json
import argparse
from typing import Optional
from bs4 import BeautifulSoup
import requests

from ecourt import ECourtScraper, ECourtCaseResult
from ecourt.config import DEFAULT_MAX_RETRIES

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def print_rich_result(result: ECourtCaseResult) -> None:
    """Renders the case details in styled rich terminal tables."""
    console = Console()

    # Title Banner
    banner = Panel(
        Text(f"{result.court_name}\nCNR: {result.cnr}", justify="center", style="bold cyan"),
        title="[bold green]eCourts India - Case Report[/bold green]",
        border_style="green",
    )
    console.print(banner)

    # 1. Case Details Table
    t_details = Table(title="Case Details", border_style="cyan", show_lines=True)
    t_details.add_column("Field", style="bold yellow")
    t_details.add_column("Value", style="white")

    for k, v in result.case_details.model_dump().items():
        if v:
            t_details.add_row(k.replace('_', ' ').title(), str(v))
    console.print(t_details)

    # 2. Case Status Table
    t_status = Table(title="Case Status", border_style="magenta", show_lines=True)
    t_status.add_column("Field", style="bold yellow")
    t_status.add_column("Value", style="white")

    for k, v in result.case_status.model_dump().items():
        if v:
            t_status.add_row(k.replace('_', ' ').title(), str(v))
    console.print(t_status)

    # 3. Parties Table
    t_parties = Table(title="Parties & Advocates", border_style="blue", show_lines=True)
    t_parties.add_column("Role", style="bold green")
    t_parties.add_column("Name", style="white")
    t_parties.add_column("Advocate", style="cyan")

    for p in result.petitioners:
        t_parties.add_row("Petitioner", p.name, p.advocate or "N/A")
    for r in result.respondents:
        t_parties.add_row("Respondent", r.name, r.advocate or "N/A")
    console.print(t_parties)

    # 4. Acts Table
    if result.acts:
        t_acts = Table(title="Under Act(s) & Section(s)", border_style="yellow", show_lines=True)
        t_acts.add_column("Under Act", style="bold white")
        t_acts.add_column("Under Section", style="cyan")
        for a in result.acts:
            t_acts.add_row(a.under_act, a.under_section)
        console.print(t_acts)

    # 5. Processes Table
    if result.processes:
        t_proc = Table(title="Processes Issued", border_style="red", show_lines=True)
        t_proc.add_column("Process ID", style="bold yellow")
        t_proc.add_column("Title", style="white")
        t_proc.add_column("Date", style="cyan")
        for proc in result.processes:
            t_proc.add_row(proc.process_id, proc.process_title, proc.process_date)
        console.print(t_proc)

    # 6. IA Status Table
    if result.ia_status:
        t_ia = Table(title="Interlocutory Application (IA) Status", border_style="cyan", show_lines=True)
        t_ia.add_column("IA Number", style="bold yellow")
        t_ia.add_column("Party Name", style="white")
        t_ia.add_column("Filing Date", style="white")
        t_ia.add_column("Next Date", style="cyan")
        t_ia.add_column("Purpose", style="magenta")
        t_ia.add_column("Status", style="green")
        for ia in result.ia_status:
            t_ia.add_row(ia.ia_number, ia.party_name, ia.filing_date, ia.next_date, ia.purpose or "", ia.status)
        console.print(t_ia)

    # 7. Case History Table
    if result.case_history:
        t_hist = Table(title="Case Hearing History", border_style="green", show_lines=True)
        t_hist.add_column("Judge", style="white")
        t_hist.add_column("Business on Date", style="cyan")
        t_hist.add_column("Hearing Date", style="yellow")
        t_hist.add_column("Purpose of Hearing", style="bold green")
        for h in result.case_history:
            t_hist.add_row(h.judge, h.business_on_date, h.hearing_date, h.purpose_of_hearing)
        console.print(t_hist)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="eCourts India Case Scraper by CNR number with automated captcha solving."
    )
    parser.add_argument(
        "--cnr",
        "-c",
        type=str,
        help="16-digit alphanumeric CNR Number. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["table", "json", "raw"],
        default="table",
        help="Output format: 'table' (rich colored tables), 'json', or 'raw' (HTML). Default: table.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Path to save output file (e.g. result.json or result.html).",
    )
    parser.add_argument(
        "--proxy",
        "-p",
        type=str,
        default=None,
        help="Outbound proxy URL (e.g. http://user:pass@host:port). Can also be set via ECOURT_PROXY.",
    )
    parser.add_argument(
        "--retries",
        "-r",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Maximum captcha solving attempts. Default: {DEFAULT_MAX_RETRIES}.",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Custom initial URL with query parameters/token (optional).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress intermediate progress logs.",
    )

    args = parser.parse_args()

    scraper = ECourtScraper(proxy=args.proxy)

    # User-defined CNR input
    cnr = args.cnr
    if not cnr:
        try:
            cnr = input("Enter 16-digit CNR Number: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user.")
            sys.exit(0)

    if not cnr:
        print("Error: CNR Number is required.", file=sys.stderr)
        sys.exit(1)

    try:
        result = scraper.search_case(
            cino=cnr,
            max_retries=args.retries,
            initial_url=args.url,
            verbose=not args.quiet,
        )
    except Exception as e:
        print(f"\n[Error] {e}", file=sys.stderr)
        sys.exit(1)

    # Output formatting
    if args.format == "json":
        json_output = result.model_dump_json(indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"\nResult saved to {args.output}")
        else:
            print(json_output)

    elif args.format == "raw":
        raw_html = result.raw_html or ""
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(raw_html)
            print(f"\nRaw HTML saved to {args.output}")
        else:
            print(raw_html)

    else:  # Table / Pretty format
        if HAS_RICH:
            print_rich_result(result)
        else:
            # Fallback simple text print if rich is unavailable
            print("\n=== CASE DETAILS ===")
            for k, v in result.case_details.model_dump().items():
                print(f"{k}: {v}")
            print("\n=== CASE STATUS ===")
            for k, v in result.case_status.model_dump().items():
                print(f"{k}: {v}")
            print("\n=== PETITIONERS ===")
            for p in result.petitioners:
                print(f"- {p.name} (Advocate: {p.advocate})")
            print("\n=== RESPONDENTS ===")
            for r in result.respondents:
                print(f"- {r.name}")
            print("\n=== ACTS ===")
            for a in result.acts:
                print(f"- {a.under_act}: {a.under_section}")
            print("\n=== HISTORY ===")
            for h in result.case_history:
                print(f"- {h.business_on_date} -> Next: {h.hearing_date} [{h.purpose_of_hearing}]")

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result.model_dump_json(indent=2))
            print(f"\nResult saved to {args.output}")


if __name__ == "__main__":
    main()
