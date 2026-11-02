# 用 faster-whisper 给 AI 成曲的人声做逐词时间戳（日语），输出 json。CPU int8 即可，约 1–3 分钟。
# 用法：python tools/lyrics_align.py music.wav out/lyrics.json "歌词提示（可选）"
import sys, json
from faster_whisper import WhisperModel
audio, out = sys.argv[1], sys.argv[2]
hint = sys.argv[3] if len(sys.argv) > 3 else None
m = WhisperModel('medium', device='cpu', compute_type='int8', cpu_threads=8)
segs, info = m.transcribe(audio, language='ja', word_timestamps=True, initial_prompt=hint)
res = [{'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text,
        'words': [{'s': round(w.start, 2), 'e': round(w.end, 2), 'w': w.word} for w in (s.words or [])]}
       for s in segs]
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for s in res:
    print(f"{s['start']:6.2f}-{s['end']:6.2f} {s['text']}")
