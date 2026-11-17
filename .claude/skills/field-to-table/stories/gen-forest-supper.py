import json

E = ["ELLIE"]
light = {
    "morning": "Early morning in late November, soft cool grey daylight, thin mist between the trees.",
    "late morning": "Late morning in late November, bright soft overcast daylight.",
    "afternoon": "Afternoon in late November, soft low sun through the window, clear and bright, not golden.",
    "dusk": "Dusk in late November, soft blue fading daylight outside and one plain warm lamp on inside; everything clearly visible.",
}
outfits = {
    "walk": "a long oatmeal wool coat over a cream chunky-knit cardigan, a rust knitted scarf, dark-green rubber boots",
    "kitchen": "a cream chunky-knit cardigan with the sleeves pushed to the forearm over a white linen blouse, a faded olive linen apron",
    "supper": "a cream chunky-knit cardigan over a white linen blouse",
}
places = {
    "woods": "an old beech and oak wood just behind the village in late autumn: copper-brown beech leaves thick on the ground, mossy roots and fallen logs, a narrow earth path, a small clear brook over flat grey stones, thin mist between tall grey trunks",
    "garden": "a small cottage kitchen garden in late November: raised wooden beds of leeks, kale and parsley, a wet gravel path, an old apple tree with a few last red apples, a little wooden hen house with three brown hens behind wire, a low mossy dry-stone wall, the grey stone cottage with a sage-green back door",
    "kitchen": "a small plain cottage kitchen: a white butler sink under a small-paned window onto the garden, a pale oak worktop, a sage-green range cooker, cream wall tiles, one wooden shelf with a few plain glass jars",
    "table": "a small round pale-oak table by the kitchen window, two plain wooden chairs, the garden outside the small-paned window, a plain lamp with a linen shade on the sill",
}
refs = {
    "woods": {"kind": "place", "brief": "The beech wood empty, nobody in it, seen from the narrow path: tall grey beech trunks, copper leaves on the ground, a fallen mossy log, the small brook to one side. Soft grey morning light with thin mist."},
    "garden": {"kind": "place", "brief": "The kitchen garden empty, nobody in it, seen from the back door: the raised beds of leeks and kale, the gravel path, the apple tree with a few red apples, the little hen house, the dry-stone wall. Bright soft overcast daylight."},
    "kitchen": {"kind": "place", "brief": "The kitchen empty, nobody in it, seen from the doorway: the butler sink under the small-paned window, the oak worktop, the sage-green range cooker with a cream enamel pot on it. Bright soft daylight."},
    "table": {"kind": "place", "brief": "The small round oak table by the kitchen window, empty, two chairs, the garden outside the window, a plain lamp with a linen shade on the sill. Soft daylight."},
    "the basket": {"kind": "prop", "brief": "A round willow basket with a handle, lined with a faded blue-and-white checked cloth, empty, standing on a pale oak worktop. Soft daylight."},
    "Pip": {"kind": "prop", "brief": "Pip the cat sitting upright on a pale oak kitchen floor, looking slightly to the side, full body in view, soft daylight."},
}
B = []


def c(ch, w, t, o, cast, shot, move, px=0.5, py=0.5, **kw):
    B.append(dict(ch=ch, where=w, time=t, outfit=o, kind="clip", cast=cast, shot=shot, move=move, _p=(px, py), **kw))


def s(ch, w, t, shot, hold=3.5, **kw):
    B.append(dict(ch=ch, where=w, time=t, kind="still", cast=[], shot=shot, hold=hold, **kw))


# i. the wood
s(1, "woods", "morning", "Wide empty landscape of the beech wood in the early mist from the path, no woman and no person anywhere: tall grey trunks fading into the mist, copper leaves thick on the ground, the empty path.", 5.0, chapter=True)
c(1, "garden", "morning", "walk", E, "Ellie seen from behind at the sage-green back door of the cottage, the empty willow basket on her arm, pulling the door closed.", "She pulls the door closed with a soft click of the latch and turns toward the garden path; the camera stays locked off.", props=["the basket"])
c(1, "woods", "morning", "walk", E, "Ellie seen from behind, small in the frame, walking slowly along the narrow path between the grey beech trunks, the basket on her arm.", "She walks slowly away along the path through the mist with soft steps on dry leaves; the trees and the camera stay perfectly still.", 0.5, 0.55, props=["the basket"])
c(1, "woods", "morning", "walk", [], "Close-up of the leaf-covered path: her dark-green rubber boots stepping slowly through copper beech leaves.", "Her boots take two slow steps through the leaves with a dry rustle; the leaves stay on the ground.")
s(1, "woods", "morning", "Close-up of a mossy fallen beech log in the mist, a cluster of small orange-yellow chanterelle mushrooms growing at its foot among the leaves.")
c(1, "woods", "morning", "walk", [], "Close-up of the forest floor: her hands in oatmeal wool coat sleeves part the copper leaves and find a cluster of orange-yellow chanterelle mushrooms.", "Her fingers slowly push the leaves aside to show the chanterelles; the mushrooms stay in the ground.", 0.5, 0.6)
c(1, "woods", "morning", "walk", [], "Close-up of her hands in oatmeal wool coat sleeves twisting one orange-yellow chanterelle gently out of the moss.", "She slowly twists the chanterelle free and lifts it, a little soil and moss on its stem.")
c(1, "woods", "morning", "walk", [], "Top-down close-up of a round willow basket lined with blue-and-white checked cloth standing on the copper beech leaves of the forest floor outdoors, a small handful of orange-yellow chanterelles in it; her hand lays one more chanterelle in.", "Her hand lays the chanterelle in the basket and draws back out of frame; the others stay where they are.")
c(1, "woods", "morning", "walk", E, "Ellie seen from the side, crouching by a mossy oak root, her face bowed toward the ground, the basket beside her on the leaves.", "She slowly brushes the leaves at the root with one hand, head bowed; the camera stays still.", 0.45, 0.5, props=["the basket"])
c(1, "woods", "morning", "walk", [], "Close-up of a robin with a red breast perched on a mossy beech branch in the mist.", "The robin turns its head and hops once along the branch; the branch and the mist stay still.", 0.5, 0.45)
c(1, "woods", "morning", "walk", [], "Close-up of a fat brown cep mushroom with a pale stem standing in green moss under the oak; her hand in an oatmeal wool sleeve closes around its stem.", "Her hand slowly lifts the cep out of the moss with a soft tearing sound of moss.")
s(1, "woods", "morning", "Close-up of the brook in the beech wood: clear water over flat grey stones, a few copper leaves caught at the edge, mist above.")
c(1, "woods", "morning", "walk", [], "Close-up of the clear brook over flat grey stones, a few copper beech leaves turning slowly on the water.", "Only the water moves, rippling over the stones and carrying one leaf slowly downstream; nothing else moves and no one walks in.")
c(1, "woods", "morning", "walk", [], "Close-up of the ground under a hazel bush: brown hazelnuts among yellow leaves; her fingers in oatmeal wool sleeves pick up three hazelnuts one by one.", "Her fingers pick up the hazelnuts slowly with a small dry click of shells.", 0.5, 0.55)
c(1, "woods", "morning", "walk", [], "Close-up of a bramble at the edge of the wood with a few last dark blackberries; her fingers in oatmeal wool sleeves pick one and lay it into a small enamel cup.", "She picks one blackberry slowly and drops it into the cup with a soft tap.")
c(1, "woods", "morning", "walk", E, "Ellie seen from the side sitting on a fallen mossy log, the basket beside her, pouring tea from a steel flask into its cup, her head bowed.", "She pours slowly and a thin wisp of steam rises from the cup; the trees and the camera stay still.", 0.45, 0.5, props=["the basket"])
s(1, "woods", "morning", "Top-down close-up of a round willow basket lined with blue-and-white checked cloth standing on the copper beech leaves of the forest floor outdoors: orange-yellow chanterelles, two fat brown ceps, a handful of hazelnuts and a small enamel cup of blackberries on the cloth.", 4.0)
c(1, "woods", "morning", "walk", E, "Ellie seen from behind walking back out of the beech wood toward the light at the wood's edge, the full basket on her arm.", "She walks slowly away along the path; the mist and the trees stay still and the camera does not follow.", 0.5, 0.55, props=["the basket"])

# ii. the garden
s(2, "garden", "late morning", "Wide view of the kitchen garden in soft overcast light: the raised beds of leeks and kale, the gravel path, the apple tree with a few red apples, the hen house, nobody in it.", 5.0, chapter=True)
c(2, "garden", "late morning", "walk", [], "Close-up of the leek bed: her hands in oatmeal wool coat sleeves ease one tall leek out of the dark wet soil.", "She pulls the leek slowly up out of the soil, roots and a little earth hanging from it.")
c(2, "garden", "late morning", "walk", [], "Close-up of the parsley in the raised bed; her fingers in oatmeal wool sleeves pinch off a few curly parsley stems.", "Her fingers snap a few stems slowly and gather them in her palm.")
c(2, "garden", "late morning", "walk", [], "Close-up of the kale bed: her hands in oatmeal wool coat sleeves snap off two dark-green curly kale leaves.", "She snaps the leaves off slowly at the stem with a crisp sound.")
c(2, "garden", "late morning", "walk", E, "Ellie seen from behind under the old apple tree, reaching up to one of the last red apples on a bare branch.", "She reaches up slowly and twists the apple off the branch; the branch springs back a little; the camera stays locked off.", 0.5, 0.4)
c(2, "garden", "late morning", "walk", [], "Close-up of the open straw nest box of the little wooden hen house: two brown eggs in the straw; her hand in an oatmeal wool sleeve lifts one egg out.", "Her hand slowly lifts one egg out of the straw; the other egg stays where it is.")
c(2, "garden", "late morning", "walk", [], "Close-up of three brown hens pecking slowly on the wet gravel behind the wire of the hen house.", "The hens peck slowly at the gravel; the wire and the hen house stay still.", 0.5, 0.55)
s(2, "garden", "late morning", "Close-up of the willow basket set on the dry-stone wall, now full: chanterelles, ceps, hazelnuts, the cup of blackberries, a leek, curly parsley, two red apples and two brown eggs.", 4.0, props=["the basket"])
c(2, "garden", "late morning", "walk", E, "Ellie seen from behind walking up the wet gravel path to the sage-green back door with the full basket, Pip the cat trotting ahead of her.", "She walks two slow steps to the door and Pip slips in first; the camera stays still.", props=["the basket", "Pip"])

# iii. the kitchen
s(3, "kitchen", "afternoon", "Wide view of the bright kitchen with nobody in it: the full willow basket on the oak worktop by the butler sink, the garden through the small-paned window.", 5.0, chapter=True, props=["the basket"])
c(3, "kitchen", "afternoon", "kitchen", [], "Top-down close-up of the oak worktop: her hands in cream knit sleeves empty the basket, laying out the chanterelles, ceps, hazelnuts, leek, parsley, apples and eggs on the checked cloth.", "Her hands lay the last few things out slowly; each thing stays where she puts it.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the butler sink under the window: her hands in cream knit sleeves rinse the muddy leek under a thin stream of cold tap water.", "Water runs over the leek and the soil washes away slowly into the sink.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of a small soft brush in her hand brushing soil and a beech leaf off an orange-yellow chanterelle over a folded tea towel.", "She brushes the chanterelle slowly with short strokes; bits of soil fall on the towel.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of her hands in cream knit sleeves tearing a cleaned chanterelle into long strips with her fingers over a wooden board.", "Her fingers pull the mushroom apart slowly into strips that fall on the board.")
c(3, "kitchen", "afternoon", "kitchen", [], "Top-down close-up of a wooden board: the brown ceps already sliced into thick pale slices and the leek already sliced into green-and-white rings, in two neat piles; her hand gathers the leek rings.", "Her hand slowly sweeps the leek rings together into one pile.")
c(3, "kitchen", "afternoon", "kitchen", E, "Ellie seen from the side at the window worktop, head bowed, cracking hazelnuts with a small iron nutcracker into a white bowl.", "She squeezes the nutcracker slowly and a shell cracks; she drops the nut in the bowl; the camera stays still.", 0.45, 0.5)
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of Pip the cat sitting on the kitchen floor by the range cooker, watching up toward the worktop.", "Pip blinks slowly and his tail tip curls once; the kitchen stays still.", 0.5, 0.45, props=["Pip"])
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of a black cast-iron pan on the sage-green range: a pat of pale butter starts to melt and foam.", "The butter slides slowly and foams with a soft sizzle.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the black cast-iron pan: her hand in a cream knit sleeve tips the pale leek rings from the wooden board into the foaming butter.", "The leek rings slide into the pan with a loud sizzle and a little steam rises.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the cast-iron pan of soft pale-green leeks: her hand stirs them slowly with a wooden spoon.", "The wooden spoon turns the leeks slowly with a soft sizzle and a thin curl of steam.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the cast-iron pan: torn orange-yellow chanterelles and thick pale cep slices sizzling in butter with the soft leeks, just starting to turn golden at the edges.", "The mushrooms sizzle and shrink a little; steam rises slowly; the wooden spoon rests on the rim.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the cast-iron pan of golden mushrooms and leeks: her fingers sprinkle a pinch of coarse salt and a few thyme leaves over them.", "Salt and thyme fall slowly onto the sizzling mushrooms.")
s(3, "kitchen", "afternoon", "Close-up of the kitchen window: soft low afternoon sun on a few plain glass jars on the sill, the garden beyond the small panes.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of a cream enamel pot on the range: her hand in a cream knit sleeve tips the golden mushrooms and leeks from the cast-iron pan into the pot.", "The mushrooms slide into the pot with a soft scrape of the spoon.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the cream enamel pot of golden mushrooms: a jug pours pale stock over them.", "Stock pours slowly from the jug and steam starts to rise.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the cream enamel pot on the range: pale-brown mushroom soup bubbling gently, steam rising.", "The soup bubbles slowly and steam curls up; the pot stays still.")
c(3, "kitchen", "afternoon", "kitchen", [], "Close-up of the cream enamel pot of bubbling pale-brown mushroom soup: her hand drops torn dark-green kale leaves into it.", "The kale leaves sink slowly into the bubbling soup.")
c(3, "kitchen", "afternoon", "kitchen", E, "Ellie seen from behind at the sage-green range, head bowed over the cream enamel pot, stirring slowly with a wooden spoon.", "She stirs slowly; steam rises past her shoulder; the camera stays locked off.", 0.5, 0.45)

# iv. the oven
s(4, "kitchen", "afternoon", "Close-up of the oak worktop in soft low sun: two red apples with their cores already taken out on a small enamel dish, a white bowl of shelled hazelnuts and the cup of blackberries beside them.", 5.0, chapter=True)
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of her hands in cream knit sleeves crushing shelled hazelnuts with a stone mortar and pestle.", "The pestle crushes the nuts slowly with a dull grinding sound.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the small enamel dish of two cored red apples: her fingers press crushed hazelnuts and a few blackberries into the hollow of each apple.", "Her fingers press the filling in slowly; the apples stay on the dish.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the two filled red apples on the enamel dish: a spoon drips golden honey over the top of each.", "Honey runs slowly off the spoon and down the side of the apples.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the open oven door of the sage-green range: her hands in a faded quilted oven glove slide the enamel dish of filled apples onto the rack.", "She slides the dish in slowly and draws her hands back; the oven door stays open.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of a loaf of crusty sourdough bread on a wooden board, already sliced into thick slices; her hands lay two slices on a ridged cast-iron griddle on the range.", "She lays the slices down slowly and they start to sizzle softly.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the ridged cast-iron griddle: her fingers turn a thick slice of sourdough over to show dark toasted stripes.", "She turns the toast slowly; a little steam rises.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of a small white dish of soft butter: her hand stirs chopped parsley into it with a small spoon.", "The spoon folds the green parsley into the butter slowly.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of a small steel pan of simmering water on the range: a spoon lowers one brown egg into the water.", "The spoon lowers the egg slowly into the bubbling water and draws back.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of her hands in cream knit sleeves peeling a soft-boiled brown egg over a small white plate.", "Her fingers slowly peel the shell away in small pieces that fall on the plate.")
c(4, "kitchen", "afternoon", "kitchen", [], "Close-up of the open oven of the sage-green range: the two baked red apples on the enamel dish, skins wrinkled and split, purple blackberry juice bubbling in the dish.", "The juice bubbles slowly around the apples and a little steam drifts out; the dish stays still.", 0.5, 0.55)

c(4, "kitchen", "afternoon", "kitchen", E, "Ellie seen from the side at the window, head bowed, wiping her hands slowly on her olive linen apron while the soup steams on the range behind her.", "She wipes her hands slowly and looks down at the garden; the camera stays still.", 0.45, 0.45)

# v. supper
s(5, "garden", "dusk", "Wide view of the grey stone cottage from the kitchen garden at blue dusk: one warm lit window, the bare apple tree, nobody outside.", 5.0, chapter=True)
c(5, "table", "dusk", "supper", [], "Close-up of the round oak table by the dark window: her hands in cream knit sleeves set down a white bowl and a plain spoon on a linen napkin.", "She sets the bowl down slowly and straightens the spoon; the lamp light stays steady.")
c(5, "kitchen", "dusk", "supper", [], "Close-up of the cream enamel pot on the range: a ladle in her hand lifts pale-brown mushroom soup and pours it into a white bowl.", "The soup pours slowly from the ladle into the bowl and steam rises.")
c(5, "table", "dusk", "supper", [], "Top-down close-up of the white bowl of pale-brown mushroom soup with golden chanterelles on top: her fingers scatter torn parsley and a swirl of cream.", "The cream sinks slowly into the soup in a swirl; steam rises.")
c(5, "table", "dusk", "supper", [], "Close-up of a thick slice of toasted sourdough on a small plate: her hand spreads green parsley butter on it with a butter spreader, a peeled soft-boiled egg halved on the plate beside it.", "The butter melts slowly into the warm toast as she spreads it.")
s(5, "table", "dusk", "Top-down view of the round oak table at dusk: the bowl of mushroom soup with steam, the toast with green butter and a halved soft-boiled egg, a baked apple in a small dish with purple juice, a glass of water, the lamp light from the side.", 5.0)
c(5, "table", "dusk", "supper", E, "Ellie seen from behind and a little to the side, sitting down at the round oak table by the window, the dusk garden blue outside.", "She sits down slowly and pulls her chair in; the lamp and the window stay still; the camera stays locked off.")
c(5, "table", "dusk", "supper", [], "Close-up of the white bowl of mushroom soup: a spoon dips in and lifts a golden chanterelle and soup.", "The spoon lifts slowly out of the soup and out of frame; steam rises.")
c(5, "table", "dusk", "supper", [], "Close-up of her hands in cream knit sleeves tearing the buttered toast in two over the plate.", "The toast tears slowly with a soft crunch; a few crumbs fall.")
c(5, "table", "dusk", "supper", [], "Close-up of Pip the cat curled on the second wooden chair at the table, the lamp light on his fur.", "Pip breathes slowly and his ear twitches once; nothing else moves.", props=["Pip"])
c(5, "table", "dusk", "supper", [], "Close-up of the baked red apple in a small white dish, purple blackberry juice around it: a spoon breaks into the soft apple and the hazelnut filling.", "The spoon slowly breaks the soft apple open and steam rises from inside.")
c(5, "table", "dusk", "supper", E, "Ellie seen from behind at the table by the dark window, her head bowed over the bowl, holding the warm bowl in both hands.", "She lifts the bowl a little in both hands and holds it; the window and lamp stay still.", 0.5, 0.45)
s(5, "table", "dusk", "Close-up of the table after supper: the empty white bowl with the spoon in it, a few crumbs on the plate, the empty apple dish, lamp light from the side.", 4.0)
c(5, "garden", "dusk", "supper", [], "Wide view of the cottage window from the dark garden: the warm lit window, the bare apple tree in the foreground, nobody outside.", "Only the bare branches sway a little in the breeze; nobody walks in; the camera stays still.", 0.55, 0.45)
c(5, "table", "dusk", "supper", E, "Ellie seen from behind standing at the dark kitchen window after supper, holding a mug of tea in both hands, the blue garden outside.", "She lifts the mug slowly and a thin wisp of steam rises; the window and the lamp stay still; the camera stays locked off.", 0.5, 0.45)

beats = []
for b in B:
    px, py = b.pop("_p", (0.5, 0.5))
    if b["kind"] == "clip":
        b["cuts"] = [[0.3, 4.6], [5.0, 4.4, 1.32, px, py]]
    if not b["cast"]:
        b.pop("cast")
    beats.append(b)
beats[-1]["cuts"] = [[0.3, 4.6], [5.0, 4.8, 1.25, 0.5, 0.45]]


def find(word):
    return next(i for i, b in enumerate(beats, 1) if word in b["shot"])


story = {
    "story_id": "forest-supper", "slug": "forest-supper", "title": "an empty basket",
    "eyebrow": "a november day", "season": "late autumn", "xf": 0.4,
    "light": light, "outfits": outfits, "places": places, "refs": refs,
    "chapters": [
        {"n": 1, "title": "i.  the wood", "sub": "chanterelles, ceps, hazelnuts"},
        {"n": 2, "title": "ii.  the garden", "sub": "a leek, two apples, two eggs"},
        {"n": 3, "title": "iii.  the kitchen", "sub": "mushroom soup"},
        {"n": 4, "title": "iv.  the oven", "sub": "baked apples, toast"},
        {"n": 5, "title": "v.  supper", "sub": "everything we found"}],
    "beats": beats,
}
story["teaser"] = {
    "text": "I walked into the woods with an empty basket. This is what we had for dinner.", "text_secs": 5.5,
    "shots": [[find("a ladle in her hand"), 1.5, 3.0], [find("twisting one orange-yellow chanterelle"), 1.0, 2.6, 1.2, 0.5, 0.5],
              [find("tips the pale leek rings"), 0.8, 2.6], [find("purple blackberry juice bubbling"), 1.0, 2.6],
              [find("walking slowly along the narrow path"), 1.0, 2.8], [find("lifts a golden chanterelle"), 1.0, 2.6],
              [find("Pip the cat curled"), 1.0, 2.4], [find("sitting down at the round oak table"), 2.0, 3.6]]}
story["short"] = {
    "text": "what one November wood gave me for dinner",
    "shots": [[find("twisting one orange-yellow chanterelle"), 0.5, 2.8, 0.5], [find("a fat brown cep"), 1.0, 2.4, 0.5],
              [find("tips the pale leek rings"), 0.8, 2.4, 0.5], [find("a ladle in her hand"), 1.5, 2.6, 0.5],
              [find("spoon breaks into the soft apple"), 1.0, 2.4, 0.5], [find("sitting down at the round oak table"), 2.0, 3.0, 0.5]]}
open("story.json", "w").write(json.dumps(story, indent=1, ensure_ascii=False) + "\n")
print(len(beats), "beats", sum(b["kind"] == "clip" for b in beats), "clips")
