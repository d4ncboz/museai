#!/usr/bin/env python3
"""Build ../ideas/ideas.json: 1000 field-to-table day plans (subject x setting x thread), each a whole arc
from the source (field, hill, stream, tree) through the work to the meal or the finished thing.

  python3 gen_ideas.py            rewrite ideas.json (stable ids: same input -> same ids)

Subjects are the heart (what the hands do for 12 minutes); settings and threads vary the place and the
small reason the day matters. Every subject lists only work muse films well: no knives on screen (things are
already cut, or split by hand, pounded, pressed, poured), no other people, no live animals killed or handled.
"""
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "ideas" / "ideas.json"

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


def main():
    rng = random.Random(1001)
    ideas, n = [], 0
    combos = []
    for s in SUBJECTS:
        key, kind, season = s[0], s[1], s[2]
        for sk, sd in SETTINGS:
            if SEASON_OK[sk] != "all" and season not in SEASON_OK[sk]:
                continue
            for tk, td in THREADS:
                if tk in THREAD_OK and season not in THREAD_OK[tk]:
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
        hook = rng.choice(HOOKS).format(src=src.split(" ")[-1], key=key_, season=season)
        ideas.append({
            "id": f"ft-{n:04d}", "subject": key_, "kind": kind, "season": season, "setting": st[0],
            "place": st[1], "thread": th[0], "thread_text": th[1], "source": src, "work": stages,
            "results": results, "enjoy": enjoy,
            "chapters": ["the source: " + src] + stages[:3] + ["the table: " + enjoy],
            "hook": hook, "title": f"{key_.title()} · {st[0]}",
        })
        if n == 1000:
            break
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(ideas, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(ideas)} ideas from {len(SUBJECTS)} subjects -> {OUT}")


if __name__ == "__main__":
    main()
