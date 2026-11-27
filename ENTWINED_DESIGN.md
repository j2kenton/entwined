# Entwined — Game Design Doc (draft)

> **Status:** the full journey is built in `game/`. Section 10.4 is how it plays now and 10.5 is the story as it now stands; earlier sections are the history, and where they disagree with those two, those two win. This doc is still a working draft.
> Names marked *(placeholder)* are stand-ins until we pick real ones.
> **Platform:** a game that plays in the terminal, with truecolor pixel-art graphics.
> **Prototypes** (`prototype/`): concept art, a battle clip and a playable battle. They're for getting a feel only and aren't kept in sync with this doc.

---

## 1. The pitch

A classic-era creature-collecting adventure. You pick one of six heroes, each bonded to one element. You travel through the five other lands, beating each land's ruler in creature battles. Each ruler is impressed enough to join your quest. Then the six of you storm the **Obsidian Citadel**, where six villains wait, one for each hero. Every hero has to defeat their own **nemesis**, ending with yours.

Underneath, there's a mystery. The villains have suddenly become far stronger, and nobody knows why.

---

## 2. Core rules of the world

### 2.1 Bonding and elements
- As people grow up, they develop a bond with **one element**, matching their personality. A fiery person bonds with fire creatures, and so on.
- You can only train creatures of **your own element**. Everyone believes this is a law of nature.
- *(Side idea, out of scope for now: what about someone who never bonds?)*

### 2.2 The team limit: five
- How many creatures you can hold grows with age: about **1 as a small child**, **2 as a teenager**, up to **5 as an adult**. **Five is the maximum.**
- **Why five:** creatures of the same element are alike, and alike things clash. Keep more than five fire creatures together and they end up burning each other, and the place, down. Everyone who has tried has failed.
- This mirrors the heroes: **you and your nemesis were childhood best friends, but you were too alike.** You shared an element, fought over the same creatures, and fought over the same sweetheart.

### 2.3 The element wheel *(decided: your variant, with realism exceptions)*

```
   Wave → Flame → Root → Breeze → Soil → Lightning → (back to Wave)
```

The chart lives in `tools/element_wheel.py`. Change it there, re-run, and the script re-checks the design for all six heroes.

| Strong link | Why |
|---|---|
| Wave beats Flame | Water puts out fire |
| Flame beats Root | Fire burns plants |
| Root beats Breeze | A breeze only spreads seeds and helps plants grow; roots hold firm |
| Breeze beats Soil | Wind blows soil away |
| Soil beats Lightning | The ground earths lightning |
| Lightning beats Wave | Water conducts the shock |

**The base pattern** (attacker → defender, by steps around the wheel):

| Steps | Effect | Logic |
|---|---|---|
| +1 (next) | **Strong ×2** | I beat it directly |
| +2 | Slightly weak ×0.8 | **"My prey's prey bites back."** Wave beats Flame and Flame burns Root, but roots drink water. Likewise a channelled Breeze can blow out a Flame |
| +3 (opposite) | Even ×1 | Too different to matter |
| +4 | Slightly strong ×1.25 | The reverse of +2 |
| +5 (the one before) | **Weak ×0.5** | It beats me directly |
| Same element | Slightly weak ×0.8 | Alike things resist each other, so mirror matches (you vs your nemesis) are about tactics |

**Elements are about the person, not the strength.** Breeze sounds gentle, but a Breeze master channels it into gales; the move names carry the power (Gale Force, Cyclone…). Breeze is as strong overall as any other element (see the balance line below).

**Realism exceptions:** where reality disagrees with the pattern, reality wins.

| Pair | Pattern says | Actually | Why |
|---|---|---|---|
| Flame → Soil | Even | Slightly weak ×0.8 | Soil smothers flame |
| Soil → Flame | Even | Slightly strong ×1.25 | …so soil hits flame a little harder |
| Flame → Lightning | Slightly strong | Even ×1 | No real relationship |
| Soil → Soil | Slightly weak | Even ×1 | Rock on rock is fine |
| Breeze → Breeze | Slightly weak | Even ×1 | Wind can't really resist wind |
| Lightning → Lightning | Slightly weak | Weak ×0.5 | Storms swallow lightning |

**Full chart (draft):**

| Attacker ↓ / Defender → | Wave | Flame | Root | Breeze | Soil | Lightning |
|---|---|---|---|---|---|---|
| **Wave** | ×0.8 | **×2** | ×0.8 | ×1 | ×1.25 | *×0.5* |
| **Flame** | *×0.5* | ×0.8 | **×2** | ×0.8 | ×0.8 | ×1 |
| **Root** | ×1.25 | *×0.5* | ×0.8 | **×2** | ×0.8 | ×1 |
| **Breeze** | ×1 | ×1.25 | *×0.5* | ×1 | **×2** | ×0.8 |
| **Soil** | ×0.8 | ×1.25 | ×1.25 | *×0.5* | ×1 | **×2** |
| **Lightning** | **×2** | ×0.8 | ×1 | ×1.25 | *×0.5* | ×0.5 |

**Balance** (average attack across the others): Soil ×1.16, Wave/Root/Breeze/Lightning ×1.11, Flame ×1.02. Flame comes out a touch weaker because of the soil-smothers-flame rule. We could give it something back later.

**Checked against the design** (by script, for all six heroes):
- **The hybrid twist works for every hero.** The obvious counter to the form the hybrid shows backfires to *slightly weak* when it morphs, and the best available answer is an even fight. *(Exception: the Root hero's best answer, Soil, keeps a slight edge.)*
- **Every hero's hardest land is their wheel counter,** which is also their sweetheart's element. The other lands come in a different order for each hero.

### 2.4 Element names *(decided)*

| Element | Name | Why it works |
|---|---|---|
| Water | **Wave** | Water's own moving shape, the way a flame is fire's |
| Fire | **Flame** | The living body of fire |
| Nature | **Root** | The tough, living core of a plant |
| Air | **Breeze** | Air you can feel moving |
| Earth | **Soil** | Living ground, what roots grow in |
| Lightning | **Lightning** | Kept as itself for now (no symbolic alternative fits yet) |

Order on the wheel: **Wave → Flame → Root → Breeze → Soil → Lightning → (back to Wave)**

---

## 3. Cast (placeholders)

Six heroes: 3 male and 3 female. Each has a **home land**, a **nemesis** (same element, same sex, grew up together) and a **sweetheart** (opposite sex, bonded to the element that **beats** the hero's).

| Hero *(placeholder)* | Sex | Element | Home land | Nemesis | Sweetheart (element) |
|---|---|---|---|---|---|
| **Marisol**, sky-sailor | F | Wave | Tidewell Isles | Wavemaster Sable | Levin (Lightning) |
| **Kael**, blacksmith knight | M | Flame | Ember Peaks | Flamemaster Varek | Coral (Wave) |
| **Willow**, ranger | F | Root | Thornwood | Rootmaster Nettle | Flint (Flame) |
| **Soren**, cliff-runner | M | Breeze | Skyreach Spires | Breezemaster Corvin | Linnea (Root) |
| **Bram**, stonemason | M | Soil | Stonehollow | Soilmaster Dorn | Wren (Breeze) |
| **Juno**, storm-chaser | F | Lightning | Stormcrag Plateau | Lightningmaster Vesper | Garrick (Soil) |

- **All six sweethearts get built**, but only the chosen hero's sweetheart appears in the story. For the other heroes the sweetheart is neither confirmed nor denied: they're simply never mentioned (the "fog of war").
- **Every** hero has a nemesis in the Citadel, whoever you pick.

---

## 4. The journey

### 4.1 Land order adapts to your hero
You go through the five other lands **from the one you're strongest against to the one that's strongest against you**.

Example: **Marisol (Wave)**, using the chart in 2.3:

| Order | Land | Relative to you |
|---|---|---|
| 1 | Ember Peaks (Flame) | You're strong (easiest) |
| 2 | Stonehollow (Soil) | You're slightly strong |
| 3 | Skyreach Spires (Breeze) | Even |
| 4 | Thornwood (Root) | They're slightly strong |
| 5 | Stormcrag Plateau (Lightning) | They're strong (hardest), and it's her sweetheart's element |

So difficulty is about each land **relative to you**, not a fixed ranking. The order comes from the chart, comparing both directions, so every hero's journey is different.

### 4.2 The Masters *(keeping this name for now)*
- Each land is ruled by one of the other five heroes. Nobody crosses into the next land without beating that land's ruler in a creature battle.
- They **aren't waiting in a gym**. They can confront you anywhere on the road, and you don't know when.
- **On the journey you fight with your own creatures only.**
- **Losing:** you can retry. Allies already travelling with you can also take a shot at the Master. Masters get harder, but your party grows.
- **Winning:** the Master is impressed, you tell them about your quest, they ask to join, and **they join your party**.
- Rest is possible between lands, so **you heal up** between journeys.

### 4.3 The Master's comment after you win
A short, somewhat dynamic comment on what impressed them **about you and your creatures**. It comes in two parts:

1. **Specific:** about *why you won this battle*. For example:
   - Element advantage: "Your flames went straight through my vines. I never stood a chance."
   - Speed: "I couldn't keep up with you."
   - Toughness: "I hit you with everything and you were still standing."
   - Strategy: "You saw my switch coming before I'd made it."
   - Comeback: "You should've lost three times over."
2. **General:** respect for you and your element. For example, "You water folk are calmer than I gave you credit for."

> Details to be worked out later. Possible tie-in: what a Master admired in you echoes back in the Citadel.

### 4.4 Master gifts *(first draft)*
Every hero has a personal **gift**: a down-to-earth talent, not magic and not game-breaking. You start with your own. **When a Master joins you, their gift becomes available to the party.** Because the land order depends on your hero, each playthrough gets the gifts in a different order.

| Hero | Gift | What it does |
|---|---|---|
| Marisol (Wave) | **Navigator** | Reveals hidden paths, shortcuts and secret coves on the map |
| Kael (Flame) | **Forgemaster** | Forges and upgrades charms from materials you find |
| Willow (Root) | **Herbalist** | Gathers herbs in the wild and brews remedies, so healing is cheaper |
| Soren (Breeze) | **Lookout** | Spots rare creatures and ambushes before they spot you, including a moment's warning before a Master jumps out |
| Bram (Soil) | **Campbuilder** | Makes camp on the road (once per land): a rest and save point anywhere outside the Citadel |
| Juno (Lightning) | **Storm-reader** | Reads the weather, which gives small element boosts in battle (rain helps Wave, and so on) *(only if we add weather)* |

### 4.5 Items and the satchel *(first draft)*
- You carry a **satchel** *(or pack or knapsack; something that fits the era)* with **limited slots** (say 8 slots, up to 3 of the same item per slot). Deciding what to bring is part of the strategy.
- **Kinds of item:**
  - **Remedies:** restore health. They're herbal, not magic, and **can't revive a fainted creature.** Nothing can, except rest.
  - **Tonics:** clear effects like smoke or burns.
  - **Charms:** a boost for one battle, e.g. a Wave charm makes Wave moves hit harder.
  - **Lures:** attract particular wild creatures.
  - **Curios:** quest items and keys.
- **Using an item in battle takes your turn,** as in the classics.
- **Getting items:** markets in each land's towns, Kael's forge, Willow's herbs, and loot. *(Open: what's the currency? Coins, traded materials, Rift shards…)*
- **When it's too hard,** you go back and train, restock, or change tactics. That's the classic loop.

---

## 5. The mystery

- The villains have always raided neighbouring lands, and the lands have always held them off.
- **Recently they've been surprisingly successful,** and nobody knows why. That's what gets the quest going: you have to stop them before they grow too strong.
- On the journey there are **subtle hints** only.
- **Reveal 1 (first Citadel fight):** the villains have learned to train a **sixth creature of a different element**, which breaks both "laws".
  - **Why the sixth works:** a creature of a *stronger* element becomes the **master creature**. It keeps the five same-element creatures in check, so the team doesn't burn itself apart.
  - **How** they learned to train another element is still unknown. *(Open: we haven't decided this yet.)*
- **Reveal 2 (the final fight):** your nemesis has gone further and **bred a hybrid**.

---

## 6. The Obsidian Citadel

### 6.1 Structure
- The whole party breaks in together.
- There's one floor per ally, **in the order you met them**, with your own nemesis at the top.
- Each floor holds one ally's **nemesis**, of the same element as that ally. Each hero knows their own nemesis's weaknesses from growing up together, so going in, everyone is confident.

### 6.2 No rest
- **Health carries over from floor to floor.** You can't rest once you're inside.
- Allies can **step in** to help, as often as needed, but every step-in leaves the party weaker for later floors, including the final floor.

### 6.3 Each floor's fight
1. The ally fights their nemesis's **five same-element creatures**, which go as expected.
2. When the ally thinks they've won, the nemesis brings out a **hidden sixth creature** of the element that **beats** that ally (home advantage; they prepared a surprise).
3. For the sixth creature, **another ally can step in**: ideally one whose element beats it.

### 6.4 Field powers and Citadel puzzles *(first draft)*
- **The Citadel is the first place creatures can use their element outside battle.** It stands on the Rift, which amplifies the bond between master and creature.
  - *(Possible hook for open question 2: maybe that same amplification is how the villains learned to train other elements.)*
- The Citadel has **dead ends and locked ways** between the floors. You have to work out **which of the six powers** opens the way. Your party covers all six elements, so the answer is always in your group: the puzzle is spotting it.
- Puzzles are **telegraphed** by clues in the room (scorch marks, dry channels, dead roots, a breeze through a crack), so they're about noticing, not guessing.

| Element | Field power | Example uses |
|---|---|---|
| Wave | Flood or douse | Fill a chamber to float a platform up; put out a fire wall; fill a channel to turn a waterwheel |
| Flame | Burn or light | Burn through thorns or ropes; light braziers; melt wax seals |
| Root | Grow | Grow vines to climb; bridge a gap with roots; pry stones apart |
| Breeze | Blow or scout | Clear fog or smoke; push light objects; scout the next room |
| Soil | Shape | Raise steps or pillars; shift boulders; seal a leak |
| Lightning | Power | Wake old mechanisms; open shock-locked doors |

- **Combination puzzles** come later in the climb:
  - flood a room, then send current through the water to power a machine
  - fan a flame across a gap to burn a far rope
  - water seeds so a vine bridge grows fast
- *(Option to decide later:)* using a field power **tires that creature a little**. Since there's no rest in the Citadel, puzzles would cost resources too, and you'd pick which creature spends the effort.

### 6.5 Ally fights: control (one mode)
- The ally is the one "fighting" (that's the story), but **in practice you decide**.
- You can **suggest a move at any time**.
- If you don't, the ally proposes one: "I think I'll go with this. What do you think?"
- **Press Enter to accept** their choice, or pick a different one. *(No countdown for now.)*

### 6.6 The final floor: your nemesis
1. You fight your nemesis's five same-element creatures yourself.
2. They bring out a sixth creature. Based on every other floor, you expect the element that beats you, and it **looks** like exactly that.
3. **It's a hybrid:** your shared element **plus** the element that beats you. Allies may step in for this one, as on the other floors.
4. **The hybrid morphs** into whichever of its two forms is best against whatever you send out.

**Worked example: Marisol (Wave)**, using the chart in 2.3:
- The hybrid is **Wave + Lightning**. It appears as Lightning, the element that beats her.
- The obvious counter to Lightning is Soil (it earths lightning: strong). **It morphs to Wave**, and Soil is now *slightly weak*, so her trusted counter backfires.
- Send in a Lightning ally (strong against Wave)? **It morphs to Lightning**, and storms swallow lightning (weak).
- **The best answer is Root:** slightly strong against the Wave form and even against the Lightning form, so at worst an even fight.
- **The answer:** there's no counter that gives you a big advantage, as every earlier floor did. The best you can do is find the creature that's at least decent against **both** forms, and fight your hardest with what's left, which is exactly when the party is most worn out.
- **The hybrid isn't unbeatable.** It just takes away your element advantage.

> Tie-in: the element that beats you is **your sweetheart's** element. Her creature used to beat you and your nemesis as kids. A sharp player can see the hybrid coming.

---

## 7. The personal story

- You, your nemesis and your sweetheart grew up together.
- **Her creature beat you both every time**, so neither of you impressed her much.
- You were meant to marry her. **She vanished.** You assume your nemesis, jealous, captured her.
- **The truth:** she **chose** to go with him, impressed by his new strength and his secret.
- **The hybrid was bred from her strongest creature and his.**
- **The ending:**
  1. You beat your nemesis and demand he reveal the secret.
  2. He gives in ("Okay, okay, I'll tell you"), then **flees** and disappears.
  3. You think you'll never learn the secret, but your sweetheart says, "Don't worry, I'll tell you."
  4. She's impressed by **you**, even without the secret, and comes back to you.
- *(The sequel hook is obvious: she knows the secret, and her creature plus yours…)*

---

## 8. Saving and difficulty *(decided in principle)*

**The principle:** a determined player can always *theoretically* win, but we **never break the rules to guarantee it**. There are no surprise revives and no free healing. One mistake you couldn't have known about should never cost you everything.

How:
- **Save points** on the road (towns, inns, and Bram's camps once he joins).
- **Before entering the Citadel:** a clear warning ("Once inside, there's no rest") and a save.
- **Inside the Citadel:** an automatic **checkpoint at the start of every floor**, so you can replay a floor with different choices.
- **Worst case:** reload an earlier checkpoint, or the save from before the Citadel, then go back out to train, restock and rethink.
- **Big choices are foreshadowed,** so they're fair. The sweetheart's creature hints at the hybrid's second element, for example. Save that ally!

---

## 9. Presentation (terminal)

- **Truecolor half-block rendering** (`▀`): every character cell shows 2 vertical pixels with their own colours.
- **Overworld:** isometric or pseudo-3D view of each land.
- **Battles:** turn-based, with pixel-art creature sprites, health bars, move menus and animations.
- **Target:** Windows Terminal (and any truecolor terminal), keyboard only.

---

## 10. First full version (MVP) *(built)*

The whole story from start to finish, with the minimum in each step:

1. **Intro**
2. **Choose your hero** (one of six)
3. **Fights 1–5:** the five Masters, in your hero's land order. One creature each for now
4. **Citadel intro**
5. **Floors 1–5:** each ally against their nemesis. Only the **first** creature and the **last** (the hidden sixth) for now
6. **Your nemesis:** their first creature, then the **hybrid**
7. **Outro:** victory, you demand the secret, he flees, your sweetheart comes back to you
8. **End screen**

### 10.1 Structural decisions
Everything else (names, stats, text, the chart) is a value we can change any time. These shape how it's built:

| Decision | Recommendation | Why it matters now |
|---|---|---|
| **Resolution** | **Decided: HD art drawn with real pixels (Sixel)**, tested and looking great in Windows Terminal. Any window from 100 × 16 works; terminals without Sixel automatically get the text-block version of the same art | Every screen layout and all art sizes depend on it |
| **Heroes in the MVP** | **Decided:** everything is shared and reusable for any hero, with variants only where a part must match the chosen hero (names, land order, nemesis, sweetheart, a few lines). Full text for one hero first | The changing land order is the heart of the design, and sharing keeps six heroes affordable |
| **Art** | Placeholder art is fine: one creature per element, darker recolours for villains' creatures, six hybrids, simple portraits | Art is the slowest part; recolours keep the MVP small |
| **Health carries over between floors** | **Yes** | It's what makes the Citadel strategic, and battle balance depends on it |
| **Ally steps in for the sixth creature** | **Yes**, you choose which ally | It's the point of the "last creature" fights |
| **Ally fights: suggest / Enter to accept** | **Yes**, the simple version | Core to how the Citadel feels |
| **Losing** | Retry that fight (works like a checkpoint) | Simplest version of the save design |
| **Left out of the MVP** | Catching, levelling, items, overworld walking, field-power puzzles, saving to disk | Each can be added later without rebuilding |
| **Tech** | Keep Python, with characters, creatures, moves and dialogue in **data files** | Keeps all the "values" editable without touching code |
| **Where it's built** | **Decided:** a new `game/` folder on `master`. The prototypes stay as they are in `prototype/` | Keeps the experiments available for reference |

### 10.2 What the MVP does, and the calls made while building it

It's in `game/` (`python -m game`). All of these are defaults that can change:

**Creatures (placeholder cast, one per nature).** Each has four moves: an attack of its own nature, a plain attack that never misses, and two others.

| Nature | Creature | Villains' dark version | Its other two moves |
|---|---|---|---|
| Wave | Ripplefin | Murkfin | Bubble Guard (guard), Rest (heal) |
| Flame | Emberkit | Ashkit | Kindle (power up), Smokescreen (lower accuracy) |
| Root | Bramblehog | Blighthog | Take Root (heal), Thorn Guard (guard) |
| Breeze | Gustwing | Direwing | Tailwind (power up), Dust Devil (lower accuracy) |
| Soil | Loamkin | Gravelkin | Harden (guard), Mud Shot (lower accuracy) |
| Lightning | Nimbleat | Gloombleat | Charge Up (power up), Flash (lower accuracy) |

- **Hybrids** (one per hero): Squallhorn, Scaldfin, Briarback, Galewood, Dustwhirl, Fulgurite (each named for the body it has: your sweetheart's creature). A hybrid first looks like an ordinary dark creature of the nature that beats you. Once you've chosen who faces it, it shifts to whichever of its two forms does best against that creature, and shifts again whenever you send in someone new.
- **Nemeses got first names** (their old friends wouldn't use the title): Sable (Wavemaster Sable), Varek (the Ash King), Nettle (the Blight Witch), Corvin (the Gale Tyrant), Dorn (the Iron Baron), Vesper (the Thunder Duchess).
- **A light version of levelling.** Your creature gains a level for every Master beaten (a 4% boost each), and your allies keep pace. This was the simplest way to keep later fights fair. Full levelling is still to come.
- **Losing to a Master:** try again, or let an ally you've already recruited take the fight (they suggest moves, you decide). If an ally wins it, the Master's comment is about your company instead.
- **Masters' comments** pick from eight reasons you won: a narrow escape, a very fast win, winning against a bad match-up, good guarding, relying on plain attacks, fighting through lowered accuracy, a good match-up, or none of those.
- **Hints at the mystery** come from the second and fourth Masters you recruit.
- **The Citadel.** On each floor the ally whose nemesis it is fights first. When a creature faints you choose who steps in, and when the hidden sixth creature appears you choose who faces it. The menu shows each creature's health and how its nature fares. Health and limited moves carry over between floors.
- **Your own creature can step in on lower floors,** but if it has fainted when you reach the top, you can't face your nemesis.
- **Losing a floor:** retry it, go back down a floor, or start the Citadel again fully rested. These stand in for the checkpoints in section 8.
- **The final floor:** you fight your nemesis's first creature alone. For the hybrid, anyone can step in.
- **Pictures:** HD art as real pixels (Sixel) where the terminal supports it, otherwise the same art at retro resolution as coloured text blocks. The game detects which.
- **Everything editable is in `game/data/`:** the element chart, creatures and moves, heroes (names, looks, lines), all story text with `{placeholders}` per hero, and the balance numbers.

**Balance** (from `python -m game.sim`, a careful player):
- Master fights average about 95%, 86%, 76%, 64% and 50% wins from first to last, when fought alone. With the best ally stepping in after a loss, nearly all are winnable.
- It varies a lot by hero, because the creatures differ. The hardest single match-ups: Bram's Loamkin against Marisol's Ripplefin (about 13% alone) and Soren's Gustwing against Willow's Bramblehog (about 20%). Those fights more or less need an ally. *(Open: even these out, or keep them as "bring a friend" fights?)*
- A sensible party clears the Citadel about 80% of the time per attempt, with about three creatures still standing.

*(Section 10.2 describes the first version. Section 10.3 is what the game does now.)*

### 10.3 The full journey: what was added, and the calls made

*(Section 10.4 replaced several of these rules: befriending, who fights, experience, borders, saving, and the Citadel.)*

**Two ways to play, from the title screen**
- **The full journey:** home land, five lands, the Citadel. Progress is saved.
- **A quick taste** (about ten minutes): one Master, one Citadel floor and the top, one creature each, no walking. It's the first version in miniature, kept for quick feedback.

**Eighteen creatures: three per nature.** Each nature has its starter, a quick one and a sturdy one. Villains use dark versions with their own names.

| Nature | Starter | Quick | Sturdy |
|---|---|---|---|
| Wave | Ripplefin | Glidefin | Shellby |
| Flame | Emberkit | Flaremoth | Coalback |
| Root | Bramblehog | Twigtail | Stumpkin |
| Breeze | Gustwing | Whirlet | Driftpuff |
| Soil | Loamkin | Dusthop | Pebblit |
| Lightning | Nimbleat | Flashfly | Rumblehoof |

- Quick creatures have a weaker attack that always strikes first. Sturdy ones learn a heavy attack that often misses.
- **Levels and experience.** Creatures learn their third and fourth moves as they grow. The whole team shares experience from a fight; the one in the fight gets a full share.
- **Teams of up to five** (the world's own limit). Until there are more kinds of creature, a team can hold two of the same kind.

**Walking the lands**
- Each land is a map built from a fixed seed: a road west to east, a town with an inn and a market, clearings of long growth where wild creatures roam, a hidden nook, and a border gate.
- **Home comes first.** Its wild creatures are all your own nature, so it's where you build a team.
- **In other lands** most wild creatures are that land's nature. They'll fight (good for experience) but never join. About one in four is a stray of your own nature.
- **Befriending:** in a wild fight you can reach out to a creature of your nature. The weaker it is, the likelier it accepts; a lure helps.
- **The Master** appears when you get about three-quarters of the way along the road. If you lose, you can fall back (you return to where you last rested, healed) or let a companion's team try. A beaten Master opens the border gate. Borders are one-way.
- **Resting** at the inn heals everyone, brings the wild creatures back, changes the weather and saves. Losing a wild fight sends you back to your last rest, with nothing lost.

**The satchel** holds eight bundles of up to three: remedies (heal 40%), tonics (restore move uses), charms (power up the next attack), lures. Nothing revives a fainted creature except rest. Coins come from Masters and caches; herbs and shards can be sold.

**Gifts** (yours from the start, the others as Masters join)

| Hero | Gift | In the game |
|---|---|---|
| Marisol | Navigator | Hidden ways through to a cache in each land become passable |
| Kael | Forgemaster | Forge two Rift shards into a charm, from your pack |
| Willow | Herbalist | Every herb you pick becomes a remedy |
| Soren | Lookout | A warning just before the Master appears |
| Bram | Campbuilder | Once per land, make camp anywhere: a full rest and a save |
| Juno | Storm-reader | Tells you the day's weather |

- **Weather:** most days one nature is favoured and its attacks hit 15% harder. It applies whether or not Juno is there to tell you.

**The Citadel**
- The night before, companions' creatures are brought up to your best creature's level.
- **Nemesis teams grow as you climb.** The first floor's nemesis has one dark creature of their old friend's nature, the second has two, and so on up to five on the fifth floor. Each then brings out the hidden extra of the nature that beats it. So the opening floor is a quick shock, and the full "five and one more" of the story is what you meet just before the top.
- **The top floor** is your own nemesis: three dark creatures of your nature, which your team faces alone, then the hybrid, which anyone can face. *(Kept at three because nobody can step in for you there. Open question below.)*
- You choose **whose team** steps in. Inside a fight, that master's creatures can be swapped as usual.
- **Blocked ways** between floors: fire, dry vines, a broken bridge, smoke, a pit, a dead machine. Each needs one nature's power. A wrong guess tires that master's creatures a little.
- **Checkpoints:** the journey is saved at the start of every floor. After losing a floor you can retry it or go back down to an earlier one.
- If the party isn't as strong as expected, the Citadel's creatures are scaled down to match, so nobody arrives unable to win.

**Balance** (from `python -m game.sim`; a careful player with the expected team and no items)
- Masters: 4, 4, 3, 3, 2 creatures at levels 7, 10, 11, 14, 14. Later Masters have fewer creatures because their nature already has the upper hand.
- Beating each Master alone averages roughly 92%, 87%, 73%, 61% and 53%, first to last. It still varies a lot by hero.
- The Citadel: nemesis creatures at level 18, the hidden extra at 19, your own nemesis's three at 16, the hybrid at 21. Cleared about 85% of the time per attempt.
- The five floors are almost never lost outright, since six teams can step in. What they do is wear the party down. Nearly every failed attempt ends on the top floor, usually because the hero's own team was spent on the way up. The game says so twice: the Masters offer to carry the climb before you go in, and if you lose at the top with a worn team it points you back down.

### 10.4 The rework: training, befriending and a fixed Citadel

Decided together after the first full journey. These replace the matching rules in 10.3.

**Befriending**
- A wild creature will only join **a master of its own nature** who is in your party and has room (five each). Before a land's Master joins you, its creatures can only be fought for experience; afterwards that Master can take them in.
- Weaken it, then **offer a lure**. The nearer it is to fainting and the tastier the lure, the likelier it accepts, with luck involved. It's healed when it joins. A refused lure is gone.
- **Lures** come in one kind per nature and three grades (Plain, Sweet, Rich), each costing more. A land's market sells the lures for that land's creatures.

**Fighting and growing**
- **Anyone in your party can take a fight.** Meeting a wild creature or a Master, you choose whose team goes in.
- **Only creatures that took part in a fight earn experience** from it, and only if they're still standing at the end. Each one that did gets the full amount. *(So sending a weak creature in first and swapping it out trains it, as in the classics.)*
- **Wild creatures in lands you've passed grow** as your journey goes on, so going back is still worth it.
- **Borders open both ways.** You can always walk back along the road.
- Companions are no longer brought up to your level the night before the Citadel. They are as strong as you've made them.

**Masters** have 1, 2, 3, 4 and 5 creatures, first to last, mirroring the Citadel. They join with exactly that team.

**A healing touch.** Each master can mend a creature of their own nature, three times between rests, for half its health. It can't wake a fainted creature (only rest does) and can't be used mid-fight. An elixir restores one master's touches.

**Rest points**
- One for each land and one for each Citadel floor. Arriving makes it; resting there again (the inn, or Bram's camp) replaces it.
- You can go back to any earlier one: from the title screen, or after losing a Citadel floor. Later rest points stay as they are until you reach those places again.

**The Citadel**
- **Fixed levels.** It doesn't adjust to you. Train well and you match it; rush and you're behind.
- **No rest and no way out.** If you can't win, go back to an earlier rest point and prepare better.
- **A warning at the border.** If the party plainly isn't ready, your latest companion says so strongly; if it's borderline or anyone is hurt, they say there'll be no resting inside; otherwise nothing. You can always go in anyway.
- **Team sizes:** floors one to five have 1, 2, 3, 4, 5 creatures, each followed by the one more. Your nemesis at the top has five, then the hybrid. Levels are about the same throughout; it's the numbers that grow.
- **The matching hero goes first.** Whatever a nemesis sends out, their old friend must be the first to meet it, with **any creature of theirs they like**: each time a new one comes out, you choose which of that hero's creatures faces it. Once one of that hero's creatures has fallen to it, anyone may step in, and from then on you can hand the fight to a companion whenever you like (it uses your turn, as any swap does). The same holds at the top, for you. The exception is the one more and the hybrid: you see those before you choose.
- **Between floors** you can use your satchel and your healing touches, and look over the teams.

**Numbers still to choose** (provisional values are in `game/data/tuning.json`)
- Master levels 7, 9, 11, 13, 14. With these, the first three Masters fall to almost anyone; the last two (four and five creatures of natures that have the edge on you) are rarely beaten with your own team but reliably beaten by the companion whose nature suits.
- Citadel levels: floors 16, the one more 17, your nemesis 17, the hybrid 18. In simulation the head-count matters more than the levels: the Citadel fields 26 creatures. A party with four creatures each (24) clears it nearly every time even two levels below; a party with three each (18) clears it about 60% of the time at equal level and rarely when two levels below.
- Lure prices 6, 12, 20 coins. You start with 20 coins; Masters pay 30 to 70; a cache holds 15.
- Healing: three touches each, half health.

### 10.5 The story and the titles, as they now stand

**Masters.** Someone who has mastered their nature is a Master of it: Wavemaster, Flamemaster, Rootmaster, Breezemaster, Soilmaster, Lightningmaster. Each land is kept by one (the six heroes). The six in the Citadel carry the same titles ("Flamemaster Varek"); the old villain titles (the Ash King and the rest) are gone. Your sweetheart is **Master of the Citadel**, which belongs to no land. She earned it the long way.

**Words.** They are "creatures", and the person a creature follows is its "master" (not "trainer"). "Master" with a capital is the title.

**Her creature** is a different kind from the one your companion of the same nature keeps, so the two never look alike: Levin's Rumblehoof, Coral's Glidefin, Flint's Coalback, Linnea's Stumpkin, Wren's Whirlet, Garrick's Pebblit. The nemesis's hybrid has that body, and so does the couple's own young one at the wedding.

**What everyone knows.** Nothing is forbidden. People simply found that only creatures of their own nature would ever join them, and that a sixth never lasted: five of a kind already strain against each other. So everyone keeps to one nature and stops at five.

**The secret.** Both "impossible" things work if you do them together. A sixth of a *stronger* nature keeps the other five in line. (Like a house full of brothers that a sister changes.) What nobody but the six knows is *how* to get a creature of another nature to follow you.

**The story**
1. You were to marry the Master of the Citadel. Word comes that the Citadel has fallen to six Masters who answer to nobody, led by your oldest friend and rival, with her inside.
2. You cross five lands. Each land's Master blocks the road, is beaten, hears the news and joins you.
3. Hints along the way that nothing was taken by force: a Master who knows those gates can't be broken; the gates standing open, nothing burned; doors already unlocked; a beaten nemesis saying "ask yourself who opened the gates".
4. Each floor: a companion's old friend, with one more creature than the floor below, then the one more that shouldn't be possible.
5. The top is the rooftop, at night, under the Rift. A figure waits on the platform at its centre; you take it for your nemesis and demand to know where she is. A smothered laugh. Closer, and it is her, standing free. Your nemesis steps out beside her: she invited them; you're the one who broke in. "What can I say? They're very impressive." (Impressed, not in love.) "I could beat them any day." "We'll see about that." Then five creatures, and the hybrid, bred from the nemesis's strongest creature and hers.
6. Your nemesis promises the secret, then runs for the battlements and jumps. It looks like the end of them; there is a ledge just below, and a ladder. (The last fights are on the rooftop, and she is there, standing free, from the moment you arrive.)
7. With the nemesis gone she tells you the rest: she let them show her everything, then watched you climb the tower without any of it, and the secret didn't leave with them. How much she was swept along and how much she was using them is left unsaid; it leans to the second.
8. Everyone turns to leave. She says "Wait." You walk back to her while the others go on down, and she asks you to stay.
9. "One minute." You run down after your companions: you're staying, they should go home to their lands, and they're to come back in the spring. "What's in the spring?" "My wedding. Our wedding."
10. The screen goes dark and comes back on exactly the same rooftop, in spring daylight, at the wedding: the couple raised on a platform under a canopy (white gown and veil, black suit and top hat), the five Masters below with their creatures, everyone smiling. Nobody stands behind the couple. At the foot of the steps sits a young hybrid of their two creatures: the same cross the nemesis bred in secret, but bright and gentle. No closing line: the picture says it.

**Eyes.** Every creature has the same kind of eye: dark, with a small highlight. No solid-coloured eyes, glowing eyes or coloured rims: they read as mistakes. A creature that needs a dark head gets a paler face so the eye still shows.

**The walking map** is drawn at sixteen pixels to a tile in HD, the size classic handheld games used, from small hand-made pixel grids (`game/art/tiles.py`): a person who is plainly a person from all four sides, a house for the inn with its name over the door, a striped market stall, a signpost, a chest, plants, and for each land its own trees or rocks, ground and long growth. The first version was drawn at half that detail and nothing on it could be recognised.

**Dark versions** are not the same drawing in darker colours. Each keeps its black eyes but glares from under heavy lids, loses its blush and its smile, and has changes of its own: barbs for bobbles, thorns for leaves, horns for a curl, spikes on a shell, a splintered crown, a blighted leaf, and so on. Everything added is in the creature's own colours, dulled. Nothing white or bright pink sits on top: that read as stuck on.

**Not in yet:** levelling-up animations or evolutions, more than three kinds of creature per nature, field powers outside the Citadel, walking inside the Citadel, sound.

---

## 11. Open questions (none are blockers)

1. **The game's name is *Entwined*** (decided). Before any public release, check the name: a 2014 PlayStation game called *Entwined* exists, so a subtitle may be needed. (The old working title, "Riftbound", is used by Riot Games.)
2. How do villains learn to train **another element**? *(Possible hook: the Rift amplifies bonds; see 6.4.)*
3. The Root hero's best answer to their hybrid keeps a slight edge, and Flame is a touch weaker overall. Keep, or tune? (see 2.3)
4. Rename the **Obsidian Citadel**? Obsidian is an overused "special material".
5. **Currency** for buying items.
6. Do field powers tire the creature that uses them?
7. Weather in battles (needed for Juno's gift)?
8. The real cast names *(keeping the placeholders for now)*.
9. Even out the hardest Master match-ups, or keep them as fights that need an ally? (see 10.2)
10. In text-block mode the game needs a 100 x 37 window, taller than a default terminal (120 x 30). Fine as a fallback, or worth a compact layout?
11. **How hard should the Citadel be?** Its levels are fixed, and what decides a climb is mostly how many trained creatures you bring (see 10.4). Raise its levels, or leave it so that a full, trained party wins?
12. **Coins.** Lures cost coins and wild fights don't pay any. Early on there's only enough for a few attempts. Should wild fights pay a little, lures be cheaper, or is scarcity right?
13. **Training time.** With only fighters earning experience, a full party is a lot of creatures to train. The robot player needs five to ten times as many turns as before. Too long?
14. *(Settled: creatures do earn experience inside the Citadel.)*
15. A team can hold two of the same kind of creature. Keep that, or add more kinds first?
16. Names changed after review: Brann to Flint, Tavi to Levin, Nerys to Coral, Rumblehorn to Rumblehoof, Howlet to Squallet, the six hybrids, and twelve moves that shared names with Pokémon moves. Still flagged, not changed: Nimbleat (hard to read), Driftpuff, Emberkit, Ashkit and Twigtail (close in feel to other series), and the nemeses' titles.

### 11.1 Game name candidates *(themed on the story arc)*

What the name should carry: **friends too alike, turned rivals**; a **sweetheart who's their opposite**; the belief you can bond **only one kind** of creature, broken, then **hybrids**; **which element beats which**; and **strength in joining together**.

| Name | How it ties in |
|---|---|
| **Second Nature** | Everyone has one nature, but the secret is bonding a *second*. The hybrid has two natures in one body. And the everyday meaning: what becomes instinct through training |
| **Natural Rivals** | You and your nemesis are rivals *by nature* (the same element, too alike), and the elements themselves are natural rivals (what beats what) |
| **True Nature** | The reveals: your sweetheart's true feelings, your nemesis's true plan, what creatures can truly do |
| **Nature & Nurture** | You're born with one bond (nature), but the villains' secret is that training can overcome it (nurture) |
| **Of One Nature** | The old belief, "everyone is of one nature", that the story breaks. Ironically, the heroes only win by uniting their different natures |
| **Opposite Natures** | You and your sweetheart, the elements on the wheel, and the hybrid's two forms |
| **Kindred & Contrary** | Kindred: your nemesis, too alike. Contrary: your sweetheart, the opposite |
| **Unnatural** | What the villains do (a second bond, breeding hybrids). Darker in tone |

**Feedback:** *Second Nature* is close, but on its own it doesn't sound like a game, and "Obsidian" is overused.

Closer variants that sound more like games:

| Name | Why |
|---|---|
| **Rival Natures** | Friends turned rivals *because* they share a nature, and the elements are rival natures on the wheel |
| **Natureshift** | Bonding a second nature, and the hybrid shifting between forms |
| **Crossnature** | Crossing natures: the second bond, crossbred hybrids, crossing the lands together |
| **Nature Unbound** | The one-nature law broken, for good (your team) and for ill (the hybrid) |
| **Second Nature: Masters** | Keeps the phrase, and the subtitle makes it read as a game |
| **Second Nature: Rival Bonds** | The same, with the rivalry front and centre |


More variations (round 3):

| Name | Why |
|---|---|
| **Bondbreaker** | The villains break the one-bond law; you and your nemesis broke your friendship; and you break their hold on your sweetheart |
| **Entwined** | The hybrid entwines two natures; the six heroes entwine their fates; and the love story |
| **Twin Natures** | Too-alike rivals, and the hybrid's two forms |
| **Clash of Natures** | Element against element, rival against rival |
| **Second Soul** | A second bond is like a second soul. Close to *Second Nature*, but more like a game |
| **Kindred Rivals** | Your nemesis was your kin |
| **Bound by Nature: Rivals** | Classic title-and-subtitle style |

### Decided so far
- **Game name: *Entwined*.**
- Keep the name **"Masters"** for now.
- Use **your variant of the element wheel**, with realism exceptions (2.3).
- **Element names:** Wave, Flame, Root, Breeze, Soil, Lightning (2.4).
- **Resolution:** HD art with real pixels (Sixel), with a text-block fallback (10.1).
- **MVP lives in `game/` on `master`;** the prototypes stay in `prototype/`.
- **Theoretically winnable, never by breaking the rules:** save points and checkpoints (8).
- **Master gifts, items and field-power puzzles** have first drafts (4.4, 4.5, 6.4).
- Healing inside the Citadel comes **only from what you bring**: remedies in your satchel. No resting.
