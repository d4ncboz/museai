Chat title: {TITLE}

Make one finished vertical video for TikTok and YouTube Shorts: a fast {LANGUAGE} vocabulary quiz, about 36 s. Level: {LEVEL}. Topic: {TOPIC}. Do everything in this one request and send me one MP4 file, without background music (music is added later on TikTok). Do not ask me questions; make sensible choices.

WORDS (fixed)
Use exactly these 6 words, in this order. Each line is: English word | {LANGUAGE} answer | pronunciation. Copy every spelling and pronunciation exactly as written; do not replace, reorder or correct any word.
{WORDS}

SCENE CLIPS (6 AI clips, one per word)
Generate 6 AI video clips, vertical 9:16, 1080x1920, about 10 seconds each. Each clip is a beautiful, real-looking scene from {COUNTRY} that shows its word's object clearly and large in the frame (example: {SCENE_EXAMPLE}). Pick the setting that fits the object: outdoors (landscapes, streets, stations, markets) or indoors (homes, kitchens, cafés, shops). Every clip has real motion: something moves in the scene (vehicles, people walking, steam, water, leaves) or the camera makes a slow, gentle push-in. Vary the framing across the 6 clips (close-up, medium, wide), but show small objects (an egg, an apple, a key) only in close-up or medium shots. Give all 6 clips the same warm, natural color grade (same white balance, contrast and saturation), so the video looks like one piece. Natural light. No people talking. NO text, letters, signs with readable words, or subtitles inside the clips; if an object usually carries text (a shop sign, a newspaper), frame it so no text is readable.

BUILD THE FINAL VIDEO WITH FFMPEG (all text added by ffmpeg, never by the AI model)
Output: 1080x1920, 30 fps, H.264 (-pix_fmt yuv420p) + AAC, -movflags +faststart, one MP4. {FONT_RULE}

Text style (sizes for 1080x1920): one compact dark rounded card, about 80 % of the width, about 70 % opacity, 40 px padding, only as tall as its text, centered horizontally, its center at about 40 % of the height, so most of the scene stays visible. English word 80 px bold, {LANGUAGE} answer 84 px bold ({ANSWER_STYLE}), pronunciation line 48 px, small labels 40 px. White text with a dark shadow. If an answer or pronunciation line is too wide for the card, make its font smaller until it fits on one line; never wrap or cut it. {TEXT_LAYOUT} Keep all text away from the top 8 %, the bottom 25 % and the right 12 % (platform buttons).

1. Hook, 1.5 s: clip 1 playing (moving, full color, not darkened). Big text "{LANGUAGE} {LEVEL}: Can you get 6/6?" (84 px bold, on the card) with a small label "{TOPIC}" (40 px) above it. At 0.1 s an English narrator voice (English TTS, --language en; a different voice from the {LANGUAGE} one) says: "Can you get six out of six?"

2. Progress: from the first word to the last, show "1/6" ... "6/6" in the top-left corner (48 px bold, at about 10 % from the top), matching the current word.

3. For each of the 6 words, use its clip trimmed to exactly 5.0 s, playing (the scene keeps moving):
   - 0.0-2.0 s (question): the card shows the English word. A compact countdown directly below the card (not covering it): a white circle outline about 120 px wide that empties as time runs, with a small number inside (52 px bold): 2, then 1, each exactly 1.0 s. Play a short soft clock tick at the start of each number (generate it with ffmpeg if needed).
   - 2.0-2.2 s (reveal): the countdown disappears and the card changes to the {LANGUAGE} answer with a short 200 ms animation (fade in while scaling from 92 % to 100 %). Play one short, soft reveal chime at 2.0 s, the same chime for every word, about 6 dB quieter than the voice. It means "here is the answer", not "you were right".
   - 2.2-5.0 s (answer): the {LANGUAGE} answer on one line, with the pronunciation below it (example: "{ANSWER_EXAMPLE}" with "{PRONUNCIATION_EXAMPLE}" below). The answer stays still and readable while it is spoken.
   - At 2.3 s a {LANGUAGE} voice ({LANGUAGE} TTS, --language {LANG_CODE}) says {VOICE_SAYS} once, clearly and at a natural, slightly slow pace.
   - When the voice ends (about 3.3 s), a small label "Listen & repeat" (40 px) appears under the card, and the audio stays silent until the slot ends, so the viewer can say it back.

4. End, 4.5 s, over clip 1 playing again from its start (so the end leads straight back into the opening when the video loops):
   - 0.0-2.0 s (recap): the card lists all 6 {LANGUAGE} answers in quiz order, one per line, 52 px bold, same article colors as the answers; the whole recap card stays above the bottom 25 %.
   - 2.0-4.5 s (score): big text "What was your score? 0–6" (84 px bold) and below it "Comment below" (48 px), and a small teaser line "Next: {LANGUAGE} {NEXT_LEVEL} {NEXT_TOPIC}" (40 px) under that. At 2.1 s the same English narrator voice says: "What was your score? Comment zero to six!" Do not ask for likes, follows or shares.

5. Audio: no background music. Mute all sound from the AI clips. The only sounds are the countdown ticks, the reveal chime, the {LANGUAGE} voice and the English narrator, all clear; ticks, chime and {LANGUAGE} voice at the same level for every word, narrator at the same loudness as the {LANGUAGE} voice. Normalize the whole audio to about -14 LUFS.

6. Total length about 36 s (1.5 s hook + 6 × 5.0 s + 4.5 s end). Hard cuts between parts, so every word slot stays exactly 5.0 s. If a voice line is longer than its part, speak it a little faster; never cut it and never change the part lengths.

CHECK BEFORE SENDING
- The 6 words, their order, spelling and pronunciation lines are exactly as given in WORDS, and the spoken {LANGUAGE} matches the text.
- The first word appears at 1.5 s.
- Each countdown number shows exactly 1 s; ticks line up with the numbers; the chime plays at every reveal.
- The answer is spoken once, followed by a silent "Listen & repeat" pause.
- The progress number matches the current word.
- The recap shows all 6 answers; the narrator says both lines in full, in English, exactly as written.
- All 6 clips have the same color grade and visible motion.
- The file is 1080x1920 and about 36 s.
- No AI-made text appears anywhere in the clips.

Send the MP4, then list the 6 words as: English - {LANGUAGE} answer - pronunciation.
