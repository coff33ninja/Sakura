"""
Smart Home Controller for Sakura
Control lights, music, temperature via Home Assistant API - fully async
"""
import asyncio
import os
import logging
from typing import Dict, Any, Optional, List
import httpx
from ..base import BaseTool, ToolResult, ToolStatus

class SmartHomeController(BaseTool):
    """Smart home device control via Home Assistant - async"""
    
    name = "smart_home"
    description = "Control smart home devices like lights, music, thermostat"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.ha_url = os.getenv("HOME_ASSISTANT_URL", self.config.get("url", ""))
        self.ha_token = os.getenv("HOME_ASSISTANT_TOKEN", self.config.get("token", ""))
        self.devices: Dict[str, Any] = {}
        self.client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """Initialize async Home Assistant connection"""
        if not self.ha_url or not self.ha_token:
            logging.warning("Home Assistant not configured - smart home disabled")
            self.enabled = False
            return False
        
        async with self._lock:
            self.client = httpx.AsyncClient(
                base_url=self.ha_url,
                headers={
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                },
                timeout=10.0
            )
        
        # Test connection and get devices
        try:
            response = await self.client.get("/api/states")
            if response.status_code == 200:
                states = response.json()
                self.devices = {s["entity_id"]: s for s in states}
                logging.info(f"Smart home connected (async): {len(self.devices)} devices")
                return True
        except Exception as e:
            logging.error(f"Home Assistant connection failed: {e}")
        
        self.enabled = False
        return False
    
    async def execute(self, action: str, device: str = "", **kwargs) -> ToolResult:
        """Execute smart home action"""
        if not self.client:
            return ToolResult(
                status=ToolStatus.ERROR,
                message="Smart home not connected. Set HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN in .env"
            )
        
        if not hasattr(self, 'enabled') or not self.enabled:
            return ToolResult(
                status=ToolStatus.ERROR,
                message="Smart home not initialized. Check Home Assistant connection and token."
            )
        
        actions = {
            # Lights
            "lights_on": self._lights_on,
            "lights_off": self._lights_off,
            "set_brightness": self._set_brightness,
            "set_color": self._set_color,
            # Media
            "play_music": self._play_music,
            "pause_music": self._pause_music,
            "stop_music": self._stop_music,
            "set_volume": self._set_volume,
            # Climate
            "set_temperature": self._set_temperature,
            "set_hvac_mode": self._set_hvac_mode,
            # Switches & Fans
            "switch_on": self._switch_on,
            "switch_off": self._switch_off,
            "fan_on": self._fan_on,
            "fan_off": self._fan_off,
            "set_fan_speed": self._set_fan_speed,
            # Covers (blinds, garage doors)
            "cover_open": self._cover_open,
            "cover_close": self._cover_close,
            "cover_stop": self._cover_stop,
            "set_cover_position": self._set_cover_position,
            # Scenes & Automations
            "activate_scene": self._activate_scene,
            "trigger_automation": self._trigger_automation,
            "list_scenes": self._list_scenes,
            "list_automations": self._list_automations,
            # Energy Monitoring
            "get_energy_usage": self._get_energy_usage,
            "get_device_state": self._get_device_state,
            # Discovery
            "list_devices": self._list_devices,
            "list_devices_by_type": self._list_devices_by_type,
        }
        
        if action not in actions:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown action: {action}. Available: {list(actions.keys())}"
            )
        
        return await actions[action](device, **kwargs)
    
    async def _find_device(self, device: str) -> Optional[str]:
        """Find device entity_id by name or partial match"""
        device_lower = device.lower()
        for entity_id, state in self.devices.items():
            name = state.get("attributes", {}).get("friendly_name", "").lower()
            if device_lower in entity_id.lower() or device_lower in name:
                return entity_id
        return None
    
    async def _call_service(self, domain: str, service: str, entity_id: str, data: Optional[Dict] = None) -> ToolResult:
        """Call a Home Assistant service - async"""
        try:
            payload = {"entity_id": entity_id}
            if data:
                payload.update(data)
            
            async with self._lock:
                response = await self.client.post(
                    f"/api/services/{domain}/{service}",
                    json=payload
                )
            
            if response.status_code in [200, 201]:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    message=f"Done: {service} on {entity_id}"
                )
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=response.text,
                    message=f"Failed: {response.status_code}"
                )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
                message="Service call failed"
            )
    
    async def _lights_on(self, device: str, **kwargs) -> ToolResult:
        """Turn lights on"""
        entity_id = await self._find_device(device) or f"light.{device}"
        return await self._call_service("light", "turn_on", entity_id)
    
    async def _lights_off(self, device: str, **kwargs) -> ToolResult:
        """Turn lights off"""
        entity_id = await self._find_device(device) or f"light.{device}"
        return await self._call_service("light", "turn_off", entity_id)
    
    async def _set_brightness(self, device: str, level: int = 100, **kwargs) -> ToolResult:
        """Set light brightness"""
        entity_id = await self._find_device(device) or f"light.{device}"
        brightness = int(level * 2.55)  # Convert 0-100 to 0-255
        return await self._call_service("light", "turn_on", entity_id, {"brightness": brightness})
    
    async def _set_color(self, device: str, color: str = "white", **kwargs) -> ToolResult:
        """Set light color"""
        entity_id = await self._find_device(device) or f"light.{device}"
        # Basic color name to RGB mapping
        colors = {
            "red": [255, 0, 0],
            "green": [0, 255, 0],
            "blue": [0, 0, 255],
            "white": [255, 255, 255],
            "warm": [255, 180, 100],
            "cool": [200, 220, 255],
            "purple": [128, 0, 128],
            "pink": [255, 105, 180],
            "orange": [255, 165, 0],
            "yellow": [255, 255, 0],
        }
        rgb = colors.get(color.lower(), [255, 255, 255])
        return await self._call_service("light", "turn_on", entity_id, {"rgb_color": rgb})
    
    async def _play_music(self, device: str, query: str = "", **kwargs) -> ToolResult:
        """Play music on media player"""
        entity_id = await self._find_device(device) or f"media_player.{device}"
        if query:
            return await self._call_service("media_player", "play_media", entity_id, {
                "media_content_type": "music",
                "media_content_id": query
            })
        else:
            return await self._call_service("media_player", "media_play", entity_id)
    
    async def _set_temperature(self, device: str, temp: int = 72, **kwargs) -> ToolResult:
        """Set thermostat temperature"""
        entity_id = await self._find_device(device) or f"climate.{device}"
        return await self._call_service("climate", "set_temperature", entity_id, {"temperature": temp})
    
    async def _set_hvac_mode(self, device: str, mode: str = "auto", **kwargs) -> ToolResult:
        """Set HVAC mode (heat, cool, auto, off)"""
        entity_id = await self._find_device(device) or f"climate.{device}"
        return await self._call_service("climate", "set_hvac_mode", entity_id, {"hvac_mode": mode})
    
    # Media player controls
    async def _pause_music(self, device: str, **kwargs) -> ToolResult:
        """Pause media player"""
        entity_id = await self._find_device(device) or f"media_player.{device}"
        return await self._call_service("media_player", "media_pause", entity_id)
    
    async def _stop_music(self, device: str, **kwargs) -> ToolResult:
        """Stop media player"""
        entity_id = await self._find_device(device) or f"media_player.{device}"
        return await self._call_service("media_player", "media_stop", entity_id)
    
    async def _set_volume(self, device: str, level: int = 50, **kwargs) -> ToolResult:
        """Set media player volume (0-100)"""
        entity_id = await self._find_device(device) or f"media_player.{device}"
        volume = level / 100.0  # Convert 0-100 to 0.0-1.0
        return await self._call_service("media_player", "volume_set", entity_id, {"volume_level": volume})
    
    # Switch controls
    async def _switch_on(self, device: str, **kwargs) -> ToolResult:
        """Turn switch on"""
        entity_id = await self._find_device(device) or f"switch.{device}"
        return await self._call_service("switch", "turn_on", entity_id)
    
    async def _switch_off(self, device: str, **kwargs) -> ToolResult:
        """Turn switch off"""
        entity_id = await self._find_device(device) or f"switch.{device}"
        return await self._call_service("switch", "turn_off", entity_id)
    
    # Fan controls
    async def _fan_on(self, device: str, **kwargs) -> ToolResult:
        """Turn fan on"""
        entity_id = await self._find_device(device) or f"fan.{device}"
        return await self._call_service("fan", "turn_on", entity_id)
    
    async def _fan_off(self, device: str, **kwargs) -> ToolResult:
        """Turn fan off"""
        entity_id = await self._find_device(device) or f"fan.{device}"
        return await self._call_service("fan", "turn_off", entity_id)
    
    async def _set_fan_speed(self, device: str, speed: str = "medium", **kwargs) -> ToolResult:
        """Set fan speed (low, medium, high) or percentage"""
        entity_id = await self._find_device(device) or f"fan.{device}"
        # Try percentage first, then preset mode
        if speed.isdigit():
            return await self._call_service("fan", "set_percentage", entity_id, {"percentage": int(speed)})
        return await self._call_service("fan", "set_preset_mode", entity_id, {"preset_mode": speed})
    
    # Cover controls (blinds, garage doors, curtains)
    async def _cover_open(self, device: str, **kwargs) -> ToolResult:
        """Open cover (blinds, garage door, etc.)"""
        entity_id = await self._find_device(device) or f"cover.{device}"
        return await self._call_service("cover", "open_cover", entity_id)
    
    async def _cover_close(self, device: str, **kwargs) -> ToolResult:
        """Close cover"""
        entity_id = await self._find_device(device) or f"cover.{device}"
        return await self._call_service("cover", "close_cover", entity_id)
    
    async def _cover_stop(self, device: str, **kwargs) -> ToolResult:
        """Stop cover movement"""
        entity_id = await self._find_device(device) or f"cover.{device}"
        return await self._call_service("cover", "stop_cover", entity_id)
    
    async def _set_cover_position(self, device: str, position: int = 50, **kwargs) -> ToolResult:
        """Set cover position (0=closed, 100=open)"""
        entity_id = await self._find_device(device) or f"cover.{device}"
        return await self._call_service("cover", "set_cover_position", entity_id, {"position": position})
    
    # Scenes & Automations
    async def _activate_scene(self, device: str, **kwargs) -> ToolResult:
        """Activate a scene"""
        entity_id = await self._find_device(device) or f"scene.{device}"
        return await self._call_service("scene", "turn_on", entity_id)
    
    async def _trigger_automation(self, device: str, **kwargs) -> ToolResult:
        """Trigger an automation"""
        entity_id = await self._find_device(device) or f"automation.{device}"
        return await self._call_service("automation", "trigger", entity_id)
    
    async def _list_scenes(self, device: str = "", **kwargs) -> ToolResult:
        """List available scenes"""
        scenes = []
        for entity_id, state in self.devices.items():
            if entity_id.startswith("scene."):
                name = state.get("attributes", {}).get("friendly_name", entity_id)
                scenes.append({"id": entity_id, "name": name})
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=scenes,
            message=f"Found {len(scenes)} scenes"
        )
    
    async def _list_automations(self, device: str = "", **kwargs) -> ToolResult:
        """List available automations"""
        automations = []
        for entity_id, state in self.devices.items():
            if entity_id.startswith("automation."):
                name = state.get("attributes", {}).get("friendly_name", entity_id)
                current_state = state.get("state", "unknown")
                automations.append({"id": entity_id, "name": name, "state": current_state})
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=automations,
            message=f"Found {len(automations)} automations"
        )
    
    # Energy Monitoring
    async def _get_energy_usage(self, device: str = "", **kwargs) -> ToolResult:
        """Get energy usage from sensors"""
        energy_data = []
        for entity_id, state in self.devices.items():
            # Look for energy/power sensors
            if any(x in entity_id for x in ["energy", "power", "consumption", "watt"]):
                name = state.get("attributes", {}).get("friendly_name", entity_id)
                value = state.get("state", "unknown")
                unit = state.get("attributes", {}).get("unit_of_measurement", "")
                energy_data.append({
                    "id": entity_id,
                    "name": name,
                    "value": value,
                    "unit": unit
                })
        
        if not energy_data:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=[],
                message="No energy sensors found. Check if energy monitoring is configured in Home Assistant."
            )
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=energy_data,
            message=f"Found {len(energy_data)} energy sensors"
        )
    
    async def _get_device_state(self, device: str, **kwargs) -> ToolResult:
        """Get current state of a device"""
        entity_id = await self._find_device(device)
        if not entity_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Device not found: {device}"
            )
        
        state = self.devices.get(entity_id, {})
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "entity_id": entity_id,
                "state": state.get("state"),
                "attributes": state.get("attributes", {}),
                "last_changed": state.get("last_changed"),
                "last_updated": state.get("last_updated")
            },
            message=f"State of {entity_id}"
        )
    
    async def _list_devices_by_type(self, device: str = "", device_type: str = "", **kwargs) -> ToolResult:
        """List devices filtered by type (light, switch, fan, cover, climate, media_player, sensor, scene, automation)"""
        if not device_type:
            device_type = device  # Allow passing type as device param
        
        device_list = []
        for entity_id, state in self.devices.items():
            if entity_id.startswith(f"{device_type}."):
                name = state.get("attributes", {}).get("friendly_name", entity_id)
                current_state = state.get("state", "unknown")
                device_list.append({
                    "id": entity_id,
                    "name": name,
                    "state": current_state
                })
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=device_list,
            message=f"Found {len(device_list)} {device_type} devices"
        )
    
    async def _list_devices(self, device: str = "", **kwargs) -> ToolResult:
        """List available devices"""
        device_list: List[str] = []
        for entity_id, state in self.devices.items():
            name = state.get("attributes", {}).get("friendly_name", entity_id)
            device_list.append(f"{name} ({entity_id})")
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data=device_list,
            message=f"Found {len(device_list)} devices"
        )
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            # Lights
                            "lights_on", "lights_off", "set_brightness", "set_color",
                            # Media
                            "play_music", "pause_music", "stop_music", "set_volume",
                            # Climate
                            "set_temperature", "set_hvac_mode",
                            # Switches & Fans
                            "switch_on", "switch_off", "fan_on", "fan_off", "set_fan_speed",
                            # Covers
                            "cover_open", "cover_close", "cover_stop", "set_cover_position",
                            # Scenes & Automations
                            "activate_scene", "trigger_automation", "list_scenes", "list_automations",
                            # Energy & State
                            "get_energy_usage", "get_device_state",
                            # Discovery
                            "list_devices", "list_devices_by_type"
                        ],
                        "description": "Smart home action"
                    },
                    "device": {"type": "string", "description": "Device name, room, or entity_id"},
                    "device_type": {"type": "string", "description": "Device type filter (light, switch, fan, cover, climate, media_player, sensor, scene, automation)"},
                    "level": {"type": "integer", "description": "Brightness/volume level 0-100"},
                    "color": {"type": "string", "description": "Light color (red, green, blue, white, warm, cool, purple, pink, orange, yellow)"},
                    "query": {"type": "string", "description": "Music search query or media content ID"},
                    "temp": {"type": "integer", "description": "Temperature in Fahrenheit"},
                    "mode": {"type": "string", "description": "HVAC mode (heat, cool, auto, off)"},
                    "speed": {"type": "string", "description": "Fan speed (low, medium, high) or percentage"},
                    "position": {"type": "integer", "description": "Cover position 0-100 (0=closed, 100=open)"}
                },
                "required": ["action"]
            }
        }
    
    async def cleanup(self):
        """Close async connection"""
        async with self._lock:
            if self.client:
                await self.client.aclose()
                self.client = None
