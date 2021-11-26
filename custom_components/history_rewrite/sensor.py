# -*- coding: utf-8 -*-

# Copyright (C) 2021 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.


from typing import Optional

from homeassistant.components.sensor import (
    ATTR_STATE_CLASS,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEVICE_CLASS_ENERGY, ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.util import dt as dt_util

from . import _LOGGER
from .const import DEFAULT_SENSOR_NAME, DOMAIN
from .hack import write_state_at_time

PLATFORM = "sensor"


class MacFlySensor(RestoreEntity, SensorEntity):
    def __init__(self, hass, name, api, unique_id):
        self._attr_name = name
        self._attr_unique_id = unique_id

        self._hass = hass
        self._api = api
        self._states = []
        self._state_initialized = False

    @property
    def should_poll(self):
        return True

    @property
    def state(self):
        if not self._state_initialized:
            self.async_schedule_update_ha_state(force_refresh=True)
            self._state_initialized = True
        return self._states[-1][1]

    @property
    def unit_of_measurement(self):
        return ENERGY_KILO_WATT_HOUR

    @property
    def device_class(self):
        return DEVICE_CLASS_ENERGY

    @property
    def extra_state_attributes(self):
        return {
            ATTR_STATE_CLASS: self.state_class,
        }

    @property
    def state_class(self):
        return STATE_CLASS_TOTAL_INCREASING

    async def async_added_to_hass(self) -> None:
        if state := await self.async_get_last_state():
            self._states = [(state.last_changed, state.state)]

    async def async_update(self):
        entity_id = f"{PLATFORM}.{self.name}"
        now = dt_util.now()

        # Fix naive-timezone dt's, can lead to future states
        self._states = await self._api.get_historical_data()
        self._states = [(dt_util.as_utc(dt), v) for (dt, v) in self._states]

        # Writing historical data before first state has been generate leads to
        # entity duplication (adding second entity with '_2' suffix)
        if not self._state_initialized:
            _LOGGER.debug(
                f"{entity_id} state has not been initialized yet, "
                "skipping history rewrite"
            )
            return

        try:
            attributes = self._hass.states.get(entity_id).attributes
        except AttributeError:
            attributes = None

        for (dt, state) in self._states:
            write_state_at_time(
                self._hass, entity_id, state, dt, attributes=attributes
            )
            diff = int((now - dt).total_seconds())
            mins = int(diff // 60)
            secs = diff % 60

            _LOGGER.debug(
                f"{entity_id} set to {state} at "
                f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d} "
                f"({mins:02d} min {secs:02d} secs ago)"
            )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,
):
    api = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [
        MacFlySensor(
            hass=hass,
            api=api,
            name=config_entry.data.get("name", DEFAULT_SENSOR_NAME),
            unique_id=config_entry.entry_id,
        )
    ]

    add_entities(sensors, update_before_add=True)  # Update entity on add
