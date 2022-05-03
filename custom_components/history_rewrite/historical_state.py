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

import functools
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Mapping

from homeassistant import core
from homeassistant.helpers.entity import Entity
from homeassistant.components import recorder
from homeassistant.components.recorder import models
from homeassistant.components.recorder.util import session_scope
from homeassistant.helpers.event import async_track_time_interval

from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from sqlalchemy import or_

from .hack import _build_attributes, _stringify_state, async_set

_LOGGER = logging.getLogger(__name__)

# STORE_LAST_UPDATE = "last_update"
# STORE_LAST_STATE = "last_state"


# @dataclass
# class HistoricalData:
#     log: list[tuple[datetime, Any]]
#     data: Mapping[str, Any]
#     state: Store


@dataclass
class StateAtTimePoint:
    state: Any
    when: datetime
    attributes: Dict[str, Any]


class HistoricalEntity:
    # You must know:
    # * DB keeps datetime object as utc
    # * Each time hass is started a new record is created
    # * That record can be 'unknow' or 'unavailable'

    async def async_update_history(self):
        _LOGGER.debug("You must override this method")
        return []

    @property
    def should_poll(self):
        """HistoricalEntities MUST NOT poll.
        Polling creates incorrect states at intermediate time points.
        """
        return False

    # @property
    # def last_reset(self):
    #     """Returning any else will cause discontinuities in history IDKW"""
    #     return None

    #     # Another aproach is to return data from historical entity, but causes
    #     # wrong results. Keep here for reference
    #     # FIXME: Write a proper method to access HistoricalEntity internal
    #     # state
    #     #
    #     # try:
    #     #     return self.historical.data[STORE_LAST_UPDATE]
    #     # except KeyError:
    #     #     return None

    @property
    def state(self):
        # Better report unavailable than anything
        return None

        # Another aproach is to return data from historical entity, but causes
        # wrong results. Keep here for reference.
        #
        # HistoricalEntities doesnt' pull but state is accessed only once when
        # the sensor is registered for the first time in the database
        #
        # if state := self.historical_state():
        #     return float(state)

    # @property
    # def available(self):
    #     # Leave us alone!
    #     return False

    async def _run_async_update_history(self, now=None) -> None:
        def _normalize_time_state(st):
            if not isinstance(st, StateAtTimePoint):
                return None

            if st.when.tzinfo is None:
                st.when = dt_util.as_local(st.when)

            if st.when.tzinfo is not timezone.utc:
                st.when = dt_util.as_utc(st.when)

            return st

        #
        # Normalize and filter historical states
        #
        states_at_dt = await self.async_update_history()
        states_at_dt = [_normalize_time_state(x) for x in states_at_dt]
        states_at_dt = [x for x in states_at_dt if x is not None]
        states_at_dt = list(sorted(states_at_dt, key=lambda x: x.when))

        _LOGGER.debug(f"Got {len(states_at_dt)} measures from sensor")

        #
        # Setup recorder write
        #
        if states_at_dt:
            fn = functools.partial(self._recorder_write_states, states_at_dt)
            self.recorder.async_add_executor_job(fn)

            _LOGGER.debug("Executor job set to write them")
        else:
            _LOGGER.debug("Nothing to write")

    async def async_added_to_hass(self) -> None:
        """Once added to hass:
        - Setup internal stuff with the Store to hold internal state
        - Setup a peridioc call to update the entity
        """

        if self.should_poll:
            raise Exception("poll model is not supported")

        _LOGGER.debug(f"{self.entity_id} ready")  # type: ignore[attr-defined]

        self.recorder = recorder.get_instance(self.hass)  # type: ignore[attr-defined]
        self.recorder.async_add_executor_job(self._recorder_cleanup)

        await self._run_async_update_history()
        async_track_time_interval(
            self.hass,  # type: ignore[attr-defined]
            self._run_async_update_history,
            timedelta(hours=1),
        )
        _LOGGER.debug(f"{self.entity_id} ready")  # type: ignore[attr-defined]

    def _recorder_cleanup(self):
        with session_scope(session=self.recorder.get_session()) as session:
            invalid_states = (
                session.query(models.States)
                .filter(models.States.entity_id == self.entity_id)
                .filter(
                    or_(
                        models.States.state == "unknown",
                        models.States.state == "unavailable",
                    )
                )
            )

            if invalid_states.count():
                _LOGGER.debug(
                    f"Deleted {invalid_states.count()} invalid states from recorder"
                )
                invalid_states.delete()
                session.commit()

    def _recorder_write_states(self, states_at_dt):
        _LOGGER.debug("Writing states on recorder")

        with session_scope(session=self.recorder.get_session()) as session:
            # # Model filter-sensor
            # max_ts_in_db = (
            #     session.query(sql_func.max(models.States.last_updated))
            #     .filter(models.States.entity_id == self.entity_id)
            #     .first()[0]
            # ) or datetime(1970, 1, 1)
            # max_ts_in_db = dt_util.as_local(max_ts_in_db)

            # states_at_dt = list(sorted(states_at_dt, key=lambda x: x[0]))
            # states_at_dt = [x for x in states_at_dt if x[0] > max_ts_in_db]
            # _LOGGER.debug(f"Database states ends at: {max_ts_in_db}")

            # Model overwrite-database-records
            min_dt = states_at_dt[0].when
            # max_dt = states_at_dt[-1].when
            overlaping_states = (
                session.query(models.States)
                .filter(models.States.entity_id == self.entity_id)
                .filter(models.States.last_updated >= min_dt)
                # Delete anything newer, it's simplier
                # .filter(models.States.last_updated <= max_dt)
            )
            overlaping_states.delete()

            _LOGGER.debug(f"Sensor states starts at: {states_at_dt[0].when}")
            _LOGGER.debug(f"Sensor states ends at:   {states_at_dt[-1].when}")

            db_events = []
            for st_dt in states_at_dt:
                # sqlite> select * from events where event_id = 18133721;
                # event_id=18133721
                # event_type=state_changed
                # event_data=
                # origin=LOCAL
                # time_fired=2022-05-03 14:05:09.988100
                # context_id=
                # context_user_id=60b2dc4eb6f56d135db20968cea2905a
                # context_parent_id=

                core_state = core.State(
                    entity_id=self.entity_id,
                    state=_stringify_state(self, st_dt.state),
                    last_updated=st_dt.when,
                    # attributes=st_dt.attributes,
                )
                core_ev = core.Event(
                    event_type=core.EVENT_STATE_CHANGED,
                    time_fired=st_dt.when,
                    data={"new_state": core_state, "entity_id": self.entity_id},
                )
                event = models.Events.from_event(core_ev)
                db_events.append(event)
            session.add_all(db_events)
            session.commit()

            db_states = []
            for idx, st_dt in enumerate(states_at_dt):
                # At this point we have:
                # CREATE TABLE states (
                #     state_id INTEGER NOT NULL,
                #     entity_id VARCHAR(255),
                #     state VARCHAR(255),
                #     attributes TEXT,
                #     event_id INTEGER,
                #     last_changed DATETIME,
                #     last_updated DATETIME,
                #     old_state_id INTEGER,
                #     attributes_id INTEGER,
                # );
                # 29|sensor.mcfly|2808.0|||2022-05-03 12:00:00.000000|2022-05-03 13:00:00.000000|28|
                # 30|sensor.mcfly|3276.0|||2022-05-03 13:00:00.000000|2022-05-03 14:00:00.000000|29|
                # But we want:
                # CREATE TABLE states (
                #     state_id INTEGER NOT NULL,
                #     domain VARCHAR(64),
                #     entity_id VARCHAR(255),
                #     state VARCHAR(255),
                #     attributes TEXT,
                #     event_id INTEGER,
                #     last_changed DATETIME,
                #     last_updated DATETIME,
                #     created DATETIME,
                #     context_id VARCHAR(36),
                #     context_user_id VARCHAR(36), old_state_id INTEGER, attributes_id INTEGER,
                # );
                # 17768044||sensor.icp_es0021000002618134yh_historical|0.311||18133719|2022-05-02 21:00:00.000000|2022-05-02 21:00:00.000000||||17768043|685156
                # 17768045||sensor.icp_es0021000002618134yh_historical|0.166||18133720|2022-05-02 22:00:00.000000|2022-05-02 22:00:00.000000||||17768044|685157

                state = models.States(
                    entity_id=self.entity_id,
                    state=_stringify_state(self, st_dt.state),
                    last_updated=st_dt.when,
                    # attributes=st_dt.attributes,
                    event=db_events[idx],
                )
                db_states.append(state)

            session.add_all(db_states)
            session.commit()

            # Rebuild chain
            lastest_state = (
                session.query(models.States)
                .filter(models.States.entity_id == self.entity_id)
                .filter(models.States.last_updated < min_dt)
                .order_by(models.States.last_updated)
                .first()
            )
            db_states[0].old_state = lastest_state
            for idx in range(1, len(db_states)):
                db_states[idx].old_state = db_states[idx - 1]
                db_states[idx].old_state_id = db_states[idx - 1].state_id
                db_states[idx].last_changed = db_states[idx - 1].last_updated

            session.add_all(db_states)
            session.commit()

            _LOGGER.debug(f"Added {len(db_states)} to database")

    # async def save_state(self, params):
    #     """Convenient function to store internal state"""
    #
    #     data = self.historical.data
    #     data.update(params)
    #
    #     self.historical.data = data.copy()
    #
    #     data[STORE_LAST_UPDATE] = dt_util.as_utc(data[STORE_LAST_UPDATE]).timestamp()
    #
    #     await self.historical.state.async_save(data)
    #     return data

    # async def load_state(self):
    #     """Convenient function to load internal state"""
    #
    #     data = (await self.historical.state.async_load()) or {}
    #     data = {
    #         STORE_LAST_STATE: None,
    #         STORE_LAST_UPDATE: 0,
    #     } | data
    #
    #     data[STORE_LAST_UPDATE] = dt_util.as_utc(
    #         datetime.fromtimestamp(data[STORE_LAST_UPDATE])
    #     )
    #
    #     self.historical.data = data
    #     return data

    # def write_state_at_time(
    #     self: Entity,
    #     state: str,
    #     dt: Optional[datetime],
    #     attributes: Optional[Mapping] = None,
    # ):
    #     """
    #     Wrapper for the modified version of
    #     homeassistant.core.StateMachine.async_set
    #     """
    #     state = _stringify_state(self, state)
    #     attrs = dict(_build_attributes(self, state))
    #     attrs.update(attributes or {})
    #
    #     ret = async_set(
    #         self.hass.states,
    #         entity_id=self.entity_id,
    #         new_state=state,
    #         attributes=attrs,
    #         time_fired=dt,
    #     )
    #
    #     return ret
