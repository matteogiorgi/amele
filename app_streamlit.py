from __future__ import annotations

from datetime import date
from io import BytesIO
import re
from typing import Iterable, cast

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, PropertySet, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from condominio import (
    Appartamento,
    ArchivioCondomini,
    Condomino,
    Condominio,
    Palazzina,
    carica_archivio,
    salva_archivio,
)


st.set_page_config(
    page_title="Archivio Condomini",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(194, 220, 255, 0.95), transparent 25%),
                    radial-gradient(circle at 85% 0%, rgba(255, 227, 191, 0.85), transparent 22%),
                    linear-gradient(180deg, #f5efe3 0%, #edf2f7 100%);
            }
            .block-container {
                padding-top: 1.6rem;
                padding-bottom: 2rem;
            }
            .hero-card {
                padding: 1.5rem 1.6rem;
                border-radius: 26px;
                background: rgba(255, 255, 255, 0.84);
                border: 1px solid rgba(19, 48, 70, 0.08);
                box-shadow: 0 20px 45px rgba(21, 37, 53, 0.08);
                backdrop-filter: blur(10px);
                margin-bottom: 1rem;
            }
            .eyebrow {
                font-size: 0.82rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                color: #8a5a24;
                margin-bottom: 0.35rem;
                font-weight: 700;
            }
            .headline {
                font-size: 2.2rem;
                line-height: 1.05;
                font-weight: 800;
                color: #163047;
                margin: 0;
            }
            .subhead {
                color: #4a5f70;
                margin-top: 0.65rem;
                margin-bottom: 0;
                font-size: 1rem;
            }
            .card {
                padding: 1rem 1.1rem;
                border-radius: 20px;
                background: rgba(255, 255, 255, 0.78);
                border: 1px solid rgba(19, 48, 70, 0.08);
                box-shadow: 0 14px 30px rgba(21, 37, 53, 0.06);
            }
            .badge {
                display: inline-block;
                padding: 0.22rem 0.58rem;
                border-radius: 999px;
                background: #163047;
                color: white;
                font-size: 0.82rem;
                font-weight: 700;
                margin-bottom: 0.55rem;
            }
            button:disabled {
                opacity: 1 !important;
                cursor: default !important;
            }
            button[kind="secondary"]:disabled {
                background: linear-gradient(135deg, #163047 0%, #29506f 100%) !important;
                color: white !important;
                border: 1px solid rgba(22, 48, 71, 0.15) !important;
            }
            div[data-baseweb="select"] > div {
                background: linear-gradient(135deg, #163047 0%, #29506f 100%);
                border-color: rgba(22, 48, 71, 0.15);
                color: white;
            }
            div[data-baseweb="select"] span {
                color: white;
            }
            div[data-baseweb="select"] svg {
                fill: white;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_archivio() -> ArchivioCondomini:
    if "archivio_condomini" not in st.session_state:
        st.session_state.archivio_condomini = carica_archivio()
    return st.session_state.archivio_condomini


def get_active_section() -> str:
    pending_section = st.session_state.pop("next_active_section", None)
    if pending_section:
        st.session_state.active_section = pending_section
    if "active_section" not in st.session_state:
        st.session_state.active_section = "Condomini"
    if st.session_state.active_section not in {
        "Condomini",
        "Palazzine",
        "Appartamenti",
    }:
        st.session_state.active_section = "Condomini"
    return st.session_state.active_section


def save_and_refresh(
    archivio: ArchivioCondomini, message: str, active_section: str | None = None
) -> None:
    salva_archivio(archivio)
    st.session_state.archivio_condomini = archivio
    st.session_state.flash_message = message
    if active_section:
        st.session_state.next_active_section = active_section
    st.rerun()


def show_flash_message() -> None:
    message = st.session_state.pop("flash_message", None)
    if message:
        st.success(message)


def format_currency(value: float) -> str:
    return f"€ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def total_registered_payments(movimenti: Iterable) -> float:
    totale = 0.0
    for movimento in movimenti:
        if movimento.tipo == "pagamento":
            totale += movimento.importo
    return round(totale, 2)


def condominio_options(archivio: ArchivioCondomini) -> dict[str, Condominio]:
    ordered = sorted(archivio.condomini, key=lambda item: item.nome.lower())
    return {condominio.nome: condominio for condominio in ordered}


def palazzina_options(condominio: Condominio) -> dict[str, Palazzina]:
    ordered = sorted(condominio.palazzine, key=lambda item: item.nome.lower())
    return {palazzina.nome: palazzina for palazzina in ordered}


def appartamento_options(palazzina: Palazzina) -> dict[str, Appartamento]:
    ordered = sorted(
        palazzina.appartamenti, key=lambda item: (item.interno, item.codice)
    )
    return {
        f"{appartamento.codice} · int. {appartamento.interno} · piano {appartamento.piano}": appartamento
        for appartamento in ordered
    }


def condomino_compilato(nome: str, cognome: str) -> bool:
    return bool(nome.strip() and cognome.strip())


def build_condomino(
    *,
    nome: str,
    cognome: str,
    telefono: str = "",
    email: str = "",
    codice_fiscale: str = "",
) -> Condomino:
    return Condomino(
        nome=nome.strip(),
        cognome=cognome.strip(),
        telefono=telefono.strip(),
        email=email.strip(),
        codice_fiscale=codice_fiscale.strip(),
    )


def slugify_filename(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip())
    return slug.strip("_") or "export"


def location_from_address(address: str) -> str:
    if not address.strip():
        return "Luogo non specificato"
    parts = [part.strip() for part in address.split(",") if part.strip()]
    return parts[-1] if parts else address.strip()


def format_document_date(value: date) -> str:
    mesi = [
        "gennaio",
        "febbraio",
        "marzo",
        "aprile",
        "maggio",
        "giugno",
        "luglio",
        "agosto",
        "settembre",
        "ottobre",
        "novembre",
        "dicembre",
    ]
    return f"{value.day} {mesi[value.month - 1]} {value.year}"


def _pdf_paragraph(
    text: str, style: PropertySet, *, allow_markup: bool = False
) -> Paragraph:
    if allow_markup:
        safe_text = text.replace("&", "&amp;")
    else:
        safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe_text, cast(ParagraphStyle, style))


def _build_info_table(rows: list[tuple[str, str]], styles) -> Table:
    data = [
        [
            _pdf_paragraph(f"<b>{label}</b>", styles["BodyText"], allow_markup=True),
            _pdf_paragraph(value or "-", styles["BodyText"]),
        ]
        for label, value in rows
    ]
    table = Table(data, colWidths=[4.2 * cm, 11.8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _build_grid_table(headers: list[str], rows: list[list[str]], styles) -> Table:
    data = [
        [
            _pdf_paragraph(f"<b>{header}</b>", styles["BodyText"], allow_markup=True)
            for header in headers
        ]
    ]
    data.extend(
        [
            [_pdf_paragraph(value or "-", styles["BodyText"]) for value in row]
            for row in rows
        ]
    )
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e7f5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#163047")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c9d4df")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f5f7fa")],
                ),
            ]
        )
    )
    return table


def build_component_pdf(
    *,
    title: str,
    info_rows: list[tuple[str, str]],
    movement_rows: list[list[str]],
    child_table: tuple[list[str], list[list[str]]] | None = None,
    footer_text: str | None = None,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#163047"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="FooterRight",
            parent=styles["BodyText"],
            alignment=2,
            textColor=colors.HexColor("#4a5f70"),
        )
    )

    story = [
        _pdf_paragraph(title, styles["Title"]),
        Spacer(1, 0.35 * cm),
        _pdf_paragraph("Dati principali", styles["SectionTitle"]),
        _build_info_table(info_rows, styles),
        Spacer(1, 0.35 * cm),
    ]

    if child_table and child_table[1]:
        headers, rows = child_table
        story.extend(
            [
                _pdf_paragraph("Elementi collegati", styles["SectionTitle"]),
                _build_grid_table(headers, rows, styles),
                Spacer(1, 0.35 * cm),
            ]
        )

    story.append(_pdf_paragraph("Movimenti", styles["SectionTitle"]))
    if movement_rows:
        story.append(
            _build_grid_table(
                ["Data", "Tipo", "Descrizione", "Importo"], movement_rows, styles
            )
        )
    else:
        story.append(_pdf_paragraph("Nessun movimento registrato.", styles["BodyText"]))

    if footer_text:
        story.extend(
            [
                Spacer(1, 0.5 * cm),
                _pdf_paragraph(footer_text, styles["FooterRight"]),
            ]
        )

    doc.build(story)
    return buffer.getvalue()


def render_export_button(*, label: str, pdf_bytes: bytes, filename: str) -> None:
    st.download_button(
        label,
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        use_container_width=True,
    )


def persistent_selectbox(
    label: str,
    options: list[str],
    *,
    state_key: str,
    widget_key: str,
) -> str:
    if not options:
        raise ValueError("Le opzioni del selettore non possono essere vuote.")

    selected = st.session_state.get(state_key)
    if selected not in options:
        selected = options[0]
    st.session_state[state_key] = selected

    widget_value = st.session_state.get(widget_key)
    if widget_value not in options:
        st.session_state[widget_key] = selected

    def sync_selection() -> None:
        st.session_state[state_key] = st.session_state[widget_key]

    return st.selectbox(
        label,
        options,
        key=widget_key,
        on_change=sync_selection,
    )


def all_movements(archivio: ArchivioCondomini) -> list:
    movements = []
    for condominio in archivio.condomini:
        movements.extend(condominio.movimenti)
        for palazzina in condominio.palazzine:
            movements.extend(palazzina.movimenti)
            for appartamento in palazzina.appartamenti:
                movements.extend(appartamento.movimenti)
    return movements


def render_header(archivio: ArchivioCondomini) -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="eyebrow">Amministratore Elettronico</div>
            <h1 class="headline">AmEle</h1>
            <p class="subhead">
                {len(archivio.condomini)} condomini, {archivio.totale_palazzine()} palazzine e {archivio.totale_appartamenti()} appartamenti con rendiconti separati.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_global_summary(archivio: ArchivioCondomini) -> None:
    all_payments = total_registered_payments(all_movements(archivio))
    residenti = sum(
        1
        for condominio in archivio.condomini
        for palazzina in condominio.palazzine
        for appartamento in palazzina.appartamenti
        if appartamento.occupante
    )
    with st.sidebar:
        st.markdown("### Resoconto globale")
        st.metric("Condomini", len(archivio.condomini))
        st.metric("Palazzine", archivio.totale_palazzine())
        st.metric("Appartamenti", archivio.totale_appartamenti())
        st.metric("Saldo complessivo", format_currency(archivio.totale_saldo()))
        st.metric("Residenti assegnati", residenti)
        st.metric("Pagamenti registrati", format_currency(all_payments))


def render_section_nav() -> str:
    sections = ["Condomini", "Palazzine", "Appartamenti"]
    active_section = get_active_section()
    cols = st.columns(len(sections))
    for col, section in zip(cols, sections):
        with col:
            clicked = st.button(
                section,
                key=f"nav_{section}",
                use_container_width=True,
                type="secondary",
                disabled=(section == active_section),
            )
            if clicked:
                st.session_state.active_section = section
                st.rerun()
    return active_section


def render_rendiconto_panel(
    archivio: ArchivioCondomini,
    *,
    target,
    title: str,
    active_section: str,
    saldo_complessivo_label: str | None = None,
    saldo_complessivo_valore: float | None = None,
) -> None:
    col1, col2 = st.columns([1.1, 1.2])
    with col1:
        st.write(f"**{title}**")
        st.metric("Saldo proprio", format_currency(target.saldo()))
        if saldo_complessivo_label and saldo_complessivo_valore is not None:
            st.metric(
                saldo_complessivo_label,
                format_currency(saldo_complessivo_valore),
            )
        if st.button(
            "Nuovo movimento",
            key=f"open_new_movement_{active_section}",
            use_container_width=True,
        ):
            open_add_movimento_dialog(
                archivio,
                target=target,
                title=title,
                active_section=active_section,
            )

    with col2:
        st.write("**Movimenti registrati**")
        if not target.movimenti:
            st.caption("Nessun movimento presente.")
        else:
            rows = [
                {
                    "Data": movimento.data_movimento,
                    "Tipo": movimento.tipo,
                    "Descrizione": movimento.descrizione,
                    "Importo": format_currency(movimento.importo),
                }
                for movimento in reversed(target.movimenti)
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)


@st.dialog("Nuovo movimento", width="large")
def open_add_movimento_dialog(
    archivio: ArchivioCondomini,
    *,
    target,
    title: str,
    active_section: str,
) -> None:
    st.caption(title)
    with st.form(f"movement_form_{active_section}", clear_on_submit=True):
        descrizione = st.text_input("Descrizione")
        tipo = st.selectbox("Tipo movimento", ["addebito", "pagamento"])
        importo = st.number_input("Importo", min_value=0.0, step=10.0, format="%.2f")
        submitted = st.form_submit_button(
            "Registra movimento", use_container_width=True
        )
    if submitted:
        if not descrizione.strip():
            st.error("La descrizione è obbligatoria.")
        else:
            target.aggiungi_movimento(
                descrizione=descrizione.strip(), importo=importo, tipo=tipo
            )
            save_and_refresh(archivio, "Movimento registrato.", active_section)


@st.dialog("Aggiungi condominio", width="large")
def open_add_condominio_dialog(archivio: ArchivioCondomini) -> None:
    with st.form("new_condominio", clear_on_submit=True):
        nome = st.text_input("Nome condominio")
        indirizzo = st.text_input("Indirizzo")
        note = st.text_area("Note", height=90)
        submitted = st.form_submit_button("Conferma aggiunta", use_container_width=True)
    if submitted:
        if not nome.strip():
            st.error("Il nome del condominio è obbligatorio.")
        else:
            try:
                archivio.aggiungi_condominio(
                    Condominio(
                        nome=nome.strip(),
                        indirizzo=indirizzo.strip(),
                        note=note.strip(),
                    )
                )
            except ValueError as error:
                st.error(str(error))
            else:
                save_and_refresh(archivio, "Condominio aggiunto.", "Condomini")


@st.dialog("Aggiungi palazzina", width="large")
def open_add_palazzina_dialog(
    archivio: ArchivioCondomini, condominio: Condominio
) -> None:
    st.caption(f"Condominio selezionato: {condominio.nome}")
    with st.form("new_palazzina", clear_on_submit=True):
        nome = st.text_input("Nome palazzina")
        note = st.text_area("Note palazzina", height=100)
        submitted = st.form_submit_button("Conferma aggiunta", use_container_width=True)
    if submitted:
        if not nome.strip():
            st.error("Il nome della palazzina è obbligatorio.")
        else:
            try:
                condominio.aggiungi_palazzina(
                    Palazzina(nome=nome.strip(), note=note.strip())
                )
            except ValueError as error:
                st.error(str(error))
            else:
                save_and_refresh(archivio, "Palazzina aggiunta.", "Palazzine")


@st.dialog("Aggiungi appartamento", width="large")
def open_add_appartamento_dialog(
    archivio: ArchivioCondomini,
    condominio: Condominio,
    palazzina: Palazzina,
) -> None:
    st.caption(
        f"Condominio selezionato: {condominio.nome} | Palazzina selezionata: {palazzina.nome}"
    )
    with st.form("new_appartamento", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        codice = c1.text_input("Codice")
        interno = c2.text_input("Interno")
        piano = c3.text_input("Piano")
        c4, c5, c6 = st.columns(3)
        superficie = c4.number_input(
            "Superficie mq", min_value=0.0, step=1.0, format="%.2f"
        )
        millesimi = c5.number_input("Millesimi", min_value=0.0, step=1.0, format="%.2f")
        prop_nome = c6.text_input("Nome proprietario")
        prop_cols = st.columns(3)
        prop_cognome = prop_cols[0].text_input("Cognome proprietario")
        prop_tel = prop_cols[1].text_input("Telefono proprietario")
        prop_email = prop_cols[2].text_input("Email proprietario")
        prop_cf = st.text_input("Codice fiscale proprietario")
        note = st.text_area("Note", height=100)
        st.caption(
            "Residente opzionale. Se lasci nome e cognome vuoti, verrà usato automaticamente il proprietario."
        )
        o1, o2, o3 = st.columns(3)
        occ_nome = o1.text_input("Nome residente")
        occ_cognome = o2.text_input("Cognome residente")
        occ_tel = o3.text_input("Telefono residente")
        o4, o5 = st.columns(2)
        occ_email = o4.text_input("Email residente")
        occ_cf = o5.text_input("Codice fiscale residente")
        submitted = st.form_submit_button("Conferma aggiunta", use_container_width=True)
    if submitted:
        if (
            not codice.strip()
            or not interno.strip()
            or not piano.strip()
            or not condomino_compilato(prop_nome, prop_cognome)
        ):
            st.error(
                "Codice, interno, piano, nome e cognome del proprietario sono obbligatori."
            )
        else:
            proprietario = build_condomino(
                nome=prop_nome,
                cognome=prop_cognome,
                telefono=prop_tel,
                email=prop_email,
                codice_fiscale=prop_cf,
            )
            occupante = proprietario
            if occ_nome.strip() or occ_cognome.strip():
                if not condomino_compilato(occ_nome, occ_cognome):
                    st.error(
                        "Se specifichi il residente, nome e cognome sono obbligatori."
                    )
                    return
                occupante = build_condomino(
                    nome=occ_nome,
                    cognome=occ_cognome,
                    telefono=occ_tel,
                    email=occ_email,
                    codice_fiscale=occ_cf,
                )
            try:
                palazzina.aggiungi_appartamento(
                    Appartamento(
                        codice=codice.strip(),
                        interno=interno.strip(),
                        piano=piano.strip(),
                        superficie_mq=round(superficie, 2),
                        millesimi=round(millesimi, 2),
                        proprietario=proprietario,
                        occupante=occupante,
                        note=note.strip(),
                    )
                )
            except ValueError as error:
                st.error(str(error))
            else:
                save_and_refresh(archivio, "Appartamento aggiunto.", "Appartamenti")


@st.dialog("Modifica condominio", width="large")
def open_edit_condominio_dialog(
    archivio: ArchivioCondomini, target: Condominio
) -> None:
    with st.form("update_condominio"):
        nome = st.text_input("Nome condominio", value=target.nome)
        indirizzo = st.text_input("Indirizzo", value=target.indirizzo)
        note = st.text_area("Note", value=target.note, height=90)
        submitted = st.form_submit_button("Salva modifiche", use_container_width=True)
    if submitted:
        if not nome.strip():
            st.error("Il nome del condominio è obbligatorio.")
        else:
            try:
                archivio.aggiorna_condominio(
                    target,
                    nome=nome,
                    indirizzo=indirizzo,
                    note=note,
                )
            except ValueError as error:
                st.error(str(error))
            else:
                save_and_refresh(archivio, "Condominio aggiornato.", "Condomini")


@st.dialog("Modifica palazzina", width="large")
def open_edit_palazzina_dialog(
    archivio: ArchivioCondomini, condominio: Condominio, target: Palazzina
) -> None:
    st.caption(f"Condominio selezionato: {condominio.nome}")
    with st.form("update_palazzina"):
        nome = st.text_input("Nome palazzina", value=target.nome)
        note = st.text_area("Note palazzina", value=target.note, height=100)
        submitted = st.form_submit_button("Salva modifiche", use_container_width=True)
    if submitted:
        if not nome.strip():
            st.error("Il nome della palazzina è obbligatorio.")
        else:
            try:
                condominio.aggiorna_palazzina(target, nome=nome, note=note)
            except ValueError as error:
                st.error(str(error))
            else:
                save_and_refresh(archivio, "Palazzina aggiornata.", "Palazzine")


@st.dialog("Modifica appartamento", width="large")
def open_edit_appartamento_dialog(
    archivio: ArchivioCondomini,
    palazzina: Palazzina,
    target: Appartamento,
) -> None:
    with st.form("update_appartamento"):
        c1, c2, c3 = st.columns(3)
        codice = c1.text_input("Codice", value=target.codice)
        interno = c2.text_input("Interno", value=target.interno)
        piano = c3.text_input("Piano", value=target.piano)
        c4, c5, c6 = st.columns(3)
        superficie = c4.number_input(
            "Superficie mq",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            value=float(target.superficie_mq),
        )
        millesimi = c5.number_input(
            "Millesimi",
            min_value=0.0,
            step=1.0,
            format="%.2f",
            value=float(target.millesimi),
        )
        prop_nome = c6.text_input("Nome proprietario", value=target.proprietario.nome)
        prop_cols = st.columns(3)
        prop_cognome = prop_cols[0].text_input(
            "Cognome proprietario", value=target.proprietario.cognome
        )
        prop_tel = prop_cols[1].text_input(
            "Telefono proprietario", value=target.proprietario.telefono
        )
        prop_email = prop_cols[2].text_input(
            "Email proprietario", value=target.proprietario.email
        )
        prop_cf = st.text_input(
            "Codice fiscale proprietario", value=target.proprietario.codice_fiscale
        )
        note = st.text_area("Note", value=target.note, height=100)
        st.caption(
            "Residente opzionale. Se lasci nome e cognome vuoti, verrà usato automaticamente il proprietario."
        )
        occupante_attuale = target.occupante
        occupante_uguale_al_proprietario = (
            occupante_attuale == target.proprietario if occupante_attuale else False
        )
        occ_default_nome = (
            ""
            if occupante_uguale_al_proprietario
            else (occupante_attuale.nome if occupante_attuale else "")
        )
        occ_default_cognome = (
            ""
            if occupante_uguale_al_proprietario
            else (occupante_attuale.cognome if occupante_attuale else "")
        )
        occ_default_tel = (
            ""
            if occupante_uguale_al_proprietario
            else (occupante_attuale.telefono if occupante_attuale else "")
        )
        occ_default_email = (
            ""
            if occupante_uguale_al_proprietario
            else (occupante_attuale.email if occupante_attuale else "")
        )
        occ_default_cf = (
            ""
            if occupante_uguale_al_proprietario
            else (occupante_attuale.codice_fiscale if occupante_attuale else "")
        )
        o1, o2, o3 = st.columns(3)
        occ_nome = o1.text_input("Nome residente", value=occ_default_nome)
        occ_cognome = o2.text_input("Cognome residente", value=occ_default_cognome)
        occ_tel = o3.text_input("Telefono residente", value=occ_default_tel)
        o4, o5 = st.columns(2)
        occ_email = o4.text_input("Email residente", value=occ_default_email)
        occ_cf = o5.text_input("Codice fiscale residente", value=occ_default_cf)
        submitted = st.form_submit_button("Salva modifiche", use_container_width=True)
    if submitted:
        if (
            not codice.strip()
            or not interno.strip()
            or not piano.strip()
            or not condomino_compilato(prop_nome, prop_cognome)
        ):
            st.error(
                "Codice, interno, piano, nome e cognome del proprietario sono obbligatori."
            )
        else:
            proprietario = build_condomino(
                nome=prop_nome,
                cognome=prop_cognome,
                telefono=prop_tel,
                email=prop_email,
                codice_fiscale=prop_cf,
            )
            occupante = proprietario
            if occ_nome.strip() or occ_cognome.strip():
                if not condomino_compilato(occ_nome, occ_cognome):
                    st.error(
                        "Se specifichi il residente, nome e cognome sono obbligatori."
                    )
                    return
                occupante = build_condomino(
                    nome=occ_nome,
                    cognome=occ_cognome,
                    telefono=occ_tel,
                    email=occ_email,
                    codice_fiscale=occ_cf,
                )
            try:
                palazzina.aggiorna_appartamento(
                    target,
                    codice=codice,
                    interno=interno,
                    piano=piano,
                    superficie_mq=superficie,
                    millesimi=millesimi,
                    proprietario=proprietario,
                    note=note,
                )
                target.occupante = occupante
            except ValueError as error:
                st.error(str(error))
            else:
                save_and_refresh(archivio, "Appartamento aggiornato.", "Appartamenti")


@st.dialog("Conferma eliminazione", width="large")
def open_delete_condominio_dialog(
    archivio: ArchivioCondomini, nome_condominio: str
) -> None:
    st.warning(
        f"Stai per eliminare il condominio '{nome_condominio}' con tutte le sue palazzine, appartamenti e rendiconti."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Conferma eliminazione",
            key="confirm_delete_condominio",
            use_container_width=True,
        ):
            archivio.rimuovi_condominio(nome_condominio)
            save_and_refresh(archivio, "Condominio rimosso.", "Condomini")
    with col2:
        if st.button(
            "Annulla",
            key="cancel_delete_condominio",
            use_container_width=True,
            type="secondary",
        ):
            st.rerun()


@st.dialog("Conferma eliminazione", width="large")
def open_delete_palazzina_dialog(
    archivio: ArchivioCondomini,
    condominio: Condominio,
    nome_palazzina: str,
) -> None:
    st.warning(
        f"Stai per eliminare la palazzina '{nome_palazzina}' del condominio '{condominio.nome}' con tutti gli appartamenti e rendiconti collegati."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Conferma eliminazione",
            key="confirm_delete_palazzina",
            use_container_width=True,
        ):
            condominio.rimuovi_palazzina(nome_palazzina)
            save_and_refresh(archivio, "Palazzina rimossa.", "Palazzine")
    with col2:
        if st.button(
            "Annulla",
            key="cancel_delete_palazzina",
            use_container_width=True,
            type="secondary",
        ):
            st.rerun()


@st.dialog("Conferma eliminazione", width="large")
def open_delete_appartamento_dialog(
    archivio: ArchivioCondomini,
    palazzina: Palazzina,
    codice_appartamento: str,
) -> None:
    st.warning(
        f"Stai per eliminare l'appartamento '{codice_appartamento}' e il relativo rendiconto."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Conferma eliminazione",
            key="confirm_delete_appartamento",
            use_container_width=True,
        ):
            palazzina.rimuovi_appartamento(codice_appartamento)
            save_and_refresh(archivio, "Appartamento rimosso.", "Appartamenti")
    with col2:
        if st.button(
            "Annulla",
            key="cancel_delete_appartamento",
            use_container_width=True,
            type="secondary",
        ):
            st.rerun()


def render_condominio_tab(archivio: ArchivioCondomini) -> None:
    if not archivio.condomini:
        st.info("Aggiungi il primo condominio per iniziare.")

    if st.button("Aggiungi condominio", key="open_add_condominio"):
        open_add_condominio_dialog(archivio)

    target = None
    if archivio.condomini:
        options = condominio_options(archivio)
        target_name = persistent_selectbox(
            "Seleziona condominio",
            list(options.keys()),
            state_key="state_manage_condominio",
            widget_key="manage_condominio",
        )
        target = options[target_name]
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(
                "Modifica condominio",
                use_container_width=True,
                key="edit_condominio_button",
            ):
                open_edit_condominio_dialog(archivio, target)
        with col2:
            if st.button(
                "Elimina condominio",
                type="secondary",
                use_container_width=True,
                key="delete_condominio_button",
            ):
                open_delete_condominio_dialog(archivio, target_name)
        with col3:
            render_export_button(
                label="Esporta condominio",
                pdf_bytes=build_component_pdf(
                    title=f"Condominio {target.nome}",
                    info_rows=[
                        ("Nome", target.nome),
                        ("Indirizzo", target.indirizzo or "-"),
                        ("Note", target.note or "-"),
                        ("Saldo proprio", format_currency(target.saldo())),
                        ("Saldo complessivo", format_currency(target.totale_saldo())),
                    ],
                    child_table=(
                        [
                            "Palazzina",
                            "Appartamenti",
                            "Saldo proprio",
                            "Saldo complessivo",
                        ],
                        [
                            [
                                palazzina.nome,
                                str(len(palazzina.appartamenti)),
                                format_currency(palazzina.saldo()),
                                format_currency(palazzina.totale_saldo()),
                            ]
                            for palazzina in target.palazzine
                        ],
                    ),
                    movement_rows=[
                        [
                            movimento.data_movimento,
                            movimento.tipo,
                            movimento.descrizione,
                            format_currency(movimento.importo),
                        ]
                        for movimento in target.movimenti
                    ],
                    footer_text=f"{location_from_address(target.indirizzo)}, {format_document_date(date.today())}",
                ),
                filename=f"condominio_{slugify_filename(target.nome)}.pdf",
            )
        st.caption(
            "L'eliminazione rimuove anche palazzine, appartamenti e rendiconti collegati."
        )

    if not archivio.condomini or target is None:
        return

    rows = []
    for condominio in archivio.condomini:
        rows.append(
            {
                "Condominio": condominio.nome,
                "Indirizzo": condominio.indirizzo or "-",
                "Palazzine": len(condominio.palazzine),
                "Appartamenti": condominio.totale_appartamenti(),
                "Saldo proprio": format_currency(condominio.saldo()),
                "Saldo complessivo": format_currency(condominio.totale_saldo()),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    render_rendiconto_panel(
        archivio,
        target=target,
        title=f"Rendiconto del condominio {target.nome}",
        active_section="Condomini",
        saldo_complessivo_label="Saldo complessivo con livelli figli",
        saldo_complessivo_valore=target.totale_saldo(),
    )


def render_palazzine_tab(archivio: ArchivioCondomini) -> None:
    if not archivio.condomini:
        st.info("Prima devi creare almeno un condominio.")
        return

    condominio_map = condominio_options(archivio)
    selected_name = persistent_selectbox(
        "Condominio",
        list(condominio_map.keys()),
        state_key="state_palazzina_condominio",
        widget_key="palazzina_condominio",
    )
    condominio = condominio_map[selected_name]

    if st.button("Aggiungi palazzina", key="open_add_palazzina"):
        open_add_palazzina_dialog(archivio, condominio)

    if not condominio.palazzine:
        st.caption("Nessuna palazzina disponibile.")
    else:
        options = palazzina_options(condominio)
        target_name = persistent_selectbox(
            "Seleziona palazzina",
            list(options.keys()),
            state_key="state_manage_palazzina",
            widget_key="manage_palazzina",
        )
        target = options[target_name]
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(
                "Modifica palazzina",
                use_container_width=True,
                key="edit_palazzina_button",
            ):
                open_edit_palazzina_dialog(archivio, condominio, target)
        with col2:
            if st.button(
                "Elimina palazzina",
                type="secondary",
                use_container_width=True,
                key="delete_palazzina_button",
            ):
                open_delete_palazzina_dialog(archivio, condominio, target_name)
        with col3:
            render_export_button(
                label="Esporta palazzina",
                pdf_bytes=build_component_pdf(
                    title=f"Palazzina {target.nome}",
                    info_rows=[
                        ("Condominio", condominio.nome),
                        ("Nome", target.nome),
                        ("Note", target.note or "-"),
                        ("Saldo proprio", format_currency(target.saldo())),
                        ("Saldo complessivo", format_currency(target.totale_saldo())),
                    ],
                    child_table=(
                        ["Codice", "Interno", "Piano", "Proprietario", "Saldo proprio"],
                        [
                            [
                                appartamento.codice,
                                appartamento.interno,
                                appartamento.piano,
                                appartamento.proprietario.nome_completo,
                                format_currency(appartamento.saldo()),
                            ]
                            for appartamento in target.appartamenti
                        ],
                    ),
                    movement_rows=[
                        [
                            movimento.data_movimento,
                            movimento.tipo,
                            movimento.descrizione,
                            format_currency(movimento.importo),
                        ]
                        for movimento in target.movimenti
                    ],
                    footer_text=f"{location_from_address(condominio.indirizzo)}, {format_document_date(date.today())}",
                ),
                filename=(
                    f"palazzina_{slugify_filename(condominio.nome)}_"
                    f"{slugify_filename(target.nome)}.pdf"
                ),
            )
        st.caption(
            "L'eliminazione rimuove anche gli appartamenti e i rendiconti della palazzina."
        )
        render_rendiconto_panel(
            archivio,
            target=target,
            title=f"Rendiconto della palazzina {target.nome}",
            active_section="Palazzine",
            saldo_complessivo_label="Saldo complessivo con appartamenti",
            saldo_complessivo_valore=target.totale_saldo(),
        )

    rows = [
        {
            "Palazzina": palazzina.nome,
            "Appartamenti": len(palazzina.appartamenti),
            "Saldo proprio": format_currency(palazzina.saldo()),
            "Saldo complessivo": format_currency(palazzina.totale_saldo()),
        }
        for palazzina in condominio.palazzine
    ]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)


def render_appartamenti_tab(archivio: ArchivioCondomini) -> None:
    if not archivio.condomini:
        st.info("Prima devi creare almeno un condominio.")
        return

    condominio_map = condominio_options(archivio)
    selected_condominio = persistent_selectbox(
        "Condominio",
        list(condominio_map.keys()),
        state_key="state_app_condominio",
        widget_key="app_condominio",
    )
    condominio = condominio_map[selected_condominio]
    if not condominio.palazzine:
        st.info("Il condominio selezionato non ha ancora palazzine.")
        return

    palazzina_map = palazzina_options(condominio)
    selected_palazzina = persistent_selectbox(
        "Palazzina",
        list(palazzina_map.keys()),
        state_key="state_app_palazzina",
        widget_key="app_palazzina",
    )
    palazzina = palazzina_map[selected_palazzina]

    if st.button("Aggiungi appartamento", key="open_add_appartamento"):
        open_add_appartamento_dialog(archivio, condominio, palazzina)

    target: Appartamento | None = None
    if not palazzina.appartamenti:
        st.caption("Nessun appartamento disponibile.")
    else:
        options = appartamento_options(palazzina)
        target_label = persistent_selectbox(
            "Seleziona appartamento",
            list(options.keys()),
            state_key="state_manage_appartamento",
            widget_key="manage_appartamento",
        )
        target = options[target_label]
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(
                "Modifica appartamento",
                use_container_width=True,
                key="edit_appartamento_button",
            ):
                open_edit_appartamento_dialog(archivio, palazzina, target)
        with col2:
            if st.button(
                "Elimina appartamento",
                type="secondary",
                use_container_width=True,
                key="delete_appartamento_button",
            ):
                open_delete_appartamento_dialog(archivio, palazzina, target.codice)
        with col3:
            render_export_button(
                label="Esporta appartamento",
                pdf_bytes=build_component_pdf(
                    title=f"Appartamento {target.codice}",
                    info_rows=[
                        ("Condominio", condominio.nome),
                        ("Palazzina", palazzina.nome),
                        ("Codice", target.codice),
                        ("Interno", target.interno),
                        ("Piano", target.piano),
                        ("Superficie", f"{target.superficie_mq:.2f} mq"),
                        ("Millesimi", f"{target.millesimi:.2f}"),
                        ("Proprietario", target.proprietario.nome_completo),
                        ("Telefono proprietario", target.proprietario.telefono or "-"),
                        ("Email proprietario", target.proprietario.email or "-"),
                        (
                            "Codice fiscale proprietario",
                            target.proprietario.codice_fiscale or "-",
                        ),
                        (
                            "Occupante",
                            target.occupante.nome_completo if target.occupante else "-",
                        ),
                        (
                            "Telefono occupante",
                            (
                                target.occupante.telefono
                                if target.occupante and target.occupante.telefono
                                else "-"
                            ),
                        ),
                        (
                            "Email occupante",
                            (
                                target.occupante.email
                                if target.occupante and target.occupante.email
                                else "-"
                            ),
                        ),
                        (
                            "Codice fiscale occupante",
                            (
                                target.occupante.codice_fiscale
                                if target.occupante and target.occupante.codice_fiscale
                                else "-"
                            ),
                        ),
                        ("Note", target.note or "-"),
                        ("Saldo proprio", format_currency(target.saldo())),
                    ],
                    movement_rows=[
                        [
                            movimento.data_movimento,
                            movimento.tipo,
                            movimento.descrizione,
                            format_currency(movimento.importo),
                        ]
                        for movimento in target.movimenti
                    ],
                    footer_text=f"{location_from_address(condominio.indirizzo)}, {format_document_date(date.today())}",
                ),
                filename=(
                    f"appartamento_{slugify_filename(condominio.nome)}_"
                    f"{slugify_filename(palazzina.nome)}_{slugify_filename(target.codice)}.pdf"
                ),
            )
        st.caption("L'eliminazione rimuove anche il rendiconto dell'appartamento.")

    rows = [
        {
            "Codice": appartamento.codice,
            "Interno": appartamento.interno,
            "Piano": appartamento.piano,
            "Proprietario": appartamento.proprietario.nome_completo,
            "Occupante": (
                appartamento.occupante.nome_completo
                if appartamento.occupante
                else "Non assegnato"
            ),
            "Saldo proprio": format_currency(appartamento.saldo()),
        }
        for appartamento in palazzina.appartamenti
    ]
    if rows and target is not None:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        render_rendiconto_panel(
            archivio,
            target=target,
            title=f"Rendiconto appartamento {target.codice}",
            active_section="Appartamenti",
        )


def main() -> None:
    load_styles()
    archivio = get_archivio()
    get_active_section()
    render_global_summary(archivio)
    show_flash_message()
    render_header(archivio)
    active_section = render_section_nav()

    if active_section == "Condomini":
        render_condominio_tab(archivio)
    elif active_section == "Palazzine":
        render_palazzine_tab(archivio)
    else:
        render_appartamenti_tab(archivio)


if __name__ == "__main__":
    main()
