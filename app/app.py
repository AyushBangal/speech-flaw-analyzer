import sys, json, os, subprocess, tempfile
sys.path.insert(0, "src")
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from detect import detect

st.set_page_config(page_title="Speech Flaw Analyzer", layout="wide")
st.warning("Educational prototype. Decision support only, not a substitute for a human judge.")
st.title("Speech Flaw Analyzer")

CASES = {
    "Injected: rushed pace": ("labels/test_features.json", "labels/test_rushed_features.json", "data/flawed/test_rushed.wav"),
    "Injected: long pause": ("labels/test_features.json", "labels/test_pause_features.json", "data/flawed/test_pause.wav"),
    "Injected: volume drop": ("labels/test_features.json", "labels/test_volume_features.json", "data/flawed/test_volume.wav"),
    "Clean B vs clean A (false-alarm test)": ("labels/speech1_features.json", "labels/speech1_B_features.json", "data/baseline/speech1_B.wav"),
}

@st.cache_data
def load(p):
    return pd.DataFrame(json.load(open(p)))

def show(base_p, part_p, wav):
    base, part = load(base_p), load(part_p)
    regions = detect(base_p, part_p)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
        subplot_titles=("Pitch (semitones vs speaker median)", "Energy (z-score)", "Word duration (s)"))
    for i, col in enumerate(["f0_st_med", "energy_z", "dur"], start=1):
        fig.add_trace(go.Scatter(x=base["start"], y=base[col].astype(float), name="baseline",
                                 line=dict(color="gray"), showlegend=(i == 1)), row=i, col=1)
        fig.add_trace(go.Scatter(x=part["start"], y=part[col].astype(float), name="participant",
                                 line=dict(color="royalblue"), showlegend=(i == 1)), row=i, col=1)
    for r in regions:
        fig.add_vrect(x0=r["start"], x1=r["end"], fillcolor="red", opacity=0.2, line_width=0)
    fig.update_layout(height=700, xaxis3_title="Time in each recording (s)")
    st.plotly_chart(fig, use_container_width=True)
    st.subheader(f"Detected flaw regions: {len(regions)}")
    if not regions:
        st.success("No flaws detected.")
    for r in regions:
        st.markdown(f"**{r['type']}**: {r['start']:.2f}s to {r['end']:.2f}s")
        st.write(r["why"][0] + (f" (+{len(r['why']) - 1} more words)" if len(r["why"]) > 1 else ""))
        if os.path.exists(wav):
            st.audio(wav, start_time=int(r["start"]))

tab1, tab2 = st.tabs(["Prepared recordings", "Upload your own"])

with tab1:
    name = st.selectbox("Recording to analyze", list(CASES))
    b, p, w = CASES[name]
    if os.path.exists(b) and os.path.exists(p):
        show(b, p, w)
    else:
        st.error("Feature files not found. Run align.py and features.py first.")

with tab2:
    st.write("Compared against the reference reading (speaker A) of the Gettysburg text. "
             "The transcript must be the same text, word for word.")
    up = st.file_uploader("Audio", type=["wav", "mp3", "m4a", "ogg", "mp4"])
    txt = st.file_uploader("Transcript (.txt)", type=["txt"])
    if up and txt and st.button("Analyze"):
        d = tempfile.mkdtemp()
        raw = os.path.join(d, "in" + os.path.splitext(up.name)[1])
        wav, tx = os.path.join(d, "u.wav"), os.path.join(d, "u.txt")
        asr, words, feats = (os.path.join(d, n) for n in ("asr.json", "words.json", "feats.json"))
        open(raw, "wb").write(up.getbuffer())
        open(tx, "wb").write(txt.getbuffer())
        try:
            with st.spinner("Converting, aligning, extracting features (1-2 min)..."):
                for cmd in (
                    ["ffmpeg", "-y", "-i", raw, "-ac", "1", "-ar", "22050", wav],
                    [sys.executable, "src/align.py", wav, asr],
                    [sys.executable, "src/fix_words.py", tx, asr, words],
                    [sys.executable, "src/features.py", wav, words, feats],
                ):
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
            show("labels/speech1_features.json", feats, wav)
        except subprocess.CalledProcessError as e:
            st.error("Processing failed. Check the audio and that the transcript matches the reference text.")
            st.code((e.stderr or "")[-1500:])