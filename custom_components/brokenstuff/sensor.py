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

from .api import AsyncBrokenAPI
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

# from homeassistant.const import DEVICE_CLASS_ENERGY, ENERGY_KILO_WATT_HOUR
# from homeassistant.components.sensor import (
#     ATTR_LAST_RESET,
#     ATTR_STATE_CLASS,
#     STATE_CLASS_TOTAL_INCREASING,
# )

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType

from . import _LOGGER
from .const import DEFAULT_SENSOR_NAME, DOMAIN

# Util stuff:
# from homeassistant.helpers.restore_state import RestoreEntity
# from homeassistant.core import callback


class BrokenSensor(SensorEntity):
    def __init__(self, name, api, unique_id):
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._api = api
        self._state = None

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug(f"{self!r} added to hass")

    async def async_update(self):
        self._state = self._api.get_data()

    # @property
    # def device_info(self):
    #     return self._device_info

    @property
    def should_poll(self):
        return True

    @property
    def state(self):
        return self._state

    # @property
    # def unit_of_measurement(self):
    #     return ENERGY_KILO_WATT_HOUR

    # @property
    # def device_class(self):
    #     return DEVICE_CLASS_ENERGY

    # @property
    # def extra_state_attributes(self):
    #     return {
    #         ATTR_LAST_RESET: self.last_reset,
    #         ATTR_STATE_CLASS: self.state_class,
    #     }

    # @property
    # def state_class(self):
    #     return STATE_CLASS_TOTAL_INCREASING


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
    discovery_info: Optional[
        DiscoveryInfoType
    ] = None,  # noqa DiscoveryInfoType | None
):
    api = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [
        BrokenSensor(
            hass=hass,
            api=api,
            name=config_entry.data.get("name", DEFAULT_SENSOR_NAME),
            unique_id=config_entry.entry_id,
        )
    ]

    add_entities(sensors, update_before_add=False)  # Update entity on add
