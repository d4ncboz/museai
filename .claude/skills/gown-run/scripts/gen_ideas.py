"""Build the gown-run idea bank: 100 ideas = one gown x one real place, each with the 7-shot list of the
reference reel (follow-run, reveal, touch, hair, swirl, wide, hero frame).

  python3 scripts/gen_ideas.py        # writes ../ideas.json and ../ideas.md

Every gown is used 4 times, every place twice, never the same pair twice, and the gown's colour must pop
against the place (POP list of the place: a red cape on green moss, not a green gown on green moss).
To widen the bank add gowns or places at the END of the lists (ids of existing ideas stay stable) and
raise N.
"""
import json
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
N = 100

# (short name, colour family, full description for the prompt, how the fabric moves, hair styling)
GOWNS = [
    ("crimson hooded cape", "red",
     "a floor-length crimson silk-velvet hooded cape worn open over a matching red chiffon gown with a "
     "long ruffled hem", "the cape and skirt billow behind her in huge slow red waves",
     "long copper waves pinned half-up with a thin gold leaf circlet"),
    ("ivory chiffon train gown", "white",
     "an ivory silk-chiffon gown with a fitted bodice, long sheer sleeves and a four-metre chiffon train",
     "the train floats and ripples behind her like smoke", "loose copper waves with tiny white flowers woven in"),
    ("emerald medieval gown", "green",
     "an emerald-green velvet medieval gown with long trailing bell sleeves and a gold-embroidered girdle",
     "the heavy velvet swings and the bell sleeves trail in the air", "a copper crown braid with loose waves below"),
    ("sapphire cape ball gown", "blue",
     "a sapphire-blue satin ball gown with a full skirt and a cathedral-length sheer blue cape from the shoulders",
     "the sheer cape lifts high behind her while the satin skirt sways", "a low copper chignon with loose strands"),
    ("blush tulle princess gown", "pink",
     "a blush-pink layered tulle princess gown with an off-shoulder neckline and a sweeping tiered skirt",
     "dozens of tulle layers bounce and flutter", "soft copper curls with a pearl hair vine"),
    ("gold goddess gown", "gold",
     "a one-shoulder gold Grecian goddess gown of shimmering pleated chiffon with long panels falling from the "
     "shoulder", "the long gold panels stream sideways in the wind and catch the light",
     "a loose copper Grecian braid with a gold leaf band"),
    ("black lace gothic gown", "black",
     "a black lace gothic gown with a high neck, long lace sleeves and a long sheer black chiffon cape",
     "the sheer black cape billows like a dark flag", "long copper waves falling free to the waist"),
    ("lavender fairy dress", "purple",
     "a lavender organza fairy dress with layered petal-shaped skirt panels and a sheer back cape",
     "the petal layers flutter and lift one by one", "copper waves with a delicate silver flower crown"),
    ("burnt-orange silk slip", "orange",
     "a burnt-orange bias-cut silk slip dress with a very long matching silk scarf tied at the neck",
     "the long scarf streams out behind her and the silk ripples", "copper waves tied with a loose silk ribbon"),
    ("silver-grey chiffon gown", "silver",
     "a silver-grey chiffon gown with long flowing angel sleeves open from the shoulder and a long hem",
     "the open sleeves float up like wings", "a sleek low copper ponytail wrapped in a silver cord"),
    ("scarlet ao dai", "red",
     "a scarlet silk Vietnamese ao dai with long front and back panels over flowing white silk trousers",
     "the long silk panels flutter and lift behind her", "long straight copper hair loose down her back"),
    ("white Greek chiton", "white",
     "a white draped linen Greek chiton with a gold rope belt and a long white himation shawl",
     "the shawl and the draped linen ripple in the breeze", "a copper braided crown with a gold band"),
    ("mustard chiffon maxi", "yellow",
     "a mustard-yellow flowing chiffon maxi dress with a deep open back and a full circle skirt",
     "the circle skirt swirls and flares wide", "messy copper waves with a few loose strands"),
    ("wine velvet off-shoulder gown", "red",
     "a deep wine-red velvet off-shoulder gown with a long flowing chiffon overskirt",
     "the chiffon overskirt flies back while the velvet swings heavily", "a low copper bun with face-framing strands"),
    ("royal purple cloak", "purple",
     "a royal-purple velvet hooded cloak lined in silver satin, worn over a silver gown",
     "the cloak opens and billows, flashing its silver lining", "copper waves under the open hood"),
    ("teal silk hanfu", "blue",
     "a teal silk hanfu with very wide sleeves, a layered skirt and long pale ribbons at the waist",
     "the wide sleeves and long ribbons float slowly in the air", "a copper half-up knot with a jade hairpin"),
    ("powder blue regency gown", "blue",
     "a powder-blue empire-waist Regency gown with a very long sheer white shawl over her arms",
     "the sheer shawl floats out behind her in a long arc", "copper curls pinned up in a Regency style"),
    ("fuchsia lehenga", "pink",
     "a fuchsia silk lehenga with gold embroidery and a long sheer gold-edged dupatta trailing from her shoulder",
     "the dupatta streams far behind her and the full skirt sways", "a long copper braid with gold jewellery"),
    ("white embroidered kaftan", "white",
     "a white flowing silk kaftan with gold embroidery at the neck and very wide floor-length sleeves",
     "the whole kaftan billows and the wide sleeves fill with wind", "loose copper waves with a thin gold chain"),
    ("forest elven cloak", "green",
     "a forest-green hooded silk-and-wool elven cloak over a pale sage gown, with a leaf-shaped silver clasp",
     "the cloak sweeps and ripples behind her", "copper waves with tiny braids at the temples"),
    ("coral boho tiered maxi", "orange",
     "a coral-red bohemian tiered maxi dress with flutter sleeves and lace trim",
     "the tiers bounce and flare with every step", "loose beach-wave copper hair with a woven headband"),
    ("midnight star tulle gown", "blue",
     "a midnight-navy tulle gown embroidered with tiny silver stars and a long tulle train",
     "the starry tulle train drifts and sparkles", "copper waves with a few silver star pins"),
    ("champagne satin cape-sleeve gown", "gold",
     "a champagne satin bias-cut gown with long chiffon cape sleeves falling to the ground",
     "the cape sleeves stream behind her in long gold-white ribbons", "a sleek copper twist at the nape"),
    ("rose-red flying train gown", "red",
     "a rose-red chiffon gown with a five-metre flying train",
     "the five-metre train flies up and snakes through the air behind her", "copper waves loose to the waist"),
    ("snow cape and icy gown", "white",
     "an ice-blue satin gown under a snow-white hooded cape trimmed with soft faux fur",
     "the white cape lifts and sweeps over the ground", "copper waves under the fur-trimmed hood"),
]

# (place, ground she runs over, landmark she runs toward, texture she touches, wide shot 2, hero frame,
#  light/season, colours that pop there)
# Exact shape of the landmark, put at the head of every brief: a vague "castle ruin" makes muse draw a
# different castle in every shot (gr-001 v1). Places without an entry get "{place}: {landmark}"; write the
# real shape into the briefs before rendering (SKILL.md step 2) and add it here.
DETAIL = {
    "Ardvreck Castle, Loch Assynt, Scotland":
        "ONE small roofless ruined stone tower house, a tall narrow rectangular keep with a jagged broken top and "
        "one rounded stair-turret corner, standing alone on a low grassy promontory in the loch, the big mountain "
        "Quinag behind across the water. It is the only building: never several towers, never a large castle, "
        "never curtain walls",
    "Cliffs of Moher, Ireland":
        "sheer dark layered sandstone cliffs about 200 m high dropping straight into the deep blue Atlantic, a "
        "long wavy line of headlands stretching away to the south, flat bright green grass on top. O'Brien's "
        "Tower: ONE small round grey stone tower, two storeys, with a flat battlemented top (no roof, no cone, "
        "no spire), standing alone near the cliff edge behind a low wall of upright grey flagstone slabs. It is "
        "the only building: never a castle, never several towers, never houses",
}

PLACES = [
    ("Ardvreck Castle, Loch Assynt, Scotland", "wild green grass and heather", "the roofless stone castle ruin on the loch shore",
     "the rough lichen-covered stone of the castle wall", "fallen castle stones and tall grass by the dark loch",
     "in a broken stone window gap of the ruin wall", "bright fresh day, soft sun breaking through white clouds, blue sky patches, vivid green grass", ["red", "gold", "white", "blue", "yellow"]),
    ("Cliffs of Moher, Ireland", "the green clifftop grass", "O'Brien's Tower on the cliff edge",
     "an old dry-stone wall on the clifftop", "the long line of sheer green cliffs above the Atlantic",
     "at the grassy cliff edge, safely back from the drop, the ocean far below", "soft late-afternoon light through clouds",
     ["red", "white", "gold", "purple", "yellow", "orange"]),
    ("Valensole lavender fields, Provence", "a path between endless lavender rows", "a lone stone farmhouse among the lavender",
     "the warm stone of the farmhouse doorway", "endless purple lavender rows to the horizon",
     "in the middle of a lavender row, a single tree beside her", "golden-hour summer sun", ["white", "gold", "yellow", "red"]),
    ("Erg Chebbi dunes, Merzouga, Morocco", "the soft orange sand ridge of a dune", "the highest dune crest against the sky",
     "the rippled sand of the dune as she kneels and lets it run through her fingers", "endless orange dune ridges, NO trees, NO plants",
     "on top of the dune crest against the sky", "warm low sunset light, long dune shadows", ["blue", "white", "red", "purple", "green", "black", "silver"]),
    ("Oia, Santorini, Greece", "a whitewashed lane of steps", "the blue-domed church above the caldera",
     "a whitewashed wall with bougainvillea", "white houses tumbling down the cliff to the deep blue sea",
     "on a white terrace wall with the caldera and the sea behind her", "warm sunset light", ["red", "gold", "pink", "white"]),
    ("Reynisfjara black sand beach, Iceland", "the wet black volcanic sand", "the tall basalt sea stacks rising from the surf",
     "the hexagonal basalt columns of the cave wall", "black sand, white surf and the basalt sea stacks",
     "at the mouth of the basalt column cave", "bright day, sun breaking through white clouds over a blue sea", ["red", "gold", "white", "orange", "yellow"]),
    ("Val d'Orcia, Tuscany", "a gravel road winding over golden hills", "the cypress-lined farmhouse on the hilltop",
     "the trunk of a tall cypress tree", "rolling golden hills with rows of cypress trees",
     "between two tall cypress trees at the top of the winding road", "golden-hour summer light", ["red", "white", "blue", "black"]),
    ("Hallstatt, Austria", "a lakeside wooden boardwalk", "the white church spire on the lake shore",
     "the weathered wooden railing of the boardwalk", "the village and the mountains reflected in the still lake",
     "at the end of a wooden jetty over the lake", "bright clear morning sun, blue sky", ["red", "gold", "white", "yellow"]),
    ("Göreme, Cappadocia, Turkey", "a dusty ridge path", "the fairy-chimney rock towers with hot-air balloons above",
     "the soft carved tufa rock of a fairy chimney", "fairy chimneys and dozens of hot-air balloons in the sky",
     "on a rooftop terrace with balloons rising behind her", "pink-gold sunrise", ["red", "white", "blue"]),
    ("Geirangerfjord, Norway", "a green mountain meadow", "the deep fjord and the Seven Sisters waterfall",
     "the mossy turf roof of an old farm hut", "the steep green fjord walls and the waterfall",
     "on a flat rock above the fjord", "soft cool summer light", ["red", "gold", "yellow", "white"]),
    ("Old Bagan, Myanmar", "a sandy path through dry grass", "the ancient brick temple stupas",
     "the old red brick of a temple wall", "hundreds of stupas on the green plain with balloons in the morning sky",
     "in an arched temple doorway", "bright clear morning sun, a few balloons in a blue sky", ["white", "blue", "green"]),
    ("Arashiyama bamboo grove, Kyoto", "the stone path through tall bamboo", "the tall green bamboo tunnel",
     "a smooth green bamboo stalk", "towering bamboo stalks swaying overhead",
     "in the middle of the empty bamboo path, light falling through", "soft early morning light", ["red", "white", "pink", "gold", "orange"]),
    ("Ma Pi Leng Pass, Hà Giang, Vietnam", "a grassy ridge above the canyon", "the deep Nho Quế river canyon",
     "an old grey limestone boulder", "layered limestone mountains and the jade river far below",
     "on a rock ledge at the canyon edge, safely back from the drop", "golden late-afternoon light", ["red", "white", "gold", "yellow"]),
    ("Ha Long Bay, Vietnam", "a stone path to a summit viewpoint", "the hundreds of limestone karst islands in the emerald bay",
     "the jagged limestone of the summit rock", "karst islands and small boats on the emerald water",
     "on the summit viewpoint above the bay", "bright warm afternoon sun", ["red", "white", "gold"]),
    ("Hội An Ancient Town, Vietnam", "an old yellow-walled lane", "the Japanese covered bridge",
     "an old yellow plaster wall with bougainvillea", "silk lanterns strung over the river",
     "on the riverbank under a row of glowing lanterns", "bright warm late-afternoon sun", ["white", "blue", "green"]),
    ("Seceda, Dolomites, Italy", "a green alpine meadow", "the jagged Seceda ridge",
     "an old wooden hay barn wall", "rolling green alpine pastures under the sawtooth peaks",
     "at the top of the meadow with the ridge behind her", "clear golden afternoon light", ["red", "white", "gold", "purple"]),
    ("Lake Bled, Slovenia", "a grassy lakeshore path", "the island church in the middle of the lake",
     "the stone wall of the castle terrace", "the castle on its cliff above the turquoise lake",
     "at the end of a wooden pier facing the island", "soft autumn morning light", ["red", "gold", "white"]),
    ("Neuschwanstein Castle, Bavaria", "a sloping alpine meadow", "the white fairytale castle on its rock",
     "the old wooden fence of the meadow", "the castle above autumn forests and blue lakes",
     "on the Marienbrücke bridge with the castle behind her", "golden autumn light", ["red", "blue", "gold", "white"]),
    ("Chefchaouen, Morocco", "blue-washed stairs", "the blue medina alleys climbing the hill",
     "a blue-painted wall with potted plants", "the whole blue town climbing the mountain",
     "in a blue arched doorway", "soft bright morning light", ["orange", "yellow", "red", "white", "gold"]),
    ("Petra, Jordan", "the sandy floor of the Siq canyon", "the rose-red Treasury facade",
     "the rose-red sandstone of the canyon wall", "the narrow Siq walls rising high, NO trees",
     "at the foot of the Treasury steps, small under the facade", "warm light glowing on red rock", ["blue", "white", "green", "black", "silver"]),
    ("Keukenhof tulip fields, Netherlands", "a grass path between tulip stripes", "an old Dutch windmill",
     "the wooden sail frame of the windmill", "striped fields of red, yellow and pink tulips",
     "between two tulip stripes with the windmill behind her", "bright spring light", ["white", "blue", "black"]),
    ("Hirosaki Castle, Japan", "a path under blooming cherry trees", "the white castle keep framed by blossoms",
     "a blossoming cherry branch", "cherry blossoms over the moat, petals on the water",
     "on a red wooden bridge over the moat", "soft spring light, falling petals", ["red", "white", "blue", "black"]),
    ("Tōfuku-ji in autumn, Kyoto", "a stone path through red maples", "the wooden Tsutenkyo bridge in a sea of red leaves",
     "the old wooden temple railing", "a valley of fiery red and orange maples",
     "on the wooden bridge above the maples", "warm autumn light", ["blue", "white", "green", "black", "silver"]),
    ("Luoping rapeseed fields, Yunnan", "a narrow path through yellow flowers", "the green conical karst hills",
     "a rough stone on the field edge", "endless yellow rapeseed around green karst hills",
     "on a small rise in the middle of the yellow fields", "bright spring light", ["blue", "red", "white", "purple", "silver"]),
    ("Torres del Paine, Patagonia", "a golden grass plain", "the three granite towers",
     "a twisted wind-bent lenga tree trunk", "a turquoise lake below the jagged granite massif",
     "on a rock above the turquoise lake", "dramatic clouds, sun breaking through", ["red", "gold", "yellow", "white"]),
    ("Old Man of Storr, Isle of Skye", "a muddy green hill trail", "the tall rock pinnacle on the ridge",
     "the rough basalt rock at the foot of the pinnacle", "green hills and lochs far below the pinnacles, NO trees",
     "on a grassy knoll facing the pinnacle", "bright day, sun breaking through white clouds", ["red", "gold", "white", "yellow"]),
    ("Monument Valley, Utah", "the red dirt track", "the great sandstone buttes",
     "the red sandstone of a boulder", "red buttes on the flat desert plain, NO trees",
     "on a rock ledge looking at the buttes", "warm golden sunset light", ["blue", "white", "green", "black", "silver"]),
    ("Salar de Uyuni, Bolivia", "the shallow water of the salt flat", "the endless mirror of sky and clouds",
     "the white salt crust as she crouches", "a perfect sky reflection with no horizon, NO trees",
     "alone in the middle of the mirror, her reflection below her", "soft pastel sunset", ["red", "gold", "black", "purple"]),
    ("Moraine Lake, Canada", "the rocky lakeshore trail", "the turquoise lake below the ten peaks",
     "a big grey lakeside boulder", "the turquoise lake and the jagged peaks",
     "on the rock pile above the lake", "clear early morning light", ["red", "gold", "yellow", "white", "pink"]),
    ("Amalfi Coast, Italy", "a terraced path between lemon trees", "the pastel village tumbling to the sea",
     "a lemon tree branch heavy with lemons", "the coastline of pastel villages and cliffs",
     "on a stone balcony above the sea", "warm golden afternoon light", ["white", "red", "blue", "black"]),
    ("Tegallalang rice terraces, Bali", "a narrow path along the terrace edge", "the palm-crowned green terraces",
     "a palm tree trunk", "layered green rice terraces and coconut palms",
     "on a terrace edge with the valley below", "bright clear morning sun", ["red", "white", "gold", "pink", "orange"]),
    ("Ta Prohm, Angkor, Cambodia", "a stone causeway", "the temple swallowed by giant tree roots",
     "the giant silk-cotton tree roots over the stones", "carved stone galleries in the jungle",
     "in a carved stone doorway framed by roots", "green-gold jungle light", ["red", "white", "gold", "orange"]),
    ("Lauterbrunnen valley, Switzerland", "a green valley meadow", "the tall Staubbach waterfall falling from the cliff",
     "the wooden wall of an old chalet", "the green valley between sheer cliffs and waterfalls",
     "on the meadow in front of the waterfall", "fresh sunny summer light", ["red", "gold", "white", "purple"]),
    ("Glencoe in heather season, Scotland", "the purple heather moor", "the dark mountain Buachaille Etive Mòr",
     "an old stone by the burn", "purple moorland under the brooding mountains, NO trees",
     "on a rock by the river with the mountain behind her", "bright day, sunlight between white clouds", ["white", "gold", "red", "yellow"]),
    ("Temple of Poseidon, Cape Sounion, Greece", "a dry grassy hilltop", "the white marble temple columns",
     "a marble column", "the temple on the cape above the Aegean",
     "between two marble columns with the sea behind", "golden sunset light", ["red", "gold", "black", "purple"]),
    ("Alhambra gardens, Granada", "a garden path between hedges", "the Moorish palace towers",
     "the carved stucco of an arch", "fountains and long reflecting pools in the gardens",
     "in a carved Moorish archway", "warm late-afternoon light", ["white", "blue", "green", "red"]),
    ("Bluebell woods, Hertfordshire, England", "a path through a carpet of bluebells", "a sunlit beech tree cathedral",
     "the smooth grey bark of a beech", "a forest floor carpeted in bluebells",
     "in a sunbeam among the bluebells", "soft spring morning light through leaves", ["white", "gold", "red", "yellow", "orange"]),
    ("Reine, Lofoten, Norway", "a snowy path by the harbour", "the red fishing cabins below the sharp peaks",
     "the red wooden wall of a fishing cabin", "red cabins on the fjord under snowy peaks",
     "on a snowy rock by the fjord", "pink winter light", ["red", "gold", "black", "purple"]),
    ("Winter birch forest, Lapland, Finland", "deep fresh snow", "a frozen lake beyond the white birches",
     "a white birch trunk dusted with snow", "snow-laden birches and spruces",
     "on the edge of the frozen lake", "soft blue-pink winter light", ["red", "green", "gold", "black", "purple", "pink"]),
    ("Múlafossur, Faroe Islands", "the green clifftop grass", "the waterfall falling into the sea by the village",
     "a turf-roofed stone wall", "the waterfall, the cliffs and the grassy hills, NO trees",
     "on the cliff path above the waterfall", "bright day, sun and drifting white clouds", ["red", "gold", "yellow", "white", "orange"]),
    ("Mont-Saint-Michel, France", "the wet tidal sand", "the abbey on its rock island",
     "the old stone of the ramparts", "the abbey island across the shining tidal flats",
     "on the sand with the abbey far behind her", "soft golden evening light", ["red", "blue", "gold"]),
    ("Château de Chenonceau, France", "the formal garden path", "the château arching over the river",
     "a carved stone balustrade", "the château's arches reflected in the river",
     "on the garden terrace facing the château", "soft morning light", ["red", "blue", "black"]),
    ("Sunflower fields, Tuscany", "a path through tall sunflowers", "a hilltop farmhouse beyond the flowers",
     "a sunflower head", "a sea of sunflowers on the rolling hills",
     "among the sunflowers taller than her waist", "golden summer evening", ["blue", "white", "red", "black"]),
    ("Jökulsárlón glacier lagoon, Iceland", "the black shore", "the blue icebergs floating in the lagoon",
     "a stranded block of clear ice on the shore", "icebergs drifting under the glacier, NO trees",
     "on the black shore among ice blocks", "soft pastel arctic light", ["red", "gold", "black", "yellow", "pink"]),
    ("Sengokuhara pampas grass, Hakone", "a path through tall silver pampas grass", "the golden grass hillside",
     "a plume of pampas grass", "silver-gold pampas grass waving on the hills",
     "on the path at the top of the grass slope", "golden autumn backlight", ["blue", "red", "white", "black", "pink"]),
    ("Kawachi Fuji Garden, Japan", "the path under the wisteria", "the long wisteria tunnel",
     "a hanging wisteria cluster", "endless hanging purple and white wisteria",
     "at the end of the wisteria tunnel", "soft spring light", ["white", "gold", "blue", "red", "pink"]),
    ("Song-Köl lake, Kyrgyzstan", "the high green steppe", "the white yurts by the alpine lake",
     "the felt wall of a yurt", "horses grazing by the lake, NO trees",
     "on the grassy lakeshore", "clear high-altitude light", ["red", "gold", "pink", "white", "silver"]),
    ("Wadi Rum, Jordan", "the red sand valley", "the towering sandstone cliffs",
     "the eroded red sandstone of an arch", "red sand and rock towers, NO trees",
     "on a natural rock bridge", "warm golden afternoon light", ["blue", "white", "green", "black", "silver", "purple"]),
    ("Nine Arches Bridge, Ella, Sri Lanka", "a path through green tea and jungle", "the stone viaduct among jungle",
     "a tea bush", "the stone arches spanning the jungle valley",
     "on the hillside facing the bridge", "bright clear morning sun", ["red", "white", "gold", "orange"]),
    ("Whitby Abbey, England", "the green headland grass", "the Gothic abbey ruin",
     "the weathered stone of a Gothic arch", "the abbey ruin against the sky above the sea",
     "framed in a tall Gothic arch of the ruin", "bright day, soft sun through white clouds", ["red", "white", "gold", "yellow", "silver", "purple"]),
]

# Music styles (name, music.py --style, bpm), rotated over the ideas so neighbouring videos never share a
# sound; ideas.py also skips a style used in the last 3 videos. All catchy with a sung hook from the first
# beat (gr-001 v1: a moody instrumental did not hold viewers). Add new styles at the END.
MUSIC = [
    ("celtic-pop", "uplifting celtic pop anthem, catchy female vocal hook, bright tin whistle melody, fiddle, "
     "acoustic guitar strums, driving stomp-clap drums, energetic, anthemic, radio hit", 100),
    ("folk-stomp", "feel-good indie folk stomp, catchy female vocal hook with group oh-oh chants, banjo, "
     "hand claps, kick-drum stomps, bright and joyful", 104),
    ("dream-pop", "dreamy summer pop, airy female vocal hook, shimmering synths, plucked guitar, "
     "light four-on-the-floor beat, euphoric chorus", 108),
    ("tropical-house", "tropical house pop, catchy female vocal chop hook, marimba plucks, warm bass, "
     "steel drums, sunny and danceable", 110),
    ("cinematic-pop", "epic cinematic pop, powerful female vocal hook, big drums, soaring strings, "
     "piano chords, anthemic lift on the chorus", 96),
    ("acoustic-pop", "upbeat acoustic pop, sweet female vocal hook, ukulele and acoustic guitar, "
     "whistled melody, finger snaps, carefree", 102),
    ("disco-pop", "nu-disco pop, catchy female vocal hook, funky guitar, groovy bass, strings stabs, "
     "four-on-the-floor, glamorous", 116),
    ("world-pop", "world pop anthem, catchy female vocal hook, hand drums, flutes and plucked strings "
     "in the place's own tradition, uplifting", 100),
    ("synthwave", "bright synthwave pop, catchy female vocal hook, retro arpeggios, punchy drums, "
     "big glowing chorus", 112),
    ("orchestral-pop", "joyful orchestral pop, catchy female vocal hook, pizzicato strings, glockenspiel, "
     "marching snare, sweeping brass on the chorus", 104),
]

SHOTS = [  # (seconds in the cut, brief) - the reference reel's 7 beats
    (4.2, "Low tracking shot from directly behind, the camera follows the woman as she runs lightly across "
          "{ground} toward {landmark}. She wears {gown}; {motion}. The landmark stays ahead of her, framed "
          "above her shoulder. {light}."),
    (1.6, "Wide static shot: {landmark} fills most of the frame. The woman, tiny in her {colour} {short}, "
          "walks toward it in the lower part of the frame, seen from behind. {light}."),
    (1.3, "Medium shot from behind and slightly to the side: she reaches up and rests her hand on {texture}, "
          "looking up at it, her face turned away; the {short} falls in deep folds. {light}."),
    (1.3, "Medium shot from directly behind at shoulder height: she walks slowly away, her hair is {hair}, "
          "catching the light; the {short} trails behind her. {light}."),
    (1.6, "From behind and to one side, she half-turns while walking and a gust lifts the {short} into a "
          "sweeping arc of {colour} fabric; {motion}. Her face stays turned away. {light}."),
    (1.1, "Wide shot: the woman, small in the frame in her {colour} {short}, stands among {wide2}, seen from "
          "behind. {light}."),
    (3.9, "Static wide shot, camera perfectly still: she stands {frame}, her back to the camera, gazing at the "
          "view; the wind slowly moves the {short} and her hair. {light}. The final, most beautiful frame."),
]


def build():
    ideas, used_pairs, gown_count = [], set(), [0] * len(GOWNS)
    for k in range(N):
        pi = k % len(PLACES)
        place, ground, landmark, texture, wide2, frame, light, pop = PLACES[pi]
        # walk the gowns from a rotating start so neighbouring ideas get different gowns
        order = [(k * 7 + j) % len(GOWNS) for j in range(len(GOWNS))]
        # least-used gown whose colour pops here; ties go to the rotation order
        free = [g for g in order if (g, pi) not in used_pairs and gown_count[g] < 4]
        gi = min((g for g in free if GOWNS[g][1] in pop), key=lambda g: gown_count[g], default=None)
        if gi is None:  # the last places of the run: a fifth use beats a gown that vanishes into the scenery
            gi = next((g for g in order if GOWNS[g][1] in pop and (g, pi) not in used_pairs), None)
        if gi is None:
            gi = min(free, key=lambda g: gown_count[g])
        used_pairs.add((gi, pi))
        gown_count[gi] += 1
        short, colour, gown, motion, hair = GOWNS[gi]
        f = dict(ground=ground, landmark=landmark, texture=texture, wide2=wide2, frame=frame,
                 gown=gown, motion=motion, hair=hair, short=short, colour=colour,
                 light=light[0].upper() + light[1:])
        ideas.append({
            "id": f"gr-{k + 1:03d}",
            "title": f"{short.capitalize()} at {place}",
            "gown": short, "colour": colour, "place": place,
            "gown_full": gown, "hair": hair, "light": light,
            "music": MUSIC[k % len(MUSIC)][0], "music_style": MUSIC[k % len(MUSIC)][1],
            "bpm": MUSIC[k % len(MUSIC)][2],
            "shots": [f"Place: {place}: {DETAIL.get(place, landmark)}. The same landmark in every shot. " + s.format(**f)
                      for _, s in SHOTS],
            "cuts": [t for t, _ in SHOTS],
        })
    return ideas


def main():
    ideas = build()
    (SKILL / "ideas.json").write_text(json.dumps(ideas, ensure_ascii=False, indent=1) + "\n")
    md = ["# gown-run idea bank", "", f"{len(ideas)} ideas, built by `scripts/gen_ideas.py` (do not edit by hand).", "",
          "| id | gown | colour | place | light | music |", "|---|---|---|---|---|---|"]
    md += [f"| {i['id']} | {i['gown']} | {i['colour']} | {i['place']} | {i['light']} | {i['music']} |" for i in ideas]
    (SKILL / "ideas.md").write_text("\n".join(md) + "\n")
    print(f"{len(ideas)} ideas, {len({i['gown'] for i in ideas})} gowns, {len({i['place'] for i in ideas})} places")


if __name__ == "__main__":
    main()
