import asyncio
import os
import edge_tts

# ============================================================
#  YOUR TEST SENTENCE  ->  every voice reads exactly this
# ============================================================
SENTENCE = ("Good evening. Officials confirmed today that the old harbor bridge "
            "will reopen next week, two months ahead of schedule.")

GENDER = "Female"            # "Female" or "Male"
LOCALE_PREFIX = "en-"        # "en-" = all English accents. "en-US" / "en-GB" to narrow it down
NEWS_ONLY = False            # True = only voices Microsoft tags as News / reporter-style

RATE = "+0%"                 # try "+75%" to hear them at your watcher speed
PITCH = "+0Hz"

OUT_DIR = "samples_female"
CONCURRENCY = 5              # how many voices to generate at once
# ============================================================


def tags(v):
    t = v.get("VoiceTag", {}) or {}
    cats = ", ".join(t.get("ContentCategories", [])) or "-"
    pers = ", ".join(t.get("VoicePersonalities", [])) or "-"
    return cats, pers


async def make_sample(sem, num, voice):
    name = voice["ShortName"]
    path = os.path.join(OUT_DIR, f"{GENDER.lower()}{num:02d} {name}.mp3")
    async with sem:
        try:
            await edge_tts.Communicate(SENTENCE, name, rate=RATE, pitch=PITCH).save(path)
            print(f"{os.path.basename(path)}")
        except Exception as e:
            print(f"{GENDER.lower()}{num:02d}  FAILED ({name}): {e}")


async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    voices = await edge_tts.list_voices()
    picks = [v for v in voices
             if v["Gender"] == GENDER and v["Locale"].startswith(LOCALE_PREFIX)]
    if NEWS_ONLY:
        picks = [v for v in picks if "News" in tags(v)[0]]
    picks.sort(key=lambda v: v["ShortName"])

    # Key file: which number is which voice, plus Microsoft's own style tags
    with open(os.path.join(OUT_DIR, "voice_key.txt"), "w", encoding="utf-8") as f:
        f.write(f'Sentence: "{SENTENCE}"\nRate {RATE}, pitch {PITCH}\n\n')
        for i, v in enumerate(picks, 1):
            cats, pers = tags(v)
            f.write(f"{GENDER.lower()}{i:02d} = {v['ShortName']:<34} "
                    f"for: {cats:<20} sounds: {pers}\n")

    print(f"Generating {len(picks)} {GENDER.lower()} voices...\n")
    sem = asyncio.Semaphore(CONCURRENCY)
    await asyncio.gather(*(make_sample(sem, i, v) for i, v in enumerate(picks, 1)))
    print(f"\nDone. Files are in the '{OUT_DIR}' folder (see voice_key.txt).")

asyncio.run(main())