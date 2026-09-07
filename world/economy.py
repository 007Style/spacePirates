"""world/economy.py — Dynamic economy: price tables, supply/demand, contraband."""
from __future__ import annotations
import random
import json
import os
from settings import DATA_DIR


# Base prices for resources (credits per unit)
BASE_RESOURCE_PRICES = {
    "metal":         50,
    "fuel":          30,
    "supplies":      20,
    "void_crystals": 500,
    "contraband":    200,
}

# Items legal everywhere vs. contraband in specific nations
CONTRABAND_NATIONS = {
    "contraband": ["terran_compact", "merchant_syndicate", "technocracy"],
}


class SectorEconomy:
    """Per-sector price state."""
    def __init__(self, sector_id: str, nation_id: str = ""):
        self.sector_id  = sector_id
        self.nation_id  = nation_id
        # Price multipliers start at 1.0, drift with supply/demand
        self.multipliers: dict[str, float] = {k: 1.0 for k in BASE_RESOURCE_PRICES}
        # Randomly init slight variance
        for k in self.multipliers:
            self.multipliers[k] = round(random.uniform(0.8, 1.3), 2)

    def get_price(self, resource: str, rep_modifier: float = 1.0) -> int:
        base = BASE_RESOURCE_PRICES.get(resource, 100)
        mult = self.multipliers.get(resource, 1.0)
        return max(1, int(base * mult * rep_modifier))

    def on_sell(self, resource: str, amount: int) -> None:
        """Selling increases supply → lowers price."""
        m = self.multipliers.get(resource, 1.0)
        self.multipliers[resource] = max(0.5, m - 0.02 * amount)

    def on_buy(self, resource: str, amount: int) -> None:
        """Buying decreases supply → raises price."""
        m = self.multipliers.get(resource, 1.0)
        self.multipliers[resource] = min(3.0, m + 0.03 * amount)

    def drift(self) -> None:
        """Gradual drift back toward baseline."""
        for k in self.multipliers:
            m = self.multipliers[k]
            if m > 1.0:
                self.multipliers[k] = max(1.0, m - 0.01)
            elif m < 1.0:
                self.multipliers[k] = min(1.0, m + 0.01)

    def to_dict(self) -> dict:
        return {"sector_id": self.sector_id, "multipliers": self.multipliers}


class AuctionItem:
    def __init__(self, item_data: dict, starting_bid: int, duration: float = 120.0):
        self.item_data    = item_data
        self.current_bid  = starting_bid
        self.high_bidder  = "NPC"
        self.duration     = duration
        self.elapsed      = 0.0
        self.sold         = False

    @property
    def time_left(self) -> float:
        return max(0.0, self.duration - self.elapsed)

    def npc_bid(self) -> None:
        """Simulate NPC counter-bid."""
        if random.random() < 0.4:
            self.current_bid = int(self.current_bid * random.uniform(1.05, 1.20))
            self.high_bidder = "NPC"

    def player_bid(self, amount: int) -> bool:
        if amount > self.current_bid:
            self.current_bid = amount
            self.high_bidder = "player"
            return True
        return False

    def tick(self, dt: float) -> bool:
        """Returns True when auction ends."""
        self.elapsed += dt
        if not self.sold and random.random() < 0.02:  # occasional NPC counter
            self.npc_bid()
        if self.elapsed >= self.duration:
            self.sold = True
            return True
        return False


class Economy:
    DRIFT_INTERVAL = 60.0  # seconds between price drift ticks

    def __init__(self, galaxy=None, reputation_mgr=None):
        self.galaxy         = galaxy
        self.rep_mgr        = reputation_mgr
        self._sector_econs: dict[str, SectorEconomy] = {}
        self._drift_timer   = 0.0
        self.active_auctions: list[AuctionItem] = []
        self._auction_timer  = 300.0   # seconds between new auctions at nation stations

        if galaxy:
            for sid, sector in galaxy.sectors.items():
                self._sector_econs[sid] = SectorEconomy(sid, sector.nation_id)

    def sector_economy(self, sector_id: str) -> SectorEconomy:
        if sector_id not in self._sector_econs:
            self._sector_econs[sector_id] = SectorEconomy(sector_id)
        return self._sector_econs[sector_id]

    # ── Buy / Sell ─────────────────────────────────────────────────────────────
    def buy_resource(self, sector_id: str, resource: str, amount: int,
                     player_credits: int, nation_id: str = "") -> dict:
        econ    = self.sector_economy(sector_id)
        rep_mod = self.rep_mgr.price_modifier(nation_id) if self.rep_mgr else 1.0
        price   = econ.get_price(resource, rep_mod) * amount
        if player_credits < price:
            return {"ok": False, "reason": f"Need {price} credits"}
        econ.on_buy(resource, amount)
        return {"ok": True, "cost": price, "resource": resource, "amount": amount}

    def sell_resource(self, sector_id: str, resource: str, amount: int,
                      nation_id: str = "") -> dict:
        econ    = self.sector_economy(sector_id)
        rep_mod = self.rep_mgr.price_modifier(nation_id) if self.rep_mgr else 1.0
        # Sell at 60% of buy price
        price   = int(econ.get_price(resource, rep_mod) * 0.6) * amount
        econ.on_sell(resource, amount)
        return {"ok": True, "earned": price, "resource": resource, "amount": amount}

    # ── Contraband ────────────────────────────────────────────────────────────
    def scan_for_contraband(self, ship, nation_id: str, wanted_level: int) -> dict:
        contraband_nations = CONTRABAND_NATIONS.get("contraband", [])
        if nation_id not in contraband_nations:
            return {"caught": False}
        has_contraband = ship.resources.get("contraband", 0) if hasattr(ship, "resources") else 0
        if not has_contraband:
            return {"caught": False}
        # Catch chance scales with wanted level
        catch_chance = 0.2 + wanted_level * 0.12
        # Smuggler path reduces chance
        if hasattr(ship, "chosen_path") and ship.chosen_path == "B":
            catch_chance *= 0.5
        if random.random() < catch_chance:
            return {"caught": True, "confiscated": has_contraband,
                    "fine": has_contraband * 150}
        return {"caught": False}

    # ── Black Market ──────────────────────────────────────────────────────────
    def get_black_market_stock(self, luck: float = 0.0) -> list[dict]:
        from progression.rarity import rarity_system
        try:
            with open(os.path.join(DATA_DIR, "weapons.json")) as f:
                pool = json.load(f)
            return rarity_system.roll_drop_table(pool, luck=luck + 1.0, count=4)
        except Exception:
            return []

    # ── Auction House ─────────────────────────────────────────────────────────
    def start_auction(self, item_data: dict) -> None:
        base_price = item_data.get("price", 500)
        starting   = int(base_price * random.uniform(0.4, 0.8))
        self.active_auctions.append(AuctionItem(item_data, starting))

    def update(self, dt: float) -> list[dict]:
        events: list[dict] = []
        self._drift_timer -= dt
        if self._drift_timer <= 0:
            self._drift_timer = self.DRIFT_INTERVAL
            for econ in self._sector_econs.values():
                econ.drift()

        # Auction ticks
        for auction in list(self.active_auctions):
            ended = auction.tick(dt)
            if ended:
                events.append({"type": "auction_ended", "auction": auction})
                self.active_auctions.remove(auction)

        self._auction_timer -= dt
        if self._auction_timer <= 0:
            self._auction_timer = 300.0
            self._maybe_spawn_auction()

        return events

    def _maybe_spawn_auction(self) -> None:
        try:
            with open(os.path.join(DATA_DIR, "weapons.json")) as f:
                pool = json.load(f)
            if pool:
                item = random.choice(pool)
                self.start_auction(item)
                from core.events import bus
                bus.publish("notification",
                            msg=f"🔔 Auction started: {item['name']}!",
                            color=(255, 200, 40))
        except Exception:
            pass

    def to_dict(self) -> dict:
        return {
            "sector_econs": {sid: e.to_dict()
                             for sid, e in self._sector_econs.items()},
        }
