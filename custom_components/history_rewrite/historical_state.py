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
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Optional
from homeassistant.core import State, MappingProxyType
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .hack import (
    _build_attributes,
    _stringify_state,
    async_set,
)

_LOGGER = logging.getLogger(__name__)


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
            self.write_state_at_time(
                None,
                dt=zero_dt
                # self, None, dt=zero_dt, attributes={"last_reset": zero_dt}
            )

        self._purge_historical_data(since=latest_state)
        for (dt, value) in self._historical.data:
            _LOGGER.debug(f"Write historical state: {value} @ {dt}")
            self.write_state_at_time(
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

    def write_state_at_time(
        self: Entity,
        state: str,
        dt: Optional[datetime],
        attributes: Optional[MappingProxyType] = None,
    ):
        # if attributes is None:
        #     old_state = self.hass.states.get(self.entity_id)
        #     if old_state:
        #         attributes = self.hass.states.get(self.entity_id).attributes
        #     else:
        #         attributes = None

        state = _stringify_state(self, state)
        attrs = dict(_build_attributes(self, state))
        attrs.update(attributes or {})

        return async_set(
            self.hass.states,
            entity_id=self.entity_id,
            new_state=state,
            attributes=attrs,
            time_fired=dt,
        )
