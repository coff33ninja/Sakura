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
    
    async def execute(self, action: str, device: str, **kwargs) -> ToolResult:
        """Execute smart home action"""
        if not self.client or not self.enabled:
            return ToolResult(
                status=ToolStatus.ERROR,
                message="Smart home not connected"
            )
        
        actions = {
            "lights_on": self._lights_on,
            "lights_off": self._lights_off,
            "set_brightness": self._set_brightness,
            "set_color": self._set_color,
            "play_music": self._play_music,
            "set_temperature": self._set_temperature,
            "list_devices": self._list_devices,
        }
        
        if action not in actions:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Unknown action: {action}"
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
                        "enum": ["lights_on", "lights_off", "set_brightness", "set_color", "play_music", "set_temperature", "list_devices"],
                        "description": "Smart home action"
                    },
                    "device": {"type": "string", "description": "Device name or room"},
                    "level": {"type": "integer", "description": "Brightness level 0-100"},
                    "color": {"type": "string", "description": "Light color"},
                    "query": {"type": "string", "description": "Music search query"},
                    "temp": {"type": "integer", "description": "Temperature in Fahrenheit"}
                },
                "required": ["action", "device"]
            }
        }
    
    async def cleanup(self):
        """Close async connection"""
        async with self._lock:
            if self.client:
                await self.client.aclose()
                self.client = None
