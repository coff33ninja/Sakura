# Speaker Recognition Integration Example

This file shows how to integrate speaker recognition into the main Sakura flow.

## Integration Points

### 1. Initialize Speaker Recognition

In `main.py` `AIGirlfriend.initialize()`:

```python
# Initialize speaker recognition
self.speaker_auth = await self.tool_registry.get_tool("speaker_recognition")

# Set initial auth mode from config
auth_mode_env = os.getenv("SPEAKER_RECOGNITION_MODE", "OPTIONAL")
await self.speaker_auth.execute("set_auth_mode", mode=auth_mode_env)

logging.info(f"🔐 Speaker Recognition initialized - Mode: {auth_mode_env}")
```

### 2. Check Speaker on Audio Input

In the main audio listening loop:

```python
async def _process_audio_chunk(self, audio_chunk: bytes):
    """Process incoming audio with speaker verification"""
    
    # Authenticate speaker
    auth_result = await self.speaker_auth.execute("authenticate", 
        audio_sample=audio_chunk
    )
    
    if not auth_result.get("authenticated"):
        if self.speaker_auth._auth_mode == AuthenticationMode.STRICT:
            # Reject unrecognized speakers
            logging.warning(f"❌ Unrecognized speaker (confidence: {auth_result.get('confidence', 0):.1%})")
            await self.audio_manager.play_text(
                "I don't recognize your voice. Please ask the owner."
            )
            return False
        else:
            # Log but continue (OPTIONAL mode)
            logging.warning(f"⚠️ Unknown speaker: confidence {auth_result.get('confidence', 0):.1%}")
    else:
        # Log authenticated user
        speaker_name = auth_result.get("speaker_name", "Unknown")
        confidence = auth_result.get("confidence", 0)
        logging.info(f"✅ Speaker authenticated: {speaker_name} ({confidence:.1%})")
    
    return True
```

### 3. Tool Integration - Handle Enrollment Requests

The speaker recognition tool is already registered as a tool, so Gemini can call it:

```python
# When user says: "Sakura, learn my voice"
# Gemini will call:
await tool_registry.execute("speaker_recognition", "enroll", {
    "speaker_name": "Owner",
    "audio_samples": [sample1, sample2, sample3, sample4, sample5],
    "is_owner": True
})
```

### 4. Handle Authentication Mode Commands

User can change auth mode through natural language:

```
User: "Sakura, set authentication to STRICT"
→ Gemini calls: speaker_recognition.set_auth_mode(mode="STRICT")
→ Sakura now rejects unrecognized speakers

User: "Sakura, what's your security mode?"
→ Gemini calls: speaker_recognition.get_auth_mode()
→ Response: "Voice authentication enabled in STRICT mode"
```

## Complete Integration Example

Here's how it all flows together:

```python
# main.py - AIGirlfriend class

async def initialize(self):
    """Initialize all components including speaker recognition"""
    
    # ... existing initialization code ...
    
    # Initialize speaker recognition
    logging.info("🔐 Initializing speaker recognition...")
    self.speaker_auth = await self.tool_registry.get_tool("speaker_recognition")
    if self.speaker_auth:
        auth_mode = os.getenv("SPEAKER_RECOGNITION_MODE", "OPTIONAL")
        await self.speaker_auth.execute("set_auth_mode", mode=auth_mode)
        logging.info(f"✅ Speaker recognition ready - Mode: {auth_mode}")

async def run(self):
    """Main run loop with speaker verification"""
    
    while self.running:
        # Get audio from microphone
        audio_chunk = await self.audio_manager.listen()
        
        if not audio_chunk:
            continue
        
        # IMPORTANT: Check speaker authentication
        is_recognized = await self._verify_speaker(audio_chunk)
        
        if not is_recognized:
            if self.speaker_auth._auth_mode == AuthenticationMode.STRICT:
                logging.warning("Unrecognized speaker - rejecting in STRICT mode")
                continue  # Skip processing
            # else: Continue in OPTIONAL mode
        
        # Process audio through Gemini
        await self.gemini_client.send_audio_chunk(audio_chunk)
        
        # ... rest of processing ...

async def _verify_speaker(self, audio_chunk: bytes) -> bool:
    """Verify if speaker is recognized"""
    
    if not self.speaker_auth:
        return True  # No speaker recognition enabled
    
    if self.speaker_auth._auth_mode == AuthenticationMode.DISABLED:
        return True  # Speaker recognition disabled
    
    result = await self.speaker_auth.execute("authenticate", 
        audio_sample=audio_chunk
    )
    
    if result.status != ToolStatus.SUCCESS:
        logging.warning(f"Authentication error: {result.error}")
        return self.speaker_auth._auth_mode != AuthenticationMode.STRICT
    
    authenticated = result.data.get("authenticated", False)
    confidence = result.data.get("confidence", 0.0)
    speaker_name = result.data.get("speaker_name", "Unknown")
    
    if authenticated:
        logging.info(f"✅ {speaker_name} ({confidence:.1%})")
        return True
    else:
        if self.speaker_auth._auth_mode == AuthenticationMode.STRICT:
            logging.warning(f"❌ Unrecognized speaker ({confidence:.1%})")
            return False
        else:
            logging.warning(f"⚠️ Low confidence: {speaker_name} ({confidence:.1%})")
            return True  # Continue anyway in OPTIONAL mode
```

## Environment Variables

Add to `.env`:

```bash
# Speaker Recognition Settings
SPEAKER_RECOGNITION_ENABLED=true
SPEAKER_RECOGNITION_MODE=OPTIONAL  # DISABLED, OPTIONAL, STRICT, or TRAINING
SPEAKER_MIN_CONFIDENCE=0.75
SPEAKER_MIN_AUDIO_SAMPLES=5
SPEAKER_MIN_AUDIO_DURATION_MS=500
SPEAKER_MAX_AUDIO_DURATION_MS=30000
```

## Database Queries

Check speaker recognition data:

```sql
-- List all enrolled speakers
SELECT speaker_id, name, is_owner, samples_count, created_at 
FROM speaker_profiles;

-- Check authentication history
SELECT speaker_id, authenticated, confidence, attempted_at 
FROM authentication_log 
ORDER BY attempted_at DESC 
LIMIT 50;

-- Check audio samples for a speaker
SELECT speaker_id, COUNT(*) as total_samples, AVG(confidence) as avg_confidence
FROM speaker_samples 
GROUP BY speaker_id;

-- Recent authentication success rate
SELECT 
    COUNT(*) as total_attempts,
    SUM(CASE WHEN authenticated THEN 1 ELSE 0 END) as successful,
    ROUND(100.0 * SUM(CASE WHEN authenticated THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate
FROM authentication_log 
WHERE attempted_at > datetime('now', '-24 hours');
```

## Testing the Integration

```bash
# Test speaker enrollment
python -c "
import asyncio
from tools.speaker_recognition import SpeakerAuthentication
import numpy as np

async def test():
    auth = SpeakerAuthentication()
    await auth.initialize()
    
    # Create sample audio
    samples = []
    for i in range(5):
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.int16)
        samples.append(audio.tobytes())
    
    # Enroll
    result = await auth.execute('enroll',
        speaker_name='Test User',
        audio_samples=samples,
        is_owner=True
    )
    
    print(f'Enrolled: {result.status}')
    print(f'Speaker ID: {result.data[\"speaker_id\"]}')

asyncio.run(test())
"

# Run full test suite
pytest tests/tools/test_speaker_recognition.py -v
```

## Security Considerations

1. **Audio Processing**
   - Raw audio is NEVER stored
   - Only voice features (mathematical vectors) are saved
   - Features cannot be used to reconstruct original voice

2. **Database Security**
   - SQLite stored locally on your PC
   - Encrypt your Windows drive (BitLocker) for additional security
   - Regular backups in `speaker_profiles.json`

3. **Authentication Level**
   - Behavioral-based, not cryptographic
   - Designed for convenience + personalization
   - Not suitable for high-security operations (use PIN/biometric for that)

## Troubleshooting

If speaker recognition isn't working:

1. **Check initialization**: Look for "✅ Speaker recognition ready" in logs
2. **Verify audio quality**: `"Sakura, check my voice quality"`
3. **Check mode**: `"Sakura, what's your auth mode?"`
4. **Review profiles**: `"Sakura, list my voice profiles"`
5. **Check logs**: Look for authentication attempts in `sakura.log`

## Future Enhancements

- [ ] Deep learning embeddings (I-vectors, x-vectors)
- [ ] Automatic profile improvement
- [ ] Multi-language support
- [ ] Speaker adaptation over time
- [ ] Gender classification
- [ ] Age estimation
- [ ] Emotion detection
- [ ] Speech quality assessment

---

For more details, see [docs/tools/speaker_recognition.md](../docs/tools/speaker_recognition.md) and [docs/SPEAKER_RECOGNITION_GUIDE.md](../docs/SPEAKER_RECOGNITION_GUIDE.md)
