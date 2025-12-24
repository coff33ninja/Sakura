# Smart Home Tool

**File:** `tools/smart_home/controller.py`  
**Actions:** 6

Home Assistant integration for smart home control.

## Actions

| Action | Description |
|--------|-------------|
| `lights_on` | Turn on lights |
| `lights_off` | Turn off lights |
| `set_brightness` | Set light brightness (0-255) |
| `set_color` | Set light color (RGB) |
| `play_music` | Control media player |
| `set_temperature` | Set thermostat temperature |
| `list_devices` | List all discovered devices |

## Configuration

Set in `.env`:
```env
HOME_ASSISTANT_URL=http://192.168.1.100:8123
HOME_ASSISTANT_TOKEN=your_long_lived_access_token
```

## Getting Home Assistant Token

1. Go to your Home Assistant profile
2. Scroll to "Long-Lived Access Tokens"
3. Create new token
4. Copy to `.env`

## Device Discovery

On initialization, the tool queries Home Assistant for all device states and caches them.

## Example Usage

```python
# Turn on living room lights
await tool.execute("lights_on", device="light.living_room")

# Set brightness to 50%
await tool.execute("set_brightness", 
    device="light.bedroom",
    brightness=128
)

# Set color to red
await tool.execute("set_color",
    device="light.rgb_strip",
    r=255, g=0, b=0
)

# Set thermostat
await tool.execute("set_temperature",
    device="climate.main",
    temperature=72
)

# List all devices
result = await tool.execute("list_devices")
```

## Supported Device Types

- `light.*` - Lights (on/off, brightness, color)
- `media_player.*` - Media players
- `climate.*` - Thermostats
- `switch.*` - Switches
- `cover.*` - Blinds/covers
