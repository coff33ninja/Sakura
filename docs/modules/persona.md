# Persona Module

**File:** `modules/persona.py`

Personality definitions and response templates for Sakura.

## Personality Modes

| Mode | Gender | Description |
|------|--------|-------------|
| `friendly` | Neutral | Warm, helpful assistant (default) |
| `flirty` | Female | Playful, affectionate |
| `romantic` | Female | Sweet, caring (PG-13) |
| `tsundere` | Female | Classic anime tsundere |
| `friendly_m` | Neutral | Warm, helpful male |
| `flirty_m` | Male | Charming, affectionate |
| `romantic_m` | Male | Sweet, caring (PG-13) |
| `kuudere` | Male | Cool, calm but caring |

## Configuration

Set in `.env`:
```env
SAKURA_PERSONALITY=friendly
```

## Voice Matching

Recommended voice/persona combinations:

| Persona | Recommended Voice |
|---------|-------------------|
| friendly, flirty, romantic, tsundere | Aoede, Kore |
| friendly_m, flirty_m, romantic_m, kuudere | Charon, Fenrir |
| Any | Puck (neutral) |

Warning shown if voice gender doesn't match persona.

## Response Templates

Each persona includes:
- Wake-up responses
- Goodbye responses
- Error responses
- Idle responses
