import asyncio
import edge_tts

VOICE = "en-US-AriaNeural"   # change this to try other voices
OUTPUT = "output.mp3"

async def text_to_mp3(text: str, output: str = OUTPUT):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output)
    print(f"Saved to {output}")

if __name__ == "__main__":
    print("Paste your text below. When finished, press Enter, then Ctrl+Z (Windows) or Ctrl+D (Mac/Linux), then Enter again.\n")
    import sys
    text = sys.stdin.read().strip()
    if text:
        asyncio.run(text_to_mp3(text))
    else:
        print("No text provided.")