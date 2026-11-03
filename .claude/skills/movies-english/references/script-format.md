# Script format (library/batch_NN.json = JSON array of these)

Measured from the user's three reference reels (2026-11-03): 15-30 s, 9:16, 24 fps, 6-12 hard cuts,
1990s rom-com film look, beautiful leads in glamorous everyday places (bakery, ski slope, Christmas
mansion), only 2-5 short spoken lines (2-7 words each), white centred captions, and a punchline or
twist in the last 3 s (she tips him a dollar, she skis into him and he "teaches skiing", she packs a
suitcase over a fart). The comedy is in the picture and the timing, the words are few, so a learner
catches every one. Movies English adds: one key phrase per video, highlighted in the captions, a
Vietnamese line under each English line, and a 2.5 s phrase card at the end.

```json
{
  "id": "ME-0001",
  "title_en": "Rain Check",
  "title_vi": "Hẹn dịp khác nhé",
  "genre": "romcom",
  "level": "B1",
  "cast": ["VIV", "JAMIE"],
  "wardrobe": {"VIV": "coat", "JAMIE": "city"},
  "setting": "Rain-soaked West Village street at dusk, late 1990s, outside a small cafe with a striped awning, yellow cabs, wet cobblestones reflecting warm shop lights",
  "phrase": {
    "en": "take a rain check",
    "vi": "hẹn dịp khác",
    "type": "idiom",
    "explain_vi": "Lịch sự từ chối lời mời bây giờ nhưng ngầm hứa sẽ nhận vào dịp khác.",
    "example_en": "I'm busy tonight. Can I take a rain check?",
    "example_vi": "Tối nay mình bận. Hẹn bạn dịp khác nhé?"
  },
  "hook_vi": "Từ chối crush kiểu sang chảnh 😏",
  "shots": [
    {"id": "S1", "sec": 4, "framing": "wide", "cast": ["VIV", "JAMIE"], "action": "Viv shelters under a narrow cafe awning in pouring rain, arms crossed, no umbrella; Jamie walks up holding a big black umbrella and stops beside her.", "line": null},
    {"id": "S2", "sec": 4, "framing": "close", "cast": ["JAMIE"], "action": "Jamie under his umbrella, rain behind him, looks at her with a lopsided grin.", "line": {"who": "JAMIE", "en": "Need an umbrella?", "vi": "Cần ô không?"}},
    {"id": "S3", "sec": 4, "framing": "close", "cast": ["VIV"], "action": "Viv raises one brow, unimpressed.", "line": {"who": "VIV", "en": "Is that a pickup line?", "vi": "Đang tán tỉnh tôi đấy à?"}},
    {"id": "S4", "sec": 4, "framing": "close", "cast": ["JAMIE"], "action": "Jamie shrugs innocently.", "line": {"who": "JAMIE", "en": "It's an umbrella.", "vi": "Đây là cái ô mà."}},
    {"id": "S5", "sec": 4, "framing": "close", "cast": ["VIV"], "action": "Viv gives a sweet fake smile and turns to leave.", "line": {"who": "VIV", "en": "I'll take a rain check.", "vi": "Để dịp khác nhé."}},
    {"id": "S6", "sec": 4, "framing": "wide", "cast": ["VIV"], "action": "Viv steps proudly off the curb; a yellow cab drives through a puddle and drenches her head to toe; she freezes, mouth open.", "line": null},
    {"id": "S7", "sec": 4, "framing": "two-shot", "cast": ["VIV", "JAMIE"], "action": "Jamie calmly steps in and holds the umbrella over the soaked Viv, grinning.", "line": {"who": "JAMIE", "en": "Rain check's here.", "vi": "Dịp khác tới rồi đây."}},
    {"id": "S8", "sec": 4, "framing": "close", "cast": ["VIV"], "action": "Viv, dripping wet under his umbrella, glares, then a small smile breaks.", "line": {"who": "VIV", "en": "You're buying coffee.", "vi": "Anh mời cà phê đấy."}}
  ],
  "twist": "Her elegant brush-off is undone by a cab splash a second later; the 'rain check' arrives instantly.",
  "cta_vi": "Bạn sẽ nói gì nếu là Viv? Comment bằng tiếng Anh nhé 👇"
}
```

## Rules (check.py enforces the countable ones)
- 4-8 shots, `sec` 3-5 each, 16-32 s total; 2-6 spoken lines, each ≤ 8 words, one line per shot, one speaker per shot.
- The key phrase (`phrase.en`, any inflection) appears in one spoken line, word for word.
- A speaker is never filmed from behind; a line shot is `close`, `medium` or `two-shot` with the speaker's face visible.
- Line 1 within the first 5 s; the hook is a situation, never a greeting or a lesson.
- The last shot is the payoff: a twist, a callback to the phrase, or a romantic beat. No moral, no teacher voice.
- Every shot is one simple filmable action in one place; physical comedy is simple (a splash, a slip, a door, a reveal).
- Cast keys and wardrobe keys come from series/cast.json; extras are described in `action` (a waiter, a cab driver), never named recurring people.
- Natural, idiomatic modern English; no slang that dates fast, nothing crude, no brand names, no real people.
- `vi`: natural spoken Vietnamese with the same tone and humour (anh/em/tôi/cậu chosen by relationship), not word-by-word.
- `hook_vi` ≤ 8 words; `cta_vi` invites a comment in English.
- No two scripts share a key phrase across the whole library.
