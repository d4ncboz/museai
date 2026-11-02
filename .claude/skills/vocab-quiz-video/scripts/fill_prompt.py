#!/usr/bin/env python3
"""Build the muse.ai prompt from prompt-template.md + languages/<lang>.md + episode values."""

import argparse
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent


def front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        sys.exit(f"{path}: no front matter")
    values = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        # Strip only the one space after the colon: some values start with a space on purpose.
        values[key.strip().upper()] = value[1:] if value.startswith(" ") else value
    return values


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lang", required=True, help="file name in languages/, e.g. german")
    ap.add_argument("--level", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--next-level", required=True)
    ap.add_argument("--next-topic", required=True)
    a = ap.parse_args()

    lang_file = SKILL / "languages" / f"{a.lang}.md"
    if not lang_file.exists():
        sys.exit(f"No playbook {lang_file}. Copy languages/_new-language.md first.")
    values = front_matter(lang_file)
    values.update(LEVEL=a.level, TOPIC=a.topic, NEXT_LEVEL=a.next_level, NEXT_TOPIC=a.next_topic)

    optional = {"GRAMMAR_CHECK", "WORD_NOTES"}
    empty = [k for k, v in values.items() if not v.strip() and k not in optional]
    if empty:
        sys.exit(f"{lang_file}: fill these keys: {', '.join(empty)}")

    prompt = (SKILL / "prompt-template.md").read_text(encoding="utf-8")
    prompt = re.sub(r"\{([A-Z_]+)\}", lambda m: values.get(m.group(1), m.group(0)), prompt)
    left = sorted(set(re.findall(r"\{[A-Z_]+\}", prompt)))
    if left:
        sys.exit(f"Unfilled placeholders: {', '.join(left)}")
    print(prompt.strip())


if __name__ == "__main__":
    main()
