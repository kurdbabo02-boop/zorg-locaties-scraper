"""
Zorg Locaties — Streamlit interface
Vindt 24/7 zorginstellingen in Nederland en België met contactgegevens.
"""

import io, sys, os
from datetime import datetime
from typing import List

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import CareLocation
from config.regions import NL_PROVINCES, BE_PROVINCES

# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Zorg Locaties Finder",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sessiestatus ──────────────────────────────────────────────────────────────
for k, v in dict(results=[], last_run=None, df=None, dark_mode=False).items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Thema CSS ─────────────────────────────────────────────────────────────────
DARK_CSS = """
<style>
.stApp { background-color:#0e1117 !important; }
section[data-testid="stSidebar"] { background-color:#151b28 !important; }
section[data-testid="stSidebar"] * { color:#e8f0ff !important; }
.stTextInput input,.stTextArea textarea { background:#1e2535 !important; color:#e8f0ff !important; border-color:#2d3a52 !important; }
.stDataFrame { background:#1e2535 !important; }
h1,h2,h3,h4,p,label,span,.stMarkdown { color:#e8f0ff !important; }
.stButton > button { background:#1e2535 !important; color:#e8f0ff !important; border-color:#2d3a52 !important; }
</style>"""

COMMON_CSS = """<style>
.main-title { font-size:2rem; font-weight:700; color:#1F4E79; margin-bottom:0; }
.sub-title  { font-size:.9rem; color:#888; margin-top:0; margin-bottom:1.2rem; }
.stat-card  { background:#f0f6ff; border-left:4px solid #1F4E79; border-radius:6px; padding:12px 16px; margin-bottom:8px; }
.stat-label { font-size:.7rem; color:#888; text-transform:uppercase; letter-spacing:.05em; }
.stat-value { font-size:1.6rem; font-weight:700; color:#1F4E79; line-height:1.2; }
.sidebar-section { font-size:.7rem; font-weight:700; color:#1F4E79; text-transform:uppercase; letter-spacing:.07em; margin-top:.9rem; margin-bottom:.2rem; }
</style>"""

if st.session_state.dark_mode:
    st.markdown(DARK_CSS, unsafe_allow_html=True)
st.markdown(COMMON_CSS, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏥 Zorg Locaties")
    st.caption("24/7 zorginstellingen in NL & BE")
    dark_on = st.toggle("🌙 Dark mode", value=st.session_state.dark_mode)
    if dark_on != st.session_state.dark_mode:
        st.session_state.dark_mode = dark_on
        st.rerun()
    st.divider()

    st.markdown('<div class="sidebar-section">🌍 Land</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    include_nl = c1.checkbox("🇳🇱 NL", value=True)
    include_be = c2.checkbox("🇧🇪 BE", value=True)

    st.markdown('<div class="sidebar-section">📍 Regio</div>', unsafe_allow_html=True)
    region_pool = (NL_PROVINCES if include_nl else []) + (BE_PROVINCES if include_be else [])
    selected_regions = st.multiselect(
        "Provincies (leeg = heel NL + BE)",
        options=sorted(set(region_pool)), placeholder="Alle provincies",
    )

    st.markdown('<div class="sidebar-section">🏥 Zorgtype (24/7)</div>', unsafe_allow_html=True)
    care_types = st.multiselect(
        "Type instelling",
        options=["Verpleeghuis","Woonzorgcentrum","Kleinschalig wonen",
                 "Alzheimer / dementie centrum","Hospice"],
        default=["Verpleeghuis","Woonzorgcentrum","Kleinschalig wonen",
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
        help="Snel: ~8 queries, <30 sec.\nUitgebreid: alle regio's, kan minuten duren.")

    st.markdown('<div class="sidebar-section">📞 Contactgegevens</div>', unsafe_allow_html=True)
    do_enrich = st.toggle("Bezoek websites voor telefoon & e-mail", value=True,
        help="Bezoekt elke gevonden website om telefoon en e-mail op te halen. Duurt iets langer.")

    st.markdown('<div class="sidebar-section">⚙️ Bronnen</div>', unsafe_allow_html=True)
    use_zorgkaart = st.checkbox("Zorgkaart NL",         value=True)
    use_vektis    = st.checkbox("Vektis AGB open data", value=True)
    use_search    = st.checkbox("DuckDuckGo zoeken",    value=True)
    use_belgium   = st.checkbox("Belgische bronnen",    value=include_be)

    st.divider()
    start_btn = st.button("🔍 Start zoeken", type="primary",
                          use_container_width=True,
                          disabled=not (include_nl or include_be))

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">🏥 Zorg Locaties Finder</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">24/7 zorginstellingen in Nederland en België — ouderenzorg & dementie</p>',
            unsafe_allow_html=True)

# ── Constanten ────────────────────────────────────────────────────────────────
CARE_TYPE_MAP = {
    "Verpleeghuis":                 ["verpleeghuis","ouderengeneeskunde"],
    "Woonzorgcentrum":              ["woonzorgcentrum"],
    "Kleinschalig wonen":           ["kleinschalig_wonen"],
    "Alzheimer / dementie centrum": ["dementie_centrum","alzheimer_centrum"],
    "Hospice":                      ["hospice"],
}
EXCL_TERMS = ["thuiszorg","dagopvang","dagverzorging","thuisverpleging",
              "vacature","werken bij","solliciteer"]

# ── Scrapers uitvoeren ────────────────────────────────────────────────────────
def run_scrapers(countries, regions, care_sel, f_dem, f_eld,
                 sm, em, flags, quick) -> List[CareLocation]:
    from scrapers import ZorgkaartScraper, SearchScraper, VektisScraper, BelgiumScraper
    from config.queries import EXCLUDED_CARE_TYPES

    locs: List[CareLocation] = []
    if flags["zorgkaart"] and "NL" in countries:
        locs.extend(ZorgkaartScraper().scrape())
    if flags["vektis"] and "NL" in countries:
        locs.extend(VektisScraper().scrape())
    if flags["search"]:
        locs.extend(SearchScraper(quick_mode=quick, region_override=regions or None).scrape())
    if flags["belgium"] and "BE" in countries:
        locs.extend(BelgiumScraper().scrape())

    locs = [l for l in locs if l.care_type not in EXCLUDED_CARE_TYPES]
    locs = [l for l in locs if not any(t in l.name.lower() for t in EXCL_TERMS)]
    locs = [l for l in locs if l.country in countries]
    if regions:
        locs = [l for l in locs if not l.province or
                any(r.lower() in (l.province+" "+l.city).lower() for r in regions)]
    allowed = []
    for label in care_sel:
        allowed.extend(CARE_TYPE_MAP.get(label, []))
    if allowed:
        locs = [l for l in locs if not l.care_type or l.care_type in allowed]
    if f_dem and not f_eld:
        locs = [l for l in locs if "dementie" in l.specializations]
    elif f_eld and not f_dem:
        locs = [l for l in locs if "ouderenzorg" in l.specializations]
    if sm: locs = [l for l in locs if l.is_small]
    if em: locs = [l for l in locs if l.is_emerging]

    seen, unique = set(), []
    for l in locs:
        k = l.dedup_key()
        if k not in seen:
            seen.add(k); unique.append(l)
    return unique


def make_df(locs: List[CareLocation]) -> pd.DataFrame:
    rows = []
    for l in locs:
        parts = [p for p in [l.address, f"{l.postal_code} {l.city}".strip(),
                              f"({l.country})"] if p.strip()]
        rows.append({
            "☑":        False,
            "Naam":     l.name,
            "Locatie":  ", ".join(parts),
            "Telefoon": l.phone  or "",
            "E-mail":   l.email  or "",
            "Website":  l.website or l.source_url or "",
        })
    return pd.DataFrame(rows)


# ── Zoeken starten ────────────────────────────────────────────────────────────
if start_btn:
    countries = [c for c, inc in [("NL",include_nl),("BE",include_be)] if inc]
    flags = dict(zorgkaart=use_zorgkaart, vektis=use_vektis,
                 search=use_search, belgium=use_belgium)
    steps = [k for k, v in flags.items() if v]
    LABELS = dict(zorgkaart="Zorgkaart Nederland", vektis="Vektis AGB-register",
                  search="DuckDuckGo zoeken", belgium="Belgische bronnen")

    bar  = st.progress(0, text="Initialiseren...")
    info = st.empty()
    all_locs: List[CareLocation] = []

    # Stap 1 — scrapers
    total_steps = len(steps) + (1 if do_enrich else 0)
    for i, step in enumerate(steps):
        info.info(f"🔍 {LABELS[step]}...")
        bar.progress(i / total_steps, text=f"Bezig: {LABELS[step]}...")
        try:
            partial = run_scrapers(
                countries, selected_regions, care_types,
                focus_dem, focus_eld, only_small, only_emerging,
                {k:(k==step) for k in flags}, quick_mode,
            )
            all_locs.extend(partial)
        except Exception as e:
            st.warning(f"⚠️ {LABELS[step]} mislukt: {e}")

    # Globale dedup
    seen, unique = set(), []
    for l in all_locs:
        k = l.dedup_key()
        if k not in seen:
            seen.add(k); unique.append(l)

    # Stap 2 — contactgegevens verrijken
    if do_enrich and unique:
        from utils.enrich import enrich_one
        from utils.http import get_session

        enrich_step = len(steps)
        bar.progress(enrich_step / total_steps, text="Contactgegevens ophalen...")
        enrich_session = get_session()
        enrich_box = st.empty()

        for idx, loc in enumerate(unique):
            if loc.email and loc.phone:
                continue
            enrich_box.caption(f"📞 {loc.name[:50]}...")
            try:
                unique[idx] = enrich_one(loc, enrich_session)
            except Exception:
                pass

        enrich_box.empty()

    bar.progress(1.0, text="Klaar!")
    info.empty()

    st.session_state.results  = unique
    st.session_state.last_run = datetime.now().strftime("%d-%m-%Y %H:%M")
    st.session_state.df       = make_df(unique)

# ── Resultaten tonen ──────────────────────────────────────────────────────────
results: List[CareLocation] = st.session_state.results

if results:
    df_master: pd.DataFrame = st.session_state.df

    # Statistieken
    nl = sum(1 for l in results if l.country=="NL")
    be = sum(1 for l in results if l.country=="BE")
    has_email = sum(1 for l in results if l.email)
    has_phone = sum(1 for l in results if l.phone)

    c1,c2,c3,c4 = st.columns(4)
    for col, lbl, val in [(c1,"Totaal",len(results)),(c2,"Nederland",nl),
                          (c3,"België",be),(c4,"Met e-mail",has_email)]:
        col.markdown(
            f'<div class="stat-card"><div class="stat-label">{lbl}</div>'
            f'<div class="stat-value">{val}</div></div>', unsafe_allow_html=True)
    if st.session_state.last_run:
        st.caption(f"Laatste zoekopdracht: {st.session_state.last_run} — "
                   f"📞 {has_phone} met telefoon · 📧 {has_email} met e-mail")

    st.divider()

    # Zoekbalk
    search_q = st.text_input("🔎 Zoek in resultaten",
                             placeholder="bijv. Amsterdam, verpleeghuis...")
    df_view = df_master.copy()
    if search_q:
        mask = (df_view["Naam"].str.contains(search_q,case=False,na=False) |
                df_view["Locatie"].str.contains(search_q,case=False,na=False))
        df_view = df_view[mask].reset_index(drop=True)

    st.caption(f"{len(df_view)} van {len(results)} locaties weergegeven — "
               "**klik ☑ om te selecteren**")

    edited = st.data_editor(
        df_view,
        use_container_width=True,
        hide_index=True,
        height=480,
        column_config={
            "☑":        st.column_config.CheckboxColumn("☑",      width="small",  default=False),
            "Naam":     st.column_config.TextColumn("Naam instelling", width="large"),
            "Locatie":  st.column_config.TextColumn("Locatie",         width="large"),
            "Telefoon": st.column_config.TextColumn("Telefoon",        width="medium"),
            "E-mail":   st.column_config.TextColumn("E-mail",          width="medium"),
            "Website":  st.column_config.LinkColumn("Website", display_text="🔗", width="small"),
        },
        disabled=["Naam","Locatie","Telefoon","Website"],
        key="table_editor",
    )

    selected_df = edited[edited["☑"] == True].copy()
    n_sel = len(selected_df)

    # ── Download ──────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📥 Downloaden")

    scope = st.radio(
        "Exporteer:",
        ["Alle resultaten", "Alleen geselecteerde rijen"],
        horizontal=True,
        disabled=(n_sel == 0),
        index=1 if n_sel > 0 else 0,
    )
    src = selected_df if (scope == "Alleen geselecteerde rijen" and n_sel > 0) else edited

    # Export kolommen: alleen naam, locatie, telefoon, e-mail
    EX_COLS = ["Naam", "Locatie", "Telefoon", "E-mail"]
    ex_df = src[EX_COLS].rename(columns={
        "Naam":     "Naam instelling",
        "Locatie":  "Locatie",
        "Telefoon": "Telefoon",
        "E-mail":   "E-mail",
    })
    st.caption(f"{len(ex_df)} rijen — kolommen: Naam, Locatie, Telefoon, E-mail")

    dl1, dl2 = st.columns(2)

    # Excel
    with dl1:
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            xbuf = io.BytesIO()
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Zorg Locaties"

            HF = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
            HFI = PatternFill("solid", fgColor="1F4E79")
            AF  = PatternFill("solid", fgColor="EBF3FB")
            CF  = Font(name="Calibri", size=10)
            LF  = Font(name="Calibri", size=10, color="0563C1", underline="single")
            AL  = Alignment(horizontal="left", vertical="center")
            BO  = Border(bottom=Side(style="thin", color="D9D9D9"))
            WIDTHS = [40, 44, 20, 34]

            ws.row_dimensions[1].height = 22
            for ci, (col, w) in enumerate(zip(ex_df.columns, WIDTHS), 1):
                c = ws.cell(row=1, column=ci, value=col)
                c.font = HF; c.fill = HFI
                c.alignment = Alignment(horizontal="center", vertical="center")
                ws.column_dimensions[get_column_letter(ci)].width = w

            for ri, (_, row) in enumerate(ex_df.iterrows(), 2):
                fill = AF if ri % 2 == 0 else None
                ws.row_dimensions[ri].height = 16
                for ci, col in enumerate(ex_df.columns, 1):
                    val = str(row.get(col, "") or "")
                    cell = ws.cell(row=ri, column=ci, value=val)
                    cell.alignment = AL; cell.border = BO
                    if fill: cell.fill = fill
                    if col == "E-mail" and "@" in val:
                        cell.hyperlink = f"mailto:{val}"
                        cell.font = LF
                    else:
                        cell.font = CF

            ws.auto_filter.ref = f"A1:{get_column_letter(len(ex_df.columns))}1"
            ws.freeze_panes = "A2"
            wb.save(xbuf); xbuf.seek(0)

            dl1.download_button(
                "📊 Download Excel",
                data=xbuf,
                file_name=f"zorg_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            dl1.error(f"Excel fout: {e}")

    # CSV
    with dl2:
        csv_b = ex_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        dl2.download_button(
            "📄 Download CSV",
            data=csv_b,
            file_name=f"zorg_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

else:
    st.info("👈 Stel je filters in en klik **Start zoeken**.")
    st.markdown("""
    **Wat zoekt dit systeem?**
    - 🏠 Verpleeghuizen en woonzorgcentra (24/7 zorg)
    - 🧠 Dementie- en Alzheimer-afdelingen
    - 🏡 Kleinschalige woonvormen voor ouderen
    - Zowel **Nederland** als **België**

    **Contactgegevens ophalen** bezoekt automatisch elke gevonden website
    om telefoonnummers en e-mailadressen te vinden.

    **Tip:** gebruik **Snel zoeken** voor resultaten in <30 seconden.
    """)
