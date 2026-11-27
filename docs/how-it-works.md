# How it works

The wave visualizer runs in three steps.

## 1. Listen: analyse the song

For every video frame (30 per second by default), the script takes a short slice of audio and runs a **Fourier transform** (FFT) on it. That splits the sound into frequencies, from deep bass (40 Hz) up to bright highs (12 kHz).

Those frequencies are grouped into bands spaced the way our ears hear them (logarithmic), so bass, mids and highs each get a fair share of the wave. Then the script:

- converts the levels to a log scale and normalises them so loud and quiet songs both look good
- makes peaks **rise fast and fall slowly** (`SMOOTHING`), like a real VU meter
- blurs slightly between neighbouring bands so the line stays smooth
- mirrors left and right so the wave is symmetrical, with bass in the centre
- tapers the ends so the wave starts and ends flat

## 2. Remember: bake into an image

All the levels are stored in a small float image called `ZV_WaveData`:

- **x (width)** = position along the wave
- **y (height)** = frame number

A 3-minute song at 30 fps is only 96 × 5400 pixels. It's packed inside the .blend file, so the project works even if you move it to another computer.

## 3. Move: Geometry Nodes

The `ZV_Wave` node group:

1. Makes a straight line and resamples it into many points.
2. For each point, looks up its value in the image: x from its position on the line, y from the current frame.
3. Moves the point up by that value × `Height`.
4. Optionally adds an upside-down copy (`Mirror`).
5. Turns the curve into a thin glowing tube and applies the emission material.

Each echo layer uses the same node group with a smaller **Height** and a **Delay** of a few frames, which creates the trailing echo effect.

## Why this way?

- **No add-ons, no baking F-curves by hand:** it all happens in one script.
- **Fast playback:** reading one image is much lighter than hundreds of animated objects.
- **Easy to remix:** open the Geometry Nodes editor and add your own effects, like twisting, colour by height or particles.
