Chat title: {TITLE}

Make one finished vertical video for TikTok and YouTube Shorts: a {LANGUAGE} vocabulary quiz. Level: {LEVEL}. Topic: {TOPIC}. Do everything in this one request and send me one MP4 file, without background music (music is added later on TikTok). Do not ask me questions; make sensible choices.

WORDS (fixed)
Use exactly these 6 words, in this order. Each line is: English word | {LANGUAGE} answer | pronunciation. Copy every spelling and pronunciation exactly as written; do not replace, reorder or correct any word.
{WORDS}

SCENE CLIPS (6 AI clips, one per word)
Generate 6 AI video clips, vertical 9:16, 1080x1920, about 10 seconds each. Each clip is a beautiful, real-looking scene from {COUNTRY} that matches its word and shows the word's object clearly (example: {SCENE_EXAMPLE}). Use {COUNTRY}'s landscapes, landmarks, buildings, streets, food. Slow, smooth camera, natural light. No people talking. NO text, letters, signs with readable words, or subtitles inside the clips.

BUILD THE FINAL VIDEO WITH FFMPEG (all text added by ffmpeg, never by the AI model)
Output: 1080x1920, 30 fps, H.264 (-pix_fmt yuv420p) + AAC, -movflags +faststart, one MP4. {FONT_RULE}

Text style (sizes for 1080x1920): one dark rounded card, about 84 % of the width, about 80 % opacity, 48 px padding, centered horizontally, its center at about 40 % of the height. English word 76 px bold, {LANGUAGE} answer 80 px bold ({ANSWER_STYLE}), pronunciation line 36 px, level/topic label 32 px. White text with a dark shadow. If an answer or pronunciation line is too wide for the card, make its font smaller until it fits on one line; never wrap or cut it. {TEXT_LAYOUT} Keep all text away from the top 8 %, the bottom 25 % and the right 12 % (platform buttons).

1. Hook, 3.0 s: the first frame of clip 1, darkened. Small label "{LANGUAGE_UPPER} · {LEVEL} · {TOPIC}" (32 px) above big text "Can you get 6/6 in {LANGUAGE}?" (76 px bold). At 0.3 s an English narrator voice (English TTS, --language en; a different voice from the {LANGUAGE} one) says: "Can you get six out of six in {LANGUAGE}? Let's go!"

2. Progress: from the first word to the last, show "1/6" ... "6/6" in the top-left corner (36 px bold, at about 9 % from the top), matching the current word.

3. For each of the 6 words, use its clip trimmed to exactly 7.0 s:
   - 0.0-3.5 s: the card shows the small label "{LEVEL} · {TOPIC}" and the English word. The card stays on screen the whole time.
   - 0.5-3.5 s: a compact countdown directly below the card (not covering it): a white circle outline about 140 px wide that empties as time runs, with a small number inside (56 px bold): 3, 2, 1, each exactly 1.0 s. Play a short clock tick at the start of each number (generate it with ffmpeg if needed).
   - 3.5-7.0 s: the countdown disappears and the card changes to the {LANGUAGE} answer on one line, with the pronunciation below it (example: "{ANSWER_EXAMPLE}" with "{PRONUNCIATION_EXAMPLE}" below). The answer stays still and readable while it is spoken.
   - At 3.6 s a {LANGUAGE} voice ({LANGUAGE} TTS, --language {LANG_CODE}) says {VOICE_SAYS}, clearly and slowly.
   - At about 5.0 s a small label "Listen & repeat" (32 px) appears under the card, and at 5.3 s the voice says it once more.

4. End card, 5.0 s: "How many did you get right?" big in the center, "Comment your score: 0–6!" below it, and a small teaser line "Next: {LANGUAGE} {NEXT_LEVEL} {NEXT_TOPIC}" (32 px) under that. At 0.3 s the same English narrator voice says: "How many did you get right? Comment your score below! Next time: {LANGUAGE} {NEXT_LEVEL}, {NEXT_TOPIC}."

5. Audio: no background music. Mute all sound from the AI clips. The only sounds are the countdown ticks, the {LANGUAGE} voice and the English narrator, all clear; ticks and {LANGUAGE} voice at the same loudness for every word, narrator at the same loudness as the {LANGUAGE} voice. Normalize the whole audio to about -14 LUFS.

6. Total length about 50 s (3 s hook + 6 × 7 s + 5 s end). Hard cuts between parts, so every word slot stays exactly 7.0 s. If a narrator line is longer than its part, speak it a little faster; never cut it and never change the part lengths.

CHECK BEFORE SENDING
- The 6 words, their order, spelling and pronunciation lines are exactly as given in WORDS, and the spoken {LANGUAGE} matches the text both times.
- Each countdown number shows exactly 1 s; ticks line up with the numbers.
- The progress number matches the current word.
- The narrator says both lines in full, in English, exactly as written.
- The file is 1080x1920 and about 50 s.
- No AI-made text appears anywhere in the clips.

Send the MP4, then list the 6 words as: English - {LANGUAGE} answer - pronunciation.
