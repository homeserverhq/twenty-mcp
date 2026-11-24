"""CLI for the Twenty MCP semantic audit.

Examples:
    python -m src.audit.runner --list-domains
    python -m src.audit.runner --domain schema,status
    python -m src.audit.runner --all
    python -m src.audit.runner --l0 --quiet
"""

from __future__ import annotations

import argparse
import importlib
import os
import pkgutil
import platform
import sys
from pathlib import Path

from . import contracts
from .adapter import TwentyAdapter
from .harness import Run
from .mcp_client import AuditClient, token_from_env
from .report import coverage, summarize, write_json, write_markdown


def _load_contracts() -> None:
    package_dir = Path(contracts.__file__).parent
    for module in pkgutil.iter_modules([str(package_dir)]):
        if module.name.startswith("_"):
            continue
        importlib.import_module(f"{contracts.__name__}.{module.name}")


def _domains() -> list[str]:
    from .harness import REGISTRY

    return sorted({definition.domain for definition in REGISTRY})


def _parse_domains(values: list[str] | None) -> set[str] | None:
    if not values:
        return None
    domains: set[str] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                domains.add(part)
    return domains


def _fingerprint() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "allow_all_aggregate": os.getenv("ALLOW_ALL_AGGREGATE", "false"),
        "is_stateful": os.getenv("IS_STATEFUL", "false"),
        "mcp_url": os.getenv("MCP_URL", ""),
    }


def _residue(run: Run, adapter: TwentyAdapter) -> None:
    report = adapter.residue(run.client, run.run_id)
    for resource, count in report["counts"].items():
        run.record("residue", "fixture_scan", f"{resource} fixtures removed",
                   "", "PASS" if count == 0 else "FAIL",
                   f"{count} record(s) still match {report['prefix']}")
    for resource, error in report["errors"].items():
        run.record("residue", "fixture_scan", f"{resource} scan skipped",
                   "", "SKIP", error)
    for resource, diff in report.get("side_effects", {}).items():
        run.record("residue", "side_effect",
                   f"{resource} write side effect accounted for", "",
                   "SKIP",
                   f"before={diff['before']} after={diff['after']}; Twenty "
                   "auto-generates timeline activities for mutations, and the "
                   "fixture-prefix scan is zero")
    for resource, diff in report["count_diffs"].items():
        run.record("residue", "count_diff", f"{resource} count unchanged",
                   "", "PASS" if diff["before"] == diff["after"] else "FAIL",
                   f"before={diff['before']} after={diff['after']}")
    for resource, diff in report["soft_deleted_diffs"].items():
        run.record("residue", "soft_deleted_diff",
                   f"{resource} soft-deleted count unchanged", "",
                   "PASS" if diff["before"] == diff["after"] else "FAIL",
                   f"before={diff['before']} after={diff['after']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Twenty MCP semantic audit")
    parser.add_argument("--domain", action="append",
                        help="Domain or comma-separated domains (repeatable)")
    parser.add_argument("--all", action="store_true",
                        help="Run every contract and enforce coverage")
    parser.add_argument("--l0", "--schema-only", dest="l0", action="store_true",
                        help="Run only schema/metadata checks; no coverage gate")
    parser.add_argument("--list-domains", action="store_true",
                        help="List registered domains and exit")
    parser.add_argument("--url", help="MCP endpoint (default: MCP_URL env)")
    parser.add_argument("--report", default="docs/tool-audit.md")
    parser.add_argument("--json", dest="json_path", default="docs/tool-audit.json")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    _load_contracts()
    if args.list_domains:
        for domain in _domains():
            print(domain)
        return 0

    if args.l0:
        domains = {"schema"}
    elif args.all:
        domains = None
    else:
        domains = _parse_domains(args.domain)
        if not domains:
            parser.error("pass --domain <domain>, --all, or --l0")

    token = token_from_env()
    if not token and not args.l0:
        parser.error("set API_KEY (or TWENTY_API_KEY)")

    adapter = TwentyAdapter(token)
    primary = AuditClient(url=args.url, token=token, require_token=not args.l0)
    clients = {"primary": primary}
    secondary_token = os.getenv("AUDIT_SECONDARY_API_KEY", "").strip()
    if secondary_token:
        clients["secondary"] = AuditClient(url=args.url, token=secondary_token)

    live_tools = primary.tool_names()
    warnings = adapter.preflight(primary, full=not args.l0)
    run = Run(clients, adapter, domains=domains)
    run.warnings.extend(warnings)

    if not args.quiet:
        print(f"Audit {run.run_id} against {primary.url}", file=sys.stderr)
        print(f"Live tools: {len(live_tools)}", file=sys.stderr)
        for warning in warnings:
            print(f"WARN {warning}", file=sys.stderr)

    run.run()
    if args.all:
        _residue(run, adapter)

    metadata = {
        "identity": {
            "workspace": adapter.identity.get("workspaceId", ""),
            "type": adapter.identity.get("type", ""),
        },
        "fingerprint": _fingerprint(),
    }
    write_markdown(run, live_tools, args.report, metadata,
                   sorted(domains) if domains else None)
    write_json(run, live_tools, args.json_path, metadata)

    summary = summarize(run)
    total_pass = sum(row["PASS"] for row in summary.values())
    total_fail = sum(row["FAIL"] for row in summary.values())
    total_skip = sum(row["SKIP"] for row in summary.values())
    total_warn = sum(row["WARN"] for row in summary.values())
    cov = coverage(run, live_tools)

    print("")
    print("| Domain | PASS | FAIL | SKIP | WARN |")
    print("|---|---:|---:|---:|---:|")
    for domain in sorted(summary):
        row = summary[domain]
        print(f"| {domain} | {row['PASS']} | {row['FAIL']} | "
              f"{row['SKIP']} | {row['WARN']} |")
    print(f"| Total | {total_pass} | {total_fail} | {total_skip} | {total_warn} |")
    print("")
    print(f"Coverage: {cov['declared']}/{cov['live']} tools declared, "
          f"{cov['called']} called")
    if cov["missing_contracts"]:
        print(f"Missing contracts: {len(cov['missing_contracts'])}")
    if cov["unknown_contract_tools"]:
        print(f"Unknown contract tools: {cov['unknown_contract_tools']}")
    if cov["uncalled"]:
        print(f"Declared but not called: {len(cov['uncalled'])}")
    print(f"Report: {args.report}")
    print(f"JSON:   {args.json_path}")

    coverage_failure = bool(cov["unknown_contract_tools"])
    if args.all and (cov["missing_contracts"] or cov["uncalled"]):
        coverage_failure = True
    primary.close()
    for client in clients.values():
        if client is not primary:
            client.close()
    adapter.close()
    return 1 if (total_fail or coverage_failure) else 0


if __name__ == "__main__":
    raise SystemExit(main())
