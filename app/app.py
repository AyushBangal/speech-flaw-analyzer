import sys, json, os, subprocess, tempfile, difflib, re
sys.path.insert(0, "src")
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from detect import detect
from detect_solo import detect_solo

st.set_page_config(page_title="Speech Flaw Analyzer", layout="wide")
st.warning("Educational prototype. Decision support only, not a substitute for a human judge.")
st.title("Speech Flaw Analyzer")

REF_TXT = "data/baseline/speech1.txt"
REF_FEATS = "labels/speech1_features.json"

CASES = {
    "Injected: rushed pace": ("labels/test_features.json", "labels/test_rushed_features.json", "data/flawed/test_rushed.wav"),
    "Injected: long pause": ("labels/test_features.json", "labels/test_pause_features.json", "data/flawed/test_pause.wav"),
    "Injected: volume drop": ("labels/test_features.json", "labels/test_volume_features.json", "data/flawed/test_volume.wav"),
    "Clean B vs clean A (false-alarm test)": ("labels/speech1_features.json", "labels/speech1_B_features.json", "data/baseline/speech1_B.wav"),
}

def toks(t):
    return re.sub(r"[^a-z0-9' ]", " ", t.lower()).split()

def similarity(a, b):
    return difflib.SequenceMatcher(None, toks(a), toks(b), autojunk=False).ratio()

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
    st.plotly_chart(fig, width="stretch")
    st.subheader(f"Detected flaw regions: {len(regions)}")
    if not regions:
        st.success("No flaws detected.")
    for r in regions:
        st.markdown(f"**{r['type']}**: {r['start']:.2f}s to {r['end']:.2f}s")
        st.write(r["why"][0] + (f" (+{len(r['why']) - 1} more words)" if len(r["why"]) > 1 else ""))
        if os.path.exists(wav):
            st.audio(wav, start_time=int(r["start"]))

def run_pipeline(data, ext, tx_path):
    d = tempfile.mkdtemp()
    raw = os.path.join(d, "in" + ext)
    wav = os.path.join(d, "u.wav")
    asr, words, feats = (os.path.join(d, n) for n in ("asr.json", "words.json", "feats.json"))
    open(raw, "wb").write(data)
    for cmd in (
        ["ffmpeg", "-y", "-i", raw, "-ac", "1", "-ar", "22050", wav],
        [sys.executable, "src/align.py", wav, asr],
        [sys.executable, "src/fix_words.py", tx_path, asr, words],
        [sys.executable, "src/features.py", wav, words, feats],
    ):
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    return wav, feats, asr

def analyze(data, ext, tx_path):
    try:
        with st.spinner("Converting, aligning, extracting features (1-2 min)..."):
            wav, feats, asr = run_pipeline(data, ext, tx_path)
        heard = " ".join(w["word"] for w in json.load(open(asr)))
        ref = open(REF_TXT, encoding="utf-8").read()
        sim = similarity(ref, heard)
        st.subheader("What we heard")
        st.caption(f"Speech recognition output, {sim:.0%} match with the reference text")
        st.write(heard)
        if sim < 0.8:
            st.error("This doesn't match the reference text, so no comparison was run. "
                     "Read the text shown above, or use the Free speech mode.")
            return
        show(REF_FEATS, feats, wav)
    except subprocess.CalledProcessError as e:
        st.error("Processing failed. Check the audio and that the text matches the reference.")
        st.code((e.stderr or "")[-1500:])

def run_free(data, ext):
    d = tempfile.mkdtemp()
    raw = os.path.join(d, "in" + ext)
    wav = os.path.join(d, "u.wav")
    asr, feats = os.path.join(d, "asr.json"), os.path.join(d, "feats.json")
    open(raw, "wb").write(data)
    for cmd in (
        ["ffmpeg", "-y", "-i", raw, "-ac", "1", "-ar", "22050", wav],
        [sys.executable, "src/align.py", wav, asr],
        [sys.executable, "src/features.py", wav, asr, feats],
    ):
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    return wav, feats, asr

def analyze_free(data, ext):
    try:
        with st.spinner("Converting, transcribing, extracting features (1-2 min)..."):
            wav, feats, asr = run_free(data, ext)
        st.subheader("What we heard")
        st.write(" ".join(w["word"] for w in json.load(open(asr))))
        df = load(feats)
        regions = detect_solo(feats)
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
            subplot_titles=("Pitch (semitones vs speaker median)", "Energy (z-score)", "Word duration (s)"))
        for i, col in enumerate(["f0_st_med", "energy_z", "dur"], start=1):
            fig.add_trace(go.Scatter(x=df["start"], y=df[col].astype(float),
                                     line=dict(color="royalblue"), showlegend=False), row=i, col=1)
        for r in regions:
            fig.add_vrect(x0=r["start"], x1=r["end"], fillcolor="red", opacity=0.2, line_width=0)
        fig.update_layout(height=700, xaxis3_title="Time (s)")
        st.plotly_chart(fig, width="stretch")
        st.subheader(f"Detected flaw regions: {len(regions)}")
        if not regions:
            st.success("No flaws detected.")
        for r in regions:
            st.markdown(f"**{r['type']}**: {r['start']:.2f}s to {r['end']:.2f}s")
            st.write(r["why"][0] + (f" (+{len(r['why']) - 1} more windows)" if len(r["why"]) > 1 else ""))
            st.audio(wav, start_time=int(r["start"]))
    except subprocess.CalledProcessError as e:
        st.error("Processing failed.")
        st.code((e.stderr or "")[-1500:])

tab1, tab2 = st.tabs(["Prepared recordings", "Upload or record"])

with tab1:
    name = st.selectbox("Recording to analyze", list(CASES))
    b, p, w = CASES[name]
    if os.path.exists(b) and os.path.exists(p):
        show(b, p, w)
    else:
        st.error("Feature files not found. Run align.py and features.py first.")

with tab2:
    st.write("Your reading is compared with the reference reading (speaker A) of the first two "
             "paragraphs of the Gettysburg Address.")
    mode = st.radio("Input", ["Record live", "Upload a file", "Free speech (no reference)"], horizontal=True)

    if mode == "Record live":
        st.info("Read this text aloud, word for word, in a quiet room:")
        st.write(open(REF_TXT, encoding="utf-8").read())
        if "rec_n" not in st.session_state:
            st.session_state.rec_n = 0
        rec = st.audio_input("Record", key=f"rec_{st.session_state.rec_n}")
        if rec:
            st.caption("Listen to your recording. Analyze it, or retake if you stumbled.")
            c1, c2 = st.columns(2)
            do_analyze = c1.button("Analyze recording", type="primary")
            do_retake = c2.button("Retake")
            if do_retake:
                st.session_state.rec_n += 1
                st.rerun()
            if do_analyze:
                analyze(rec.getvalue(), ".wav", REF_TXT)
    elif mode == "Upload a file":
        up = st.file_uploader("Audio", type=["wav", "mp3", "m4a", "ogg", "mp4"])
        txt = st.file_uploader("Transcript (.txt)", type=["txt"])
        if up and txt and st.button("Analyze upload"):
            content = txt.getvalue().decode("utf-8", errors="ignore")
            sim = similarity(open(REF_TXT, encoding="utf-8").read(), content)
            if sim < 0.9:
                st.error(f"This transcript matches the reference text only {sim:.0%}. "
                         "This prototype compares against one reference reading.")
                st.stop()
            tx = os.path.join(tempfile.mkdtemp(), "u.txt")
            open(tx, "wb").write(txt.getvalue())
            analyze(up.getvalue(), os.path.splitext(up.name)[1], tx)
    else:
        st.info("Speak anything for 20 seconds or more. You are compared with your own average delivery, not a reference.")
        frec = st.audio_input("Record", key="free_rec")
        if frec and st.button("Analyze free speech"):
            analyze_free(frec.getvalue(), ".wav")