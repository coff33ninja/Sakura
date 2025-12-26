# Speaker Recognition Tool

**Status**: ✅ Implemented (v1.0)  
**Category**: Security & Personalization  
**Actions**: 10

## Overview

The Speaker Recognition tool provides voice authentication and speaker identification. Only respond to your voice - reject all other speakers. Perfect for security, personalization, and ensuring your AI assistant is truly *yours*.

## Key Features

- **Voice Enrollment** - Train the AI to recognize your voice with 5+ samples
- **Voice Authentication** - Verify speaker identity during conversations
- **Multi-Speaker Support** - Enroll multiple family members with different permission levels
- **Audio Quality Checking** - Ensure clear audio for reliable recognition
- **Database Persistence** - Store speaker profiles in SQLite with automatic JSON backup
- **Owner Account** - Mark primary users as owners for special handling
- **Authentication Logging** - Track all authentication attempts with confidence scores
- **Flexible Modes** - DISABLED, OPTIONAL, STRICT, or TRAINING modes

## How It Works

### 1. Enrollment (Training)
```
User: "Sakura, learn my voice"
→ Sakura records 5+ voice samples
→ Extracts voice features (MFCC-like)
→ Creates speaker profile
→ Stores in database + JSON backup
```

### 2. Authentication (Real-time)
```
Incoming audio
→ Extract voice features
→ Compare against all enrolled profiles
→ Return confidence score
→ Approve/Reject based on threshold
→ Log attempt
```

### 3. Recognition Quality
- **Excellent (80%+)**: Use for critical operations
- **Good (60-79%)**: Safe for general use
- **Fair (40-59%)**: May need retry
- **Poor (<40%)**: Reject, ask for re-record

## Actions (10 total)

### Enrollment & Management
- **enroll** - Teach the AI your voice (5+ samples, 3-30 seconds each)
- **remove_profile** - Delete a speaker profile
- **list_profiles** - Show all enrolled speakers

### Authentication
- **authenticate** - Verify if current speaker is recognized
- **set_current_speaker** - Manually mark speaker (for testing)
- **get_current_speaker** - Get authenticated speaker info

### Configuration
- **set_auth_mode** - Change security level (DISABLED/OPTIONAL/STRICT/TRAINING)
- **get_auth_mode** - Get current authentication mode

### Diagnostics
- **verify_audio_quality** - Check if audio is clear enough
- **get_speaker_info** - Get details about a speaker profile

## Configuration Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| **DISABLED** | No authentication | Testing, demos |
| **OPTIONAL** | Authenticate but continue if fails | Convenience + fallback |
| **STRICT** | Reject unrecognized speakers | High security |
| **TRAINING** | Record & learn during conversations | Enrollment phase |

## Feature Extraction

The tool uses a simplified MFCC (Mel-Frequency Cepstral Coefficient) approach:

1. **Frame Energy** - Loudness of each time frame
2. **Zero Crossing Rate** - Voice frequency characteristics
3. **Spectral Centroid** - Tonal information
4. **Statistical Features** - Mean, std dev, min, max of above

Results in a compact vector for fast comparison.

## Comparison Algorithm

- **Cosine Similarity** - Fast, accurate speaker matching
- **Confidence Threshold** - Customizable per profile (default: 0.75)
- **Multi-Sample Averaging** - Use best match from all enrollment samples

## Database Schema

```sql
-- Speaker profiles
CREATE TABLE speaker_profiles (
    speaker_id TEXT PRIMARY KEY,
    name TEXT,
    is_owner BOOLEAN,
    confidence_threshold REAL DEFAULT 0.75,
    samples_count INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    metadata TEXT  -- JSON with enrollment_quality, etc.
);

-- Audio samples & features
CREATE TABLE speaker_samples (
    id INTEGER PRIMARY KEY,
    speaker_id TEXT,
    audio_hash TEXT UNIQUE,
    duration_ms INTEGER,
    confidence REAL,
    features TEXT,  -- JSON array of feature vectors
    created_at TIMESTAMP
);

-- Authentication log
CREATE TABLE authentication_log (
    id INTEGER PRIMARY KEY,
    speaker_id TEXT,
    authenticated BOOLEAN,
    confidence REAL,
    attempted_at TIMESTAMP
);
```

## Usage Examples

### Enroll Your Voice
```python
# Collect 5-10 voice samples, each 3-30 seconds
# "Say a few sentences about yourself, clearly"

result = await speaker_tool.execute("enroll",
    speaker_name="Owner",
    audio_samples=[sample1, sample2, sample3, sample4, sample5],
    is_owner=True
)
# Returns: speaker_id, quality score, confirmation
```

### Authenticate During Conversation
```python
# Called automatically on new audio chunk
result = await speaker_tool.execute("authenticate",
    audio_sample=current_audio_chunk
)
# Returns: AuthenticationResult with confidence, speaker_id, etc.
```

### Set Strict Security
```python
await speaker_tool.execute("set_auth_mode", mode="STRICT")
# Now Sakura rejects all unrecognized speakers

await speaker_tool.execute("get_current_speaker")
# Returns: speaker_id, name, is_owner
```

### Check Audio Quality
```python
result = await speaker_tool.execute("verify_audio_quality",
    audio_sample=sample
)
# Returns: quality_score (0-1), rating (Excellent/Good/Fair/Poor)
```

## Integration with Main Flow

In `main.py`:

```python
# After initializing audio
self.speaker_auth = await self.tool_registry.get_tool("speaker_recognition")

# For each audio chunk
auth_result = await self.speaker_auth.execute("authenticate", 
    audio_sample=audio_chunk
)

if not auth_result.get("authenticated"):
    if self.auth_mode == "STRICT":
        # Reject and ask for re-enrollment
        await self.audio_manager.play_text("Sorry, I don't recognize your voice")
        return
    else:
        # Log and continue (OPTIONAL mode)
        logging.warning(f"Unknown speaker: {auth_result['confidence']:.2%}")
```

## Limitations & Future Improvements

### Current Limitations
- Uses simplified MFCC (not full deep learning)
- No speaker adaptation over time
- Single language (English)
- No real-time feature learning

### Future Enhancements
- Deep neural network embeddings (I-vectors, x-vectors)
- Automatic profile refinement with high-confidence samples
- Phoneme-specific features
- Background noise robustness
- Multi-language support
- Speaker verification confidence calibration

## Security Notes

- **Speaker profiles stored locally** - No cloud upload
- **Features extracted, not audio** - Audio discarded after extraction
- **Confidence-based** - Not cryptographic, behavioral-based
- **Soft authentication** - Designed for convenience, not bank-grade security

## Testing

```bash
# Run speaker recognition tests
pytest tests/tools/test_speaker_recognition.py -v

# With verbose audio quality checks
pytest tests/tools/test_speaker_recognition.py -v -s
```

## Configuration

Set in `.env`:
```bash
SPEAKER_RECOGNITION_ENABLED=true
SPEAKER_RECOGNITION_MODE=OPTIONAL  # or STRICT, DISABLED, TRAINING
MIN_AUDIO_SAMPLES=5
MIN_CONFIDENCE_THRESHOLD=0.75
```

## Privacy & Data Retention

- All speaker profiles stored in local `sakura.db`
- JSON backup in `speaker_profiles.json` for portability
- Authentication log retained for 90 days (configurable)
- No data sent to external services
- User can delete profiles anytime with `remove_profile`

---

**Created**: 2025-12-26  
**Tested with**: Python 3.12, numpy, aiosqlite
