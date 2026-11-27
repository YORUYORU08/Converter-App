import asyncio
import os
import edge_tts

VOICE = "en-GB-RyanNeural"
TEXT = ("The old lighthouse keeper sat by the fire, his voice low and slow. "
        "\"Come closer, child,\" he said, \"and I will tell you how the storm took the sea.\"")
OUT_DIR = "ryan_samples"
CONCURRENCY = 4

PITCHES = [0, -10, -20, -30, -40]                  # Hz, lower = deeper/older
RATES = ["-10%", "+0%", "+50%", "+100%"]           # +100% is baked-in 2x speed

async def make(sem, name, pitch, rate):
    path = os.path.join(OUT_DIR, name)
    async with sem:
        try:
            await edge_tts.Communicate(TEXT, VOICE, rate=rate, pitch=f"{pitch:+d}Hz").save(path)
            print(f"{name}  (pitch {pitch:+d}Hz, rate {rate})")
        except Exception as e:
            print(f"{name} FAILED: {e}")

async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    jobs = []
    for p in PITCHES:
        for r in RATES:
            name = f"ryan_pitch{p:+d}_rate{r.replace('%','')}.mp3"
            jobs.append(make(sem, name, p, r))
    print(f"Generating {len(jobs)} samples...\n")
    await asyncio.gather(*jobs)
    print(f"\nDone. Check the '{OUT_DIR}' folder.")

asyncio.run(main())