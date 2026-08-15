"""Authors Darkspire levels 1-10.  Run:  python tools/gen_levels.py

Stair alignment (down on N lands at the same coords as up on N+1):
  L1 (17,3) -> L2 · L2 (3,16) -> L3 · L3 (16,2) -> L4 · L4 (8,17) -> L5
  L5 (12,4) -> L6 · L6 (4,18) -> L7 · L7 (16,3) -> L8 · L8 (3,3) -> L9
  L9 (10,16) -> L10 (no stairs down; the portal is the only way home)
Elevator shafts: (2,2) links L1<->L4; (18,18) links L4<->L9 (needs black key).
Chute on L2 (12,8) drops to L3.
"""

from levelgen import Builder


def level1():
    b = Builder("The Undercroft", 1)
    b.room(8, 15, 11, 18, doors=[("N", 10), ("S", 10)])   # entry hall
    b.room(3, 15, 6, 17, doors=[("E", 16)])               # guard room
    b.room(1, 4, 5, 9, doors=[("S", 3), ("E", 6)])        # west crypt
    b.room(8, 5, 13, 10, doors=[("S", 10), ("W", 7), ("E", 8), ("N", 11)])
    b.room(15, 12, 18, 16, doors=[("W", 14)])             # east cells
    b.room(15, 2, 18, 5, doors=[("S", 16)])               # northeast vault
    b.vrun(7, 0, 13, gaps=(6, 12))
    b.vrun(14, 0, 11, gaps=(8,))
    b.hrun(13, 0, 6, gaps=(2,))
    b.hrun(2, 7, 13, gaps=(9,))
    b.start = {"x": 10, "y": 19, "facing": 0}
    b.special(10, 19, type="stairs_up")
    b.special(17, 3, type="stairs_down")
    b.special(2, 2, type="elevator", floors=[1, 4])
    b.message(10, 13, "The air smells of old stone and older bones.")
    b.message(10, 11, "Faint echoes drift from a great hall ahead.")
    b.message(16, 6, "Scratched above an arch: THE SIGIL LIES DEEPER.")
    b.message(2, 3, "A caged shaft of chains and pulleys hums here.")
    return b


def level2():
    b = Builder("The Flooded Cisterns", 2)
    b.room(15, 1, 18, 5, doors=[("W", 3), ("S", 16)])     # arrival gallery
    b.room(8, 1, 12, 5, doors=[("S", 10), ("W", 3)])      # north basin
    b.room(1, 1, 5, 5, doors=[("E", 3)])                  # silt vault
    b.room(1, 8, 4, 12, doors=[("N", 2), ("E", 10)])      # sigil chamber
    b.room(9, 9, 12, 13, doors=[("N", 10), ("S", 11)])    # drowned shrine
    b.room(16, 9, 18, 13, doors=[("W", 11)])              # leech pools
    b.room(1, 15, 5, 18, doors=[("N", 3)])                # stair vault
    b.vrun(7, 0, 19, gaps=(3, 10, 16))
    b.vrun(14, 2, 17, gaps=(8, 14))
    b.hrun(15, 8, 13, gaps=(11,))
    b.hrun(7, 0, 6, gaps=(5,))
    b.start = {"x": 17, "y": 3, "facing": 2}
    b.special(17, 3, type="stairs_up")
    b.special(3, 16, type="stairs_down", requires="bronze_sigil",
              locked_text="A bronze door seals the stair. A sigil-shaped socket waits.")
    b.special(2, 10, type="quest_item", grant="bronze_sigil",
              text="Amid the silt gleams the BRONZE SIGIL of the Undercroft!")
    b.special(10, 7, type="spinner")
    b.special(12, 8, type="chute", to_depth=3,
              text="The floor collapses — you plunge into the dark below!")
    b.special(18, 18, type="teleporter", to=[1, 1])
    b.dark(1, 8, 4, 12)
    b.message(16, 3, "Water whispers through the stones.")
    b.message(10, 10, "The drowned kneel at an altar of barnacles.")
    b.message(2, 8, "It is black as pitch here. Something gleams below.")
    return b


def level3():
    b = Builder("The Foundry", 3)
    b.room(1, 14, 5, 18, doors=[("N", 3), ("E", 16)])     # arrival hall
    b.room(7, 7, 12, 11, doors=[("W", 9), ("S", 10), ("E", 8)])  # forge hall
    b.room(14, 1, 18, 4, doors=[("S", 15)])               # master vault (stairs)
    b.room(1, 1, 4, 5, doors=[("S", 2), ("E", 3)])        # slag pits
    b.room(15, 8, 18, 12, doors=[("W", 10)])              # cooling racks
    b.room(7, 14, 12, 17, doors=[("N", 9), ("E", 15)])    # smelter row
    b.vrun(6, 0, 12, gaps=(3, 9))
    b.hrun(13, 6, 19, gaps=(8, 15))
    b.hrun(6, 7, 19, gaps=(11, 17))
    b.start = {"x": 3, "y": 16, "facing": 0}
    b.special(3, 16, type="stairs_up")
    b.special(16, 2, type="stairs_down", requires="iron_key",
              locked_text="A door of black iron. Its lock is shaped like a hammer.")
    b.special(9, 9, type="encounter", id="forge_warden", once=True,
              groups=[["forge_warden", "1d1"], ["ember_hound", "1d2"]],
              grant="iron_key",
              text="The FORGE WARDEN rises from the coals, hammer in hand!",
              victory_text="From the Warden's cooling grip falls the IRON KEY.")
    b.special(5, 9, type="pit", dice="2d6", text="A fire vent erupts underfoot!")
    b.special(13, 8, type="pit", dice="2d6", text="A fire vent erupts underfoot!")
    b.special(9, 13, type="pit", dice="2d6", text="A fire vent erupts underfoot!")
    b.special(10, 15, type="spinner")
    b.message(3, 14, "Heat beats down from somewhere ahead.")
    b.message(9, 10, "Anvils the size of oxen. Nothing sane forged here.")
    b.message(15, 2, "The vault of the forge-masters.")
    return b


def level4():
    b = Builder("The Fungal Warrens", 4)
    b.room(14, 1, 18, 4, doors=[("W", 2), ("S", 16)])     # arrival grotto
    b.room(1, 1, 4, 4, doors=[("S", 2), ("E", 2)])        # elevator cage
    b.room(3, 6, 7, 10, doors=[("N", 5), ("E", 8)])       # font hollow
    b.room(12, 10, 16, 14, doors=[("W", 12), ("N", 14)])  # riddle grotto
    b.room(6, 15, 11, 18, doors=[("N", 8)])               # stair warren
    b.vrun(10, 0, 8, gaps=(4,))
    b.hrun(9, 8, 19, gaps=(9, 14))
    b.hrun(14, 0, 5, gaps=(1,))
    b.vrun(13, 14, 19, gaps=(17,))
    b.start = {"x": 16, "y": 2, "facing": 2}
    b.special(16, 2, type="stairs_up")
    b.special(8, 17, type="stairs_down")
    b.special(2, 2, type="elevator", floors=[1, 4])
    b.special(5, 8, type="font", dice="1d8",
              text="A spring of clear water glows faintly here.")
    b.special(14, 12, type="riddle", grant="pale_word",
              text="A dead courtier's ghost whispers: 'I speak without a mouth "
                   "and hear without ears. Nobody sees me, but I answer all "
                   "who call. Say my name.'",
              answer="echo",
              success="'Yes... ECHO. Speak it at the Pale Court's gate.'")
    b.special(9, 9, type="spinner")
    b.special(4, 14, type="spinner")
    b.special(18, 17, type="teleporter", to=[1, 17])
    b.special(18, 18, type="elevator", floors=[4, 9], requires="black_key",
              locked_text="A second shaft, chained shut. The lock is black iron.")
    b.dark(0, 15, 5, 19)
    b.message(16, 4, "Spores drift like snow that never lands.")
    b.message(2, 4, "The elevator cage rattles, hungry to move.")
    b.message(8, 15, "Below, something pale holds court.")
    return b


def level5():
    b = Builder("The Pale Court", 5)
    b.room(6, 3, 14, 8, doors=[("S", 10)])                # the court itself
    b.room(1, 1, 4, 4, doors=[("E", 2)])                  # bone antechamber
    b.room(16, 1, 18, 6, doors=[("W", 3)])                # gallery of masks
    b.room(1, 10, 5, 14, doors=[("N", 3), ("E", 12)])     # wraith cloister
    b.room(6, 16, 11, 18, doors=[("N", 8), ("E", 17)])    # arrival crypt
    b.room(14, 12, 18, 16, doors=[("W", 14), ("N", 16)])  # tomb rows
    b.hrun(10, 0, 19, gaps=(2, 10, 16))
    b.vrun(13, 10, 15, gaps=(12,))
    b.vrun(5, 5, 9, gaps=(6,))
    b.start = {"x": 8, "y": 17, "facing": 0}
    b.special(8, 17, type="stairs_up")
    b.special(12, 4, type="stairs_down", requires="ivory_crown",
              locked_text="A pale arch bars the stair: 'TRIBUTE', it demands.")
    b.special(10, 9, type="gate", requires="pale_word",
              text="Pale guards cross their halberds. They await a word.")
    b.special(10, 5, type="encounter", id="pale_countess", once=True,
              groups=[["pale_countess", "1d1"], ["court_specter", "1d3"]],
              grant="ivory_crown",
              text="The PALE COUNTESS descends from her throne of ribs.",
              victory_text="The IVORY CROWN clatters from her fading brow.")
    b.special(4, 4, type="spinner")
    b.dark(0, 10, 5, 14)
    b.message(8, 16, "Cold silk brushes your face. Nothing is there.")
    b.message(10, 8, "Music, thin as frost, drifts from the court.")
    b.message(3, 10, "The cloister drinks your lanternlight.")
    return b


def level6():
    b = Builder("The Shifting Halls", 6)
    b.room(10, 2, 14, 6, doors=[("W", 4), ("S", 12)])     # arrival
    b.room(2, 16, 6, 18, doors=[("N", 4)])                # stair landing
    b.room(15, 15, 18, 18, doors=[("N", 16)])             # cartographer's cell
    b.room(2, 8, 6, 12, doors=[("E", 10), ("N", 4)])      # false library
    b.vrun(8, 8, 19, gaps=(11, 17))
    b.hrun(7, 0, 9, gaps=(4, 7))
    b.hrun(14, 8, 19, gaps=(10, 16))
    b.vrun(16, 0, 6, gaps=(2,))
    b.start = {"x": 12, "y": 4, "facing": 2}
    b.special(12, 4, type="stairs_up")
    b.special(4, 18, type="stairs_down")
    b.special(3, 3, type="spinner")
    b.special(9, 9, type="spinner")
    b.special(15, 6, type="spinner")
    b.special(6, 15, type="spinner")
    b.special(17, 12, type="spinner")
    b.special(1, 10, type="teleporter", to=[18, 10])
    b.special(10, 18, type="teleporter", to=[10, 1])
    b.special(18, 2, type="teleporter", to=[2, 15])
    b.message(12, 6, "The walls here were built by something that hates maps.")
    b.message(16, 16, "A torn map fragment, inked in a steady hand: 'trust the "
                      "counted step, not the remembered one.'")
    b.message(4, 17, "The stair below breathes like a sleeping animal.")
    return b


def level7():
    b = Builder("The Menagerie", 7)
    # a row of cages along the north wall
    b.room(2, 2, 4, 4, doors=[("S", 3)])
    b.room(6, 2, 8, 4, doors=[("S", 7)])
    b.room(10, 2, 12, 4, doors=[("S", 11)])
    b.room(14, 2, 16, 4, doors=[("S", 15)])      # stairs down in this cage
    b.room(8, 7, 12, 10, doors=[("N", 10), ("S", 9)])   # the Amalgam's pit
    b.room(14, 12, 18, 15, doors=[("W", 13)])    # feeding pens
    b.room(2, 14, 6, 18, doors=[("N", 4), ("E", 16)])   # arrival kennels
    b.hrun(6, 0, 19, gaps=(3, 7, 11, 15, 18))
    b.hrun(12, 0, 7, gaps=(2, 5))
    b.vrun(13, 16, 19, gaps=(17,))
    b.start = {"x": 4, "y": 18, "facing": 0}
    b.special(4, 18, type="stairs_up")
    b.special(16, 3, type="stairs_down", requires="black_key",
              locked_text="This cage holds only a stair — behind a black-barred gate.")
    b.special(10, 8, type="encounter", id="amalgam", once=True,
              groups=[["the_amalgam", "1d1"], ["cage_stalker", "1d2"]],
              grant="black_key",
              text="The pit stirs. THE AMALGAM — a dozen beasts sewn into one — rises.",
              victory_text="In the Amalgam's gullet: the BLACK KEY, half-digested.")
    b.special(5, 14, type="spinner")
    b.special(12, 13, type="pit", dice="2d6",
              text="A cage floor snaps shut on the party!")
    b.message(4, 17, "Cages. Hundreds of cages. Most are empty. Most.")
    b.message(10, 9, "Bones of every shape carpet this pit.")
    b.message(15, 3, "The last cage was never meant to hold an animal.")
    return b


def level8():
    b = Builder("The Ember Gaol", 8)
    b.room(14, 1, 18, 5, doors=[("W", 3), ("S", 16)])    # arrival landing
    b.room(1, 1, 5, 5, doors=[("S", 2), ("E", 3)])       # stair cell (down)
    b.room(8, 8, 12, 12, doors=[("N", 10)])              # the Seraph's cell
    b.room(1, 15, 6, 18, doors=[("N", 2), ("E", 17)])    # ash yards
    b.room(15, 14, 18, 18, doors=[("N", 16)])            # stoke rooms
    b.hrun(6, 0, 13, gaps=(4, 9))
    b.vrun(7, 6, 14, gaps=(10,))
    b.hrun(14, 6, 19, gaps=(8, 16))
    b.start = {"x": 16, "y": 3, "facing": 2}
    b.special(16, 3, type="stairs_up")
    b.special(3, 3, type="stairs_down")
    b.special(10, 7, type="encounter", id="gaol_keeper", once=True,
              groups=[["gaol_keeper", "1d1"], ["chain_devil", "1d2"]],
              text="The GAOL KEEPER unfolds from the wall of chains before the cell.")
    b.special(10, 10, type="quest_item", grant="seraph_blessing",
              text="You shatter the chains of the BOUND SERAPH. Wings of quiet "
                   "fire unfurl — and a lasting blessing settles on the party.")
    b.special(7, 15, type="pit", dice="2d8", text="Embers geyser from a floor grate!")
    b.special(13, 5, type="pit", dice="2d8", text="Embers geyser from a floor grate!")
    b.zones.setdefault("null", []).append([8, 8, 12, 12])   # cell eats magic
    b.message(16, 5, "Heat, chains, and far below — weeping.")
    b.message(10, 8, "Inside the cell, your spells die on your lips.")
    b.message(2, 15, "The ash out here is knee-deep and still warm.")
    return b


def level9():
    b = Builder("The Null Ward", 9)
    b.room(1, 1, 5, 5, doors=[("S", 2), ("E", 4)])       # arrival (stairs up)
    b.room(9, 14, 12, 17, doors=[("N", 10)])             # descent vault
    b.room(15, 7, 18, 10, doors=[("W", 8)])              # the Lens reliquary
    b.room(15, 16, 18, 18, doors=[("N", 17)])            # elevator vault
    b.vrun(8, 0, 12, gaps=(4, 9))
    b.hrun(6, 0, 14, gaps=(2, 11))
    b.hrun(13, 0, 8, gaps=(5,))
    b.vrun(14, 6, 15, gaps=(8, 12))
    b.start = {"x": 3, "y": 3, "facing": 2}
    b.special(3, 3, type="stairs_up")
    b.special(10, 16, type="stairs_down", requires="wardlantern",
              locked_text="The final stair. Without the Wardlantern, the descent "
                          "is folly — the Temple would arm you, if they knew.")
    b.special(16, 8, type="quest_item", grant="void_lens",
              text="On a lead pedestal: the VOID LENS. Through it, lies unravel.")
    b.special(15, 8, type="encounter", id="blind_watcher", once=True,
              groups=[["blind_watcher", "1d1"], ["void_shade", "1d2"]],
              text="Something eyeless turns toward you anyway: the BLIND WATCHER.")
    b.special(18, 18, type="elevator", floors=[4, 9], requires="black_key",
              locked_text="The shaft is chained with black iron.")
    b.special(7, 7, type="spinner")
    b.special(12, 3, type="spinner")
    b.dark(0, 6, 19, 19)
    b.zones.setdefault("null", []).append([6, 0, 13, 10])
    b.message(3, 4, "The dark here is total, and the silence eats spells. "
                    "Word must reach the Temple that you walk this deep.")
    b.message(10, 15, "Below: warmth. The first warmth in nine levels.")
    b.message(16, 7, "A reliquary of things that see truly.")
    return b


def level10():
    b = Builder("The Archon's Sanctum", 10)
    b.room(7, 1, 13, 5)                                   # the sanctum: no door
    b.hillusion(6, 10)                                    # ...only an illusion
    b.room(1, 1, 4, 4, doors=[("E", 2)])                  # vestry
    b.room(16, 1, 18, 4, doors=[("W", 2)])                # reliquary
    b.room(8, 14, 12, 18, doors=[("N", 10)])              # arrival nave
    b.hrun(9, 0, 19, gaps=())
    b.hillusion(9, 5, 14)                                 # two hidden ways north
    b.hrun(12, 3, 16, gaps=(4, 15))
    b.vrun(6, 10, 19, gaps=(13, 16))
    b.vrun(15, 10, 19, gaps=(11, 17))
    b.start = {"x": 10, "y": 16, "facing": 0}
    b.special(10, 16, type="stairs_up")
    b.special(10, 4, type="encounter", id="vexis", once=True,
              groups=[["vexis", "1d1"], ["sanctum_guard", "1d2"],
                      ["flame_wraith", "1d2"]],
              grant="everflame_taken",
              text="VEXIS, THE MAD ARCHON, turns from the caged flame. "
                   "'You brought my lantern. How thoughtful.'",
              victory_text="The Archon falls. The EVERFLAME leaps into the "
                           "Wardlantern — and it SINGS.")
    b.special(10, 2, type="portal", requires="everflame_taken",
              text="A dormant portal of white marble. It ignores you utterly.")
    b.special(5, 8, type="encounter", id="echo_west", once=True,
              groups=[["archon_echo", "1d1"], ["sanctum_guard", "1d1"]],
              text="An ECHO of the Archon flickers into being, furious.")
    b.special(14, 8, type="encounter", id="echo_east", once=True,
              groups=[["archon_echo", "1d1"], ["flame_wraith", "1d1"]],
              text="An ECHO of the Archon flickers into being, laughing.")
    b.message(10, 15, "Illusion coats these halls like lacquer. Trust the Lens.")
    b.message(10, 5, "Beyond the false wall: firelight, and a voice talking to it.")
    b.message(2, 2, "Vestments for a congregation of one.")
    return b


if __name__ == "__main__":
    for build in (level1, level2, level3, level4, level5,
                  level6, level7, level8, level9, level10):
        b = build()
        path = b.write()
        print(f"wrote {path.name}: {b.name}")
