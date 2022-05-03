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


import logging
from datetime import timedelta
from typing import Optional

from homeassistant.components.sensor import (
    ATTR_LAST_RESET,
    ATTR_STATE_CLASS,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEVICE_CLASS_ENERGY, ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.util import dt as dt_util

from .const import DEFAULT_SENSOR_NAME, DOMAIN
from .historical_state import HistoricalEntity, StateAtTimePoint

_LOGGER = logging.getLogger(__name__)


class MacFlySensor(HistoricalEntity, SensorEntity):
    def __init__(self, name, api, unique_id):
        self._api = api

        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_unit_of_measurement = ENERGY_KILO_WATT_HOUR
        # self._attr_native_unit_of_measurement = ENERGY_KILO_WATT_HOUR
        self._attr_device_class = DEVICE_CLASS_ENERGY

    @property
    def extra_state_attributes(self):
        return {
            # ATTR_LAST_RESET: self.last_reset,
            ATTR_STATE_CLASS: STATE_CLASS_MEASUREMENT,
        }

    @property
    def state_class(self):
        return STATE_CLASS_MEASUREMENT

    async def async_update_history(self):
        # Query for the last day since the start of the current hour
        slow_api = True

        if slow_api:
            step = timedelta(hours=1)
            end = dt_util.now().replace(minute=0, second=0, microsecond=0)
            start = end - timedelta(days=1)

        else:
            now = dt_util.now()
            step = timedelta(seconds=120)
            end = now.replace(second=0, microsecond=0)
            start = end - timedelta(minutes=60)

        # Mangle API data
        log = self._api.get_historical_data(start, end, step)
        log = [
            StateAtTimePoint(
                state=v,
                when=end,
                # when=dt_util.as_utc(end),
                attributes={"last_reset": dt_util.as_utc(start)},
            )
            for (start, end, v) in log
        ]

        return log
        # self.extend_historical_log(log)
        # if not self.should_poll:
        #     await self.flush_historical_log()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,
):
    api = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [
        MacFlySensor(
            api=api,
            name=config_entry.data.get("name", DEFAULT_SENSOR_NAME),
            unique_id=config_entry.entry_id,
        )
    ]

    add_entities(sensors, update_before_add=True)  # Update entity on add
