---
language:
language_upper:
lang_code:
country:
word_list:
answer_form:
grammar_check:
word_notes:
pronunciation:
pronunciation_example:
answer_example:
answer_style:
voice_says:
scene_example:
font_rule:
text_layout:
---

# <Language> — playbook

Copy this file to `languages/<language>.md` and fill every key above. `languages/german.md` is the worked example.

## How to fill the keys

| Key | Meaning | German value | Other examples |
|---|---|---|---|
| `language` | Name in English | German | Spanish, Japanese |
| `language_upper` | Badge text | GERMAN | SPANISH |
| `lang_code` | TTS and speech-to-text code | de | es, fr, ja, zh |
| `country` | Where the scenery comes from | Germany | Spain, Japan |
| `word_list` | Official list per level | Goethe-Institut Wortliste | Instituto Cervantes Plan Curricular (es), HSK list (zh), JLPT list (ja) |
| `answer_form` | What the answer shows | the German noun with its article (der/die/das) | the Spanish noun with its article (el/la); the Chinese word in simplified characters |
| `grammar_check` | Added to "Double-check every spelling…"; start with a space, or leave empty | ` and article (der/die/das)` | ` and article (el/la)`; empty for Japanese |
| `word_notes` | Language traps; start with a space, or leave empty | der See / die See | Spanish: el agua is feminine |
| `pronunciation` | Pronunciation aid to prepare | broad IPA in slashes | pinyin with tone marks (zh); romaji (ja) |
| `pronunciation_example` | One example line | /ˈbaːnˌhoːf/ | huǒchēzhàn (zh) |
| `answer_example` | One example answer | der Bahnhof | la estación; 火车站 |
| `answer_style` | Colors in the answer | article colored by gender (der blue, die red, das green), noun in white | article in light blue (es); characters in white, pinyin in light blue (zh) |
| `voice_says` | What the voice reads | the article and noun together | the article and noun (es); the word (zh, ja) |
| `scene_example` | One scene example | die Brücke = a bridge clearly in view | la playa = a beach clearly in view |
| `font_rule` | Font that covers the script | DejaVu Sans with IPA | Noto Sans CJK SC (zh), Noto Sans JP (ja), Noto Naskh Arabic (ar) |
| `text_layout` | Direction and line breaks | Left-to-right text. | Right-to-left text, Arabic shaping on (ar); no hyphenation (CJK) |

## Choices and why

## Episodes made

| Version | Date | Words | Result |
|---|---|---|---|

## Lessons

## Check settings

`bash scripts/check_video.sh <file> <lang_code>`
