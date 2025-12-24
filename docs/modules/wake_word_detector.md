# Wake Word Detector Module

**File:** `modules/wake_word_detector.py`

Wake word detection using Picovoice Porcupine.

## Features

- Built-in keywords (no training needed)
- Custom .ppn file support
- GPU acceleration (Porcupine v4)
- Low-latency detection

## Built-in Keywords

No training required:
```
alexa, americano, blueberry, bumblebee, computer,
grapefruit, grasshopper, hey barista, hey google,
hey siri, jarvis, ok google, pico clock, picovoice,
porcupine, terminator
```

## Configuration

Set in `.env`:
```env
# Required
PICOVOICE_ACCESS_KEY=your_access_key

# Wake word (built-in or custom)
WAKE_WORD_KEYWORDS=jarvis

# Custom .ppn file path (optional)
WAKE_WORD_PATH=path/to/Sakura_en_windows_v4_0_0.ppn

# GPU acceleration (optional)
PORCUPINE_DEVICE=best  # best, gpu:0, cpu, cpu:8
```

## Custom Wake Words

1. Train at [Picovoice Console](https://console.picovoice.ai/)
2. Download .ppn file for Windows
3. Set `WAKE_WORD_PATH` in `.env`

## Usage

```python
detector = WakeWordDetector(
    access_key="your_key",
    keywords=["jarvis"],
    keyword_paths=["path/to/custom.ppn"],
    device="best"
)

detector.initialize()

# Process audio
while True:
    audio_chunk = get_audio()
    keyword_index = detector.process(audio_chunk)
    if keyword_index >= 0:
        print(f"Wake word detected: {detector.keywords[keyword_index]}")
        # Start listening...

detector.cleanup()
```

## GPU Acceleration

Porcupine v4 supports GPU:
```env
# Auto-select best device
PORCUPINE_DEVICE=best

# Force GPU
PORCUPINE_DEVICE=gpu:0

# Force CPU with thread count
PORCUPINE_DEVICE=cpu:8
```

## Audio Requirements

- Sample rate: 16kHz
- Format: 16-bit PCM
- Frame length: 512 samples

## Graceful Fallback

If wake word detection fails:
- Logs warning
- Falls back to continuous listening
- Voice interaction still works
