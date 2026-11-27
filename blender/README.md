# Blender scripts

Tested with **Blender 5.x**.

## Wave visualizer

### In Blender

1. **Scripting** tab → **Open** → `scripts/wave_visualizer.py`
2. Set `AUDIO_PATH` at the top (mp3, wav, flac or ogg).
3. Optional: set `LOGO_PATH` to a PNG with a transparent background.
4. **Run Script** (Alt+P). For a long song, analysing the audio takes a few seconds.
5. Preview with Space, render with Ctrl+F12.

Run it again after changing settings. It only replaces its own objects (names starting with `ZV_`), so the rest of your scene is left alone. It also hides Blender's default cube so it doesn't block the wave (`HIDE_DEFAULT_CUBE`).

### From the command line (no UI)

```
blender -b -P wave_visualizer.py -- --audio "song.mp3"
blender -b -P wave_visualizer.py -- --audio "song.mp3" --landscape --render
```

| Flag | Meaning |
|---|---|
| `--audio PATH` | song file (required) |
| `--logo PATH` | PNG logo above the wave |
| `--landscape` | 1920x1080 instead of 1080x1920 |
| `--render` | render the animation straight away |

### What gets created

- `ZV_Visualizer` collection with 3 wave layers, a camera and an optional logo
- `ZV_Wave` Geometry Nodes group: you can tweak it in the Geometry Nodes editor
- `ZV_WaveData` image: the baked audio levels (packed into the .blend file)
- Render settings: EEVEE, MP4 (H.264 + AAC audio), bloom glow in the compositor

### Tips

- Want it smoother? Raise `SMOOTHING` to 0.7–0.8.
- Too jumpy or too flat? Change `WAVE_HEIGHT`.
- Fewer, bigger bumps: lower `BANDS` to 48. More detail: raise it to 128.
- One clean line only: keep just the first entry in `LAYERS` and set `MIRROR = False`.
