# Audio Manager Module

**File:** `modules/audio_manager.py`

Handles audio input/output operations for voice interaction.

## Features

- Microphone input (16kHz)
- Speaker output (24kHz)
- PyAudio for streaming
- Pygame mixer for effects

## Sample Rates

Gemini Live API requirements:
- **Input (mic)**: 16kHz - what Gemini expects
- **Output (speaker)**: 24kHz - what Gemini returns

## Configuration

```python
manager = AudioManager(
    sample_rate=24000,  # Output rate
    chunk_size=1024
)
```

## Usage

```python
manager = AudioManager()
manager.initialize()

# Read from microphone
audio_chunk = manager.read_audio_chunk()

# Play audio
manager.play_audio(audio_data)

# Cleanup
manager.cleanup()
```

## Audio Streams

### Input Stream (Microphone)
```python
stream_in = p.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,  # 16kHz for Gemini
    input=True,
    frames_per_buffer=1024
)
```

### Output Stream (Speaker)
```python
stream_out = p.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=24000,  # 24kHz from Gemini
    output=True,
    frames_per_buffer=2048  # Larger for smooth playback
)
```

## Error Handling

- Graceful handling of audio device errors
- Fallback when devices unavailable
- Overflow protection on read

## Dependencies

```
pyaudio>=0.2.14
pygame>=2.5.0
numpy
```
