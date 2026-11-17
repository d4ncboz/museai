#!/usr/bin/env python3
"""Build ../ideas/ideas.json: 1000 field-to-table day plans (subject x setting x thread), each a whole arc
from the source (field, hill, stream, tree) through the work to the meal or the finished thing.

  python3 gen_ideas.py [--bank countryside|cottage|all]
      countryside -> ideas.json (Chinese countryside, ids ft-NNNN); cottage -> cottage.json (ELLIE and Pip in a
      Western cottage: basket out, gather, cook, eat at dusk; ids fc-NNNN); default all. Stable ids: same input -> same ids.

Subjects are the heart (what the hands do for 12 minutes); settings and threads vary the place and the
small reason the day matters. Every subject lists only work muse films well: no knives on screen (things are
already cut, or split by hand, pounded, pressed, poured), no other people, no live animals killed or handled.
"""
import argparse
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "ideas" / "ideas.json"
COTTAGE_OUT = OUT.with_name("cottage.json")

# (key, kind, seasons, source, [work stages], [results], enjoy)
SUBJECTS = [
    # ingredient lives: one thing from the field to many dishes
    ("chestnut", "food", "autumn", "chestnut burrs under old trees on the slope", ["washing in the stream", "sun-drying on a bamboo tray", "sand-roasting in the wok", "pounding in a stone mortar"], ["sugar-roasted chestnuts", "chestnut rice in a clay pot", "flower-shaped chestnut cakes"], "dusk table under the eaves"),
    ("sweet potato", "food", "autumn", "digging sweet potatoes from red earth", ["washing in a wooden tub", "steaming in a bamboo steamer", "mashing with a wooden pestle", "drying slices on racks"], ["roasted sweet potatoes in the stove ashes", "sweet potato glutinous cakes", "dried sweet potato strips"], "warm sweet potato by the stove at night"),
    ("persimmon", "food", "autumn", "picking persimmons with a forked bamboo pole", ["peeling by hand after softening", "hanging on strings under the eaves", "pressing flat", "pulping"], ["dried persimmon cakes", "persimmon jam", "persimmon pancakes"], "persimmons hung like lanterns at dusk"),
    ("pumpkin", "food", "autumn", "carrying ripe pumpkins up from the vines", ["breaking into pieces by hand", "steaming", "mashing", "kneading with rice flour"], ["pumpkin millet porridge", "pumpkin rice cakes", "steamed pumpkin with honey"], "breakfast in the mist"),
    ("peanut", "food", "autumn", "pulling peanut plants from sandy soil", ["shaking off soil", "washing", "sun-drying", "roasting and rubbing off skins"], ["boiled salted peanuts", "peanut brittle", "peanut sesame paste"], "a bowl of peanuts by the fire"),
    ("taro", "food", "autumn", "lifting taro from the wet field edge", ["scrubbing", "steaming whole", "peeling by hand", "mashing"], ["taro with sugar dip", "taro balls in syrup", "taro and rice porridge"], "steaming bowls on a rainy evening"),
    ("corn", "food", "summer", "breaking corn ears from tall stalks", ["husking", "stripping kernels by hand", "grinding on a stone mill", "steaming"], ["corn cakes on bamboo leaves", "corn porridge", "grilled corn"], "corn at the edge of the field at sunset"),
    ("rice", "food", "autumn", "pulling golden rice sheaves in the terrace by hand", ["threshing on a wooden frame", "sun-drying on mats", "hulling in a stone mortar", "washing new rice"], ["new-rice clay pot rice", "rice crust", "sweet rice cakes"], "the first bowl of new rice"),
    ("wheat", "food", "summer", "gathering ripe wheat into sheaves by hand", ["threshing by beating", "winnowing in the wind", "stone milling", "kneading dough"], ["hand-pulled noodles", "steamed buns", "scallion pancakes"], "noodles in the courtyard"),
    ("soybean", "food", "autumn", "pulling dry soybean plants", ["beating pods", "soaking", "stone grinding", "boiling soy milk"], ["fresh tofu pressed in cloth", "soy milk", "tofu skin"], "warm tofu with chilli oil"),
    ("mung bean", "food", "summer", "picking dark mung bean pods", ["sun-drying pods", "shelling by hand", "soaking", "simmering"], ["mung bean soup cooled in the stream", "mung bean cakes", "bean sprouts"], "cool soup on a hot afternoon"),
    ("lotus root", "food", "autumn", "pulling lotus root from the pond mud", ["washing in the pond", "stuffing with sticky rice", "simmering", "pieces already sliced"], ["sweet sticky-rice lotus root", "lotus root soup", "lotus seed sweet soup"], "a boat on the pond at dusk"),
    ("bamboo shoot", "food", "spring", "digging bamboo shoots in the morning forest", ["peeling sheaths by hand", "boiling", "sun-drying", "braising"], ["oil-braised bamboo shoots", "dried bamboo shoots", "bamboo shoot rice"], "lunch in the bamboo shade"),
    ("winter bamboo shoot", "food", "winter", "finding winter bamboo shoots under fallen leaves", ["peeling sheaths", "blanching", "braising", "smoking"], ["braised shoots", "shoot soup", "smoked shoots"], "soup by the fire"),
    ("tea", "food", "spring", "picking tender tea buds on the hill", ["withering on bamboo trays", "pan-firing by hand in the wok", "rolling", "drying"], ["green tea", "tea-leaf rice", "tea eggs"], "first tea of spring"),
    ("rose", "food", "summer", "picking roses at dawn", ["separating petals", "rubbing with sugar", "sealing in jars", "drying"], ["rose jam", "rose cakes", "rose tea"], "a cup of rose tea"),
    ("osmanthus", "food", "autumn", "shaking osmanthus blossoms onto a cloth", ["picking out stems", "layering with honey", "drying", "steeping"], ["osmanthus honey", "osmanthus rice cake", "osmanthus rice wine"], "the yard smelling of osmanthus"),
    ("chrysanthemum", "food", "autumn", "picking small yellow chrysanthemums", ["steaming flowers", "sun-drying", "steeping", "mixing into dough"], ["chrysanthemum tea", "chrysanthemum cakes", "chrysanthemum rice wine"], "tea on the double ninth"),
    ("plum", "food", "summer", "picking green plums", ["washing", "salting", "layering with rock sugar", "smoking"], ["plum wine", "sour plum drink", "preserved plums"], "a cold plum drink"),
    ("loquat", "food", "spring", "picking loquats from a tall tree", ["peeling by hand", "simmering with rock sugar", "jarring", "drying leaves"], ["loquat syrup", "loquat jam", "loquat in syrup"], "loquats on a blue plate"),
    ("cherry", "food", "spring", "picking small red cherries", ["washing", "pitting by hand", "simmering", "soaking in wine"], ["cherry jam", "cherry wine", "cherry rice cakes"], "a bowl of cherries in the grass"),
    ("peach", "food", "summer", "picking peaches in the orchard", ["peeling by hand after blanching", "simmering", "jarring", "drying"], ["peach jam", "peaches in syrup", "peach blossom-shaped cakes"], "a cold peach by the stream"),
    ("watermelon", "food", "summer", "carrying watermelons from the sandy field", ["cooling in the stream", "breaking open by hand", "juicing", "candying the rind"], ["watermelon juice", "watermelon jelly", "candied rind"], "watermelon on the stone step"),
    ("grape", "food", "summer", "picking grapes from the vine trellis", ["washing", "crushing by hand", "fermenting", "drying"], ["grape wine", "raisins", "grape jelly"], "a glass under the trellis"),
    ("pear", "food", "autumn", "picking pears", ["peeling by hand after steaming", "simmering with rock sugar", "reducing to paste", "drying"], ["autumn pear paste", "steamed pear with rock sugar", "dried pears"], "warm pear soup for a cough"),
    ("apple", "food", "autumn", "picking mountain apples", ["washing", "drying rings on strings", "simmering", "pressing"], ["dried apple rings", "apple paste", "apple vinegar"], "apples by the window"),
    ("pomelo", "food", "winter", "picking pomelos from a tall tree", ["peeling by hand", "simmering peel", "candying", "mixing with honey"], ["honey pomelo tea", "candied pomelo peel", "pomelo salad"], "pomelo tea in winter"),
    ("mandarin", "food", "winter", "picking mandarins on the hill", ["peeling", "drying peels", "simmering", "candying"], ["dried tangerine peel", "mandarin jam", "mandarin tea"], "mandarins on the stove top"),
    ("radish", "food", "winter", "pulling white radishes", ["washing", "drying strips on bamboo racks", "salting", "pickling"], ["radish cake", "dried radish strips", "pickled radish"], "a winter breakfast"),
    ("cabbage", "food", "winter", "lifting cabbages from frosty beds", ["washing", "salting", "packing jars", "stir-frying"], ["pickled cabbage", "cabbage dumplings", "sour cabbage soup"], "a pot of soup in the snow"),
    ("chilli", "food", "autumn", "picking red chillies", ["stringing on cotton", "sun-drying", "pounding in a mortar", "frying oil"], ["chilli oil", "fermented chilli paste", "dried chilli strings"], "red strings under the eaves"),
    ("garlic", "food", "summer", "pulling garlic bulbs", ["braiding the stems", "drying under eaves", "peeling", "pickling in vinegar"], ["laba garlic", "garlic braids", "garlic sauce"], "green garlic in a jar"),
    ("potato", "food", "summer", "digging potatoes", ["washing", "steaming", "mashing", "starch washing"], ["potato pancakes", "potato starch noodles", "roasted potatoes in ash"], "potatoes from the fire"),
    ("cucumber", "food", "summer", "picking cucumbers from the trellis", ["washing in the stream", "smashing by hand", "salting", "pickling"], ["smashed cucumber", "cucumber pickles", "cucumber noodles"], "a cool lunch"),
    ("tomato", "food", "summer", "picking tomatoes", ["blanching", "peeling by hand", "simmering", "jarring"], ["tomato sauce", "tomato egg noodles", "tomato hot pot"], "a summer evening meal"),
    ("eggplant", "food", "summer", "picking eggplants", ["steaming whole", "tearing by hand", "dressing", "sun-drying"], ["steamed eggplant", "eggplant with garlic", "dried eggplant"], "lunch under the trellis"),
    ("pea", "food", "spring", "picking pea pods", ["shelling", "blanching", "mashing", "steaming"], ["pea rice", "pea jelly", "pea cakes"], "green bowls in spring"),
    ("broad bean", "food", "spring", "picking broad beans", ["shelling", "peeling by hand", "frying", "mashing"], ["broad bean paste", "fried broad beans", "bean and rice"], "spring picnic"),
    ("wild herbs", "food", "spring", "gathering wild greens on the hillside", ["washing in the stream", "blanching", "pounding", "mixing dough"], ["green rice balls", "wild greens dumplings", "herb pancakes"], "a spring picnic on the hill"),
    ("mushroom", "food", "summer", "gathering mushrooms after rain", ["brushing clean", "sun-drying", "frying", "simmering broth"], ["mushroom broth", "mushroom oil", "dried mushrooms"], "soup after the rain"),
    ("walnut", "food", "autumn", "knocking walnuts from the tree", ["hulling with gloves", "washing", "sun-drying", "cracking with a stone"], ["walnut cookies", "walnut milk", "honey walnuts"], "walnuts by the fire"),
    ("sesame", "food", "autumn", "carrying dry sesame bundles", ["beating seeds out", "washing", "roasting", "grinding in a stone mill"], ["black sesame paste", "sesame candy", "sesame balls"], "sweet soup at night"),
    ("buckwheat", "food", "autumn", "gathering buckwheat in the high field", ["threshing", "milling", "kneading", "pressing noodles"], ["buckwheat noodles", "buckwheat cakes", "buckwheat tea"], "noodles with a view"),
    ("millet", "food", "autumn", "gathering millet heads", ["drying", "threshing", "milling", "steaming"], ["millet porridge", "millet cakes", "millet wine"], "porridge in the morning"),
    ("glutinous rice", "food", "winter", "fetching sacks of sticky rice from the store room", ["soaking", "steaming", "pounding in a stone trough", "shaping"], ["rice cakes", "sweet rice balls", "rice wine"], "new year table"),
    ("egg", "food", "spring", "collecting eggs from the hen house straw", ["washing", "salting in clay", "boiling", "pickling"], ["salted eggs", "tea eggs", "steamed egg custard"], "breakfast"),
    ("honey", "food", "summer", "lifting honeycomb from a log hive in a veil", ["draining comb", "straining through cloth", "jarring", "baking"], ["honeycomb", "honey cakes", "honey lemon tea"], "honey on warm buns"),
    ("fish", "food", "autumn", "lifting a bamboo fish trap from the river", ["fish already cleaned", "salting", "smoking", "steaming"], ["steamed fish", "smoked fish", "fish soup"], "a riverbank meal"),
    ("lotus seed", "food", "summer", "picking lotus pods from a small boat", ["popping seeds out by hand", "drying", "simmering", "mashing"], ["lotus seed soup", "lotus paste buns", "dried lotus seeds"], "on the boat at dusk"),
    ("water chestnut", "food", "winter", "pulling water chestnuts from the paddy mud", ["washing", "peeling by hand after boiling", "grinding", "setting"], ["water chestnut cake", "sweet soup", "starch"], "a winter dessert"),
    ("yam", "food", "winter", "digging long yams", ["washing", "steaming", "mashing", "shaping"], ["yam cakes", "yam porridge", "honey yam"], "warm bowls in snow"),
    ("ginger", "food", "autumn", "digging ginger", ["washing", "pounding", "simmering with brown sugar", "drying"], ["ginger brown sugar tea", "candied ginger", "ginger milk curd"], "warm drink on a cold night"),
    ("hawthorn", "food", "autumn", "picking red hawthorn berries", ["washing", "seeding with a straw", "simmering", "candying"], ["candied hawthorn sticks", "hawthorn cakes", "hawthorn drink"], "red sticks in the sun"),
    ("jujube", "food", "autumn", "shaking red dates from the tree", ["washing", "sun-drying", "steaming", "pitting"], ["date cakes", "date porridge", "drunken dates"], "a pot of date tea"),
    ("kiwi", "food", "autumn", "picking wild kiwis on vines", ["ripening in rice", "peeling", "simmering", "drying"], ["kiwi jam", "kiwi wine", "dried kiwi"], "kiwi jam on steamed buns"),
    ("bayberry", "food", "summer", "picking red bayberries", ["soaking in salt water", "simmering", "soaking in liquor", "drying"], ["bayberry wine", "bayberry drink", "bayberry jam"], "a chilled bowl"),
    ("sugarcane", "food", "winter", "carrying sugarcane stalks from the field", ["peeling by hand", "pressing in a wooden press", "boiling juice", "setting"], ["brown sugar blocks", "sugarcane juice", "ginger brown sugar"], "sugar cooling in moulds"),
    ("rapeseed", "food", "spring", "gathering rapeseed pods", ["beating seeds", "roasting", "pressing oil", "frying"], ["fresh oil fried dough", "oil-braised shoots", "flower tea"], "the yellow field at dusk"),
    ("herbs for soup", "food", "winter", "digging angelica roots and picking herbs", ["washing", "sun-drying", "simmering", "steeping"], ["herbal root soup", "herbal tea", "herb bundles"], "a pot simmering all day"),
    ("mulberry", "food", "spring", "picking dark mulberries from low branches", ["washing", "simmering", "straining through cloth", "drying"], ["mulberry jam", "mulberry wine", "mulberry drink"], "purple fingers and a cool drink"),
    ("bamboo-tube rice", "food", "autumn", "choosing green bamboo tubes in the forest", ["soaking rice", "filling the tubes", "plugging with leaves", "roasting over the fire"], ["bamboo-tube rice", "bamboo-tube soup", "rice with sesame salt"], "splitting the tubes by the fire"),
    ("fig", "food", "summer", "picking soft figs", ["washing", "simmering", "drying", "steaming"], ["fig jam", "dried figs", "fig and lily soup"], "figs on a leaf"),
    ("wild strawberry", "food", "spring", "picking tiny wild strawberries on the bank", ["washing", "crushing with sugar", "simmering", "setting with rice flour"], ["strawberry jam", "strawberry rice cakes", "strawberry drink"], "a picnic on the bank"),
    ("rice noodles", "food", "summer", "fetching new rice from the store", ["soaking", "stone grinding", "steaming sheets", "rolling"], ["rice noodles", "rolled rice sheets", "noodle soup"], "noodles in the morning"),
    ("pine nut", "food", "autumn", "gathering pine cones under tall pines", ["sun-drying cones", "shaking out nuts", "cracking with a stone", "roasting"], ["pine nut candy", "pine nut porridge", "roasted pine nuts"], "nuts by the fire"),
    ("maltose candy", "food", "winter", "sprouting wheat on bamboo trays", ["mashing with rice", "straining", "boiling down", "pulling the candy"], ["maltose", "sesame candy", "puffed rice candy"], "candy before the new year"),
    ("red bean", "food", "autumn", "pulling red bean plants", ["beating pods", "soaking", "simmering", "mashing to paste"], ["red bean soup", "red bean buns", "red bean paste"], "sweet soup on a cold night"),
    # preserves and ferments
    ("rice wine", "preserve", "winter", "steaming sticky rice", ["cooling on bamboo", "mixing with yeast", "sealing in a clay jar", "straining"], ["sweet rice wine", "rice wine eggs", "fermented rice balls"], "warm rice wine at night"),
    ("soy sauce", "preserve", "summer", "steaming soybeans", ["molding on bamboo trays", "brining in clay jars", "stirring in the sun", "pressing"], ["home soy sauce", "bean paste", "braised tofu"], "the jars in the sun"),
    ("vinegar", "preserve", "autumn", "gathering fallen fruit", ["crushing", "fermenting in clay jars", "stirring", "straining"], ["fruit vinegar", "pickles", "vinegar drink"], "vinegar in old bottles"),
    ("pickles", "preserve", "autumn", "picking mustard greens", ["sun-wilting", "salting", "packing jars", "sealing with water"], ["sour vegetables", "pickled mustard", "sour vegetable soup"], "jars lined up in the cool store room"),
    ("smoked pork", "preserve", "winter", "hanging cured pork over the stove", ["pork already salted", "smoking with cypress", "washing", "steaming"], ["smoked pork with garlic shoots", "smoked sausage rice", "smoked pork soup"], "new year meal"),
    ("tofu", "preserve", "winter", "soaking soybeans overnight", ["stone grinding", "boiling", "setting with brine", "pressing in cloth"], ["fresh tofu", "fermented tofu", "smoked tofu"], "tofu in the snow"),
    ("bean paste", "preserve", "summer", "picking broad beans", ["peeling", "molding", "mixing with chilli", "sunning in a jar"], ["chilli bean paste", "twice-cooked dishes", "noodles with paste"], "jars on the roof"),
    ("dried fruit", "preserve", "autumn", "gathering the last fruit", ["pieces already sliced", "drying on bamboo", "turning", "packing in paper"], ["dried fruit gifts", "fruit tea", "fruit cakes"], "packets tied with string"),
    ("tea cakes", "preserve", "spring", "picking leaves on the high hill", ["steaming leaves", "pressing in cloth", "drying on racks", "wrapping in paper"], ["pressed tea cakes", "tea", "tea-smoked eggs"], "tea poured on the porch"),
    ("jam pantry", "preserve", "summer", "picking berries along the path", ["washing", "simmering", "jarring", "labelling"], ["three jams", "jam buns", "berry drink"], "a shelf of jars"),
    # crafts
    ("indigo dye", "craft", "summer", "gathering armfuls of indigo leaves", ["soaking leaves", "stirring the vat", "tying cloth patterns", "dipping and airing"], ["indigo scarf", "indigo tablecloth", "a dyed shirt"], "blue cloth in the wind"),
    ("cotton", "craft", "autumn", "picking white cotton bolls", ["drying", "seeding by hand", "fluffing with a bow", "spinning"], ["cotton thread", "a quilt", "a cushion"], "sleeping under the new quilt"),
    ("silk floss", "craft", "summer", "collecting cocoons", ["boiling cocoons", "stretching floss by hand", "layering", "sewing a cover"], ["silk floss quilt", "silk pouches", "silk thread"], "a light quilt"),
    ("bamboo basket", "craft", "spring", "choosing bamboo poles in the forest", ["strips already split", "soaking strips", "weaving", "finishing the rim"], ["a basket", "a sieve", "a fruit tray"], "first use of the new basket"),
    ("paper", "craft", "spring", "gathering bark and bamboo fibre", ["soaking", "pounding", "pulling sheets on a screen", "drying on a wall"], ["handmade paper", "a notebook", "a paper fan"], "writing on new paper"),
    ("ink", "craft", "winter", "collecting soot from a pine fire", ["mixing with glue", "kneading", "pressing in moulds", "drying"], ["ink sticks", "a poem on paper", "a painted fan"], "ink grinding at night"),
    ("pottery", "craft", "summer", "digging clay by the river", ["sieving", "wedging", "shaping on a kick wheel", "firing in a small kiln"], ["bowls", "a teapot", "small cups"], "tea in her own cups"),
    ("straw sandals", "craft", "autumn", "gathering rice straw after harvest", ["soaking", "twisting rope", "weaving", "evening the ends by hand"], ["straw sandals", "a straw mat", "a broom"], "walking in new sandals"),
    ("soap", "craft", "summer", "gathering soapberries", ["soaking", "boiling", "mixing with oil", "drying bars"], ["soapberry wash", "herbal soap", "a clean cloth"], "washing at the stream"),
    ("broom", "craft", "autumn", "gathering broom grass", ["drying", "binding", "evening the ends by hand", "fixing a bamboo handle"], ["two brooms", "a brush", "a clean courtyard"], "a swept yard at dusk"),
    ("wooden furniture repair", "craft", "winter", "fetching seasoned wood from the shed", ["sanding", "joining", "oiling", "painting"], ["a mended stool", "a shelf", "a tea tray"], "tea on the mended table"),
    ("embroidered pouch", "craft", "spring", "picking dye flowers and herbs", ["dyeing thread", "drawing the pattern", "stitching", "filling with herbs"], ["herb pouches", "a cushion", "a hair band"], "pouches hung by the bed"),
    ("flower crown", "craft", "spring", "picking spring flowers", ["drying", "wrapping silk", "binding wire", "arranging"], ["a flower crown", "hairpins", "a garland"], "wearing it by the pond"),
    ("winter quilt", "craft", "winter", "fluffing stored cotton", ["airing in the sun", "beating", "layering", "stitching the cover"], ["a thick quilt", "pillow covers", "slippers"], "the first cold night"),
    ("persimmon dye", "craft", "summer", "picking green persimmons", ["pounding", "fermenting juice", "brushing on cloth", "sunning"], ["brown-dyed cloth", "a fan", "a bag"], "the cloth in the sun"),
    ("closet makeover", "craft", "spring", "clearing the old woodshed", ["scrubbing", "sanding", "building shelves", "hanging cloth curtains"], ["a forest closet", "shelves", "a reading corner"], "a nap in the new corner"),
    # festival days
    ("spring festival", "festival", "winter", "sweeping the house and the yard", ["making rice cakes", "steaming buns", "pasting paper cuts", "frying snacks"], ["new year snacks", "a reunion table", "red paper cuts"], "new year's eve table"),
    ("dragon boat day", "festival", "summer", "gathering bamboo leaves and mugwort", ["soaking rice", "wrapping zongzi", "boiling", "hanging mugwort"], ["zongzi", "salted eggs", "herb bundles"], "zongzi by the river"),
    ("mid-autumn", "festival", "autumn", "picking osmanthus and taro", ["making dough", "filling mooncakes", "pressing moulds", "baking"], ["mooncakes", "osmanthus wine", "taro"], "moon over the hills"),
    ("winter solstice", "festival", "winter", "grinding flour", ["mixing filling", "wrapping dumplings", "boiling", "making dipping sauce"], ["dumplings", "sweet rice balls", "warm soup"], "dumplings by the fire"),
    ("laba", "festival", "winter", "gathering eight grains and beans", ["soaking", "simmering all night", "pickling garlic", "stirring"], ["laba porridge", "laba garlic", "date cakes"], "a bowl of laba porridge"),
    ("qingming", "festival", "spring", "picking mugwort", ["blanching", "pounding with rice", "filling", "steaming"], ["green rice balls", "spring rolls", "tea"], "a spring outing"),
    ("double ninth", "festival", "autumn", "picking chrysanthemums on the hill", ["steaming cakes", "brewing wine", "drying flowers", "climbing"], ["double ninth cakes", "chrysanthemum wine", "tea"], "a view from the hilltop"),
    ("lantern festival", "festival", "winter", "grinding sticky rice", ["making sesame filling", "rolling rice balls", "boiling", "folding paper lanterns"], ["sweet rice balls", "paper lanterns", "sesame paste"], "lanterns at night"),
    ("qixi", "festival", "summer", "gathering flowers and fruit", ["making fruit plates", "folding paper", "baking crisp knots", "embroidering"], ["crisp sugar knots", "a fruit plate", "a pouch"], "stars over the yard"),
    ("shangsi outing", "festival", "spring", "picking shepherd's purse", ["boiling eggs with it", "packing a basket", "walking to the river", "floating flowers"], ["shepherd's purse eggs", "a picnic", "flower crowns"], "a picnic by the water"),
]

SETTINGS = [
    ("bamboo hollow", "an old farmhouse in a hollow of tall green bamboo with a stream behind it"),
    ("terrace hamlet", "a stone farmhouse above curving rice terraces on a steep mountainside"),
    ("misty ridge", "a tile-roofed farmhouse high on a misty ridge, layered hills below"),
    ("river bend", "a wooden house at a slow green river bend with a stone landing"),
    ("tea hill", "a small cottage among rounded tea bushes on a gentle hill"),
    ("lotus village", "a white-walled house beside a wide lotus pond with a small wooden boat"),
    ("karst valley", "a farmhouse in a flat green valley under tall limestone peaks"),
    ("orchard slope", "an old house on a slope of fruit trees with a stone wall"),
    ("snow hamlet", "a timber house in a high mountain hamlet with snow on the roofs"),
    ("lakeside reeds", "a reed-thatched house on a quiet lake shore with reeds and a jetty"),
    ("pine gorge", "a stone house in a narrow gorge of pines with a waterfall nearby"),
    ("plateau meadow", "a farmhouse on a high green meadow with yaks far away and snow peaks"),
]

THREADS = [
    ("first harvest", "the first harvest of the year: everything is tasted for the first time"),
    ("one thing, many dishes", "one ingredient becomes four different things by dusk"),
    ("for the winter jar", "most of it is put away in jars for the cold months; one small bowl is eaten today"),
    ("rain turns the day", "rain comes at noon and the work moves under the eaves"),
    ("gift down the mountain", "a basket of the result is wrapped in cloth and left at the path for the village below"),
    ("an old recipe", "she follows a handwritten recipe card from an old tin, step by step"),
    ("the second try", "the first batch fails quietly; the second, slower one comes right"),
    ("the dog's share", "Doudou waits all day for a share and gets it at the end"),
    ("first frost", "the first frost of the year whitens the field in the morning"),
    ("a new tool", "she makes or mends the tool first, then uses it all day"),
    ("from seed saved", "the plants grew from seeds saved last year; she saves new seeds at the end"),
    ("sound of the day", "the day is told through its sounds: water, fire, wind, chopsticks"),
]

SEASON_OK = {"bamboo hollow": "all", "terrace hamlet": "all", "misty ridge": "all", "river bend": "all",
             "tea hill": "all", "lotus village": "spring summer autumn", "karst valley": "all",
             "orchard slope": "all", "snow hamlet": "winter", "lakeside reeds": "all", "pine gorge": "all",
             "plateau meadow": "summer autumn"}
THREAD_OK = {"first frost": "autumn winter", "rain turns the day": "spring summer autumn"}

HOOKS = ["from the {src} to the table", "one quiet day of {key}", "{key}, start to finish", "a whole day for {key}",
         "slow {season} with {key}", "everything from {key}"]


# ---- Western cottage bank (ELLIE, Pip the cat): basket out, gather, home, cook, eat at dusk ----
# kinds: forage (wood/hedgerow/shore dinner), garden (kitchen-garden harvest dinner), bake, preserve
COTTAGE_SUBJECTS = [
    # forage
    ("wild garlic", "forage", "spring", "picking wild garlic leaves under the trees with a basket", ["washing in a stone sink", "tearing leaves by hand", "pounding in a mortar with oil", "folding into soft dough"], ["wild garlic soup", "wild garlic butter on warm bread", "wild garlic omelette"], "soup in a bowl by the window at dusk"),
    ("nettle", "forage", "spring", "picking young nettle tops in thick gloves", ["blanching in a pot", "squeezing dry by hand", "stirring into a pot", "simmering gently"], ["nettle soup", "nettle and potato mash", "nettle tea"], "green soup and bread at the window"),
    ("elderflower", "forage", "spring", "cutting creamy elderflower heads from the hedge", ["shaking out the insects", "steeping in a big bowl", "straining through muslin", "bottling"], ["elderflower cordial", "elderflower fritters", "elderflower sugar"], "a cold glass of cordial at dusk"),
    ("dandelion", "forage", "spring", "gathering dandelion flowers in a sunny meadow", ["picking off the petals", "simmering with sugar", "straining", "folding into batter"], ["dandelion syrup", "dandelion fritters", "dandelion tea"], "golden syrup on warm pancakes"),
    ("watercress", "forage", "spring", "picking watercress from a clear stream", ["rinsing in running water", "shaking dry", "simmering soup", "whisking a dressing"], ["watercress soup", "watercress and egg sandwiches", "watercress salad"], "soup with a slice of bread at dusk"),
    ("sorrel", "forage", "spring", "picking lemony sorrel leaves from the meadow edge", ["washing", "wilting in butter", "stirring into cream", "whisking eggs"], ["sorrel soup", "sorrel omelette", "sorrel sauce on new potatoes"], "a green plate by the window"),
    ("hawthorn leaves", "forage", "spring", "picking tender hawthorn leaves and buds from the hedge", ["washing", "tearing small", "tossing with oil", "folding into bread dough"], ["hedgerow salad", "hedgerow flatbread", "leaf and cheese sandwiches"], "a hedgerow supper"),
    ("primrose", "forage", "spring", "picking a handful of primroses from a mossy bank", ["rinsing the petals", "pressing into butter", "scattering on a salad", "setting on sugar"], ["primrose butter", "candied primroses", "spring salad"], "a pretty plate at dusk"),
    ("wood sorrel", "forage", "spring", "kneeling to pick wood sorrel in the woods", ["rinsing in a bowl", "patting dry", "mixing with soft cheese", "tossing a salad"], ["wood sorrel salad", "herb cheese on toast", "sorrel tea"], "toast on the doorstep"),
    ("meadowsweet", "forage", "summer", "picking frothy meadowsweet by the river", ["shaking out", "steeping in water", "straining", "adding honey"], ["meadowsweet cordial", "meadowsweet cream", "iced tea"], "a cold glass on the step"),
    ("lime blossom", "forage", "summer", "gathering linden blossom under the big tree", ["drying on a cloth", "crumbling into a pot", "steeping", "pouring"], ["blossom tea", "blossom shortbread", "blossom syrup"], "tea at dusk with the window open"),
    ("wild strawberry", "forage", "summer", "picking tiny wild strawberries on a sunny bank", ["rinsing in a bowl", "crushing with sugar", "simmering a little", "folding into cream"], ["wild strawberry jam", "strawberries and cream", "strawberry scones"], "scones with cream at dusk"),
    ("bilberry", "forage", "summer", "picking bilberries with purple fingers", ["rinsing", "simmering with sugar", "rolling out pastry", "filling a tin"], ["bilberry pie", "bilberry compote", "bilberry pancakes"], "warm pie by the window"),
    ("samphire", "forage", "summer", "picking green samphire on the salt marsh", ["rinsing in fresh water", "snipping off woody ends by hand", "boiling briefly", "tossing in butter"], ["buttered samphire", "samphire with new potatoes", "samphire omelette"], "a plate of green by the window"),
    ("mint", "forage", "summer", "picking wild mint along the stream", ["rinsing", "bruising in a mortar", "steeping", "stirring into yogurt"], ["mint tea", "mint and pea soup", "mint sauce"], "tea by the window at dusk"),
    ("wild raspberry", "forage", "summer", "picking wild raspberries along the woodland edge", ["rinsing", "mashing with sugar", "simmering", "pouring into jars"], ["raspberry jam", "raspberry crumble", "raspberry vinegar"], "warm crumble with cream"),
    ("blackberry", "forage", "autumn", "picking blackberries from the brambles in the hedgerow lane", ["rinsing in a colander", "simmering with sugar", "sprinkling crumble topping", "baking"], ["blackberry jam", "blackberry crumble", "blackberry cordial"], "crumble and custard by the window"),
    ("sloe", "forage", "autumn", "picking dusky sloes after the first frost", ["rinsing", "pricking with a pin", "layering with sugar", "pouring into a big jar"], ["sloe syrup", "sloe jelly", "sloe tea"], "a small glass at dusk"),
    ("rosehip", "forage", "autumn", "picking red rosehips from the wild rose hedge", ["rinsing", "simmering", "straining through muslin", "boiling with sugar"], ["rosehip syrup", "rosehip tea", "rosehip jelly"], "toast with jelly at dusk"),
    ("hazelnut", "forage", "autumn", "gathering hazelnuts from under the old hazels", ["husking by hand", "drying on a tray", "cracking with a stone", "toasting in a pan"], ["toasted hazelnuts", "hazelnut butter", "hazelnut cookies"], "nuts and tea by the fire"),
    ("sweet chestnut", "forage", "autumn", "gathering chestnuts from the leaf litter under big trees", ["rinsing", "scoring already done", "roasting in a pan on the fire", "peeling by hand"], ["roast chestnuts", "chestnut soup", "chestnut puree"], "warm chestnuts by the window"),
    ("elderberry", "forage", "autumn", "picking heavy elderberry clusters from the hedge", ["stripping berries with a fork", "simmering", "straining", "bottling"], ["elderberry syrup", "elderberry jam", "elderberry tea"], "a warm cup at dusk"),
    ("crab apple", "forage", "autumn", "picking small crab apples from a leaning tree", ["rinsing", "simmering whole", "dripping through muslin overnight", "boiling with sugar"], ["crab apple jelly", "crab apple tea", "apple butter"], "jelly on warm scones"),
    ("damson", "forage", "autumn", "picking damsons from the hedge", ["rinsing", "simmering whole", "straining out the stones by hand", "pouring into jars"], ["damson jam", "damson crumble", "damson sauce"], "crumble by the window at dusk"),
    ("wild mushroom", "forage", "autumn", "kneeling in the leaves to pick wild chanterelles in the beech wood", ["brushing clean with a soft brush", "tearing by hand", "frying in butter", "stirring into soft eggs"], ["mushrooms on toast", "mushroom soup", "creamy mushroom pasta"], "mushrooms on toast at dusk"),
    ("field mushroom", "forage", "autumn", "picking field mushrooms in the dewy meadow at dawn", ["brushing clean", "peeling by hand", "frying in butter", "stirring in cream"], ["mushroom breakfast", "mushroom pie", "mushroom soup"], "a late breakfast by the window"),
    ("beechnut", "forage", "autumn", "gathering beechnuts from the forest floor", ["shelling by hand", "drying", "toasting in a pan", "grinding in a mortar"], ["toasted beechnuts", "beechnut cookies", "nut butter on bread"], "nuts and tea by the fire"),
    ("walnut", "forage", "autumn", "gathering fallen walnuts from under the old tree", ["husking with gloves", "drying on a rack", "cracking with a stone", "toasting"], ["walnut bread", "walnut cake", "walnut and honey bites"], "cake and tea at dusk"),
    ("pine tips", "forage", "winter", "snapping fresh green pine tips in the frosty forest", ["rinsing", "steeping in hot water", "simmering with sugar", "straining"], ["pine needle tea", "pine syrup", "pine shortbread"], "hot tea by the stove"),
    ("winter mushroom", "forage", "winter", "picking oyster mushrooms from a fallen log in the cold wood", ["brushing clean", "tearing into strips", "frying in butter", "simmering broth"], ["mushroom broth", "mushrooms on toast", "mushroom risotto"], "warm bowl by the stove"),
    ("winter cress", "forage", "winter", "picking peppery cress from a frosty stream bank", ["rinsing in cold water", "shaking dry", "mixing a dressing", "simmering a soup"], ["cress soup", "cress sandwich", "cress and potato salad"], "soup by the fire"),
    ("rosehip winter", "forage", "winter", "picking the last rosehips from a frosty hedge", ["rinsing", "simmering", "straining", "warming with honey"], ["warm rosehip drink", "rosehip porridge", "rosehip jam on toast"], "a hot drink at dusk"),
    # garden
    ("rhubarb", "garden", "spring", "pulling pink rhubarb stalks in the kitchen garden", ["washing", "tearing into pieces", "roasting with sugar", "rolling out pastry"], ["rhubarb crumble", "stewed rhubarb with cream", "rhubarb jam"], "crumble and custard by the window"),
    ("asparagus", "garden", "spring", "snapping green asparagus spears in the garden bed", ["rinsing", "snapping ends by hand", "boiling gently", "melting butter"], ["asparagus with soft eggs", "asparagus tart", "asparagus soup"], "a simple plate at dusk"),
    ("spring greens", "garden", "spring", "cutting spring greens and young spinach in the garden", ["washing in a bucket", "tearing leaves", "wilting in butter", "folding into pastry"], ["green pie", "greens and egg", "green soup"], "pie at the window at dusk"),
    ("radish", "garden", "spring", "pulling pink radishes from the garden bed", ["washing in a bucket", "trimming leaves by hand", "dipping in butter and salt", "mixing a leaf salad"], ["radishes with butter", "radish leaf soup", "radish salad"], "a picnic plate at dusk"),
    ("spring onion", "garden", "spring", "pulling spring onions and chives", ["rinsing", "tearing small", "stirring into batter", "frying"], ["savory pancakes", "chive scrambled eggs", "spring onion soup"], "pancakes by the window"),
    ("pea", "garden", "spring", "picking fat pea pods in the garden", ["shelling on the doorstep", "boiling briefly", "mashing with mint", "toasting bread"], ["pea soup", "pea and mint on toast", "pea risotto"], "green toast at dusk"),
    ("broad bean", "garden", "spring", "picking broad bean pods from tall plants", ["shelling by hand", "blanching", "peeling the skins", "mashing with oil"], ["broad bean mash on toast", "broad bean salad", "broad bean soup"], "toast by the window"),
    ("new potato", "garden", "summer", "digging new potatoes from the garden soil", ["rinsing in a bucket", "boiling with mint", "tossing in butter", "mixing a dressing"], ["buttered new potatoes", "potato salad", "potato and herb pie"], "potatoes and butter by the window"),
    ("strawberry", "garden", "summer", "picking strawberries from the garden bed", ["rinsing", "hulling by hand", "simmering with sugar", "whisking cream"], ["strawberry jam", "strawberry shortcake", "strawberries and cream"], "cake at dusk with the window open"),
    ("gooseberry", "garden", "summer", "picking gooseberries from thorny bushes", ["topping and tailing by hand", "simmering", "mashing", "folding into cream"], ["gooseberry fool", "gooseberry crumble", "gooseberry jam"], "fool in a glass by the window"),
    ("redcurrant", "garden", "summer", "picking red currants strand by strand", ["stripping with a fork", "simmering", "straining", "pouring into jars"], ["redcurrant jelly", "redcurrant cake", "currant syrup"], "jelly on warm scones"),
    ("courgette", "garden", "summer", "cutting courgettes and yellow flowers in the garden", ["rinsing", "grating by hand", "squeezing dry", "mixing batter"], ["courgette fritters", "courgette bread", "stuffed courgette flowers"], "fritters on the doorstep"),
    ("tomato", "garden", "summer", "picking sun-warm tomatoes in the greenhouse", ["rinsing", "tearing", "slow-roasting with herbs", "simmering sauce"], ["tomato soup", "tomato tart", "tomato salad"], "soup with bread at dusk"),
    ("cucumber", "garden", "summer", "picking cucumbers from the vines", ["rinsing", "slicing already done", "mixing with yogurt and dill", "layering in a jar"], ["cucumber salad", "cool soup", "quick pickles"], "a cool plate at dusk"),
    ("runner bean", "garden", "summer", "picking runner beans from the tall wigwam", ["rinsing", "snapping by hand", "boiling", "tossing in butter"], ["buttered beans", "bean and potato salad", "bean chutney"], "a plate by the window"),
    ("sweet pea and herbs", "garden", "summer", "picking herbs and sweet peas for the table", ["rinsing", "tearing herbs", "mixing into butter", "toasting bread"], ["herb butter", "herb omelette", "herb salad"], "a herb supper by the window"),
    ("hen eggs", "garden", "summer", "collecting warm eggs from the hens' straw", ["rinsing", "cracking into a bowl", "whisking", "cooking slowly in butter"], ["soft scrambled eggs", "egg and herb tart", "custard"], "eggs on toast at dusk"),
    ("beetroot", "garden", "summer", "pulling purple beetroot from the garden", ["scrubbing in a bucket", "boiling", "rubbing off skins by hand", "mixing with yogurt"], ["beetroot salad", "beetroot soup", "beetroot cake"], "pink soup by the window"),
    ("pumpkin", "garden", "autumn", "carrying a ripe pumpkin from the vines", ["scooping seeds by hand", "roasting in pieces", "mashing", "simmering soup"], ["pumpkin soup", "roast pumpkin seeds", "pumpkin pie"], "soup with bread by the window at dusk"),
    ("apple", "garden", "autumn", "picking apples in the old orchard", ["rinsing", "peeling already done", "simmering with cinnamon", "rolling pastry"], ["apple pie", "apple sauce", "baked apples"], "warm pie at dusk"),
    ("pear", "garden", "autumn", "picking pears from the old tree", ["rinsing", "poaching in spiced wine", "folding into batter", "baking"], ["poached pears", "pear cake", "pear jam"], "poached pear with cream by the window"),
    ("plum", "garden", "autumn", "picking plums from the orchard wall", ["rinsing", "halving by hand", "roasting with sugar", "folding into a tart"], ["plum tart", "roast plums", "plum jam"], "tart at dusk"),
    ("leek", "garden", "autumn", "pulling leeks from the garden bed", ["washing carefully", "slicing already done", "melting in butter", "simmering"], ["leek and potato soup", "leek tart", "braised leeks"], "soup by the window"),
    ("kale", "garden", "autumn", "cutting dark kale leaves after a frost", ["washing", "tearing off stems", "massaging with oil", "simmering"], ["kale soup", "crispy kale", "kale and potato bake"], "soup at dusk"),
    ("carrot", "garden", "autumn", "pulling sweet carrots from the soil", ["scrubbing", "roasting with herbs", "mashing", "simmering soup"], ["roast carrots", "carrot soup", "carrot cake"], "roast carrots by the window"),
    ("squash", "garden", "autumn", "carrying small squashes in from the garden", ["scooping seeds", "roasting", "mashing", "stuffing"], ["stuffed squash", "squash soup", "squash and sage pasta"], "supper at the window at dusk"),
    ("sweetcorn", "garden", "autumn", "snapping sweetcorn from tall stalks", ["husking", "boiling", "buttering", "stripping kernels by hand"], ["buttered corn", "corn chowder", "corn bread"], "corn by the window at dusk"),
    ("brussels sprout", "garden", "winter", "snapping sprouts from the frosty stalk", ["rinsing", "trimming by hand", "roasting", "tossing with chestnuts"], ["roast sprouts", "sprout and chestnut mix", "sprout soup"], "a winter plate by the stove"),
    ("parsnip", "garden", "winter", "lifting parsnips from the frozen ground", ["scrubbing", "roasting with honey", "mashing", "simmering soup"], ["roast parsnips", "parsnip soup", "parsnip cake"], "soup by the fire"),
    ("jerusalem artichoke", "garden", "winter", "digging knobbly artichokes from the cold soil", ["scrubbing", "roasting", "peeling by hand", "simmering soup"], ["artichoke soup", "roast artichokes", "artichoke mash"], "soup by the stove"),
    ("winter cabbage", "garden", "winter", "cutting a frosty cabbage from the garden", ["washing", "tearing leaves", "braising with apple", "simmering soup"], ["braised cabbage", "cabbage soup", "cabbage and potato bake"], "braise by the stove"),
    ("celeriac", "garden", "winter", "lifting a round celeriac from the soil", ["scrubbing", "peeling already done", "roasting", "mashing"], ["celeriac soup", "roast celeriac", "celeriac mash"], "soup at dusk"),
    ("winter herbs", "garden", "winter", "cutting rosemary, thyme and sage in the frost", ["rinsing", "bruising in a mortar", "mixing with butter", "rubbing on bread"], ["herb butter", "herb bread", "herb tea"], "warm herb bread by the stove"),
    ("garden potato", "garden", "autumn", "digging potatoes with a fork", ["brushing clean", "baking in the oven", "mashing", "stirring a soup"], ["baked potatoes", "potato soup", "potato cakes"], "baked potatoes by the stove"),
    # bake
    ("blackberry and apple pie", "bake", "autumn", "picking blackberries and windfall apples", ["rinsing", "rolling out pastry", "filling a deep dish", "baking until golden"], ["a double fruit pie", "a small tart", "pastry leaves"], "warm pie and tea by the window"),
    ("bread from the garden", "bake", "spring", "picking herbs and chives from the garden", ["mixing the dough", "kneading by hand", "proving by the stove", "baking"], ["herb bread", "herb rolls", "herb butter"], "warm bread at dusk"),
    ("elderflower cake", "bake", "spring", "cutting elderflower heads", ["steeping in syrup", "whisking batter", "baking", "glazing"], ["elderflower sponge", "elderflower biscuits", "syrup drizzle"], "cake and tea at the window"),
    ("rhubarb tart", "bake", "spring", "pulling pink rhubarb", ["roasting", "rolling pastry", "arranging in a tin", "baking"], ["rhubarb tart", "rhubarb muffins", "rhubarb custard"], "tart by the window at dusk"),
    ("herb scones", "bake", "spring", "picking herbs and eggs", ["rubbing butter into flour", "bringing to a dough", "cutting rounds already done", "baking"], ["herb scones", "cheese scones", "butter and jam"], "scones warm from the oven"),
    ("strawberry shortcake", "bake", "summer", "picking strawberries", ["whisking cream", "rubbing butter into flour", "baking", "layering"], ["shortcake", "strawberry cream sponge", "strawberry jam tart"], "cake at dusk with the window open"),
    ("gooseberry pie", "bake", "summer", "picking gooseberries", ["topping and tailing", "rolling pastry", "filling a tin", "baking"], ["gooseberry pie", "gooseberry crumble", "gooseberry custard"], "pie in the warm light"),
    ("lavender shortbread", "bake", "summer", "picking lavender from the border", ["stripping flowers", "creaming butter and sugar", "pressing the dough", "baking"], ["lavender shortbread", "lavender sugar", "lavender tea"], "biscuits and tea at dusk"),
    ("cherry clafoutis", "bake", "summer", "picking cherries from the tree", ["rinsing", "whisking batter", "arranging in a dish", "baking"], ["cherry clafoutis", "cherry jam", "cherry compote"], "warm clafoutis by the window"),
    ("plum cake", "bake", "summer", "picking plums", ["halving by hand", "whisking batter", "arranging in a tin", "baking"], ["plum cake", "plum jam", "plum compote"], "cake and tea at dusk"),
    ("apple cake", "bake", "autumn", "picking windfall apples", ["peeling already done", "whisking batter", "layering in a tin", "baking"], ["apple cake", "apple sauce", "apple crumble"], "warm cake by the window"),
    ("pear and walnut loaf", "bake", "autumn", "picking pears and gathering walnuts", ["cracking nuts", "mixing batter", "pouring into a tin", "baking"], ["pear loaf", "walnut biscuits", "pear compote"], "loaf and tea at dusk"),
    ("pumpkin bread", "bake", "autumn", "carrying in a small pumpkin", ["roasting", "mashing", "mixing batter", "baking"], ["pumpkin bread", "pumpkin muffins", "roast seeds"], "warm bread with butter"),
    ("chestnut cake", "bake", "autumn", "gathering sweet chestnuts", ["roasting", "peeling by hand", "mashing to puree", "baking"], ["chestnut cake", "chestnut cookies", "chestnut cream"], "cake by the window"),
    ("hazelnut biscuits", "bake", "autumn", "gathering hazelnuts", ["cracking by hand", "toasting", "grinding", "baking"], ["hazelnut biscuits", "nut bars", "hazelnut spread"], "biscuits and tea at dusk"),
    ("mushroom pie", "bake", "autumn", "picking mushrooms in the wood", ["brushing clean", "frying in butter", "rolling pastry", "baking"], ["mushroom pie", "mushroom pasty", "mushroom soup"], "pie at the window"),
    ("apple pie", "bake", "autumn", "picking apples in the orchard", ["rinsing", "simmering with spice", "rolling pastry", "baking"], ["apple pie", "apple turnovers", "apple compote"], "pie with cream at dusk"),
    ("soda bread", "bake", "winter", "fetching eggs and herbs", ["mixing the dough", "shaping by hand", "scoring already done", "baking"], ["soda bread", "herb butter", "soup"], "bread and soup at dusk"),
    ("gingerbread", "bake", "winter", "fetching honey and spices from the pantry", ["mixing the dough", "pressing into a tin", "baking", "dusting"], ["gingerbread", "ginger biscuits", "spiced tea"], "gingerbread by the fire"),
    ("cinnamon buns", "bake", "winter", "fetching butter and spices", ["mixing yeast dough", "kneading by hand", "rolling with cinnamon", "baking"], ["cinnamon buns", "sticky buns", "spiced tea"], "buns by the stove"),
    ("oat biscuits", "bake", "winter", "fetching oats and butter", ["mixing", "pressing into a tray", "baking", "dusting"], ["oat biscuits", "flapjacks", "porridge"], "biscuits and tea by the fire"),
    ("winter fruit loaf", "bake", "winter", "fetching dried fruit from the pantry", ["soaking fruit in tea", "mixing batter", "pouring into a tin", "baking"], ["fruit loaf", "fruit buns", "spiced tea"], "loaf by the stove"),
    ("bread and soup", "bake", "winter", "digging roots from the cold garden", ["mixing the dough", "kneading by hand", "baking", "simmering soup"], ["crusty bread", "root soup", "butter"], "bread and soup by the fire"),
    ("lemon drizzle", "bake", "spring", "picking the first herbs and fetching eggs", ["zesting by hand", "whisking batter", "baking", "drizzling syrup"], ["lemon cake", "lemon biscuits", "lemon tea"], "cake at the window"),
    # preserve
    ("strawberry jam", "preserve", "summer", "picking strawberries in the garden", ["rinsing", "hulling by hand", "simmering with sugar", "pouring into hot jars"], ["strawberry jam", "jam tarts", "strawberry sauce"], "jam on warm toast at dusk"),
    ("raspberry jam", "preserve", "summer", "picking raspberries from the canes", ["rinsing", "mashing", "simmering with sugar", "pouring into hot jars"], ["raspberry jam", "raspberry vinegar", "jam tarts"], "jam on warm bread at dusk"),
    ("rose petal jam", "preserve", "summer", "picking rose petals at dawn", ["rinsing petals", "rubbing with sugar", "simmering", "jarring"], ["rose jam", "rose syrup", "rose tea"], "jam on toast by the window"),
    ("pickled beetroot", "preserve", "summer", "pulling beetroot", ["scrubbing", "boiling", "rubbing off skins", "pouring brine into jars"], ["pickled beetroot", "beetroot relish", "beetroot soup"], "jars on the pantry shelf"),
    ("herb vinegar", "preserve", "summer", "picking tarragon, thyme and chives", ["rinsing", "bruising", "packing a bottle", "pouring vinegar"], ["herb vinegar", "herb oil", "dried herb bundles"], "bottles in the window light"),
    ("dried herbs", "preserve", "summer", "cutting bundles of thyme, mint and sage", ["rinsing", "tying with string", "hanging from the beam", "crumbling into jars"], ["dried herb jars", "herb tea", "herb salt"], "a row of jars on the shelf"),
    ("cucumber pickles", "preserve", "summer", "picking small cucumbers", ["rinsing", "packing jars with dill", "pouring warm brine", "sealing"], ["dill pickles", "quick pickles", "pickle relish"], "jars on the shelf at dusk"),
    ("peach and plum chutney", "preserve", "summer", "picking plums and herbs", ["halving by hand", "simmering with spices", "stirring", "pouring into jars"], ["plum chutney", "plum jam", "spiced plums"], "chutney with cheese on bread"),
    ("blackberry jam", "preserve", "autumn", "picking blackberries in the lane", ["rinsing", "simmering with sugar", "testing on a cold saucer", "pouring into jars"], ["blackberry jam", "blackberry syrup", "jam tarts"], "jam on warm bread at dusk"),
    ("apple jelly", "preserve", "autumn", "gathering windfall apples", ["rinsing", "simmering", "dripping through muslin", "boiling with sugar"], ["apple jelly", "apple butter", "apple sauce"], "jelly on toast"),
    ("green tomato chutney", "preserve", "autumn", "picking the last green tomatoes", ["rinsing", "simmering with spices", "stirring", "pouring into jars"], ["tomato chutney", "tomato relish", "cheese and chutney bread"], "chutney with bread and cheese"),
    ("sloe gin syrup", "preserve", "autumn", "picking sloes", ["pricking with a pin", "layering with sugar", "pouring into a jar", "shaking"], ["sloe syrup", "sloe jelly", "sloe cordial"], "a jar glowing on the shelf"),
    ("pickled walnuts", "preserve", "autumn", "gathering green walnuts", ["rinsing", "soaking in brine", "packing in jars", "sealing"], ["pickled walnuts", "walnut relish", "nut bread"], "jars on the pantry shelf"),
    ("apple butter", "preserve", "autumn", "picking apples", ["rinsing", "simmering slowly", "stirring with spice", "pouring into jars"], ["apple butter", "spiced apples", "apple jam"], "apple butter on warm toast"),
    ("pickled red cabbage", "preserve", "autumn", "cutting a red cabbage", ["rinsing", "shredding already done", "packing in jars", "pouring spiced brine"], ["pickled red cabbage", "red cabbage soup", "cabbage salad"], "jars on the shelf"),
    ("pear jam", "preserve", "autumn", "picking pears", ["rinsing", "simmering with ginger", "stirring", "jarring"], ["pear jam", "pear butter", "spiced pears"], "jam on toast at dusk"),
    ("pumpkin chutney", "preserve", "autumn", "carrying in a pumpkin", ["scooping seeds", "simmering with spices", "stirring", "pouring into jars"], ["pumpkin chutney", "pumpkin jam", "roast seeds"], "chutney with bread and cheese"),
    ("marmalade", "preserve", "winter", "fetching bitter oranges", ["squeezing by hand", "soaking peel overnight", "simmering with sugar", "pouring into hot jars"], ["orange marmalade", "marmalade cake", "orange tea"], "marmalade on warm toast by the stove"),
    ("lemon curd", "preserve", "winter", "fetching eggs and lemons", ["zesting", "whisking over warm water", "thickening", "pouring into jars"], ["lemon curd", "curd tarts", "curd on scones"], "curd on warm toast"),
    ("winter jam", "preserve", "winter", "fetching frozen summer berries", ["thawing", "simmering with sugar", "stirring", "pouring into jars"], ["berry jam", "jam tarts", "berry sauce"], "jam on toast by the fire"),
    ("spiced apple rings", "preserve", "winter", "fetching stored apples", ["peeling already done", "threading on string", "drying by the stove", "packing in jars"], ["dried apple rings", "spiced apples", "apple tea"], "apple rings in a jar by the stove"),
    ("herb salt", "preserve", "winter", "cutting rosemary and thyme in the frost", ["rinsing", "drying on the stove", "pounding with salt", "filling jars"], ["herb salt", "herb butter", "herb oil"], "a jar on the shelf"),
    ("elderflower cordial jars", "preserve", "spring", "cutting elderflower", ["shaking out", "steeping with lemon", "straining", "bottling"], ["elderflower cordial", "elderflower jelly", "cordial ice"], "a cold glass at dusk"),
    ("rhubarb jam", "preserve", "spring", "pulling pink rhubarb", ["rinsing", "layering with sugar overnight", "simmering", "pouring into jars"], ["rhubarb jam", "rhubarb syrup", "rhubarb compote"], "jam on toast by the window"),
    ("wild garlic pesto", "preserve", "spring", "picking wild garlic", ["washing", "pounding in a mortar", "mixing with oil", "packing into jars"], ["wild garlic pesto", "garlic butter", "pesto toast"], "pesto toast at dusk"),
    ("pickled radishes", "preserve", "spring", "pulling radishes", ["rinsing", "packing jars", "pouring warm brine", "sealing"], ["pickled radishes", "radish relish", "radish salad"], "a jar and bread at dusk"),
]

COTTAGE_SETTINGS = [
    ("beech wood", "a small stone cottage with a green door at the edge of an old beech wood, a kitchen garden at the side"),
    ("hedgerow lane", "a whitewashed cottage down a narrow lane between high hedgerows, a wooden gate and a little garden"),
    ("kitchen garden", "a thatched cottage with a big walled-in kitchen garden of raised beds, bean wigwams and a greenhouse"),
    ("old orchard", "a timber-framed cottage in an old orchard of leaning apple trees with long grass underneath"),
    ("river meadow", "a stone cottage beside a clear slow river with a wet meadow and a footbridge"),
    ("heather moor edge", "a low stone cottage at the edge of a purple heather moor with a drystone wall"),
    ("pine forest", "a log cottage in a quiet pine forest with a clearing and a woodpile"),
    ("lake shore", "a small cottage on a calm lake shore with reeds and a wooden jetty"),
    ("chalk downland", "a flint cottage on chalk downland with rolling green hills and a winding path"),
    ("snowy wood", "a stone cottage in a snowy wood, smoke from the chimney and footprints in the garden"),
    ("wildflower meadow", "a white cottage beside a wildflower meadow with hives of flowers and a stone path"),
    ("walled garden", "a brick cottage beside an old walled garden with espaliered fruit trees and a potting shed"),
]

COTTAGE_THREADS = [
    ("first frost", "the first frost whitens the grass in the morning and the basket is lined with a cloth"),
    ("after the rain", "after a night of rain everything smells green and the ground is soft"),
    ("the last of the season", "the last of the year's crop: she picks it slowly and eats it with care"),
    ("grandmother's card", "she follows a handwritten recipe card from an old tin, step by step"),
    ("rain indoors", "rain comes at noon and the work moves to the kitchen table by the window"),
    ("first warm day", "the first warm day of the year: the door and windows are open all day"),
    ("Pip follows", "Pip the cat follows her through the whole day and waits for his share at the end"),
    ("picnic at the end", "she carries the finished food out to eat on a blanket at the end of the day"),
    ("jar for the winter shelf", "most of it goes into jars for the winter shelf; one small bowl is eaten today"),
    ("first snow", "the first snow of the winter falls softly all day"),
    ("the second try", "the first batch is not quite right; the second, slower one comes out well"),
    ("sound of the day", "the day is told through its sounds: leaves, water, the pot, the clock"),
]

COTTAGE_SEASON_OK = {"snowy wood": "winter", "wildflower meadow": "spring summer", "heather moor edge": "summer autumn",
                     "lake shore": "spring summer autumn"}
COTTAGE_THREAD_OK = {"first frost": "autumn winter", "first warm day": "spring summer", "first snow": "winter",
                     "picnic at the end": "spring summer autumn", "rain indoors": "spring summer autumn winter"}

COTTAGE_HOOKS = ["one quiet day of {key}", "{key}, picked and cooked at home", "a basket of {key} and a long evening",
                 "slow {season} with {key}", "everything from {key}", "{key}, start to finish"]


def build(subjects, settings, threads, season_ok, thread_ok, prefix, hooks, seed, hook_src):
    rng = random.Random(seed)
    ideas, n = [], 0
    combos = []
    for s in subjects:
        season = s[2]
        for sk, sd in settings:
            if season_ok.get(sk, "all") != "all" and season not in season_ok[sk]:
                continue
            for tk, td in threads:
                if tk in thread_ok and season not in thread_ok[tk]:
                    continue
                combos.append((s, (sk, sd), (tk, td)))
    rng.shuffle(combos)
    per_subject, seen_pair = {}, set()
    for s, st, th in combos:
        key = s[0]
        if per_subject.get(key, 0) >= 10 or (key, st[0]) in seen_pair or (key, th[0]) in seen_pair:
            continue
        per_subject[key] = per_subject.get(key, 0) + 1
        seen_pair |= {(key, st[0]), (key, th[0])}
        n += 1
        key_, kind, season, src, stages, results, enjoy = s
        hook = rng.choice(hooks).format(src=hook_src(src), key=key_, season=season)
        ideas.append({
            "id": f"{prefix}-{n:04d}", "subject": key_, "kind": kind, "season": season, "setting": st[0],
            "place": st[1], "thread": th[0], "thread_text": th[1], "source": src, "work": stages,
            "results": results, "enjoy": enjoy,
            "chapters": ["the source: " + src] + stages[:3] + ["the table: " + enjoy],
            "hook": hook, "title": f"{key_.title()} · {st[0]}",
        })
        if n == 1000:
            break
    return ideas


def write(ideas, out, n_subjects):
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(ideas, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(ideas)} ideas from {n_subjects} subjects -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", choices=["countryside", "cottage", "all"], default="all")
    a = ap.parse_args()
    if a.bank in ("countryside", "all"):
        write(build(SUBJECTS, SETTINGS, THREADS, SEASON_OK, THREAD_OK, "ft", HOOKS, 1001,
                    lambda src: src.split(" ")[-1]), OUT, len(SUBJECTS))
    if a.bank in ("cottage", "all"):
        write(build(COTTAGE_SUBJECTS, COTTAGE_SETTINGS, COTTAGE_THREADS, COTTAGE_SEASON_OK, COTTAGE_THREAD_OK,
                    "fc", COTTAGE_HOOKS, 2002, lambda src: src), COTTAGE_OUT, len(COTTAGE_SUBJECTS))


if __name__ == "__main__":
    main()
