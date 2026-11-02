#!/usr/bin/env python3
"""Build the muse.ai prompt from prompt-template.md + languages/<lang>.md + episode values + the 6 picked words.

Words file: 6 lines "English | answer | pronunciation", in quiz order; lines starting with # are ignored.
Fails if a word was already used for this language in log.md -> Vocabulary.
"""

import argparse
import datetime
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


def read_words(path: Path) -> list[list[str]]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    words = [[f.strip() for f in line.split("|")] for line in lines]
    if len(words) != 6 or any(len(w) != 3 or not all(w) for w in words):
        sys.exit(f"{path}: need exactly 6 lines of 'English | answer | pronunciation'")
    return words


def used_answers(language: str) -> set[str]:
    """Answers already logged for this language in log.md -> Vocabulary."""
    log = SKILL / "log.md"
    if not log.exists():
        return set()
    text = log.read_text(encoding="utf-8")
    table = text.split("## Vocabulary", 1)[-1]
    used = set()
    for line in table.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # Columns: Episode # | Language | Level | Topic | English | Answer | Pronunciation
        if len(cells) == 7 and cells[1].lower() == language.lower():
            used.add(cells[5].lower())
    return used


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lang", required=True, help="file name in languages/, e.g. german")
    ap.add_argument("--level", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--next-level", required=True)
    ap.add_argument("--next-topic", required=True)
    ap.add_argument("--words", required=True, type=Path, help="file with the 6 picked words")
    ap.add_argument("--episode", required=True, type=int, help="episode number from series.md")
    a = ap.parse_args()

    lang_file = SKILL / "languages" / f"{a.lang}.md"
    if not lang_file.exists():
        sys.exit(f"No playbook {lang_file}. Copy languages/_new-language.md first.")
    values = front_matter(lang_file)
    values.update(LEVEL=a.level, TOPIC=a.topic, NEXT_LEVEL=a.next_level, NEXT_TOPIC=a.next_topic)
    values["TITLE"] = f"Vocab Quiz #{a.episode} · {datetime.date.today()} · {values['LANGUAGE']} {a.level} {a.topic}"

    words = read_words(a.words)
    repeated = [w[1] for w in words if w[1].lower() in used_answers(values["LANGUAGE"])]
    if repeated:
        sys.exit(f"Already used in log.md: {', '.join(repeated)}")
    values["WORDS"] = "\n".join(f"{i}. {' | '.join(w)}" for i, w in enumerate(words, 1))

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
