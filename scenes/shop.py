"""The Iron Ledger — buy, sell, equip, and pool gold."""

import pygame

from engine import palette
from engine.scene import Scene
from engine.ui import Menu, MenuItem, draw_panel
from game import data, items
from scenes.common import draw_party_bar


class ShopScene(Scene):
    def on_enter(self):
        self.message = ""
        self._to_who()

    @property
    def gs(self):
        return self.app.state

    def _to_who(self):
        self.state_ = "WHO"
        classes = data.classes()
        self.who_menu = Menu(
            [
                MenuItem(f"{c.name:<14} {classes[c.cls]['name']:<13} {c.gold:>6} gold", i)
                for i, c in enumerate(self.gs.party)
            ]
            + [MenuItem("Leave the shop", "leave")]
        )

    def _to_shopper_menu(self):
        self.state_ = "SHOP_MENU"
        c = self.shopper
        unidentified = any(not e.get("identified", True) for e in c.inventory)
        self.menu = Menu([
            MenuItem("Buy", "buy"),
            MenuItem("Sell", "sell", enabled=bool(c.inventory)),
            MenuItem("Identify", "identify", enabled=unidentified),
            MenuItem("Equip gear", "equip", enabled=bool(c.inventory)),
            MenuItem("Give an item", "trade",
                     enabled=bool(c.inventory) and len(self.gs.party) > 1),
            MenuItem("Pool party gold here", "pool", enabled=len(self.gs.party) > 1),
            MenuItem("Done", "done"),
        ])

    def _to_buy(self):
        self.state_ = "BUY"
        c = self.shopper
        catalog = data.load("items")
        self.buy_keys = [k for k, it in catalog.items()
                         if it.get("stock", True)]
        rows = []
        for key in self.buy_keys:
            it = catalog[key]
            usable = items.can_use(c, key)
            tag = "" if usable else "  (not your class)"
            rows.append(MenuItem(
                f"{it['name']:<18} {it['price']:>6}g{tag}", key,
                enabled=c.gold >= it["price"] and len(c.inventory) < items.INVENTORY_CAP,
            ))
        rows.append(MenuItem("Nothing today", "back"))
        self.buy_menu = Menu(rows)

    def _to_sell(self):
        self.state_ = "SELL"
        c = self.shopper
        rows = []
        for i, e in enumerate(c.inventory):
            identified = e.get("identified", True)
            stuck = items.is_cursed_stuck(e)
            label = f"{items.display_name(e):<18} "
            label += f"{items.sell_price(e['key']):>6}g" if identified else "     ?g"
            if e.get("equipped"):
                label += "  [equipped]"
            rows.append(MenuItem(label, i, enabled=identified and not stuck))
        rows.append(MenuItem("Nothing today", "back"))
        self.sell_menu = Menu(rows)

    def _to_identify(self):
        self.state_ = "IDENTIFY"
        c = self.shopper
        rows = [
            MenuItem(
                f"{items.display_name(e):<18} {items.identify_fee(e):>6}g", i,
                enabled=c.gold >= items.identify_fee(e),
            )
            for i, e in enumerate(c.inventory)
            if not e.get("identified", True)
        ]
        rows.append(MenuItem("Nothing today", "back"))
        self.identify_menu = Menu(rows)

    def _to_equip(self):
        self.state_ = "EQUIP"
        c = self.shopper
        rows = [
            MenuItem(
                f"{items.display_name(e):<18}"
                + ("  [equipped]" if e.get("equipped") else ""),
                i,
            )
            for i, e in enumerate(c.inventory)
        ]
        rows.append(MenuItem("Done fitting", "back"))
        self.equip_menu = Menu(rows)

    def _to_trade_items(self):
        self.state_ = "TRADE_ITEMS"
        c = self.shopper
        rows = []
        for i, e in enumerate(c.inventory):
            label = items.display_name(e) + (
                "  [equipped]" if e.get("equipped") else "")
            rows.append(MenuItem(label, i, enabled=not items.is_cursed_stuck(e)))
        rows.append(MenuItem("Never mind", "back"))
        self.trade_item_menu = Menu(rows)

    def _target_menu(self, choices):
        return Menu([
            MenuItem(f"{c.name:<14} {len(c.inventory)}/{items.INVENTORY_CAP} slots", i)
            for i, c in enumerate(choices)
        ] + [MenuItem("Never mind", "back")])

    def handle_event(self, event):
        esc = event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
        if self.state_ == "WHO":
            choice = self.who_menu.handle_event(event)
            if choice == "leave" or esc:
                self.gs.save()
                self.app.pop()
            elif choice is not None:
                self.shopper = self.gs.party[choice]
                self.message = ""
                self._to_shopper_menu()
        elif self.state_ == "SHOP_MENU":
            choice = self.menu.handle_event(event)
            if choice == "buy":
                self._to_buy()
            elif choice == "sell":
                self._to_sell()
            elif choice == "identify":
                self._to_identify()
            elif choice == "equip":
                self._to_equip()
            elif choice == "trade":
                self._to_trade_items()
            elif choice == "pool":
                self.gs.pool_gold(self.shopper)
                self.gs.save()
                self.message = f"The party's gold piles up before {self.shopper.name}."
                self._to_shopper_menu()
            elif choice == "done" or esc:
                self.gs.save()
                self._to_who()
        elif self.state_ == "BUY":
            choice = self.buy_menu.handle_event(event)
            if choice == "back" or esc:
                self._to_shopper_menu()
            elif choice is not None:
                it = items.item(choice)
                c = self.shopper
                c.gold -= it["price"]
                items.add_item(c, choice)
                self.gs.save()
                self.message = f"Bought {it['name']}."
                self._to_buy()  # refresh affordability
        elif self.state_ == "SELL":
            choice = self.sell_menu.handle_event(event)
            if choice == "back" or esc:
                self._to_shopper_menu()
            elif choice is not None:
                entry = items.remove_item(self.shopper, choice)
                price = items.sell_price(entry["key"])
                self.shopper.gold += price
                self.gs.save()
                self.message = f"Sold {items.item(entry['key'])['name']} for {price}g."
                if self.shopper.inventory:
                    self._to_sell()
                else:
                    self._to_shopper_menu()
        elif self.state_ == "IDENTIFY":
            choice = self.identify_menu.handle_event(event)
            if choice == "back" or esc:
                self._to_shopper_menu()
            elif choice is not None:
                entry = self.shopper.inventory[choice]
                self.shopper.gold -= items.identify_fee(entry)
                entry["identified"] = True
                self.gs.save()
                self.message = f"It is... {items.item(entry['key'])['name']}!"
                if any(not e.get("identified", True)
                       for e in self.shopper.inventory):
                    self._to_identify()
                else:
                    self._to_shopper_menu()
        elif self.state_ == "EQUIP":
            choice = self.equip_menu.handle_event(event)
            if choice == "back" or esc:
                self.gs.save()
                self._to_shopper_menu()
            elif choice is not None:
                index = self.equip_menu.index
                ok, msg = items.equip(self.shopper, choice)
                self.message = msg
                self._to_equip()
                self.equip_menu.index = min(index, len(self.equip_menu.items) - 1)
        elif self.state_ == "TRADE_ITEMS":
            choice = self.trade_item_menu.handle_event(event)
            if choice == "back" or esc:
                self._to_shopper_menu()
            elif choice is not None:
                self.trade_index = choice
                self.trade_choices = [c for c in self.gs.party if c is not self.shopper]
                self.trade_target_menu = self._target_menu(self.trade_choices)
                self.state_ = "TRADE_TARGET"
        elif self.state_ == "TRADE_TARGET":
            choice = self.trade_target_menu.handle_event(event)
            if choice == "back" or esc:
                self._to_trade_items()
            elif choice is not None:
                receiver = self.trade_choices[choice]
                ok, msg = items.transfer_item(self.shopper, self.trade_index, receiver)
                self.message = msg
                self.gs.save()
                self._to_shopper_menu()

    def draw(self, surf):
        tr = self.app.text
        draw_panel(surf, (30, 20, 580, 210), tr, "THE IRON LEDGER")
        if not self.gs.party:
            tr.draw(surf, "The shopkeep sees no coin in your future.", (60, 60), palette.DIM)
            tr.draw(surf, "Form a party at the tavern first. (esc)", (60, 90), palette.TEXT)
        elif self.state_ == "WHO":
            tr.draw(surf, "Who steps up to the counter?", (60, 44), palette.TEXT)
            self.who_menu.draw(surf, tr, 80, 70, width=400)
        elif self.state_ == "SHOP_MENU":
            c = self.shopper
            tr.draw(surf, f"{c.name} — {c.gold} gold, "
                    f"{len(c.inventory)}/{items.INVENTORY_CAP} pack slots",
                    (60, 44), palette.TEXT)
            self.menu.draw(surf, tr, 80, 70, width=280)
        elif self.state_ == "BUY":
            tr.draw(surf, f"{self.shopper.name}'s gold: {self.shopper.gold}",
                    (60, 40), palette.ACCENT)
            self.buy_menu.draw(surf, tr, 70, 62, width=360, max_rows=7)
        elif self.state_ == "SELL":
            tr.draw(surf, "The shopkeep pays half of new. No refunds.", (60, 44), palette.DIM)
            self.sell_menu.draw(surf, tr, 70, 66, width=360, max_rows=7)
        elif self.state_ == "IDENTIFY":
            tr.draw(surf, "\"Let's see what you've dragged up...\"", (60, 44), palette.DIM)
            self.identify_menu.draw(surf, tr, 70, 66, width=360, max_rows=7)
        elif self.state_ == "EQUIP":
            tr.draw(surf, f"{self.shopper.name} — AC {self.shopper.ac}", (60, 44), palette.TEXT)
            self.equip_menu.draw(surf, tr, 70, 66, width=340, max_rows=7)
        elif self.state_ == "TRADE_ITEMS":
            tr.draw(surf, f"{self.shopper.name}'s pack — give what?", (60, 44),
                    palette.TEXT)
            self.trade_item_menu.draw(surf, tr, 70, 66, width=340, max_rows=7)
        elif self.state_ == "TRADE_TARGET":
            tr.draw(surf, "Give to whom?", (60, 44), palette.TEXT)
            self.trade_target_menu.draw(surf, tr, 70, 66, width=340)
        if self.message and self.state_ in ("SHOP_MENU", "BUY", "SELL", "EQUIP",
                                            "IDENTIFY", "TRADE_ITEMS", "TRADE_TARGET"):
            tr.draw(surf, self.message, (330, 44), palette.ACCENT)
        draw_party_bar(surf, tr, self.gs.party)
