"""
Zorg Locaties — Streamlit interface
Vindt 24/7 zorginstellingen in Nederland en België.
"""

import io
import sys
import os
from datetime import datetime
from typing import List

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import CareLocation
from config.regions import NL_PROVINCES, NL_CITIES, BE_PROVINCES, BE_CITIES

# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Zorg Locaties Finder",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-title { font-size:2rem; font-weight:700; color:#1F4E79; margin-bottom:0; }
    .sub-title  { font-size:.95rem; color:#666; margin-top:0; margin-bottom:1.2rem; }
    .stat-card  {
        background:#f0f6ff; border-left:4px solid #1F4E79;
        border-radius:6px; padding:12px 16px; margin-bottom:8px;
    }
    .stat-label { font-size:.72rem; color:#888; text-transform:uppercase; letter-spacing:.05em; }
    .stat-value { font-size:1.6rem; font-weight:700; color:#1F4E79; line-height:1.2; }
    .sidebar-section {
        font-size:.72rem; font-weight:700; color:#1F4E79;
        text-transform:uppercase; letter-spacing:.07em;
        margin-top:.9rem; margin-bottom:.2rem;
    }
    .sel-badge {
        background:#1F4E79; color:white; border-radius:12px;
        padding:3px 10px; font-size:.8rem; font-weight:600;
        display:inline-block; margin-bottom:.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Sessiestatus ──────────────────────────────────────────────────────────────
for key, default in [("results", []), ("last_run", None), ("df", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏥 Zorg Locaties")
    st.caption("24/7 zorginstellingen in NL & BE")
    st.divider()

    st.markdown('<div class="sidebar-section">🌍 Land</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    include_nl = c1.checkbox("🇳🇱 NL", value=True)
    include_be = c2.checkbox("🇧🇪 BE", value=True)

    st.markdown('<div class="sidebar-section">📍 Regio</div>', unsafe_allow_html=True)
    region_pool = []
    if include_nl:
        region_pool += NL_PROVINCES
    if include_be:
        region_pool += BE_PROVINCES
    selected_regions = st.multiselect(
        "Provincies (leeg = heel NL + BE)",
        options=sorted(set(region_pool)),
        placeholder="Alle provincies",
    )

    st.markdown('<div class="sidebar-section">🏥 Zorgtype (24/7)</div>', unsafe_allow_html=True)
    care_types = st.multiselect(
        "Type instelling",
        options=["Verpleeghuis", "Woonzorgcentrum", "Kleinschalig wonen",
                 "Alzheimer / dementie centrum", "Hospice"],
        default=["Verpleeghuis", "Woonzorgcentrum", "Kleinschalig wonen",
                 "Alzheimer / dementie centrum"],
    )

    st.markdown('<div class="sidebar-section">🎯 Specialisatie</div>', unsafe_allow_html=True)
    focus_dem = st.checkbox("🧠 Dementie / Alzheimer", value=True)
    focus_eld = st.checkbox("👴 Ouderenzorg algemeen", value=True)

    st.markdown('<div class="sidebar-section">🔍 Focus</div>', unsafe_allow_html=True)
    only_small    = st.checkbox("Alleen kleine instellingen")
    only_emerging = st.checkbox("Alleen opkomende / nieuwe")

    st.markdown('<div class="sidebar-section">⚡ Zoeksnelheid</div>', unsafe_allow_html=True)
    quick_mode = st.toggle("Snel zoeken (aanbevolen)", value=True,
                           help="Snel: ~8 queries, klaar in <30 sec.\nUitgebreid: alle regio's, kan minuten duren.")

    st.markdown('<div class="sidebar-section">⚙️ Bronnen</div>', unsafe_allow_html=True)
    use_zorgkaart = st.checkbox("Zorgkaart NL", value=True)
    use_vektis    = st.checkbox("Vektis AGB open data", value=True)
    use_search    = st.checkbox("DuckDuckGo zoeken", value=True)
    use_belgium   = st.checkbox("Belgische bronnen", value=include_be)

    st.divider()
    start_btn = st.button("🔍 Start zoeken", type="primary",
                          use_container_width=True,
                          disabled=not (include_nl or include_be))

# ── Pagina header ─────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">🏥 Zorg Locaties Finder</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Automatisch 24/7 zorginstellingen vinden in Nederland en België — ouderenzorg & dementie</p>', unsafe_allow_html=True)

# ── Care type mapping ─────────────────────────────────────────────────────────
CARE_TYPE_MAP = {
    "Verpleeghuis":                 ["verpleeghuis", "ouderengeneeskunde"],
    "Woonzorgcentrum":              ["woonzorgcentrum"],
    "Kleinschalig wonen":           ["kleinschalig_wonen"],
    "Alzheimer / dementie centrum": ["dementie_centrum", "alzheimer_centrum"],
    "Hospice":                      ["hospice"],
}
EXCL_TERMS   = ["thuiszorg", "dagopvang", "dagverzorging", "thuisverpleging"]

# ── Scraper uitvoeren ─────────────────────────────────────────────────────────
def run_scrapers_ui(countries, regions, care_sel, f_dem, f_eld,
                    sm, em, flags, quick) -> List[CareLocation]:
    from scrapers import ZorgkaartScraper, SearchScraper, VektisScraper, BelgiumScraper
    from config.queries import EXCLUDED_CARE_TYPES

    locs: List[CareLocation] = []

    if flags["zorgkaart"] and "NL" in countries:
        locs.extend(ZorgkaartScraper().scrape())

    if flags["vektis"] and "NL" in countries:
        locs.extend(VektisScraper().scrape())

    if flags["search"]:
        locs.extend(SearchScraper(
            quick_mode=quick,
            region_override=regions or None,
        ).scrape())

    if flags["belgium"] and "BE" in countries:
        locs.extend(BelgiumScraper().scrape())

    # Filters
    locs = [l for l in locs if l.care_type not in EXCLUDED_CARE_TYPES]
    locs = [l for l in locs if not any(t in l.name.lower() for t in EXCL_TERMS)]
    locs = [l for l in locs if l.country in countries]

    if regions:
        locs = [l for l in locs if not l.province or
                any(r.lower() in (l.province + " " + l.city).lower() for r in regions)]

    allowed_types = []
    for label in care_sel:
        allowed_types.extend(CARE_TYPE_MAP.get(label, []))
    if allowed_types:
        locs = [l for l in locs if not l.care_type or l.care_type in allowed_types]

    if f_dem and not f_eld:
        locs = [l for l in locs if "dementie" in l.specializations]
    elif f_eld and not f_dem:
        locs = [l for l in locs if "ouderenzorg" in l.specializations]

    if sm:
        locs = [l for l in locs if l.is_small]
    if em:
        locs = [l for l in locs if l.is_emerging]

    # Deduplicatie
    seen, unique = set(), []
    for l in locs:
        k = l.dedup_key()
        if k not in seen:
            seen.add(k)
            unique.append(l)
    return unique


def make_df(locs: List[CareLocation]) -> pd.DataFrame:
    rows = []
    for l in locs:
        parts = [p for p in [l.address,
                              f"{l.postal_code} {l.city}".strip(),
                              f"({l.country})"] if p.strip()]
        rows.append({
            "☑":               False,
            "Naam":            l.name,
            "Locatie":         ", ".join(parts),
            "Type":            l.care_type.replace("_", " ").title() if l.care_type else "",
            "Telefoon":        l.phone or "",
            "E-mail":          l.email or "",
            "Website":         l.website or l.source_url or "",
            "Klein":           "✓" if l.is_small else "",
            "Nieuw":           "✓" if l.is_emerging else "",
        })
    return pd.DataFrame(rows)


if start_btn:
    countries = [c for c, inc in [("NL", include_nl), ("BE", include_be)] if inc]
    flags = dict(zorgkaart=use_zorgkaart, vektis=use_vektis,
                 search=use_search, belgium=use_belgium)

    steps = [k for k, v in flags.items() if v]
    progress_bar = st.progress(0, text="Initialiseren...")
    status       = st.empty()
    all_locs     = []

    for i, step in enumerate(steps):
        labels = dict(zorgkaart="Zorgkaart Nederland", vektis="Vektis AGB-register",
                      search="DuckDuckGo zoeken", belgium="Belgische bronnen")
        status.info(f"🔍 {labels[step]}...")
        progress_bar.progress(i / len(steps), text=f"Bezig: {labels[step]}...")

        try:
            partial = run_scrapers_ui(
                countries, selected_regions, care_types,
                focus_dem, focus_eld, only_small, only_emerging,
                {k: (k == step) for k in flags},
                quick_mode,
            )
            all_locs.extend(partial)
        except Exception as e:
            st.warning(f"⚠️ {labels[step]} mislukt: {e}")

    progress_bar.progress(1.0, text="Klaar!")
    status.empty()

    # Globale dedup
    seen, unique = set(), []
    for l in all_locs:
        k = l.dedup_key()
        if k not in seen:
            seen.add(k)
            unique.append(l)

    st.session_state.results  = unique
    st.session_state.last_run = datetime.now().strftime("%d-%m-%Y %H:%M")
    st.session_state.df       = make_df(unique)

# ── Resultaten ────────────────────────────────────────────────────────────────
results: List[CareLocation] = st.session_state.results

if results:
    df_master: pd.DataFrame = st.session_state.df

    # Statistieken
    nl  = sum(1 for l in results if l.country == "NL")
    be  = sum(1 for l in results if l.country == "BE")
    sm  = sum(1 for l in results if l.is_small)

    c1, c2, c3, c4 = st.columns(4)
    for col, lbl, val in [(c1,"Totaal",len(results)),(c2,"Nederland",nl),
                          (c3,"België",be),(c4,"Kleinschalig",sm)]:
        col.markdown(
            f'<div class="stat-card"><div class="stat-label">{lbl}</div>'
            f'<div class="stat-value">{val}</div></div>',
            unsafe_allow_html=True,
        )
    if st.session_state.last_run:
        st.caption(f"Laatste zoekopdracht: {st.session_state.last_run}")

    st.divider()

    # Zoekbalk
    search_q = st.text_input("🔎 Zoek in resultaten",
                              placeholder="bijv. Amsterdam of kleinschalig...")

    df_view = df_master.copy()
    if search_q:
        mask = (
            df_view["Naam"].str.contains(search_q, case=False, na=False) |
            df_view["Locatie"].str.contains(search_q, case=False, na=False) |
            df_view["Type"].str.contains(search_q, case=False, na=False)
        )
        df_view = df_view[mask].reset_index(drop=True)

    st.caption(f"{len(df_view)} van {len(results)} locaties — **klik op de checkbox ☑ om rijen te selecteren**")

    # Bewerkbare tabel met checkboxes voor selectie
    edited = st.data_editor(
        df_view,
        use_container_width=True,
        hide_index=True,
        height=480,
        column_config={
            "☑":        st.column_config.CheckboxColumn("☑", width="small", default=False),
            "Naam":     st.column_config.TextColumn("Naam instelling", width="large"),
            "Locatie":  st.column_config.TextColumn("Locatie", width="large"),
            "Type":     st.column_config.TextColumn("Type", width="medium"),
            "Telefoon": st.column_config.TextColumn("Telefoon", width="medium"),
            "E-mail":   st.column_config.TextColumn("E-mail", width="medium"),
            "Website":  st.column_config.LinkColumn("Website", display_text="🔗 Bekijk", width="small"),
            "Klein":    st.column_config.TextColumn("Klein", width="small"),
            "Nieuw":    st.column_config.TextColumn("Nieuw", width="small"),
        },
        disabled=["Naam", "Locatie", "Type", "Telefoon", "E-mail", "Website", "Klein", "Nieuw"],
        key="table_editor",
    )

    # Selectie tellen
    selected_df = edited[edited["☑"] == True]
    n_sel = len(selected_df)

    if n_sel > 0:
        st.markdown(f'<div class="sel-badge">✓ {n_sel} geselecteerd</div>', unsafe_allow_html=True)

    st.divider()

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.markdown("### 📥 Downloaden")

    export_scope = st.radio(
        "Exporteer:",
        options=["Alle resultaten", "Alleen geselecteerde rijen"],
        horizontal=True,
        disabled=(n_sel == 0),
        index=1 if n_sel > 0 else 0,
    )

    export_df = selected_df if (export_scope == "Alleen geselecteerde rijen" and n_sel > 0) else edited
    export_cols = ["Naam", "Locatie", "Type", "Telefoon", "E-mail", "Website"]
    export_df   = export_df[export_cols].copy()

    n_export = len(export_df)
    st.caption(f"{n_export} rijen worden geëxporteerd")

    dl_c1, dl_c2 = st.columns(2)

    # Excel
    with dl_c1:
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            excel_buf = io.BytesIO()
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Zorg Locaties"

            H_FONT  = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
            H_FILL  = PatternFill("solid", fgColor="1F4E79")
            A_FILL  = PatternFill("solid", fgColor="EBF3FB")
            C_FONT  = Font(name="Calibri", size=10)
            L_FONT  = Font(name="Calibri", size=10, color="0563C1", underline="single")
            LEFT    = Alignment(horizontal="left", vertical="center")
            BORDER  = Border(bottom=Side(style="thin", color="D9D9D9"))
            WIDTHS  = [38, 42, 22, 18, 32, 45]
            LABELS  = ["Naam instelling","Locatie","Type","Telefoon","E-mail","Website"]

            ws.row_dimensions[1].height = 22
            for ci, (lbl, w) in enumerate(zip(LABELS, WIDTHS), 1):
                cell = ws.cell(row=1, column=ci, value=lbl)
                cell.font = H_FONT; cell.fill = H_FILL
                cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.column_dimensions[get_column_letter(ci)].width = w

            for ri, (_, row) in enumerate(export_df.iterrows(), 2):
                fill = A_FILL if ri % 2 == 0 else None
                ws.row_dimensions[ri].height = 16
                for ci, col in enumerate(export_cols, 1):
                    val = str(row.get(col, "") or "")
                    cell = ws.cell(row=ri, column=ci, value=val)
                    cell.alignment = LEFT; cell.border = BORDER
                    if fill: cell.fill = fill
                    if col == "Website" and val.startswith("http"):
                        cell.hyperlink = val; cell.value = "Bekijk website"; cell.font = L_FONT
                    elif col == "E-mail" and "@" in val:
                        cell.hyperlink = f"mailto:{val}"; cell.font = L_FONT
                    else:
                        cell.font = C_FONT

            ws.auto_filter.ref = f"A1:{get_column_letter(len(export_cols))}1"
            ws.freeze_panes = "A2"
            wb.save(excel_buf); excel_buf.seek(0)

            st.download_button(
                "📊 Download Excel",
                data=excel_buf,
                file_name=f"zorg_locaties_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Excel fout: {e}")

    # CSV
    with dl_c2:
        csv_bytes = export_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            "📄 Download CSV",
            data=csv_bytes,
            file_name=f"zorg_locaties_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

else:
    st.info("👈 Stel je filters in via het menu aan de linkerkant en klik op **Start zoeken**.")
    st.markdown("""
    **Wat zoekt dit systeem?**
    - 🏠 Verpleeghuizen en woonzorgcentra (24/7 zorg)
    - 🧠 Dementie- en Alzheimer-afdelingen
    - 🏡 Kleinschalige woonvormen voor ouderen
    - Zowel **Nederland** als **België**

    **Tip:** gebruik **Snel zoeken** voor resultaten binnen 30 seconden.
    Zet het uit voor een uitgebreide zoekopdracht door heel NL & BE.
    """)
