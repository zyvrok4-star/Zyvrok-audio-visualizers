# Colour presets

Copy one `LAYERS` block into the SETTINGS section of `wave_visualizer.py`.
Format: `(colour RGB 0-1, height multiplier, delay in frames, glow strength)`

## Neon (default)

```python
LAYERS = [
    ((0.10, 0.85, 1.00), 1.00, 0, 12.0),   # cyan
    ((0.75, 0.25, 1.00), 0.75, 3, 8.0),    # purple
    ((1.00, 0.20, 0.55), 0.50, 6, 6.0),    # pink
]
BACKGROUND = (0.005, 0.005, 0.012)
```

## Gold

```python
LAYERS = [
    ((1.00, 0.72, 0.25), 1.00, 0, 10.0),
    ((1.00, 0.45, 0.10), 0.75, 3, 7.0),
    ((0.60, 0.20, 0.05), 0.50, 6, 5.0),
]
BACKGROUND = (0.008, 0.005, 0.002)
```

## Fire

```python
LAYERS = [
    ((1.00, 0.85, 0.30), 1.00, 0, 12.0),
    ((1.00, 0.35, 0.05), 0.75, 2, 9.0),
    ((0.80, 0.05, 0.02), 0.50, 5, 6.0),
]
BACKGROUND = (0.006, 0.002, 0.001)
```

## Ice

```python
LAYERS = [
    ((0.85, 0.95, 1.00), 1.00, 0, 10.0),
    ((0.35, 0.70, 1.00), 0.75, 3, 8.0),
    ((0.10, 0.30, 0.90), 0.50, 6, 6.0),
]
BACKGROUND = (0.002, 0.004, 0.010)
```

## Toxic

```python
LAYERS = [
    ((0.60, 1.00, 0.20), 1.00, 0, 10.0),
    ((0.10, 0.90, 0.50), 0.75, 3, 7.0),
    ((0.05, 0.50, 0.40), 0.50, 6, 5.0),
]
BACKGROUND = (0.002, 0.006, 0.004)
```

## Mono (clean, minimal)

```python
LAYERS = [
    ((1.00, 1.00, 1.00), 1.00, 0, 6.0),
]
BACKGROUND = (0.0, 0.0, 0.0)
```

Tip: very bright glow makes colours look whiter. For stronger colour, lower the glow strength to 4–6.
