import json, sys
import librosa
from faster_whisper import WhisperModel

def align(path, out):
    audio, _ = librosa.load(path, sr=16000, mono=True)
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(audio, word_timestamps=True, language="en")
    words = [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
             for s in segs for w in s.words]
    json.dump(words, open(out, "w"), indent=2)
    print(len(words), "words")

if __name__ == "__main__":
    align(sys.argv[1], sys.argv[2])