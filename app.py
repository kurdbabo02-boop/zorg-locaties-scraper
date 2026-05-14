"""
Zorg Locaties — Streamlit interface
Vindt 24/7 zorginstellingen in Nederland en België.
"""

import io
import json
import sys
import os
import threading
from datetime import datetime
from typing import List

import pandas as pd
import streamlit as st

# Zorg dat het project-root op het pad staat
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import CareLocation
from config.regions import NL_PROVINCES, NL_CITIES, BE_PROVINCES, BE_CITIES
from storage.export import to_excel, to_csv

# ──────────────────────────────────────────────────────────────────────────────
# Pagina configuratie
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Zorg Locaties Finder",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Header */
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1F4E79;
        margin-bottom: 0;
    }
    .sub-title {
        font-size: 1rem;
        color: #666;
        margin-top: 0;
        margin-bottom: 1.5rem;
    }

    /* Stat kaartjes */
    .stat-card {
        background: #f0f6ff;
        border-left: 4px solid #1F4E79;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .stat-label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }
    .stat-value { font-size: 1.6rem; font-weight: 700; color: #1F4E79; line-height: 1.2; }

    /* Tabel links */
    a { color: #1F4E79 !important; }

    /* Download knoppen */
    .stDownloadButton > button {
        background-color: #1F4E79;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1.2rem;
        font-weight: 600;
    }
    .stDownloadButton > button:hover {
        background-color: #163d61;
        color: white;
    }

    /* Sidebar sectie-titels */
    .sidebar-section {
        font-size: 0.75rem;
        font-weight: 700;
        color: #1F4E79;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-top: 1rem;
        margin-bottom: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Sessiestatus initialiseren
# ──────────────────────────────────────────────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = []
if "last_run" not in st.session_state:
    st.session_state.last_run = None
if "running" not in st.session_state:
    st.session_state.running = False

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar — filters
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/48/hospital.png", width=40)
    st.markdown("## Zorg Locaties Finder")
    st.caption("24/7 zorginstellingen in NL & BE")
    st.divider()

    # --- Land ---
    st.markdown('<div class="sidebar-section">🌍 Land</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        include_nl = st.checkbox("🇳🇱 Nederland", value=True)
    with col2:
        include_be = st.checkbox("🇧🇪 België", value=True)

    # --- Regio ---
    st.markdown('<div class="sidebar-section">📍 Regio</div>', unsafe_allow_html=True)

    selected_regions = []
    if include_nl and include_be:
        all_regions = sorted(NL_PROVINCES + BE_PROVINCES)
        selected_regions = st.multiselect(
            "Provincies (leeg = heel NL + BE)",
            options=all_regions,
            placeholder="Alle provincies",
        )
    elif include_nl:
        selected_regions = st.multiselect(
            "Provincies Nederland (leeg = alles)",
            options=sorted(NL_PROVINCES),
            placeholder="Alle provincies",
        )
    elif include_be:
        selected_regions = st.multiselect(
            "Provincies België (leeg = alles)",
            options=sorted(BE_PROVINCES),
            placeholder="Alle provincies",
        )

    # --- Zorgtype ---
    st.markdown('<div class="sidebar-section">🏥 Zorgtype (24/7)</div>', unsafe_allow_html=True)

    care_types = st.multiselect(
        "Type instelling",
        options=[
            "Verpleeghuis",
            "Woonzorgcentrum",
            "Kleinschalig wonen",
            "Alzheimer / dementie centrum",
            "Hospice",
        ],
        default=[
            "Verpleeghuis",
            "Woonzorgcentrum",
            "Kleinschalig wonen",
            "Alzheimer / dementie centrum",
        ],
    )

    # --- Specialisatie ---
    st.markdown('<div class="sidebar-section">🎯 Specialisatie</div>', unsafe_allow_html=True)
    focus_dementia  = st.checkbox("🧠 Dementie / Alzheimer", value=True)
    focus_elderly   = st.checkbox("👴 Ouderenzorg algemeen", value=True)

    # --- Klein / Opkomend ---
    st.markdown('<div class="sidebar-section">🔍 Focus</div>', unsafe_allow_html=True)
    only_small    = st.checkbox("Alleen kleine instellingen")
    only_emerging = st.checkbox("Alleen opkomende / nieuwe instellingen")

    # --- Scrapers ---
    st.markdown('<div class="sidebar-section">⚙️ Bronnen</div>', unsafe_allow_html=True)
    use_zorgkaart = st.checkbox("Zorgkaart NL", value=True)
    use_vektis    = st.checkbox("Vektis AGB open data", value=True)
    use_search    = st.checkbox("DuckDuckGo zoeken", value=True)
    use_belgium   = st.checkbox("Belgische bronnen", value=include_be)

    st.divider()

    # --- Start knop ---
    start_btn = st.button(
        "🔍 Start zoeken",
        type="primary",
        use_container_width=True,
        disabled=not (include_nl or include_be),
    )

# ──────────────────────────────────────────────────────────────────────────────
# Hoofd pagina — titel
# ──────────────────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">🏥 Zorg Locaties Finder</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Automatisch 24/7 zorginstellingen vinden in Nederland en België — focus op ouderenzorg en dementie</p>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Scraper uitvoeren
# ──────────────────────────────────────────────────────────────────────────────
CARE_TYPE_MAP = {
    "Verpleeghuis":                 ["verpleeghuis", "ouderengeneeskunde"],
    "Woonzorgcentrum":              ["woonzorgcentrum"],
    "Kleinschalig wonen":           ["kleinschalig_wonen"],
    "Alzheimer / dementie centrum": ["dementie_centrum", "alzheimer_centrum"],
    "Hospice":                      ["hospice"],
}

def run_scrapers_ui(countries, regions, care_types_sel, focus_dem, focus_eld,
                    only_sm, only_em, scraper_flags) -> List[CareLocation]:
    """Voer de geselecteerde scrapers uit en filter de resultaten."""
    from scrapers import ZorgkaartScraper, SearchScraper, VektisScraper, BelgiumScraper
    from config.queries import EXCLUDED_CARE_TYPES

    all_locs: List[CareLocation] = []

    if scraper_flags["zorgkaart"] and "NL" in countries:
        all_locs.extend(ZorgkaartScraper().scrape())

    if scraper_flags["vektis"] and "NL" in countries:
        all_locs.extend(VektisScraper().scrape())

    if scraper_flags["search"]:
        s = SearchScraper()
        # Beperk regio's als de gebruiker er specifieke heeft gekozen
        if regions:
            from config import regions as reg_module
            s._region_override = regions
        all_locs.extend(s.scrape())

    if scraper_flags["belgium"] and "BE" in countries:
        all_locs.extend(BelgiumScraper().scrape())

    # ---- Filters ----
    # 1. Alleen 24/7 typen
    results = [l for l in all_locs if l.care_type not in EXCLUDED_CARE_TYPES]
    EXCL_TERMS = ["thuiszorg", "dagopvang", "dagverzorging", "thuisverpleging"]
    results = [l for l in results if not any(t in l.name.lower() for t in EXCL_TERMS)]

    # 2. Land
    results = [l for l in results if l.country in countries]

    # 3. Regio (provincie)
    if regions:
        results = [
            l for l in results
            if not l.province or any(r.lower() in (l.province + " " + l.city).lower() for r in regions)
        ]

    # 4. Zorgtype
    allowed_types = []
    for label in care_types_sel:
        allowed_types.extend(CARE_TYPE_MAP.get(label, []))
    if allowed_types:
        results = [l for l in results if not l.care_type or l.care_type in allowed_types]

    # 5. Specialisatie
    if focus_dem and not focus_eld:
        results = [l for l in results if "dementie" in l.specializations]
    elif focus_eld and not focus_dem:
        results = [l for l in results if "ouderenzorg" in l.specializations]
    # both = geen extra filter

    # 6. Klein / Opkomend
    if only_sm:
        results = [l for l in results if l.is_small]
    if only_em:
        results = [l for l in results if l.is_emerging]

    # 7. Deduplicatie
    seen = set()
    unique = []
    for l in results:
        k = l.dedup_key()
        if k not in seen:
            seen.add(k)
            unique.append(l)

    return unique


if start_btn:
    countries = []
    if include_nl:
        countries.append("NL")
    if include_be:
        countries.append("BE")

    if not countries:
        st.error("Kies minimaal één land.")
        st.stop()

    scraper_flags = {
        "zorgkaart": use_zorgkaart,
        "vektis":    use_vektis,
        "search":    use_search,
        "belgium":   use_belgium,
    }

    status_box = st.empty()
    progress    = st.progress(0, text="Initialiseren...")

    steps = [k for k, v in scraper_flags.items() if v]
    total = len(steps)
    results = []

    for i, step in enumerate(steps):
        label_map = {
            "zorgkaart": "Zorgkaart Nederland",
            "vektis":    "Vektis AGB-register",
            "search":    "DuckDuckGo zoeken",
            "belgium":   "Belgische bronnen",
        }
        label = label_map[step]
        progress.progress((i / total), text=f"Bezig: {label}...")
        status_box.info(f"🔍 {label} doorzoeken...")

        flags_single = {k: (k == step) for k in scraper_flags}
        try:
            partial = run_scrapers_ui(
                countries, selected_regions, care_types,
                focus_dementia, focus_elderly,
                only_small, only_emerging,
                flags_single
            )
            results.extend(partial)
        except Exception as e:
            st.warning(f"⚠️ {label} mislukt: {e}")

    progress.progress(1.0, text="Klaar!")
    status_box.empty()

    # Dedup over alle scrapers heen
    seen = set()
    unique = []
    for l in results:
        k = l.dedup_key()
        if k not in seen:
            seen.add(k)
            unique.append(l)

    st.session_state.results = unique
    st.session_state.last_run = datetime.now().strftime("%d-%m-%Y %H:%M")

# ──────────────────────────────────────────────────────────────────────────────
# Resultaten tonen
# ──────────────────────────────────────────────────────────────────────────────
results: List[CareLocation] = st.session_state.results

if results:
    # --- Statistieken ---
    nl_count = sum(1 for l in results if l.country == "NL")
    be_count = sum(1 for l in results if l.country == "BE")
    sm_count = sum(1 for l in results if l.is_small)
    em_count = sum(1 for l in results if l.is_emerging)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-card"><div class="stat-label">Totaal</div><div class="stat-value">{len(results)}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-card"><div class="stat-label">Nederland</div><div class="stat-value">{nl_count}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-card"><div class="stat-label">België</div><div class="stat-value">{be_count}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="stat-card"><div class="stat-label">Kleinschalig</div><div class="stat-value">{sm_count}</div></div>', unsafe_allow_html=True)

    if st.session_state.last_run:
        st.caption(f"Laatste zoekopdracht: {st.session_state.last_run}")

    st.divider()

    # --- Zoekbalk boven tabel ---
    search_term = st.text_input("🔎 Zoek in resultaten (naam of stad)", placeholder="bijv. Amsterdam of verpleeghuis...")

    # --- Tabel bouwen ---
    def make_df(locs: List[CareLocation]) -> pd.DataFrame:
        rows = []
        for l in locs:
            parts = [p for p in [l.address, f"{l.postal_code} {l.city}".strip(), f"({l.country})"] if p.strip()]
            locatie = ", ".join(parts)

            website = l.website or l.source_url or ""
            website_display = f"[🔗 Bekijk]({website})" if website.startswith("http") else website

            rows.append({
                "Naam instelling": l.name,
                "Locatie":         locatie,
                "Type":            l.care_type.replace("_", " ").title() if l.care_type else "",
                "Telefoon":        l.phone or "",
                "E-mail":          l.email or "",
                "Website":         website_display,
                "Klein":           "✓" if l.is_small else "",
                "Nieuw":           "✓" if l.is_emerging else "",
                "_website_raw":    website,
            })
        return pd.DataFrame(rows)

    df = make_df(results)

    # Zoekfilter
    if search_term:
        mask = (
            df["Naam instelling"].str.contains(search_term, case=False, na=False) |
            df["Locatie"].str.contains(search_term, case=False, na=False)
        )
        df = df[mask]

    # Toon zonder interne kolom
    display_df = df.drop(columns=["_website_raw"])
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Website": st.column_config.LinkColumn("Website", display_text="🔗 Bekijk"),
            "Klein":   st.column_config.TextColumn("Klein",  width="small"),
            "Nieuw":   st.column_config.TextColumn("Nieuw",  width="small"),
            "Type":    st.column_config.TextColumn("Type",   width="medium"),
        },
        height=500,
    )

    st.caption(f"{len(df)} van {len(results)} locaties weergegeven")

    # --- Downloads ---
    st.divider()
    st.markdown("### 📥 Downloaden")
    dl1, dl2 = st.columns(2)

    # Excel download
    with dl1:
        excel_buf = io.BytesIO()
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Zorg Locaties"

            HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
            HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
            ALT_FILL    = PatternFill("solid", fgColor="EBF3FB")
            CELL_FONT   = Font(name="Calibri", size=10)
            LINK_FONT   = Font(name="Calibri", size=10, color="0563C1", underline="single")
            LEFT        = Alignment(horizontal="left", vertical="center")
            BORDER      = Border(bottom=Side(style="thin", color="D9D9D9"))

            COLS = ["Naam instelling", "Locatie", "Type", "Telefoon", "E-mail", "Website"]
            WIDTHS = [38, 42, 22, 18, 32, 48]

            ws.row_dimensions[1].height = 22
            for ci, (col, w) in enumerate(zip(COLS, WIDTHS), 1):
                cell = ws.cell(row=1, column=ci, value=col)
                cell.font      = HEADER_FONT
                cell.fill      = HEADER_FILL
                cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.column_dimensions[get_column_letter(ci)].width = w

            export_rows = df[COLS + ["_website_raw"]].copy() if "_website_raw" in df.columns else df[COLS].copy()

            for ri, (_, row) in enumerate(export_rows.iterrows(), 2):
                fill = ALT_FILL if ri % 2 == 0 else None
                ws.row_dimensions[ri].height = 16
                for ci, col in enumerate(COLS, 1):
                    val = str(row.get(col, "") or "")
                    # Strip markdown link syntax
                    if val.startswith("[") and "](" in val:
                        val = val.split("](")[1].rstrip(")")
                    cell = ws.cell(row=ri, column=ci, value=val)
                    cell.alignment = LEFT
                    cell.border    = BORDER
                    if fill:
                        cell.fill = fill
                    if col == "Website" and val.startswith("http"):
                        cell.hyperlink = val
                        cell.value     = "Bekijk website"
                        cell.font      = LINK_FONT
                    elif col == "E-mail" and "@" in val:
                        cell.hyperlink = f"mailto:{val}"
                        cell.font      = LINK_FONT
                    else:
                        cell.font = CELL_FONT

            ws.auto_filter.ref = f"A1:{get_column_letter(len(COLS))}1"
            ws.freeze_panes   = "A2"
            wb.save(excel_buf)
            excel_buf.seek(0)

            st.download_button(
                label="📊 Download Excel",
                data=excel_buf,
                file_name=f"zorg_locaties_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Excel fout: {e}")

    # CSV download
    with dl2:
        csv_buf = io.StringIO()
        export_cols = ["Naam instelling", "Locatie", "Type", "Telefoon", "E-mail"]
        csv_df = df[export_cols].copy()
        # Voeg raw website URL toe voor CSV
        csv_df["Website"] = df["_website_raw"]
        csv_df.to_csv(csv_buf, index=False, encoding="utf-8-sig")

        st.download_button(
            label="📄 Download CSV",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name=f"zorg_locaties_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

elif not start_btn:
    # Lege staat — welkomstscherm
    st.info("👈 Stel je filters in via het menu aan de linkerkant en klik op **Start zoeken**.")

    st.markdown("""
    **Wat zoekt dit systeem?**
    - 🏠 Verpleeghuizen en woonzorgcentra (24/7 zorg)
    - 🧠 Dementie- en Alzheimer-afdelingen
    - 🏡 Kleinschalige woonvormen voor ouderen
    - 🌿 Hospices met ouderenzorg
    - Zowel **Nederland** als **België** (Vlaanderen, Wallonië, Brussel)

    **Geen API-sleutel nodig** — gebruikt openbare bronnen:
    Zorgkaart NL, Vektis AGB-register, Belgische zorginspectie en DuckDuckGo.
    """)
