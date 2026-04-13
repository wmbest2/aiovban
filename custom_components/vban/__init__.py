"""The VBAN VoiceMeeter integration."""
import asyncio
import logging
from typing import Dict

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv

from aiovban.asyncio import AsyncVBANClient, VoicemeeterRemote

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_COMMAND_STREAM, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.BUTTON,
]

class VBANData:
    """Storage for VBAN clients and remotes."""
    def __init__(self):
        self.clients: Dict[int, AsyncVBANClient] = {}
        self.remotes: Dict[str, VoicemeeterRemote] = {}
        self.ref_counts: Dict[int, int] = {}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up VBAN VoiceMeeter from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    stream = entry.data[CONF_COMMAND_STREAM]
    listen_port = DEFAULT_PORT 

    _LOGGER.info("Initializing VBAN integration for %s:%s", host, port)

    vban_data: VBANData = hass.data.setdefault(DOMAIN, VBANData())

    if listen_port not in vban_data.clients:
        client = AsyncVBANClient()
        try:
            await client.listen("0.0.0.0", listen_port)
            vban_data.clients[listen_port] = client
            vban_data.ref_counts[listen_port] = 0
        except Exception as err:
            raise ConfigEntryNotReady(f"Failed to listen on VBAN port {listen_port}: {err}") from err
    
    client = vban_data.clients[listen_port]
    vban_data.ref_counts[listen_port] += 1

    device = await client.register_device(host, port)
    remote = VoicemeeterRemote(device, stream)
    await remote.start()
    
    attempts = 0
    while not remote.type and attempts < 100:
        await asyncio.sleep(0.1)
        attempts += 1

    vban_data.remotes[entry.entry_id] = remote

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # --- Global Service: send_raw_command (Target by Device) ---

    async def handle_send_raw_command(call: ServiceCall):
        command = call.data.get("command")
        device_ids = call.data.get("device_id", [])
        if isinstance(device_ids, str):
            device_ids = [device_ids]
            
        target_remotes = []
        if not device_ids:
            target_remotes = list(vban_data.remotes.values())
        else:
            dev_reg = dr.async_get(hass)
            for d_id in device_ids:
                d_entry = dev_reg.async_get(d_id)
                if d_entry:
                    for config_id in d_entry.config_entries:
                        if config_id in vban_data.remotes:
                            target_remotes.append(vban_data.remotes[config_id])

        for r in target_remotes:
            await r.send_command(command)

    if not hass.services.has_service(DOMAIN, "send_raw_command"):
        hass.services.async_register(DOMAIN, "send_raw_command", handle_send_raw_command, 
            schema=vol.Schema({
                vol.Required("command"): str,
                vol.Optional("device_id"): vol.All(cv.ensure_list, [cv.string]),
            }))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    vban_data: VBANData = hass.data[DOMAIN]
    remote = vban_data.remotes.pop(entry.entry_id)
    await remote.stop()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        listen_port = DEFAULT_PORT
        vban_data.ref_counts[listen_port] -= 1
        if vban_data.ref_counts[listen_port] <= 0:
            client = vban_data.clients.pop(listen_port)
            client.close()
            vban_data.ref_counts.pop(listen_port)

    return unload_ok
