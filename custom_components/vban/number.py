"""Number platform for VBAN VoiceMeeter."""
import voluptuous as vol
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VBANBaseEntity

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VBAN numbers."""
    vban_data = hass.data[DOMAIN]
    remote = vban_data.remotes[entry.entry_id]

    entities = []
    for strip in remote.strips:
        entities.append(VBANGainNumber(remote, "strip", strip.index))
    for bus in remote.buses:
        entities.append(VBANGainNumber(remote, "bus", bus.index))

    async_add_entities(entities)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "set_gain",
        {vol.Required("gain"): vol.Coerce(float)},
        "async_set_gain",
    )

class VBANGainNumber(VBANBaseEntity, NumberEntity):
    """Gain number for VBAN."""
    _attr_native_min_value = -60.0
    _attr_native_max_value = 12.0
    _attr_native_step = 0.1
    _attr_native_unit_of_measurement = "dB"

    def __init__(self, remote, kind, index):
        super().__init__(remote, kind, index)
        self._attr_unique_id = f"{remote.device.address}_{kind}_{index}_gain"
        self._attr_suggested_object_id = f"{kind}_{index + 1}_gain"

    @property
    def name(self):
        label = self.obj.label or f"{self.kind.capitalize()} {self.index + 1}"
        return f"{label} Gain"

    @property
    def native_value(self):
        return self.obj.gain

    async def async_set_native_value(self, value: float):
        await self.obj.set_gain(value)
