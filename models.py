"""Data model for the condominium archive: hierarchy, balances, and JSON persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path


DATA_FILE = Path(__file__).with_name("data.json")


@dataclass
class Person:
    """A condominium member — used both as an apartment's owner and its occupant."""

    first_name: str
    last_name: str
    phone: str = ""
    email: str = ""
    tax_code: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@dataclass
class Transaction:
    """A single accounting entry: either a charge or a payment."""

    description: str
    amount: float
    type: str
    transaction_date: str = field(default_factory=lambda: date.today().isoformat())


@dataclass
class StatementMixin:
    """Shared balance/transaction bookkeeping reused by every hierarchy level."""

    transactions: list[Transaction] = field(default_factory=list)

    def balance(self) -> float:
        total = 0.0
        for transaction in self.transactions:
            if transaction.type == "charge":
                total += transaction.amount
            elif transaction.type == "payment":
                total -= transaction.amount
        return round(total, 2)

    def add_transaction(self, description: str, amount: float, type: str) -> None:
        self.transactions.append(
            Transaction(
                description=description.strip(),
                amount=round(amount, 2),
                type=type,
            )
        )


@dataclass
class Apartment(StatementMixin):
    code: str = ""
    unit: str = ""
    floor: str = ""
    area_sqm: float = 0.0
    shares: float = 0.0
    owner: Person = field(default_factory=lambda: Person(first_name="", last_name=""))
    occupant: Person | None = None
    notes: str = ""


@dataclass
class Building(StatementMixin):
    name: str = ""
    apartments: list[Apartment] = field(default_factory=list)
    notes: str = ""

    def add_apartment(self, apartment: Apartment) -> None:
        if self.find_apartment(apartment.code):
            raise ValueError(f"An apartment with code {apartment.code} already exists.")
        self.apartments.append(apartment)

    def find_apartment(self, code: str) -> Apartment | None:
        for apartment in self.apartments:
            if apartment.code == code:
                return apartment
        return None

    def remove_apartment(self, code: str) -> None:
        apartment = self.find_apartment(code)
        if not apartment:
            raise ValueError("Apartment not found.")
        self.apartments.remove(apartment)

    def update_apartment(
        self,
        current_apartment: Apartment,
        *,
        code: str,
        unit: str,
        floor: str,
        area_sqm: float,
        shares: float,
        owner: Person,
        notes: str,
    ) -> None:
        code = code.strip()
        other = self.find_apartment(code)
        if other and other is not current_apartment:
            raise ValueError(f"An apartment with code {code} already exists.")
        previous_owner = current_apartment.owner
        # If the occupant was just mirroring the owner, keep mirroring the new owner.
        occupant_matches_owner = current_apartment.occupant == previous_owner
        current_apartment.code = code
        current_apartment.unit = unit.strip()
        current_apartment.floor = floor.strip()
        current_apartment.area_sqm = round(area_sqm, 2)
        current_apartment.shares = round(shares, 2)
        current_apartment.owner = owner
        if occupant_matches_owner:
            current_apartment.occupant = owner
        current_apartment.notes = notes.strip()

    def total_balance(self) -> float:
        return round(
            self.balance() + sum(apartment.balance() for apartment in self.apartments),
            2,
        )


@dataclass
class Condominium(StatementMixin):
    name: str = ""
    address: str = ""
    buildings: list[Building] = field(default_factory=list)
    notes: str = ""

    def add_building(self, building: Building) -> None:
        if self.find_building(building.name):
            raise ValueError(f"A building named {building.name} already exists.")
        self.buildings.append(building)

    def find_building(self, name: str) -> Building | None:
        for building in self.buildings:
            if building.name == name:
                return building
        return None

    def remove_building(self, name: str) -> None:
        building = self.find_building(name)
        if not building:
            raise ValueError("Building not found.")
        self.buildings.remove(building)

    def update_building(
        self,
        current_building: Building,
        *,
        name: str,
        notes: str,
    ) -> None:
        name = name.strip()
        other = self.find_building(name)
        if other and other is not current_building:
            raise ValueError(f"A building named {name} already exists.")
        current_building.name = name
        current_building.notes = notes.strip()

    def total_balance(self) -> float:
        return round(
            self.balance() + sum(building.total_balance() for building in self.buildings),
            2,
        )

    def total_apartments(self) -> int:
        return sum(len(building.apartments) for building in self.buildings)


@dataclass
class CondominiumArchive:
    condominiums: list[Condominium] = field(default_factory=list)

    def add_condominium(self, condominium: Condominium) -> None:
        if self.find_condominium(condominium.name):
            raise ValueError(f"A condominium named {condominium.name} already exists.")
        self.condominiums.append(condominium)

    def find_condominium(self, name: str) -> Condominium | None:
        for condominium in self.condominiums:
            if condominium.name == name:
                return condominium
        return None

    def remove_condominium(self, name: str) -> None:
        condominium = self.find_condominium(name)
        if not condominium:
            raise ValueError("Condominium not found.")
        self.condominiums.remove(condominium)

    def update_condominium(
        self,
        current_condominium: Condominium,
        *,
        name: str,
        address: str,
        notes: str,
    ) -> None:
        name = name.strip()
        other = self.find_condominium(name)
        if other and other is not current_condominium:
            raise ValueError(f"A condominium named {name} already exists.")
        current_condominium.name = name
        current_condominium.address = address.strip()
        current_condominium.notes = notes.strip()

    def total_balance(self) -> float:
        return round(sum(c.total_balance() for c in self.condominiums), 2)

    def total_buildings(self) -> int:
        return sum(len(c.buildings) for c in self.condominiums)

    def total_apartments(self) -> int:
        return sum(c.total_apartments() for c in self.condominiums)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CondominiumArchive":
        if "condominiums" not in data:
            # Pre-archive flat format: a single condominium with no wrapping archive.
            return cls(condominiums=[_legacy_condominium_from_dict(data)])

        condominiums = []
        for condominium_data in data.get("condominiums", []):
            condominiums.append(_condominium_from_dict(condominium_data))
        return cls(condominiums=condominiums)


def _transactions_from_list(items: list[dict] | None) -> list[Transaction]:
    return [Transaction(**transaction) for transaction in (items or [])]


def _person_from_dict(data: dict | None) -> Person | None:
    if not data:
        return None
    return Person(**data)


def _owner_from_legacy(value: str | dict | None) -> Person:
    """Older data files stored the owner as a plain "First Last" string."""
    if isinstance(value, dict):
        return Person(**value)
    if not value:
        return Person(first_name="", last_name="")
    parts = str(value).strip().split(maxsplit=1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""
    return Person(first_name=first_name, last_name=last_name)


def _apartment_from_dict(data: dict) -> Apartment:
    owner = _owner_from_legacy(data.get("owner"))
    occupant = _person_from_dict(data.get("occupant")) or owner
    return Apartment(
        code=data.get("code", ""),
        unit=data.get("unit", ""),
        floor=data.get("floor", ""),
        area_sqm=data.get("area_sqm", 0.0),
        shares=data.get("shares", 0.0),
        owner=owner,
        occupant=occupant,
        notes=data.get("notes", ""),
        transactions=_transactions_from_list(data.get("transactions")),
    )


def _building_from_dict(data: dict) -> Building:
    apartments = [
        _apartment_from_dict(apartment) for apartment in data.get("apartments", [])
    ]
    return Building(
        name=data.get("name", ""),
        apartments=apartments,
        notes=data.get("notes", ""),
        transactions=_transactions_from_list(data.get("transactions")),
    )


def _condominium_from_dict(data: dict) -> Condominium:
    buildings = [_building_from_dict(building) for building in data.get("buildings", [])]
    return Condominium(
        name=data.get("name", "New Condominium"),
        address=data.get("address", ""),
        buildings=buildings,
        notes=data.get("notes", ""),
        transactions=_transactions_from_list(data.get("transactions")),
    )


def _legacy_condominium_from_dict(data: dict) -> Condominium:
    """Very old flat format: apartments directly under the condominium, no buildings."""
    apartments = [
        _apartment_from_dict(apartment) for apartment in data.get("apartments", [])
    ]
    buildings = []
    if apartments:
        buildings.append(Building(name="Building A", apartments=apartments))
    return Condominium(
        name=data.get("name", "New Condominium"),
        address=data.get("address", ""),
        buildings=buildings,
        transactions=_transactions_from_list(data.get("transactions")),
    )


def save_archive(archive: CondominiumArchive, file_path: Path = DATA_FILE) -> None:
    file_path.write_text(
        json.dumps(archive.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_archive(file_path: Path = DATA_FILE) -> CondominiumArchive:
    if not file_path.exists():
        return CondominiumArchive()
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return CondominiumArchive.from_dict(data)
