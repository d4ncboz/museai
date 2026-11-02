---
language: German
language_upper: GERMAN
lang_code: de
country: Germany
word_list: the official Goethe-Institut word list (Goethe-Zertifikat Wortliste)
answer_form: the German noun with its article (der/die/das)
grammar_check:  and article (der/die/das)
word_notes:  Watch nouns whose meaning changes with the article (der See = lake, die See = sea) and pick the article that matches the scene.
pronunciation: an easy English-style pronunciation spelling (example: BAHN-hohf) and the IPA (example: /ˈbaːnˌhoːf/)
pronunciation_example: BAHN-hohf · /ˈbaːnˌhoːf/
answer_example: der Bahnhof
answer_style: article in light blue, noun in white
voice_says: the article and noun together
scene_example: die Brücke = a bridge clearly in view
font_rule: Use a font that has all IPA symbols and German umlauts (for example DejaVu Sans).
text_layout: Left-to-right text.
---

# German — reference playbook

The tested language. Use this file as the worked example when adding a language.

## Choices and why

| Item | Choice | Why |
|---|---|---|
| Word list | Goethe-Institut Wortliste per level (A1 Start Deutsch 1, A2, B1) | Official list learners study for; the review asked to verify levels against a real source |
| Answer | article + noun, article in light blue | Gender is the hard part of German nouns; the article is written too, so meaning never depends on color alone |
| Pronunciation | easy spelling + IPA | Easy spelling for casual viewers, IPA for serious learners |
| Voice | muse.ai TTS `--language de`, article + noun, said twice | muse warned the voice "may not sound fully native"; v1/v2 speech-to-text heard every word right except one doubtful case |
| Scenery | Germany: castles, half-timbered towns, Alps, lakes, markets, stations | Viewers liked the scenery most (review: "preserve") |

## Test renders (dropped 2026-11-02, not part of the series)

Kept for the lessons below. Real episodes are logged in `log.md`.

| Version | Date | Words | Result |
|---|---|---|---|
| v1 | 2026-11-02 | Bahnhof, Zug, Hotel, Flughafen, Koffer, Stadt | Format OK. English hidden during countdown; Flughafen scene was just sky; STT heard "Bahnhofer" (unconfirmed) |
| v2 | 2026-11-02 | Schloss, Brücke, Berg, See, Markt, Museum | All checks passed. Review 7/10: slow, weak hook, big countdown digits, small pronunciation text |

## Lessons

- muse.ai picked different words each run when it chose them, so the words are now picked by Claude and fixed in the prompt.
- Scenes must show the word's object clearly, or the frame at the answer time can miss it (v2: bridge hard to see).
- `das Schloss` also means "lock"; the castle scene makes it clear. Avoid such words when the scene cannot.
- muse.ai noticed a broken "·" on the intro card by itself and rebuilt; still check frames.

## Check settings

`bash scripts/check_video.sh <file> de`: speech-to-text language `de`. Expect each answer read as "der/die/das + noun".
