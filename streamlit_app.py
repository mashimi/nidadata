"""A browser-based UI for the nida package.

    pip install streamlit
    streamlit run streamlit_app.py

Same limitation as the desktop app: NIDA only supports lookup by National ID,
so the name search covers records looked up on this machine.
"""

from __future__ import annotations

import json
import os
import time

import streamlit as st

from nida import Nida
from nida.exceptions import NidaError

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "nida_history.json")

st.set_page_config(page_title="NIDA Lookup - Tanzania", page_icon="🪪",
                   layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2.2rem; max-width: 1100px;}
      [data-testid="stMetricValue"] {font-size: 1.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1, 2])

with left:
    st.subheader("Look up a person")
    nin = st.text_input("National ID (20 digits)", placeholder="19990512141150000123",
                        max_chars=25)
    fetch = st.button("Fetch record", type="primary", use_container_width=True)

    st.subheader("Search your history")
    query = st.text_input("Name", placeholder="e.g. Amani", max_chars=60)

with right:
    st.subheader("Record")

digits = "".join(ch for ch in nin if ch.isdigit())

if fetch:
    if len(digits) != 20:
        st.error("A National ID is exactly 20 digits.")
    else:
        with st.spinner("Fetching record..."):
            try:
                user = Nida(timeout=20).load_user(digits)
            except NidaError as exc:
                st.error(str(exc))
            except Exception as exc:  # keep the page alive on unexpected errors
                st.error(f"Unexpected error: {exc}")
            else:
                st.session_state["record"] = (digits, dict(user), time.time())
                try:
                    history = {}
                    if os.path.exists(HISTORY_FILE):
                        with open(HISTORY_FILE, encoding="utf-8") as handle:
                            history = json.load(handle)
                    history[digits] = {k: str(v) for k, v in user.items()
                                       if k not in ("Photo", "Signature")}
                    with open(HISTORY_FILE, "w", encoding="utf-8") as handle:
                        json.dump(history, handle, indent=2, ensure_ascii=False)
                except OSError:
                    st.warning("Fetched, but the history file could not be saved.")

if query:
    try:
        with open(HISTORY_FILE, encoding="utf-8") as handle:
            history = json.load(handle)
    except (OSError, json.JSONDecodeError):
        history = {}
    matches = {n: r for n, r in history.items()
               if query.lower() in " ".join(str(v) for v in r.values()).lower()}
    if matches:
        with left:
            st.markdown(f"**{len(matches)} cached match(es)**")
            choice = st.selectbox("Pick a record", list(matches),
                                  format_func=lambda n: (
                                      f"{matches[n].get('Fullname', matches[n].get('FULLNAME', ''))} "
                                      f"· {n}"))
            if st.button("Open cached record", use_container_width=True):
                st.session_state["record"] = (choice, dict(matches[choice]),
                                              time.time())
                st.info("Cached records have no photo or signature - "
                        "re-fetch to load the images.")
    else:
        with left:
            st.info("No cached match. Name search only covers IDs that were "
                    "already fetched on this machine.")

record = st.session_state.get("record")
if record:
    record_nin, data, _stamp = record
    name = data.get("Fullname") or data.get("Fullname") or record_nin
    st.markdown(f"### {name}")
    st.code(record_nin, language=None)

    chips = st.columns(4)
    for slot, (label, key) in zip(
            chips, (("Gender", "Gender"), ("Born", "Date_of_birth"),
                    ("District", "District"), ("Region", "Region"))):
        value = data.get(key) or data.get(key.upper())
        slot.metric(label, str(value) if value else "—")

    photo, signature = st.columns([1, 2])
    with photo:
        if data.get("Photo") is not None:
            st.image(data["Photo"], caption="Photo", width=220)
        else:
            st.info("No photo")
    with signature:
        if data.get("Signature") is not None:
            st.image(data["Signature"], caption="Signature")
        else:
            st.info("No signature")
        st.markdown("**All fields**")
        st.json({k: (str(v) if not isinstance(v, (str, int, float, type(None)))
                     else v)
                 for k, v in data.items() if k not in ("Photo", "Signature")},
                expanded=True)
else:
    st.info("Look up a 20-digit National ID, or search your lookup history by name.")
