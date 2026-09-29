#!/usr/bin/env python3
"""
extract_cookies.py — Helper to parse exported muse.ai cookies into a ready-to-inject JSON payload.

Supports:
- Chrome DevTools JSON array export (from Cookie-Editor extension or DevTools)
- Netscape cookies.txt format
- Raw header string ('name1=val1; name2=val2')

Usage:
    python scripts/extract_cookies.py input_cookies.txt [--label my-account] [--out account.json]
"""

import argparse
import json
import os
import sys

TARGET_COOKIES = {
    "hatch_sess",
    "hatch_gw",
    "hatch_native_auth_device",
    "hatch_vml",
    "datr"
}

def parse_cookies_file(file_path: str) -> dict[str, str]:
    if not os.path.exists(file_path):
        print(f"[!] Error: File {file_path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(file_path, encoding="utf-8") as f:
        content = f.read().strip()

    cookies: dict[str, str] = {}

    # 1. JSON array format (e.g. from Cookie-Editor extension)
    if content.startswith("["):
        try:
            items = json.loads(content)
            for item in items:
                name = item.get("name")
                val = item.get("value")
                if name and val:
                    cookies[name] = val
            return cookies
        except json.JSONDecodeError:
            pass

    # 2. JSON object format
    if content.startswith("{"):
        try:
            d = json.loads(content)
            if "cookies" in d and isinstance(d["cookies"], dict):
                return d["cookies"]
            return d
        except json.JSONDecodeError:
            pass

    # 3. Netscape format or key=value header format
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 7:
                name = parts[5].strip()
                val = parts[6].strip()
                cookies[name] = val
        elif "=" in line:
            for pair in line.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    cookies[k.strip()] = v.strip()

    return cookies

def main():
    parser = argparse.ArgumentParser(description="Parse muse.ai cookies into a museai JSON payload")
    parser.add_argument("file", help="Path to cookies file (JSON, Netscape, or text header)")
    parser.add_argument("--label", default="muse-account", help="Account label (default: muse-account)")
    parser.add_argument("--out", default=None, help="Save to output JSON file (default: print to stdout)")
    args = parser.parse_args()

    all_cookies = parse_cookies_file(args.file)
    extracted = {k: v for k, v in all_cookies.items() if k in TARGET_COOKIES or k.startswith("hatch_")}

    if not extracted.get("hatch_sess"):
        print("[!] Warning: 'hatch_sess' cookie was not found in the input! Account might be unauthenticated.", file=sys.stderr)

    payload = {
        "label": args.label,
        "cookies": extracted
    }

    formatted = json.dumps(payload, indent=2)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(formatted + "\n")
        print(f"[+] Successfully saved import payload to: {args.out}")
        print(f"    - Included cookies: {', '.join(extracted.keys())}")
        print("    - Inject with: curl -X POST http://127.0.0.1:18610/admin/accounts -H 'Authorization: Bearer <ADMIN_KEY>' -H 'Content-Type: application/json' -d @" + args.out)
    else:
        print(formatted)

if __name__ == "__main__":
    main()
