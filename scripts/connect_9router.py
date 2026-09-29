#!/usr/bin/env python3
"""
connect_9router.py — Auto-inject Muse AI Provider and Models into 9Router SQLite Database.

Usage:
    python scripts/connect_9router.py [--port 18610] [--api-key sk-boz-muse-api-key] [--prefix muse]
"""

import argparse
import json
import os
import sqlite3
import sys
import time

DEFAULT_DB = os.path.expanduser("~/.9router/db/data.sqlite")

def connect_9router(db_path: str, port: int, api_key: str, prefix: str):
    if not os.path.exists(db_path):
        print(f"[!] Error: 9Router database not found at {db_path}", file=sys.stderr)
        print("[!] Make sure 9Router is installed and has run at least once.", file=sys.stderr)
        sys.exit(1)

    base_url = f"http://127.0.0.1:{port}/v1"
    node_id = f"openai-compatible-chat-{prefix}"
    conn_id = f"conn-{prefix}-local"
    now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    node_data = {
        "prefix": prefix,
        "apiType": "chat",
        "baseUrl": base_url,
        "nodeName": "Muse AI",
        "models": [
            {"id": "muse-chat", "name": "Muse Chat (Personal Agent)"},
            {"id": "muse-image", "name": "Muse Image"},
            {"id": "muse-video", "name": "Muse Video"},
            {"id": "gpt-4o", "name": "Muse GPT-4o Alias"},
            {"id": "gpt-5", "name": "Muse GPT-5 Alias"},
            {"id": "claude-sonnet-4", "name": "Muse Sonnet Alias"}
        ]
    }

    conn_data = {
        "defaultModel": "muse-chat",
        "apiKey": api_key,
        "testStatus": "active",
        "lastError": None,
        "providerSpecificData": {
            "prefix": prefix,
            "apiType": "chat",
            "baseUrl": base_url,
            "nodeName": "Muse AI"
        }
    }

    print(f"[*] Connecting to 9Router SQLite: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Register or update provider node
    cur.execute("""
    INSERT OR REPLACE INTO providerNodes (id, type, name, data, createdAt, updatedAt)
    VALUES (?, ?, ?, ?, ?, ?);
    """, (node_id, "openai-compatible", "Muse AI", json.dumps(node_data), now, now))

    # 2. Register or update connection
    cur.execute("""
    INSERT OR REPLACE INTO providerConnections (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (conn_id, node_id, "apikey", "Muse AI Local Node", "admin@local", 1, 1, json.dumps(conn_data), now, now))

    conn.commit()
    conn.close()

    print("[+] Successfully registered Muse AI provider to 9Router!")
    print(f"    - Node ID   : {node_id}")
    print(f"    - Base URL  : {base_url}")
    print(f"    - Prefix    : {prefix}")
    print("    - Test Call : curl -s -X POST http://127.0.0.1:20128/v1/chat/completions \\")
    print("                  -H 'Content-Type: application/json' \\")
    print(f"                  -d '{{\"model\": \"{prefix}/muse-chat\", \"messages\": [{{\"role\": \"user\", \"content\": \"ping\"}}]}}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect museai API to 9Router Gateway")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"Path to 9Router database (default: {DEFAULT_DB})")
    parser.add_argument("--port", type=int, default=18610, help="museai service port (default: 18610)")
    parser.add_argument("--api-key", default="sk-boz-muse-api-key", help="museai API key (default: sk-boz-muse-api-key)")
    parser.add_argument("--prefix", default="muse", help="Model prefix in 9Router (default: muse)")
    args = parser.parse_args()

    connect_9router(args.db, args.port, args.api_key, args.prefix)
