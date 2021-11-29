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


from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Optional

from homeassistant.components.sensor import (
    ATTR_LAST_RESET,
    ATTR_STATE_CLASS,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEVICE_CLASS_ENERGY, ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.util import dt as dt_util

from . import _LOGGER
from .const import DEFAULT_SENSOR_NAME, DOMAIN
from .hack import write_state_at_time

PLATFORM = "sensor"
from datetime import timedelta


class HistoricalEntity(RestoreEntity):
    @dataclass
    class Data:
        data: list[tuple[datetime, Any]]
        latest_state: State

    def __init__(self, *args, **kwargs):
        self._historical = HistoricalEntity.Data(data=[], latest_state=None)
        _LOGGER.debug("historical interface inited")

        super(*args, **kwargs)

    async def async_added_to_hass(self) -> None:
        self._historical.latest = await self.async_get_last_state()
        if self._historical.latest is None:
            return

        _LOGGER.debug(
            f"Restored previous state: {self._historical.latest.state}"
        )
        _LOGGER.debug(
            f"         last-updated: {self._historical.latest.last_updated}"
        )
        _LOGGER.debug(
            f"         last-changed: {self._historical.latest.last_changed}"
        )

    def write_historical_log_to_hass(self):
        latest_state = self.get_historical_latest()

        if latest_state is None:
            _LOGGER.debug("Set initial state to timestamp 0")
            zero_dt = dt_util.as_local(datetime.fromtimestamp(0))
            write_state_at_time(
                self, None, dt=zero_dt
                # self, None, dt=zero_dt, attributes={"last_reset": zero_dt}
            )

        self._purge_historical_data(since=latest_state)
        for (dt, value) in self._historical.data:
            _LOGGER.debug(f"Write historical state: {value} @ {dt}")
            write_state_at_time(
                self,
                value,
                dt=dt,
                # attributes={"last_reset": dt-timedelta(minutes=5)},
            )
            self._historical.latest = (
                self.hass.states.get(self.entity_id) or self._historical.latest
            )

        _LOGGER.debug(
            f"After historical write latest is: {self._historical.latest}"
        )

    def extend_historical_log(
        self, data: Iterable[tuple[datetime, Any]]
    ) -> None:
        self._historical.data.extend(data)
        self._historical.data = list(
            sorted(self._historical.data, key=lambda x: x[0])
        )

    def _purge_historical_data(self, since) -> None:
        if since is None:
            _LOGGER.debug("No previous state, skip historical purge")
            return

        initial = len(self._historical.data)
        self._historical.data = [
            x for x in self._historical.data if x[0] > since.last_changed
        ]
        final = len(self._historical.data)

        _LOGGER.debug(f"Purged {initial-final} elements of {initial}")

    def get_historical_latest(self):
        return self._historical.latest


class MacFlySensor(HistoricalEntity, SensorEntity):
    def __init__(self, name, api, unique_id):
        super().__init__()
        self._api = api

        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_unit_of_measurement = ENERGY_KILO_WATT_HOUR
        self._attr_native_unit_of_measurement = ENERGY_KILO_WATT_HOUR
        self._attr_device_class = DEVICE_CLASS_ENERGY

    @property
    def extra_state_attributes(self):
        return {
            ATTR_LAST_RESET: self.last_reset,
            ATTR_STATE_CLASS: STATE_CLASS_MEASUREMENT,
        }

    @property
    def last_reset(self):
        if latest := self.get_historical_latest():
            return latest.last_changed - timedelta(minutes=5)

        return None

    @property
    def state(self):
        self.write_historical_log_to_hass()

        # What if there are no records?
        # get_historical_latest() will be None
        return float(self.get_historical_latest().state)

    async def async_update(self):
        # Fix naive-timezone dt's, can lead to future states
        log = await self._api.get_historical_data()
        log = [(dt_util.as_utc(dt), v) for (dt, v) in log]

        self.extend_historical_log(log)


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
