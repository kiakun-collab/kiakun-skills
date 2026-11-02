"""Report "dead" stretches in a rendered video: spans where the picture does not change.

Usage: python -I deadframes.py video.mp4 [min_seconds=0.3] [noise=0.0005]
Prints each frozen span, the total share of frozen time, and the longest span.
Rule of thumb for short-form video: frozen share under 10%, and no frozen span
over 0.8s except a deliberate final hold.
"""
import re
import subprocess
import sys

video = sys.argv[1]
min_d = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
noise = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0005

dur = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
    capture_output=True, text=True, check=True).stdout.strip())
log = subprocess.run(
    ["ffmpeg", "-hide_banner", "-i", video, "-map", "0:v", "-vf", f"freezedetect=n={noise}:d={min_d}", "-f", "null", "-"],
    capture_output=True, text=True).stderr

starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", log)]
ends = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", log)]
ends += [dur] * (len(starts) - len(ends))  # a freeze running to the last frame has no end marker

spans = list(zip(starts, ends))
total = sum(e - s for s, e in spans)
for s, e in spans:
    flag = "  <-- long" if e - s > 0.8 else ""
    print(f"{s:6.2f} - {e:6.2f}  {e - s:4.2f}s{flag}")
longest = max((e - s for s, e in spans), default=0)
print(f"frozen {total:.1f}s of {dur:.1f}s ({total / dur:.0%}), {len(spans)} spans, longest {longest:.2f}s")
