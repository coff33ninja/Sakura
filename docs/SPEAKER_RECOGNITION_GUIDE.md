# Speaker Recognition Quick Start Guide

## What Is Speaker Recognition?

Speaker Recognition teaches Sakura to only respond to **YOUR voice**. It:
- 🎤 Learns your voice in 5-10 samples (~1 min total)
- 🔐 Rejects requests from other speakers in STRICT mode
- 📊 Validates audio quality before acceptance
- 💾 Stores profiles locally (no cloud upload)
- 👥 Supports multiple family members with different permission levels

## Quick Start (5 minutes)

### Step 1: Enroll Your Voice

```python
# In your Sakura conversation:
"Sakura, enroll my voice"

# Sakura will say: "I'll learn your voice. Say a few sentences clearly, 5 times"
# You say 5 different sentences, each 3-30 seconds:
# 1. "This is my voice for Sakura to learn"
# 2. "My name is John and this is my voice"
# 3. "I speak clearly and Sakura recognizes me"
# 4. "Every word helps Sakura learn better"
# 5. "This is my fifth and final voice sample"

# Sakura responds:
# ✅ "Voice enrolled! Confidence: 92%. I'll only respond to you in STRICT mode."
```

### Step 2: Enable Strict Mode

```python
"Sakura, enable strict voice authentication"
# Sakura: "Voice authentication enabled. I'll only respond to recognized speakers."

# Now test with someone else speaking:
"Other person: Sakura, what time is it?"
# Sakura: "I don't recognize your voice. Please ask [Owner's name]."
```

### Step 3: Check Who's Speaking

```python
"Sakura, who am I?"
# Sakura: "You're John, my owner. Voice confidence: 89%"

# Other person tries:
"Sakura, who am I?"
# Sakura: "I don't recognize your voice. I'm sorry!"
```

## Command Reference

### Enrollment
```python
# Start training mode
"Sakura, learn my voice"
"Sakura, enroll my voice"
"Sakura, teach you my voice"

# Sakura records samples, extracts features, stores profile
```

### Authentication Control
```python
# Enable strict security
"Sakura, enable voice authentication"
"Sakura, strict mode only"
"Sakura, set auth mode to STRICT"

# Disable authentication (convenience mode)
"Sakura, disable voice authentication"
"Sakura, optional authentication"
"Sakura, anyone can talk to me"

# Check current mode
"Sakura, what's your security mode?"
"Sakura, is voice authentication enabled?"
```

### Profile Management
```python
# Add another family member
"Sakura, enroll my wife's voice"
"Sakura, learn my son's voice"
"Sakura, teach you my friend's voice"

# Check who's recognized
"Sakura, list my voice profiles"
"Sakura, who do you know?"
"Sakura, show all enrolled speakers"

# Remove someone
"Sakura, forget John's voice"
"Sakura, remove speaker profile speaker_2"
```

### Diagnostics
```python
# Check audio quality
"Sakura, is my audio clear?"
"Sakura, verify my voice quality"
"Sakura, check if this is good audio"

# Get speaker info
"Sakura, what do you know about me?"
"Sakura, show speaker_1 info"
```

## Authentication Modes

### DISABLED (No Security)
- Anyone can use Sakura
- No voice checking
- Fastest response
- Use for: Testing, demos, shared devices

```python
"Sakura, disable voice security"
```

### OPTIONAL (Convenience + Fallback)
- Tries to recognize voice, but doesn't fail if it can't
- Logs authentication attempts
- Logs warnings for unrecognized speakers
- Use for: Personal device, lenient mode

```python
"Sakura, optional voice recognition"
```

### STRICT (Security First)
- Only responds to enrolled speakers
- Rejects unrecognized voices
- Asks for re-enrollment if confidence too low
- Use for: Private data, sensitive operations

```python
"Sakura, strict voice authentication"
```

### TRAINING (Learning Mode)
- Records and learns during conversations
- Improves accuracy over time
- No rejections
- Use for: New users, refining profiles

```python
"Sakura, learning mode"
```

## Owner vs Member

### Owner Account
- Mark when enrolling: `"Sakura, enroll my voice as owner"`
- Can manage all settings
- Can add/remove other users
- Can change authentication mode
- Can access everything

### Member Account
- Regular speaker without admin rights
- Can be set to different permission levels (future)
- Can use any enrolled tools
- Cannot change authentication mode

```python
# Enroll owner (you)
"Sakura, learn my voice as the owner"

# Enroll family member
"Sakura, learn my son's voice"  # Not owner by default
```

## How Accurate Is It?

### Confidence Levels

| Score | Rating | Action |
|-------|--------|--------|
| 90%+ | Excellent | Approve immediately |
| 75-89% | Good | Approve with log |
| 60-74% | Fair | Ask for confirmation |
| <60% | Poor | Ask to re-record sample |

### Why Recognition Might Fail

- 🔊 **Noisy background** → Record in quiet room
- 📱 **Poor microphone** → Use better mic/headset
- 🤐 **Voice too quiet** → Speak normally, loud enough
- 🗣️ **Different voice state** (sick, tired) → Re-enroll when healthy
- 🎙️ **Different microphone** → Re-enroll with new mic

### Improving Recognition

1. **Enroll in quiet room** - No background noise
2. **Use consistent microphone** - Same mic every time
3. **Speak naturally** - Don't exaggerate or whisper
4. **5-10 samples** - More samples = higher accuracy
5. **Varied content** - Say different sentences

## Audio Quality Tips

```
✅ GOOD AUDIO (80%+)
- Quiet room (< 50 dB background noise)
- Clear microphone
- Normal speaking volume
- Natural speech patterns
- Distance: 10-30 cm from mic

❌ POOR AUDIO (<40%)
- Noisy room (traffic, music, conversations)
- Whispered or over-enunciated speech
- Too quiet or too loud
- Distorted/clipped audio
- Far from microphone
```

## Troubleshooting

### "I don't recognize your voice"

**Problem**: Recognition failing on enrolled user

**Solutions**:
1. Check audio quality: `"Sakura, verify my audio quality"`
2. Re-enroll with fresh samples: `"Sakura, re-learn my voice"`
3. Check background noise - move to quiet room
4. Try different microphone
5. If sick/fatigued, re-enroll when healthy

### "No current speaker authenticated"

**Problem**: Trying to get current speaker when no one authenticated

**Solutions**:
1. In OPTIONAL mode, authentication isn't required
2. In STRICT mode, you must be recognized first
3. Manually set current speaker: `"Sakura, set me as current speaker"`

### Low confidence scores

**Problem**: Always getting 60-75% confidence

**Solutions**:
1. **Enroll more samples** (8-10 instead of 5)
2. **Better microphone** - USB headset is better than laptop mic
3. **Consistent environment** - Enroll where you usually use Sakura
4. **Lower threshold** - Accept 70% instead of 75% (less secure)
5. **Re-enroll** - Remove and re-learn voice from scratch

### "Audio quality too low"

**Problem**: Can't complete enrollment due to poor audio

**Solutions**:
1. Record in quiet room
2. Speak clearly and at normal volume
3. Use better microphone
4. Move closer to microphone
5. Check microphone isn't muted
6. Restart Sakura (audio device might be misconfigured)

## Technical Details

### How Voice is Stored
- **Raw audio**: Deleted immediately after processing
- **Voice features**: Stored in SQLite `sakura.db` (vector representation)
- **Metadata**: Enrollment quality, timestamps
- **Backup**: JSON export in `speaker_profiles.json`

### Privacy
- ✅ All data stored locally on your PC
- ✅ No cloud upload
- ✅ No third-party voice analysis
- ✅ Raw audio never stored
- ✅ Features are mathematical vectors (not audio)

### What Happens to Your Voice?

```
Your Voice
    ↓
[Audio Input]
    ↓
[Process for 1-2 seconds]
    ↓
[Extract Features] → Store this (compressed vector)
    ↓
[Discard Audio] ← Audio is NOT stored
```

### Comparison Process
1. **New audio comes in** → Extract features
2. **Compare against profiles** → Cosine similarity
3. **Check confidence** → Against threshold (0.75)
4. **Return result** → Authenticated/Not Authenticated
5. **Log attempt** → For analytics

## Advanced Configuration

### Lower Confidence Threshold

```python
# More permissive (accepts 70% confidence)
# In tools/speaker_recognition/speaker_auth.py:
profile.confidence_threshold = 0.70  # Default is 0.75
```

### Require Owner for Operations

```python
# In main.py, check is_owner before sensitive operations
if not current_speaker.get('is_owner'):
    return "Only the owner can do this"
```

### Track Authentication History

```python
# Query the database
SELECT * FROM authentication_log 
WHERE authenticated = 1 
ORDER BY attempted_at DESC 
LIMIT 10;
```

## Testing Speaker Recognition

```bash
# Run all tests
pytest tests/tools/test_speaker_recognition.py -v

# Test just quality checking
pytest tests/tools/test_speaker_recognition.py::TestAudioQuality -v

# Test enrollment
pytest tests/tools/test_speaker_recognition.py::TestSpeakerAuthentication::test_enroll_speaker -v

# Run with audio playback (slow)
pytest tests/tools/test_speaker_recognition.py -v -m "not slow"
```

## Future Enhancements

- 🧠 Deep learning embeddings (I-vectors, x-vectors)
- 📈 Automatic profile refinement with good samples
- 🌍 Multi-language support
- 🎧 Noise-robust features
- 👥 Speaker adaptation (learn variations over time)
- 📊 Statistics dashboard

---

**Questions?** Check [docs/tools/speaker_recognition.md](./speaker_recognition.md) for full technical documentation.
