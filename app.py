"""Live VORP draft board for the unified FPL ranking.

Run with: streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from vorp_engine import POSITIONS, compute_vorp

DATA_PATH = Path(__file__).resolve().parent / "data" / "unified.csv"
DRAFT_STATE_PATH = Path(__file__).resolve().parent / "data" / "draft_state.json"

st.set_page_config(page_title="FPL Draft VORP Board", layout="wide")


@st.cache_data
def load_unified() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def load_drafted() -> list:
    if DRAFT_STATE_PATH.exists():
        return json.loads(DRAFT_STATE_PATH.read_text())
    return []


def save_drafted(drafted: list) -> None:
    DRAFT_STATE_PATH.write_text(json.dumps(drafted, indent=2))


if "drafted" not in st.session_state:
    st.session_state.drafted = load_drafted()

st.title("FPL Draft VORP Board")

with st.sidebar:
    st.header("League settings")
    num_teams = st.number_input("Number of teams", min_value=2, max_value=20, value=10)
    st.caption("Starters per position (defines replacement level)")
    starters = {
        "GK": st.number_input("GK starters", min_value=0, max_value=3, value=1),
        "DEF": st.number_input("DEF starters", min_value=0, max_value=8, value=4),
        "MID": st.number_input("MID starters", min_value=0, max_value=8, value=4),
        "FWD": st.number_input("FWD starters", min_value=0, max_value=6, value=2),
    }

    st.header("Draft control")
    if st.session_state.drafted and st.button("Undo last pick"):
        st.session_state.drafted.pop()
        save_drafted(st.session_state.drafted)
        st.rerun()

    if st.button("Reset draft"):
        st.session_state.drafted = []
        save_drafted(st.session_state.drafted)
        st.rerun()

raw = load_unified()
board = compute_vorp(raw, num_teams, starters)

available = board[~board["player"].isin(st.session_state.drafted)].sort_values("vorp", ascending=False)
drafted_df = board[board["player"].isin(st.session_state.drafted)]

if available.empty:
    st.subheader("No players left to draft.")
else:
    top = available.iloc[0]
    st.subheader(
        f"Suggested next pick: **{top['player']}** ({top['team']}, {top['position']}) "
        f"— VORP {top['vorp']:.1f}"
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        pick = st.selectbox(
            "Player Name",
            options=available["player"].tolist(),
            index=0,
            placeholder="Search a player to draft...",
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("Draft player", type="primary"):
            st.session_state.drafted.append(pick)
            save_drafted(st.session_state.drafted)
            st.rerun()

st.divider()

fcol1, fcol2 = st.columns([2, 2])
with fcol1:
    search = st.text_input("Filter board by name")
with fcol2:
    pos_filter = st.multiselect("Position", POSITIONS, default=POSITIONS)

view = available[available["position"].isin(pos_filter)]
if search:
    view = view[view["player"].str.contains(search, case=False, na=False)]

st.subheader(f"Available players ({len(view)})")
st.dataframe(
    view[["unified_rank", "player", "team", "position", "value", "replacement_value", "vorp", "sources_count"]]
    .rename(
        columns={
            "unified_rank": "Rank",
            "player": "Player",
            "team": "Team",
            "position": "Pos",
            "value": "Value",
            "replacement_value": "Replacement",
            "vorp": "VORP",
            "sources_count": "# Sources",
        }
    )
    .round({"Value": 1, "Replacement": 1, "VORP": 1}),
    use_container_width=True,
    hide_index=True,
)

with st.expander(f"Drafted players ({len(drafted_df)})"):
    st.dataframe(
        drafted_df[["player", "team", "position", "vorp"]].rename(
            columns={"player": "Player", "team": "Team", "position": "Pos", "vorp": "VORP (at draft)"}
        ),
        use_container_width=True,
        hide_index=True,
    )
