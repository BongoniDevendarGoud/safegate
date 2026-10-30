#!/usr/bin/env python3
"""
SafeGate CLI — Headless Terminal Tool & OSI Security Appliance
=============================================================
A standalone Command-Line Interface (CLI) tool for screening media,
managing blocklists, inspecting cryptographic audit chains, and running
the headless OSI network server.

COMMANDS:
  safegate scan <file>     Screen a video through the complete 7-Layer OSI stack
  safegate serve           Launch the headless OSI network screening server
  safegate audit           Verify cryptographic SHA-256 audit chain integrity
  safegate blocklist       Query or manage exact & perceptual blocklists
  safegate stats           Display screening metrics and telemetry in terminal
"""

import sys
import argparse
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.config import settings
from app.db import SessionLocal, init_db
from app.models.database import Upload, BlocklistHash, BlocklistPHash
from app.osi.stack import OSIProtocolStack
from app.pipeline.audit import verify_audit_chain
from app.pipeline.hashing import add_to_exact_blocklist

# ANSI Terminal Color Constants
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
GRAY = "\033[90m"


def print_banner():
    banner = f"""
{CYAN}{BOLD}======================================================================
  SafeGate -- 7-Layer OSI Video Screening Gateway & CLI Appliance
======================================================================{RESET}
{GRAY}Architecture: OSI Model Layers 1-7 | Mode: Fail-Closed & Tamper-Resistant{RESET}
"""
    print(banner)


def cmd_scan(args):
    """Executes media screening through the 7-layer OSI protocol stack."""
    if not getattr(args, "live_model", False):
        import os
        os.environ.setdefault("SAFEGATE_MOCK_MODEL", "true")

    target_path = Path(args.file)
    if not target_path.exists():
        print(f"{RED}[ERROR] Target file does not exist: {target_path}{RESET}")
        sys.exit(1)

    print(f"\n{BOLD}Initiating OSI Protocol Stack Analysis on:{RESET} {CYAN}{target_path.name}{RESET}")
    print(f"{GRAY}Size: {target_path.stat().st_size:,} bytes | Client IP: {args.ip}{RESET}\n")

    stack = OSIProtocolStack()
    db = SessionLocal()

    try:
        with open(target_path, "rb") as f:
            report = stack.process_media_stream(
                stream=f,
                original_filename=target_path.name,
                client_ip=args.ip,
                session_key=args.key or settings.CLIENT_API_KEY,
                db=db,
            )

        # Print Layer-by-Layer Diagnostics
        print(f"{BOLD}{'LAYER':<12} {'SUBSYSTEM':<32} {'STATUS':<10} {'LATENCY':<10} {'DETAILS'}{RESET}")
        print("-" * 85)

        for s in report.steps:
            if s.status == "PASS":
                color = GREEN
            elif s.status == "REVIEW":
                color = YELLOW
            else:
                color = RED

            layer_tag = f"Layer {s.layer_num}"
            print(f"{BOLD}{layer_tag:<12}{RESET} {s.layer_name:<32} {color}{BOLD}{s.status:<10}{RESET} {s.duration_ms:>6.1f}ms  {s.details}")

        print("-" * 85)

        # Verdict Badge
        v = report.verdict
        if v == "ALLOW":
            v_color = GREEN
            badge = f"{GREEN}{BOLD}>>> FINAL VERDICT: ALLOW (Published) <<<{RESET}"
        elif v == "REVIEW":
            v_color = YELLOW
            badge = f"{YELLOW}{BOLD}>>> FINAL VERDICT: REVIEW (Quarantined) <<<{RESET}"
        else:
            v_color = RED
            badge = f"{RED}{BOLD}>>> FINAL VERDICT: BLOCK (Deleted & Blocklisted) <<<{RESET}"

        print(f"\n{badge}")
        print(f"{BOLD}Upload ID:{RESET}       {report.upload_id}")
        if report.sha256_hash:
            print(f"{BOLD}SHA-256:{RESET}         {report.sha256_hash}")
        if report.nsfw_worst_score is not None:
            print(f"{BOLD}NSFW Peak:{RESET}       {report.nsfw_worst_score*100:.1f}%")
        if report.deepfake_risk_score is not None:
            print(f"{BOLD}Deepfake Risk:{RESET}   {report.deepfake_risk_score}/100")
        print(f"{BOLD}Pipeline Time:{RESET}   {report.scan_duration_sec:.3f} seconds")
        print(f"{BOLD}Explanation:{RESET}     {report.explanation}\n")

    finally:
        db.close()


def cmd_audit(args):
    """Traverses and verifies the cryptographic audit hash chain in terminal."""
    print(f"\n{BOLD}Verifying Cryptographic SHA-256 Audit Hash Chain...{RESET}")
    db = SessionLocal()
    try:
        res = verify_audit_chain(db)
        print("-" * 65)
        if res["valid"]:
            print(f"{GREEN}{BOLD}✓ AUDIT INTEGRITY: VALID (Cryptographic Chain Intact){RESET}")
        else:
            print(f"{RED}{BOLD}⚠ AUDIT INTEGRITY: COMPROMISED (Tampering Detected!){RESET}")

        print(f"Total Sequential Records: {BOLD}{res['total_entries']}{RESET}")
        print(f"Broken at Row ID:         {BOLD}{res['broken_at'] or 'None'}{RESET}")
        print(f"Verification Summary:     {res['message']}")
        print("-" * 65 + "\n")
    finally:
        db.close()


def cmd_blocklist(args):
    """Lists or adds blocklist entries."""
    db = SessionLocal()
    try:
        if args.add:
            sha = args.add.strip().lower()
            if len(sha) != 64:
                print(f"{RED}[ERROR] SHA-256 hash must be exactly 64 hexadecimal characters.{RESET}")
                return
            add_to_exact_blocklist(sha, db, source="cli-admin")
            print(f"{GREEN}[SUCCESS] Added SHA-256 to transport blocklist: {sha}{RESET}")
            return

        # List entries
        exact = db.query(BlocklistHash).order_by(BlocklistHash.id.desc()).limit(20).all()
        phash = db.query(BlocklistPHash).order_by(BlocklistPHash.id.desc()).limit(20).all()

        print(f"\n{BOLD}Exact SHA-256 Blocklist (Recent {len(exact)} Entries):{RESET}")
        for b in exact:
            print(f" - ID #{b.id:<4} SHA: {b.sha256_hash} (Source: {b.source})")

        print(f"\n{BOLD}Perceptual pHash Blocklist (Recent {len(phash)} Entries):{RESET}")
        for p in phash:
            print(f" - ID #{p.id:<4} pHash: {p.phash_hex} (Source: {p.source})")
        print()
    finally:
        db.close()


def cmd_stats(args):
    """Displays terminal screening metrics."""
    db = SessionLocal()
    try:
        total = db.query(Upload).count()
        allowed = db.query(Upload).filter(Upload.verdict == "ALLOW").count()
        reviewed = db.query(Upload).filter(Upload.verdict == "REVIEW").count()
        blocked = db.query(Upload).filter(Upload.verdict == "BLOCK").count()
        exact_bl = db.query(BlocklistHash).count()
        phash_bl = db.query(BlocklistPHash).count()

        print(f"\n{BOLD}SafeGate Telemetry & Operational Metrics:{RESET}")
        print("-" * 50)
        print(f" Total Media Processed:      {BOLD}{total}{RESET}")
        print(f" Clean Media (ALLOW):         {GREEN}{BOLD}{allowed}{RESET}")
        print(f" In Quarantine (REVIEW):      {YELLOW}{BOLD}{reviewed}{RESET}")
        print(f" Prohibited (BLOCK):          {RED}{BOLD}{blocked}{RESET}")
        print(f" Exact SHA-256 Blocklisted:   {BOLD}{exact_bl}{RESET}")
        print(f" Perceptual pHashes Indexed:  {BOLD}{phash_bl}{RESET}")
        print("-" * 50 + "\n")
    finally:
        db.close()


def cmd_serve(args):
    """Launches the headless OSI screening server."""
    import uvicorn
    from app.server import app as headless_app
    print(f"\n{GREEN}{BOLD}Launching SafeGate Headless OSI Protocol Server on http://{args.host}:{args.port}...{RESET}")
    print(f"{GRAY}Headless API Daemon -- Pure Protocol Endpoints (No HTML Web UI){RESET}\n")
    uvicorn.run(headless_app, host=args.host, port=args.port)


def main():
    print_banner()
    init_db()

    parser = argparse.ArgumentParser(
        description="SafeGate — 7-Layer OSI Video Screening CLI Tool & Headless Server"
    )
    subparsers = parser.add_subparsers(dest="command", help="SafeGate CLI Commands")

    # Command: scan
    p_scan = subparsers.add_parser("scan", help="Screen a media file through all 7 OSI layers")
    p_scan.add_argument("file", help="Path to video file (MP4, MOV, AVI, MKV, WebM)")
    p_scan.add_argument("--key", help="Client or Admin API key (defaults to .env)", default=None)
    p_scan.add_argument("--ip", help="Simulated client network IP address", default="127.0.0.1")
    p_scan.add_argument("--live-model", action="store_true", help="Download and use full 300MB HuggingFace PyTorch weights (requires internet)", default=False)
    p_scan.set_defaults(func=cmd_scan)

    # Command: audit
    p_audit = subparsers.add_parser("audit", help="Verify cryptographic SHA-256 audit hash chain")
    p_audit.set_defaults(func=cmd_audit)

    # Command: blocklist
    p_bl = subparsers.add_parser("blocklist", help="Inspect or add hashes to blocklists")
    p_bl.add_argument("--add", help="SHA-256 hexadecimal hash to blocklist", default=None)
    p_bl.set_defaults(func=cmd_blocklist)

    # Command: stats
    p_stats = subparsers.add_parser("stats", help="Display gateway operational telemetry")
    p_stats.set_defaults(func=cmd_stats)

    # Command: serve
    p_serve = subparsers.add_parser("serve", help="Run the headless OSI network screening server daemon")
    p_serve.add_argument("--host", default="127.0.0.1", help="Bind IP address")
    p_serve.add_argument("--port", type=int, default=8000, help="Listen port")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
