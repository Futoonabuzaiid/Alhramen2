# Haramain sermons (manual addition only — not scraped)

Per project policy, sermon audio/text from the Two Holy Mosques is **not**
scraped or downloaded from YouTube/broadcast platforms by this pipeline. This
folder exists so sermons can be added manually if/when permission is
obtained.

## Expected input format

One of the following per sermon, placed in a subfolder named by date and
type, e.g. `2024-03-15_jumuah_makkah/`:

**Option A — aligned CSV** (preferred for text-only contributions):
```
ref,ar,en,fr,id,ur,tr
khutba:2024-03-15-jumuah-makkah:001,"...arabic sentence...","...","...","...","...","..."
khutba:2024-03-15-jumuah-makkah:002,...
```

**Option B — separate aligned files** (one sentence per line, same line count
and order in every file):
```
2024-03-15_jumuah_makkah/
  ar.txt
  en.txt
  fr.txt
  id.txt
  ur.txt
  tr.txt
  meta.json   # {"date": "2024-03-15", "location": "Masjid al-Haram", "speaker": "...", "type": "jumuah|lesson"}
```

If audio is also being contributed (Phase 2), add:
```
  audio.wav   # 16kHz mono, or original format + a note on how to convert
```

Once added, `src/ingest_haramain.py` (to be written once real data exists)
will read either format and emit the same JSONL schema as the rest of the
pipeline, with `domain: "khutba"` and `ref` as shown above.
