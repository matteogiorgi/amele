from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path


DATA_FILE = Path(__file__).with_name("condominio_data.json")


@dataclass
class Condomino:
    nome: str
    cognome: str
    telefono: str = ""
    email: str = ""
    codice_fiscale: str = ""

    @property
    def nome_completo(self) -> str:
        return f"{self.nome} {self.cognome}".strip()


@dataclass
class Movimento:
    descrizione: str
    importo: float
    tipo: str
    data_movimento: str = field(default_factory=lambda: date.today().isoformat())


@dataclass
class RendicontoMixin:
    movimenti: list[Movimento] = field(default_factory=list)

    def saldo(self) -> float:
        totale = 0.0
        for movimento in self.movimenti:
            if movimento.tipo == "addebito":
                totale += movimento.importo
            elif movimento.tipo == "pagamento":
                totale -= movimento.importo
        return round(totale, 2)

    def aggiungi_movimento(self, descrizione: str, importo: float, tipo: str) -> None:
        self.movimenti.append(
            Movimento(
                descrizione=descrizione.strip(),
                importo=round(importo, 2),
                tipo=tipo,
            )
        )


@dataclass
class Appartamento(RendicontoMixin):
    codice: str = ""
    interno: str = ""
    piano: str = ""
    superficie_mq: float = 0.0
    millesimi: float = 0.0
    proprietario: str = ""
    occupante: Condomino | None = None
    note: str = ""


@dataclass
class Palazzina(RendicontoMixin):
    nome: str = ""
    appartamenti: list[Appartamento] = field(default_factory=list)
    note: str = ""

    def aggiungi_appartamento(self, appartamento: Appartamento) -> None:
        if self.trova_appartamento(appartamento.codice):
            raise ValueError(
                f"Esiste gia un appartamento con codice {appartamento.codice}."
            )
        self.appartamenti.append(appartamento)

    def trova_appartamento(self, codice: str) -> Appartamento | None:
        for appartamento in self.appartamenti:
            if appartamento.codice == codice:
                return appartamento
        return None

    def rimuovi_appartamento(self, codice: str) -> None:
        appartamento = self.trova_appartamento(codice)
        if not appartamento:
            raise ValueError("Appartamento non trovato.")
        self.appartamenti.remove(appartamento)

    def aggiorna_appartamento(
        self,
        appartamento_corrente: Appartamento,
        *,
        codice: str,
        interno: str,
        piano: str,
        superficie_mq: float,
        millesimi: float,
        proprietario: str,
        note: str,
    ) -> None:
        codice = codice.strip()
        altro = self.trova_appartamento(codice)
        if altro and altro is not appartamento_corrente:
            raise ValueError(f"Esiste gia un appartamento con codice {codice}.")
        appartamento_corrente.codice = codice
        appartamento_corrente.interno = interno.strip()
        appartamento_corrente.piano = piano.strip()
        appartamento_corrente.superficie_mq = round(superficie_mq, 2)
        appartamento_corrente.millesimi = round(millesimi, 2)
        appartamento_corrente.proprietario = proprietario.strip()
        appartamento_corrente.note = note.strip()

    def totale_saldo(self) -> float:
        return round(
            self.saldo()
            + sum(appartamento.saldo() for appartamento in self.appartamenti),
            2,
        )


@dataclass
class Condominio(RendicontoMixin):
    nome: str = ""
    indirizzo: str = ""
    palazzine: list[Palazzina] = field(default_factory=list)
    note: str = ""

    def aggiungi_palazzina(self, palazzina: Palazzina) -> None:
        if self.trova_palazzina(palazzina.nome):
            raise ValueError(f"Esiste gia una palazzina con nome {palazzina.nome}.")
        self.palazzine.append(palazzina)

    def trova_palazzina(self, nome: str) -> Palazzina | None:
        for palazzina in self.palazzine:
            if palazzina.nome == nome:
                return palazzina
        return None

    def rimuovi_palazzina(self, nome: str) -> None:
        palazzina = self.trova_palazzina(nome)
        if not palazzina:
            raise ValueError("Palazzina non trovata.")
        self.palazzine.remove(palazzina)

    def aggiorna_palazzina(
        self,
        palazzina_corrente: Palazzina,
        *,
        nome: str,
        note: str,
    ) -> None:
        nome = nome.strip()
        altra = self.trova_palazzina(nome)
        if altra and altra is not palazzina_corrente:
            raise ValueError(f"Esiste gia una palazzina con nome {nome}.")
        palazzina_corrente.nome = nome
        palazzina_corrente.note = note.strip()

    def totale_saldo(self) -> float:
        return round(
            self.saldo()
            + sum(palazzina.totale_saldo() for palazzina in self.palazzine),
            2,
        )

    def totale_appartamenti(self) -> int:
        return sum(len(palazzina.appartamenti) for palazzina in self.palazzine)


@dataclass
class ArchivioCondomini:
    condomini: list[Condominio] = field(default_factory=list)

    def aggiungi_condominio(self, condominio: Condominio) -> None:
        if self.trova_condominio(condominio.nome):
            raise ValueError(f"Esiste gia un condominio con nome {condominio.nome}.")
        self.condomini.append(condominio)

    def trova_condominio(self, nome: str) -> Condominio | None:
        for condominio in self.condomini:
            if condominio.nome == nome:
                return condominio
        return None

    def rimuovi_condominio(self, nome: str) -> None:
        condominio = self.trova_condominio(nome)
        if not condominio:
            raise ValueError("Condominio non trovato.")
        self.condomini.remove(condominio)

    def aggiorna_condominio(
        self,
        condominio_corrente: Condominio,
        *,
        nome: str,
        indirizzo: str,
        note: str,
    ) -> None:
        nome = nome.strip()
        altro = self.trova_condominio(nome)
        if altro and altro is not condominio_corrente:
            raise ValueError(f"Esiste gia un condominio con nome {nome}.")
        condominio_corrente.nome = nome
        condominio_corrente.indirizzo = indirizzo.strip()
        condominio_corrente.note = note.strip()

    def totale_saldo(self) -> float:
        return round(sum(condominio.totale_saldo() for condominio in self.condomini), 2)

    def totale_palazzine(self) -> int:
        return sum(len(condominio.palazzine) for condominio in self.condomini)

    def totale_appartamenti(self) -> int:
        return sum(condominio.totale_appartamenti() for condominio in self.condomini)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ArchivioCondomini":
        if "condomini" not in data:
            return cls(condomini=[_legacy_condominio_from_dict(data)])

        condomini = []
        for condominio_data in data.get("condomini", []):
            condomini.append(_condominio_from_dict(condominio_data))
        return cls(condomini=condomini)


def _movimenti_from_list(items: list[dict] | None) -> list[Movimento]:
    return [Movimento(**movimento) for movimento in (items or [])]


def _condomino_from_dict(data: dict | None) -> Condomino | None:
    if not data:
        return None
    return Condomino(**data)


def _appartamento_from_dict(data: dict) -> Appartamento:
    return Appartamento(
        codice=data.get("codice", ""),
        interno=data.get("interno", ""),
        piano=data.get("piano", ""),
        superficie_mq=data.get("superficie_mq", 0.0),
        millesimi=data.get("millesimi", 0.0),
        proprietario=data.get("proprietario", ""),
        occupante=_condomino_from_dict(data.get("occupante")),
        note=data.get("note", ""),
        movimenti=_movimenti_from_list(data.get("movimenti")),
    )


def _palazzina_from_dict(data: dict) -> Palazzina:
    appartamenti = [
        _appartamento_from_dict(appartamento)
        for appartamento in data.get("appartamenti", [])
    ]
    return Palazzina(
        nome=data.get("nome", ""),
        appartamenti=appartamenti,
        note=data.get("note", ""),
        movimenti=_movimenti_from_list(data.get("movimenti")),
    )


def _condominio_from_dict(data: dict) -> Condominio:
    palazzine = [
        _palazzina_from_dict(palazzina) for palazzina in data.get("palazzine", [])
    ]
    return Condominio(
        nome=data.get("nome", "Nuovo Condominio"),
        indirizzo=data.get("indirizzo", ""),
        palazzine=palazzine,
        note=data.get("note", ""),
        movimenti=_movimenti_from_list(data.get("movimenti")),
    )


def _legacy_condominio_from_dict(data: dict) -> Condominio:
    appartamenti = [
        _appartamento_from_dict(appartamento)
        for appartamento in data.get("appartamenti", [])
    ]
    palazzine = []
    if appartamenti:
        palazzine.append(
            Palazzina(
                nome="Palazzina A",
                appartamenti=appartamenti,
            )
        )
    return Condominio(
        nome=data.get("nome", "Nuovo Condominio"),
        indirizzo=data.get("indirizzo", ""),
        palazzine=palazzine,
        movimenti=_movimenti_from_list(data.get("movimenti")),
    )


def salva_archivio(archivio: ArchivioCondomini, file_path: Path = DATA_FILE) -> None:
    file_path.write_text(
        json.dumps(archivio.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )


def carica_archivio(file_path: Path = DATA_FILE) -> ArchivioCondomini:
    if not file_path.exists():
        return ArchivioCondomini()
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return ArchivioCondomini.from_dict(data)


def carica_condominio(file_path: Path = DATA_FILE) -> ArchivioCondomini:
    return carica_archivio(file_path)


def salva_condominio(archivio: ArchivioCondomini, file_path: Path = DATA_FILE) -> None:
    salva_archivio(archivio, file_path)
