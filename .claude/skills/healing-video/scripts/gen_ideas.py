"""Build the idea bank: ideas.json (machine) + ideas.md (one line per idea) in the skill folder.

Usage: python3 scripts/gen_ideas.py [--count 1000] [--seed 17]

Every idea is one home (a real region and its house, views, garden, local food) in one season and
weather, with one kitchen task for the girl, one animal (or none), one sound bed and a caption line,
expanded into an 8-shot list like the reference reel. Deterministic: the same seed rebuilds the same
bank, so ids stay stable. Uniqueness: no two ideas share home + season + task, each home gets an
even share, and tasks, animals and captions rotate so neighbours in the bank differ.
Add homes, tasks, animals or captions here and rebuild; ids of existing ideas change only if the
pools above them change, so append new entries at the END of each list.
"""
import argparse
import itertools
import json
import random
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SEASONS = ["spring", "summer", "autumn", "winter"]
TROPICS = ["rainy season", "dry season"]

# name, house, views (window/doorway looks out on), garden corners, local food tasks,
# animals that live there, real sounds, seasons that look right, treeless
HOMES = [
    ("Welsh hill farmhouse", "a whitewashed stone farmhouse with deep window sills and old casement windows",
     ["rolling green Welsh hills with hedgerows and grazing sheep under soft grey clouds", "a misty wooded valley beyond a dry-stone wall"],
     ["a weathered oak table on the lawn with potted geraniums", "terracotta pots of pink petunias by the stone doorstep"],
     ["baking Welsh cakes on a griddle", "pouring tea from a white teapot", "slicing fresh sourdough on a board"],
     ["sheepdog", "black cat", "robin"], ["rain", "birds", "wind"], SEASONS, False),
    ("Cotswolds stone cottage", "a honey-coloured Cotswold stone cottage with climbing roses and mullioned windows",
     ["a quiet lane of honey-stone cottages and a meadow beyond", "a wildflower meadow sloping to a willow-lined brook"],
     ["a rose arch over a gravel path", "a cottage border of foxgloves, delphiniums and lupins"],
     ["making scones with clotted cream", "arranging garden roses in a jug", "rolling out pastry for a fruit pie"],
     ["ginger cat", "spaniel", "blackbird"], ["birds", "rain", "brook"], SEASONS, False),
    ("Lake District slate cottage", "a grey slate cottage with a green door and a wood-burning stove",
     ["a still lake reflecting fells and drifting low cloud", "bracken-covered fells with a stone footpath"],
     ["a slate-walled garden with ferns and moss", "a bench by a wooden gate draped with ivy"],
     ["stirring a pot of soup on the stove", "making gingerbread", "brewing a pot of tea"],
     ["border collie", "tabby cat", "wren"], ["rain", "lake", "fire"], SEASONS, False),
    ("Scottish Highland croft", "a white croft house with a tin roof and a peat fire",
     ["heather moorland rolling to a misty loch", "a glen with a winding burn and distant hills"],
     ["a stone wall garden with rhubarb and kale", "a wooden bench beside a rowan tree"],
     ["stirring porridge in a pan", "baking oatcakes", "making shortbread"],
     ["Highland cow by the fence", "collie", "grey cat"], ["rain", "burn", "wind"], SEASONS, False),
    ("Irish thatched cottage", "a whitewashed thatched cottage with a red half-door",
     ["green fields stitched with stone walls down to the sea", "a soft green hillside under passing rain"],
     ["fuchsia hedges along a garden path", "a cottage garden of hollyhocks and nasturtiums"],
     ["baking soda bread", "churning butter in a crock", "making a pot of stew"],
     ["donkey by the wall", "black-and-white cat", "terrier"], ["rain", "birds", "sea"], SEASONS, False),
    ("Provence stone mas", "a pale stone Provençal farmhouse with blue shutters",
     ["lavender rows stretching to a hill village", "olive groves and cypress on a sunlit slope"],
     ["a shaded terrace under a plane tree", "pots of rosemary and geraniums by blue shutters"],
     ["making ratatouille", "baking a lavender honey cake", "pitting apricots for jam"],
     ["cream cat", "small terrier", "swallows"], ["cicadas", "birds", "fountain"], ["spring", "summer", "autumn"], False),
    ("Normandy half-timbered house", "a half-timbered Normandy cottage with a moss-covered roof",
     ["an apple orchard with cows grazing in long grass", "a green valley with hedgerows under soft cloud"],
     ["hydrangeas along a timber wall", "a wooden bench under apple trees"],
     ["making an apple tart", "pressing apples for cider", "whisking crêpe batter"],
     ["tabby cat", "Normandy cow", "hens"], ["rain", "birds", "orchard breeze"], SEASONS, False),
    ("Tuscan stone farmhouse", "a rustic Tuscan stone farmhouse with terracotta floors",
     ["cypress-lined road winding over golden hills", "vineyards rolling to a hilltop village"],
     ["a pergola heavy with wisteria", "lemon trees in terracotta pots on a terrace"],
     ["making fresh pasta by hand", "slicing tomatoes for bruschetta", "baking a focaccia with rosemary"],
     ["grey cat", "Lagotto dog", "swallows"], ["cicadas", "birds", "wind"], SEASONS, False),
    ("Lake Como garden villa", "an old ochre villa with green shutters on the lake shore",
     ["the calm lake with mountains and a small ferry far off", "a lakeside path under camellias"],
     ["a stone balustrade with pots of red geraniums", "a garden of camellias and azaleas"],
     ["making risotto", "arranging figs and cheese on a board", "brewing espresso in a moka pot"],
     ["white cat", "small dog", "ducks on the lake"], ["lake", "birds", "rain"], ["spring", "summer", "autumn"], False),
    ("Amalfi lemon terrace house", "a white house with a tiled terrace on terraced lemon groves",
     ["the turquoise sea far below terraced cliffs", "lemon terraces stepping down to the sea"],
     ["a pergola of lemons with a tiled table", "bougainvillea spilling over a white wall"],
     ["squeezing lemons for lemonade", "making a lemon ricotta cake", "slicing peaches into a bowl"],
     ["tortoiseshell cat", "terrier", "swifts"], ["sea", "birds", "cicadas"], ["spring", "summer", "autumn"], False),
    ("Swiss alpine chalet", "a wooden alpine chalet with carved balconies and red geraniums",
     ["green alpine meadows below snowy peaks", "a pine forest valley with a waterfall"],
     ["window boxes of red geraniums on a wooden balcony", "a meadow garden with a wooden fence and cowbells"],
     ["making cheese fondue", "baking a plum tart", "pouring warm milk into mugs"],
     ["Bernese mountain dog", "cat on a balcony", "cows with bells"], ["cowbells", "stream", "birds"], SEASONS, False),
    ("Austrian mountain farmhouse", "a wooden Tyrolean farmhouse with flower-filled balconies",
     ["a valley of meadows and a white church under mountains", "a quiet alpine lake under pine slopes"],
     ["a herb garden by a wooden fence", "a bench under a pear tree"],
     ["rolling apple strudel dough", "making dumplings", "baking braided bread"],
     ["dachshund", "tabby cat", "goats"], ["stream", "birds", "rain"], SEASONS, False),
    ("Black Forest farmhouse", "a large Black Forest farmhouse with a deep sloping roof",
     ["dark fir forests over a green valley", "a meadow with a small wooden mill and stream"],
     ["a vegetable garden by a fir hedge", "a woodpile and a bench by the barn"],
     ["baking a cherry cake", "slicing dark rye bread", "stirring mulled apple juice"],
     ["German shepherd", "black cat", "hens"], ["stream", "rain", "birds"], SEASONS, False),
    ("Norwegian fjord red cabin", "a red wooden cabin with white window frames and a grass roof",
     ["a deep fjord between steep green mountains", "a still fjord with a small wooden boat"],
     ["a grass-roof shed with wildflowers", "a wooden deck with sheepskins on chairs"],
     ["baking cinnamon buns", "making waffles", "brewing coffee in a kettle"],
     ["Norwegian forest cat", "elkhound", "seagulls"], ["fjord water", "rain", "wind"], SEASONS, False),
    ("Swedish lakeside red cottage", "a Falu-red cottage with white trim by a lake",
     ["a mirror-still lake fringed with birch trees", "a meadow of wildflowers to the lake shore"],
     ["a wooden jetty with a rowing boat", "a birch tree with a swing"],
     ["baking cardamom buns", "making lingonberry jam", "setting out fika on a tray"],
     ["grey cat", "spaniel", "ducks"], ["lake", "birds", "rain"], SEASONS, False),
    ("Finnish lakeside cabin", "a log cabin with a small sauna by a forest lake",
     ["a misty lake among pine forest at dawn", "pine and birch forest on a quiet shore"],
     ["a wooden sauna hut on the shore", "a moss path through blueberry bushes"],
     ["baking blueberry pie", "making rye bread", "brewing coffee on a stove"],
     ["Lapphund", "cat", "loon on the lake"], ["lake", "fire", "birds"], SEASONS, False),
    ("Danish thatched house", "a thatched yellow house near grassy dunes",
     ["grassy dunes rolling to a pale sea", "a field of barley under a wide sky"],
     ["a garden of roses against a yellow wall", "a white bench by a hedge"],
     ["making open rye sandwiches", "baking a butter cake", "brewing tea"],
     ["white cat", "terrier", "swallows"], ["sea", "wind", "birds"], SEASONS, False),
    ("Dutch polder farmhouse", "a brick farmhouse with green shutters by a canal",
     ["flat green polders with a windmill and grazing cows", "a canal lined with willows"],
     ["tulip beds along a brick path", "a bench by the canal under a willow"],
     ["making poffertjes", "slicing cheese on a board", "baking an apple cake"],
     ["tabby cat", "ducks on the canal", "hens"], ["canal water", "birds", "rain"], SEASONS, False),
    ("Czech Bohemian cottage", "a whitewashed cottage with a wooden porch in a Bohemian village",
     ["rolling fields and a forest edge under summer clouds", "a village pond with willows"],
     ["a garden of sunflowers and beans", "an orchard with a wooden ladder"],
     ["baking kolache", "making plum dumplings", "pickling cucumbers"],
     ["tabby cat", "dachshund", "geese"], ["birds", "rain", "pond"], SEASONS, False),
    ("Polish wooden cottage", "a painted wooden cottage with carved window frames",
     ["birch woods and a golden field", "a river bend with storks nesting"],
     ["a garden of dahlias and marigolds", "a wooden well with a bench"],
     ["making pierogi", "baking a poppy-seed roll", "picking mushrooms into a basket"],
     ["grey cat", "farm dog", "storks"], ["river", "birds", "rain"], SEASONS, False),
    ("Transylvanian village house", "a painted village house with a wooden gate",
     ["hay meadows below wooded hills", "a valley with haystacks and a fortified church"],
     ["a vegetable garden with beans on poles", "a porch with strings of drying peppers"],
     ["baking chimney cake", "stirring plum jam", "kneading bread dough"],
     ["sheepdog", "black cat", "hens"], ["birds", "rain", "stream"], SEASONS, False),
    ("Croatian olive grove stone house", "a stone house with green shutters in an olive grove",
     ["the blue Adriatic beyond silver olive trees", "an island bay with a small stone harbour"],
     ["a stone terrace with lavender", "a grape vine pergola"],
     ["pouring olive oil over bread", "making fig jam", "grilling sardines"],
     ["tabby cat", "small dog", "swallows"], ["sea", "cicadas", "birds"], ["spring", "summer", "autumn"], False),
    ("Greek island white house", "a whitewashed house with a blue door on a hillside",
     ["the deep blue Aegean below white houses", "terraced hills with olive trees to the sea"],
     ["bougainvillea over a blue door", "pots of basil on white steps"],
     ["making a Greek salad", "baking spanakopita", "brewing Greek coffee"],
     ["island cat", "donkey", "swallows"], ["sea", "wind", "cicadas"], ["spring", "summer", "autumn"], False),
    ("Sintra garden quinta", "a pastel quinta with azulejo tiles in a forest garden",
     ["misty green hills with a palace far off", "the Atlantic beyond pine forest"],
     ["a tiled bench under camellias", "a fern-lined garden fountain"],
     ["baking custard tarts", "making orange marmalade", "brewing tea"],
     ["grey cat", "Portuguese water dog", "pigeons"], ["fountain", "birds", "rain"], SEASONS, False),
    ("Andalusian white cortijo", "a white cortijo with a courtyard and blue pots",
     ["olive hills rolling to a white village", "a sunflower field under a hazy sky"],
     ["a courtyard of blue pots with geraniums", "an orange tree over a tiled fountain"],
     ["making gazpacho", "slicing oranges", "frying churros"],
     ["Spanish cat", "galgo dog", "swallows"], ["fountain", "birds", "cicadas"], ["spring", "summer", "autumn"], False),
    ("Iceland turf house", "a traditional turf-roofed house with a small wooden door",
     ["bare green lava fields to a black-sand shore, NO trees", "a waterfall over bare basalt cliffs, NO trees"],
     ["a turf wall with small wildflowers", "a wooden bench facing the treeless hills"],
     ["baking rye bread", "making skyr with berries", "brewing coffee"],
     ["Icelandic horse", "Icelandic sheepdog", "cat"], ["wind", "waterfall", "rain"], SEASONS, True),
    ("Faroe grass-roof house", "a black wooden house with a grass roof on a cliff",
     ["steep treeless green cliffs dropping to the sea, NO trees", "a fjord village under low cloud, NO trees"],
     ["a grass roof with daisies", "a stone wall with sheep beyond"],
     ["baking bread", "making fish soup", "knitting with tea"],
     ["Faroese sheep", "cat", "puffins far off"], ["wind", "sea", "rain"], SEASONS, True),
    ("Japanese countryside minka", "a thatched minka farmhouse with an engawa veranda",
     ["terraced rice fields under forested mountains", "a misty cedar forest with a small shrine path"],
     ["a moss garden with a stone lantern", "an engawa with sliding paper doors open"],
     ["making onigiri", "brewing matcha", "simmering miso soup"],
     ["shiba inu", "calico cat", "sparrows"], ["rain", "stream", "birds"], SEASONS, False),
    ("Kyoto machiya garden house", "a wooden machiya townhouse with a small inner garden",
     ["a tiny courtyard garden with maple and moss", "a quiet stone lane in old Kyoto"],
     ["a tsukubai water basin with bamboo spout", "a maple tree over moss and stepping stones"],
     ["making wagashi sweets", "brewing green tea", "arranging ikebana"],
     ["calico cat", "sparrows", "koi in a pond"], ["rain", "water basin", "birds"], SEASONS, False),
    ("Hokkaido farmhouse", "a wooden farmhouse with a red roof on open farmland",
     ["rolling fields of lavender and wheat", "a lone tree on gentle hills under wide sky"],
     ["a flower bed of cosmos", "a porch with a bench and boots"],
     ["making milk pudding", "baking melon bread", "simmering corn soup"],
     ["shiba inu", "cat", "fox far in a field"], ["wind", "birds", "rain"], SEASONS, False),
    ("Korean hanok courtyard", "a hanok house with curved tile roofs and wooden floors",
     ["a pine-covered mountain behind tiled roofs", "a stream valley with persimmon trees"],
     ["a courtyard with onggi jars", "a persimmon tree over a stone wall"],
     ["making kimchi", "steaming rice cakes", "brewing barley tea"],
     ["jindo dog", "cat", "magpies"], ["rain", "stream", "birds"], SEASONS, False),
    ("Yunnan tea-hill courtyard", "a wooden courtyard house among tea terraces",
     ["green tea terraces over misty hills", "a valley of terraced fields and clouds"],
     ["a courtyard with tea drying on bamboo trays", "a stone path with potted orchids"],
     ["brewing pu-erh tea", "making rice noodles", "steaming buns"],
     ["cat", "village dog", "chickens"], ["rain", "birds", "stream"], SEASONS, False),
    ("Sa Pa wooden house", "a wooden stilt house above rice terraces",
     ["rice terraces stepping down a misty valley", "mountains with low cloud over the valley"],
     ["a bamboo fence with marigolds", "a wooden porch with woven baskets"],
     ["steaming sticky rice", "brewing herbal tea", "making corn cakes"],
     ["water buffalo", "village dog", "cat"], ["rain", "stream", "birds"], SEASONS, False),
    ("Hoi An yellow house", "a yellow old-town house with wooden shutters and lanterns",
     ["a calm river with wooden boats", "rice fields with palms beyond the town"],
     ["bougainvillea over a yellow wall", "a courtyard with potted bonsai"],
     ["making white rose dumplings", "brewing Vietnamese drip coffee", "rolling fresh spring rolls"],
     ["cat", "small dog", "sparrows"], ["river", "rain", "birds"], TROPICS, False),
    ("Mekong delta garden house", "a wooden house among fruit orchards on a canal",
     ["a quiet canal under coconut palms", "fruit orchards with small wooden bridges"],
     ["a garden of hibiscus and banana plants", "a hammock under mango trees"],
     ["slicing mangoes", "making banana cakes", "cooking coconut sticky rice"],
     ["cat", "ducks", "village dog"], ["canal water", "rain", "birds"], TROPICS, False),
    ("Bali rice-paddy house", "an open wooden house with an alang-alang roof by rice paddies",
     ["green rice paddies with palm trees and a volcano far off", "a jungle river valley"],
     ["a frangipani tree over a stone path", "a lotus pond with a stone statue"],
     ["making fresh coconut drink", "cooking nasi goreng", "arranging frangipani offerings"],
     ["cat", "ducks in the paddy", "gecko on the wall"], ["rain", "stream", "birds"], TROPICS, False),
    ("Thai teak riverside house", "a teak house on stilts by a slow river",
     ["a slow green river with long-tail boats", "rice fields and palms under monsoon clouds"],
     ["orchids hanging from a teak beam", "a garden of banana and lemongrass"],
     ["pounding green papaya salad", "making mango sticky rice", "brewing lemongrass tea"],
     ["Thai cat", "village dog", "egrets"], ["river", "rain", "birds"], TROPICS, False),
    ("New Zealand sheep farmhouse", "a white weatherboard farmhouse with a red roof",
     ["green hills with sheep rolling to far mountains", "a lake under snowy peaks"],
     ["a garden of agapanthus and roses", "a veranda with a wooden swing seat"],
     ["baking pavlova", "making lamingtons", "brewing tea in a pot"],
     ["sheepdog", "ginger cat", "fantail bird"], ["wind", "birds", "rain"], SEASONS, False),
    ("Tasmanian cottage", "a sandstone cottage with a tin roof",
     ["lavender fields to forest hills", "a misty river valley with tall gum trees"],
     ["a garden of roses and apple trees", "a veranda with a cane chair"],
     ["baking apple crumble", "making jam drops", "brewing tea"],
     ["kelpie dog", "cat", "wren"], ["rain", "birds", "river"], SEASONS, False),
    ("Canadian lakeside log cabin", "a log cabin with a stone chimney on a lake",
     ["a clear lake under pine forest and mountains", "maple forest in colour by the shore"],
     ["a wooden dock with a canoe", "a woodpile beside a porch"],
     ["making maple pancakes", "baking butter tarts", "brewing coffee on a woodstove"],
     ["golden retriever", "cat", "loons"], ["lake", "fire", "birds"], SEASONS, False),
    ("Vermont farmhouse", "a white clapboard farmhouse with a red barn",
     ["rolling hills of maple trees", "a covered bridge over a stream"],
     ["a porch with pumpkins and rocking chairs", "a vegetable garden with a picket fence"],
     ["baking apple cider donuts", "making pumpkin pie", "pouring maple syrup"],
     ["golden retriever", "barn cat", "chickadees"], ["stream", "birds", "rain"], SEASONS, False),
    ("Pacific Northwest forest cabin", "a cedar cabin among moss-covered trees",
     ["a misty evergreen forest with ferns", "a rocky river through tall firs"],
     ["a moss-covered path with ferns", "a covered porch with blankets"],
     ["baking blackberry cobbler", "brewing pour-over coffee", "making salmon chowder"],
     ["husky", "cat", "deer at the forest edge"], ["rain", "river", "birds"], SEASONS, False),
    ("Patagonia lake cabin", "a wooden cabin by a turquoise glacier lake",
     ["a turquoise lake under jagged peaks", "a beech forest valley with a river"],
     ["a wooden fence with lupins", "a porch with wool blankets"],
     ["making empanadas", "brewing mate", "baking bread in a wood oven"],
     ["sheepdog", "cat", "horses"], ["wind", "lake", "fire"], SEASONS, False),
    ("Mexican hacienda courtyard", "a terracotta hacienda with a tiled courtyard",
     ["agave fields to blue mountains", "a valley with jacaranda trees"],
     ["a courtyard fountain with pots of bougainvillea", "a cactus garden by an adobe wall"],
     ["making fresh tortillas", "brewing hot chocolate", "slicing mangoes with lime"],
     ["xoloitzcuintli dog", "cat", "hummingbird"], ["fountain", "birds", "rain"], ["spring", "summer", "autumn"], False),
    ("Moroccan riad garden", "a riad with zellige tiles around a garden courtyard",
     ["the Atlas mountains beyond a palm grove", "a garden courtyard under a blue sky"],
     ["orange trees around a tiled fountain", "a rooftop terrace with rugs and lanterns"],
     ["pouring mint tea from a height", "making a tagine", "baking msemen"],
     ["cat", "turtle doves", "sparrows"], ["fountain", "birds", "wind"], ["spring", "summer", "autumn"], False),
    ("Slovenian alpine farmhouse", "a white farmhouse with a wooden hayrack",
     ["a green valley under the Julian Alps", "an emerald river through a gorge"],
     ["a beehive house painted in colours", "a meadow garden with a bench"],
     ["drizzling honey over bread", "making potica cake", "brewing herbal tea"],
     ["dog", "cat", "bees at the hive"], ["river", "birds", "rain"], SEASONS, False),
    ("Georgian Caucasus village house", "a stone house with a wooden balcony in a mountain village",
     ["high green valleys under snowy Caucasus peaks", "a village of stone towers in the mountains"],
     ["a grape vine over a wooden balcony", "a garden of walnut trees"],
     ["making khachapuri", "stirring churchkhela", "pouring tea from a samovar"],
     ["Caucasian shepherd dog", "cat", "cows"], ["stream", "wind", "birds"], SEASONS, False),
    ("Cornish seaside cottage", "a white fisherman's cottage with blue window frames",
     ["a small harbour with fishing boats", "cliffs above a sandy cove"],
     ["a garden wall with sea pinks", "a bench with a view over the harbour"],
     ["making Cornish pasties", "baking saffron buns", "brewing tea"],
     ["Jack Russell", "cat on a wall", "seagulls"], ["sea", "wind", "rain"], SEASONS, False),
    ("Bavarian lake house", "a wooden house with painted shutters by an alpine lake",
     ["a turquoise lake below mountains", "meadows with a chapel and peaks"],
     ["window boxes with geraniums", "a garden of apple trees and a bench"],
     ["baking pretzels", "making apple pancakes", "pouring tea"],
     ["dachshund", "tabby cat", "swans on the lake"], ["lake", "birds", "rain"], SEASONS, False),
    ("Kerala backwater house", "a tiled-roof house by palm-lined backwaters",
     ["calm backwaters with a houseboat", "paddy fields under coconut palms"],
     ["a garden of hibiscus and jasmine", "a veranda with a wooden swing"],
     ["making appam", "brewing masala chai", "grating coconut"],
     ["cat", "ducks", "kingfisher"], ["rain", "backwater", "birds"], TROPICS, False),
    ("Taiwan mountain tea house", "a wooden tea house in Alishan's tea gardens",
     ["tea plantations over a sea of clouds", "cedar forest in mist"],
     ["a terrace with tea cups on a wooden table", "a bamboo garden path"],
     ["brewing oolong tea", "making pineapple cakes", "steaming dumplings"],
     ["cat", "dog", "white egret"], ["rain", "birds", "stream"], SEASONS, False),
]

SEASON_DETAIL = {
    "spring": {"weather": ["soft spring rain", "fresh morning after rain", "bright breezy morning", "light drizzle and mist"],
               "flowers": ["tulips", "daffodils", "cherry blossom", "apple blossom", "bluebells", "lilacs", "peonies"],
               "tasks": ["planting seedlings in pots", "making elderflower cordial", "baking a lemon drizzle cake",
                         "washing fresh strawberries", "picking herbs into a basket", "making rhubarb compote"]},
    "summer": {"weather": ["warm summer rain shower", "golden late afternoon", "soft overcast summer day", "gentle summer breeze"],
               "flowers": ["roses", "geraniums", "hydrangeas", "sunflowers", "lavender", "sweet peas", "cosmos"],
               "tasks": ["making berry jam", "slicing a watermelon", "baking a cherry clafoutis", "making iced herbal tea",
                         "arranging wildflowers in a vase", "rinsing tomatoes from the garden"]},
    "autumn": {"weather": ["misty autumn morning", "steady autumn rain", "soft golden autumn light", "windy afternoon with falling leaves"],
               "flowers": ["dahlias", "chrysanthemums", "asters", "late roses", "heather", "rosehips"],
               "tasks": ["baking an apple pie", "roasting pumpkins", "making pear compote", "stirring a pot of soup",
                         "baking cinnamon cookies", "drying herbs on a string"]},
    "winter": {"weather": ["light snowfall", "frosty clear morning", "cold rain on the windows", "grey winter afternoon by the fire"],
               "flowers": ["hellebores", "winter jasmine", "snowdrops", "camellias", "holly berries", "dried flower bunches"],
               "tasks": ["making hot cocoa", "baking gingerbread cookies", "simmering spiced cider", "kneading bread by the stove",
                         "making orange and clove decorations", "baking a fruit loaf"]},
    "rainy season": {"weather": ["warm monsoon rain", "heavy tropical rain on leaves", "steamy morning after rain", "soft drizzle over the fields"],
                     "flowers": ["lotus", "frangipani", "orchids", "hibiscus", "jasmine", "ginger flowers"],
                     "tasks": ["brewing ginger tea", "steaming banana-leaf parcels", "slicing papaya", "making coconut pudding",
                               "washing herbs from the garden", "folding dumplings by the window"]},
    "dry season": {"weather": ["clear golden morning", "soft hazy afternoon", "warm breeze at sunset", "cool bright dawn"],
                   "flowers": ["bougainvillea", "frangipani", "marigolds", "lotus", "hibiscus", "orchids"],
                   "tasks": ["making fresh fruit juice", "grilling corn", "arranging flowers on a tray", "slicing pineapple",
                             "making iced coffee", "drying chillies on a tray"]},
}

CORNERS = [
    "a wooden chair with a knitted blanket by the window", "a reading nook with an open book and a cup of tea",
    "a dresser with old plates and a jug of flowers", "a sunlit windowsill with potted herbs",
    "a staircase with a basket of linen", "a pantry shelf of jam jars and dried herbs",
    "a bed with white linen and a sunlit window", "an old armchair beside a lit fireplace",
    "a writing desk with letters and a pencil", "a doorway with boots and a straw hat",
    "a kitchen shelf of copper pans and ceramic bowls", "a windowseat with cushions and the rain outside",
    "a hallway with a bench and a vase of branches", "a bathroom with a clawfoot tub and a plant",
]

SOUND_TEXT = {
    "rain": "soft rain on glass and leaves", "birds": "morning birdsong", "wind": "gentle wind in the grass",
    "brook": "a babbling brook", "burn": "a babbling Highland burn", "stream": "a clear stream over stones",
    "river": "a slow river flowing", "lake": "small waves lapping the lake shore", "sea": "distant sea waves",
    "fire": "a crackling wood fire", "cicadas": "cicadas in the warm air", "fountain": "a trickling courtyard fountain",
    "cowbells": "distant cowbells", "fjord water": "water lapping in the fjord", "canal water": "water lapping the canal",
    "pond": "frogs and a quiet pond", "orchard breeze": "a breeze through apple leaves", "waterfall": "a distant waterfall",
    "water basin": "water dripping into a stone basin", "backwater": "water lapping on the backwater",
}

CAPTIONS = [
    "the way I want to live:", "slow mornings like this", "a soft place to rest", "this is my kind of quiet",
    "nowhere else I'd rather be", "little things, every day", "breathe in, slow down", "home is a feeling",
    "rainy days are for tea", "life, but softer", "the gentle life", "let the day go slowly",
    "a quiet corner of the world", "peace looks like this", "small joys, slow days", "today, nothing to rush",
    "the sound of calm", "my happy place", "gentle days only", "to live simply",
    "a slower kind of life", "where my heart rests", "softly, softly", "this is enough",
    "days like honey", "the beauty of ordinary days", "a cup of tea and the rain", "close your eyes and listen",
    "everything is quiet here", "calm is a place", "a little cottage dream", "simple, slow, kind",
    "the world can wait", "living gently", "where time slows down", "the cosy life",
    "my dream morning", "just the birds and me", "no hurry here", "soft life in the countryside",
]

# "ode" concept (reference 2, "a love letter to the wind"): one sentence split over 6 shots, one phrase per
# shot, every shot shows the subject DOING that phrase in the home. (phrase, what the shot shows)
ODES = {
    "the wind": (["spring", "summer", "autumn", "dry season"], [
        ("a love letter to the wind that", "a sheer white curtain billowing slowly into a sunlit bedroom of {house}, {flower} on the sill"),
        ("lifts the curtains", "linen curtains lifting and falling at an open window, sunlight on old wooden floorboards"),
        ("scatters the light", "dappled sunlight through moving leaves dancing over a sofa and cushions"),
        ("sways the lamp tassels", "the fringe of a fabric lampshade swaying gently on a side table"),
        ("rustles the leaves", "a corner window full of leaves rustling outside, books and a lamp inside"),
        ("and turns the pages", "an open book on a table, its pages turning slowly by themselves in the breeze"),
    ]),
    "the rain": (["spring", "summer", "autumn", "winter", "rainy season"], [
        ("a thank you to the rain that", "raindrops running down an old window pane, {view} blurred behind"),
        ("taps on the glass", "close-up of rain tapping a window, a mug on the sill"),
        ("fills the garden", "rain falling on {garden}, {flower} glistening"),
        ("slows the afternoon", "a teacup steaming beside a rain-streaked window in {house}"),
        ("keeps us inside", "the girl, seen from behind, curled on a window seat with a blanket, rain outside"),
        ("and makes everything green", "{view} washed bright green after the rain, drops falling from the eaves"),
    ]),
    "the morning sun": (["spring", "summer", "autumn", "winter", "dry season"], [
        ("a love note to the morning sun that", "the first warm sunbeam crossing an old bedroom of {house}"),
        ("wakes the house", "sunlight sliding across a kitchen table set with bread and jam"),
        ("warms the windowsill", "a sunlit windowsill with potted herbs and {flower}"),
        ("glows in the teacup", "daylight shining through a glass teapot of tea, steam rising"),
        ("lights the garden", "morning sun on dew in {garden}"),
        ("and opens the day", "a door opening onto {view} in soft morning light"),
    ]),
    "the first snow": (["winter"], [
        ("a letter to the first snow that", "the first snowflakes drifting past an old window of {house}"),
        ("hushes the garden", "snow settling quietly on {garden}"),
        ("frosts the window", "frost patterns on a window pane, a grey morning outside"),
        ("brings the fire alive", "a wood fire crackling in a stone fireplace, a knitted blanket on the chair"),
        ("calls for cocoa", "the girl's hands holding a steaming mug of cocoa by the window"),
        ("and paints the world white", "{view} under fresh snow, calm and wide"),
    ]),
    "autumn": (["autumn"], [
        ("a love letter to autumn that", "golden leaves drifting past an open window of {house}"),
        ("colours the hills", "{view} in autumn colours"),
        ("fills the baskets", "a wicker basket of apples and pears on a wooden table"),
        ("smells of cinnamon", "a pie cooling on a windowsill, steam rising"),
        ("comes in early", "one small lamp switched on in a plain corner at dusk"),
        ("and covers the path", "fallen leaves on the garden path of {garden}"),
    ]),
    "the river": (["spring", "summer", "autumn", "winter", "rainy season", "dry season"], [
        ("a thank you to the river that", "a clear river flowing past the garden of {house}"),
        ("sings all day", "close-up of water running over smooth stones"),
        ("carries the leaves", "a few leaves floating slowly downstream"),
        ("waters the flowers", "{flower} growing on the riverbank, swaying"),
        ("keeps the ducks busy", "ducks paddling slowly near the reeds"),
        ("and lulls us to sleep", "an open window at dusk with the river below, a lamp inside"),
    ]),
    "the birds": (["spring", "summer", "autumn", "winter", "rainy season", "dry season"], [
        ("a love letter to the birds that", "small birds hopping on a garden table of {house}"),
        ("sing before sunrise", "a bird singing on a branch outside the window at dawn"),
        ("visit the feeder", "birds pecking seeds at a wooden feeder in {garden}"),
        ("bathe in the stone bowl", "a small bird splashing in a stone birdbath"),
        ("sit on the fence", "two birds resting on an old wooden fence, {view} behind"),
        ("and tell us it's morning", "the girl opening a window wide, birdsong, {view}"),
    ]),
    "slow sundays": (["spring", "summer", "autumn", "winter", "rainy season", "dry season"], [
        ("an ode to slow sundays that", "an unmade bed with white linen in soft light, {house}"),
        ("begin with warm bread", "the girl's hands slicing warm bread in the kitchen"),
        ("drift by the window", "the girl reading by the window, seen from behind, {view} outside"),
        ("smell of fresh flowers", "the girl's hands arranging {flower} in a jug"),
        ("end with tea outside", "a tea tray on a garden table in {garden}"),
        ("and ask for nothing", "{view} at golden hour, completely still"),
    ]),
    "golden hour": (["spring", "summer", "autumn", "dry season"], [
        ("a letter to golden hour that", "low golden sun streaming into {house} across the floor"),
        ("gilds the kitchen", "golden light on copper pans and a bowl of fruit"),
        ("warms the stone walls", "the outside wall of {house} in low evening sun, {flower} by the door"),
        ("stretches the shadows", "long shadows of chairs across the garden of {garden}"),
        ("glows in the meadow", "{view} in low evening sun"),
        ("and says goodnight softly", "the sun setting behind the hills seen through a window frame"),
    ]),
    "the mist": (["spring", "autumn", "winter", "rainy season"], [
        ("a love letter to the mist that", "soft morning mist over {view} through an old window"),
        ("hides the hills", "mist drifting slowly through the valley"),
        ("beads on the spiderwebs", "dew drops on a spiderweb in the garden"),
        ("softens the garden", "{garden} faint in mist"),
        ("keeps the kettle on", "a kettle steaming on the stove in {house}"),
        ("and lifts by noon", "the mist thinning to reveal {view} in soft light"),
    ]),
}

MUSIC = [
    "soft felt piano, warm and slow", "gentle acoustic guitar fingerpicking with soft strings",
    "music box and soft piano, dreamy", "warm cello and piano, tender", "soft harp and flute, airy",
    "lofi piano with vinyl crackle, very calm", "ambient pads with gentle piano, peaceful",
    "celtic harp and low whistle, pastoral", "kalimba and soft pads, light", "solo piano in a quiet room, intimate",
]


def with_article(x):
    w = x.split()[0]
    if w.endswith("s") or w == "geese":
        return x
    return ("an " if x[0].lower() in "aeiou" else "a ") + x


def build(count, seed):
    rng = random.Random(seed)
    per_home = -(-count // len(HOMES)) + 10  # spare: homes with few season+task pairs give fewer
    ideas = []
    cap_cycle = itertools.cycle(rng.sample(CAPTIONS, len(CAPTIONS)))
    mus_cycle = itertools.cycle(rng.sample(MUSIC, len(MUSIC)))
    for hi, (home, house, views, gardens, local, animals, sounds, seasons, treeless) in enumerate(HOMES):
        combos = []
        for season in seasons:
            sd = SEASON_DETAIL[season]
            tasks = local + sd["tasks"]
            for task, weather in itertools.product(tasks, sd["weather"]):
                combos.append((season, task, weather))
        rng.shuffle(combos)
        # spread over seasons and tasks first: take one per (season, task) before repeating a task
        seen, pick = set(), []
        for c in combos:
            if (c[0], c[1]) not in seen:
                seen.add((c[0], c[1]))
                pick.append(c)
        for k, (season, task, weather) in enumerate(pick[:per_home]):
            sd = SEASON_DETAIL[season]
            flower = rng.choice(sd["flowers"])
            animal = animals[k % len(animals)] if k % 4 != 3 else None  # 3 of 4 ideas have an animal
            sound = sounds[k % len(sounds)]
            if season in ("winter", "rainy season") and sound == "cicadas":
                sound = "fire"
            wet = any(w in weather for w in ("rain", "drizzle", "monsoon"))
            if wet:
                sound = "rain"
            elif sound == "rain":  # no rain sound under a clear sky
                sound = next((x for x in sounds if x != "rain"), "birds")
            view = views[k % len(views)]
            garden = gardens[(k // 2) % len(gardens)]
            shots = [
                f"Through an open old window of {house}: {view}, {weather}. A small vase of {flower} on the sill.",
                f"A beautiful corner inside {house}: {rng.choice(CORNERS)}, soft light, {weather} outside.",
                f"In the kitchen of {house}: the girl, seen from behind and the side, {task}; steam or soft window light, hands moving slowly.",
                f"Close-up of the girl's hands {task}, real texture of food and wood, calm and unhurried.",
                f"The garden: {garden}, {flower} moving in a light breeze, {weather}.",
                (f"{with_article(animal)[0].upper()}{with_article(animal)[1:]} relaxing near the house, moving gently and naturally, {weather}." if animal
                 else f"Close-up detail: {SOUND_TEXT.get(sound, sound)} - the source of the sound in the frame, {weather}."),
                f"A table set outside or by the window with tea, a small plate of what she made and a jug of {flower}, {weather}.",
                f"Back to the view: {view}, seen past a window frame or doorway, {weather}, calm and wide.",
            ]
            if treeless:
                for j in (0, 4, 7):  # the shots that show the landscape
                    shots[j] += " NO trees, NO forest, NO bushes anywhere in the landscape."
            ideas.append({
                "id": f"hv-{len(ideas) + 1:04d}",
                "title": f"{season.capitalize()} {task} in {a_home(home)}" + (f" with {with_article(animal)}" if animal else ""),
                "home": home, "season": season, "weather": weather, "task": task,
                "animal": animal, "flower": flower, "sound": SOUND_TEXT.get(sound, sound),
                "caption": next(cap_cycle), "music": next(mus_cycle), "shots": shots, "_order": (k, hi),
            })
    # round-robin over homes (k-th idea of every home, then k+1-th) so consecutive ids differ
    ideas.sort(key=lambda i: i.pop("_order"))
    ideas = ideas[:count]
    for n, i in enumerate(ideas, 1):
        i["id"] = f"hv-{n:04d}"
    return ideas


WATER = {"river", "stream", "brook", "burn", "canal water", "backwater", "lake", "fjord water"}


def a_home(home):
    return ("an " if home[0].lower() in "aeiou" else "a ") + home


def build_odes(seed):
    """Every home x subject x fitting season, each a 6-shot ode (concept 'ode')."""
    rng = random.Random(seed + 1)
    mus = itertools.cycle(rng.sample(MUSIC, len(MUSIC)))
    odes = []
    for hi, (home, house, views, gardens, _local, _animals, sounds, seasons, treeless) in enumerate(HOMES):
        for subject, (fits, lines) in ODES.items():
            if subject == "the river" and not set(sounds) & WATER:
                continue  # no river at this home
            for season in [x for x in seasons if x in fits]:
                sd = SEASON_DETAIL[season]
                fmt = dict(house=house, view=rng.choice(views), garden=rng.choice(gardens), flower=rng.choice(sd["flowers"]))
                shots = [v.format(**fmt) + f", {rng.choice(sd['weather'])}." for _, v in lines]
                if treeless:
                    shots = [x + " NO trees, NO forest, NO bushes in the landscape." for x in shots]
                odes.append({
                    "id": None, "concept": "ode",
                    "title": f"An ode to {subject} - {season} in {a_home(home)}",
                    "home": home, "season": season, "weather": "", "task": f"ode to {subject}",
                    "animal": None, "flower": fmt["flower"], "sound": "",
                    "caption": lines[0][0], "lines": [p for p, _ in lines], "music": next(mus), "shots": shots,
                    "_order": (rng.random(), hi),
                })
    rng.shuffle(odes)
    # round-robin over subjects (homes are shuffled within each) so neighbouring odes differ
    seen, subj = {}, list(ODES)
    for o in odes:
        seen[o["task"]] = seen.get(o["task"], 0) + 1
        o["_order"] = (seen[o["task"]], subj.index(o["task"][len("ode to "):]))
    odes.sort(key=lambda o: o.pop("_order"))
    return odes


def bank(count, seed):
    """2 postcards : 1 ode, then renumber."""
    n_odes = count // 3
    cards, odes = build(count - n_odes, seed), build_odes(seed)[:n_odes]
    for c in cards:
        c["concept"] = "postcard"
    out, ci, oi = [], iter(cards), iter(odes)
    for k in range(count):
        out.append(next(oi) if k % 3 == 2 else next(ci))
    for n, i in enumerate(out, 1):
        i["id"] = f"hv-{n:04d}"
    keys = {(i["home"], i["season"], i["task"]) for i in out}
    assert len(keys) == len(out), "duplicate home+season+task"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=17)
    a = ap.parse_args()
    ideas = bank(a.count, a.seed)
    (SKILL / "ideas.json").write_text(json.dumps(ideas, ensure_ascii=False, indent=1) + "\n")
    lines = ["# Healing video ideas", "", f"{len(ideas)} ideas, built by `scripts/gen_ideas.py`. "
             "Used ones are in `~/.config/museai/healing-history.json` (`scripts/ideas.py list`).", ""]
    lines += [f"- **{i['id']}** {i['title']} - {i['weather']}, {i['flower']}, {i['sound']} · \"{i['caption']}\""
              if i["concept"] == "postcard" else
              f"- **{i['id']}** {i['title']} · \"{' / '.join(i['lines'])}\"" for i in ideas]
    (SKILL / "ideas.md").write_text("\n".join(lines) + "\n")
    print(f"{len(ideas)} ideas → ideas.json, ideas.md")


if __name__ == "__main__":
    main()
