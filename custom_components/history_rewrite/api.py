# -*- coding: utf-8 -*-
#
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

from datetime import datetime, timedelta
import random


class API:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    @property
    def device_info(self):
        return {"name": "Time machine device"}

    @staticmethod
    def calculate_value(point, aprox):
        rstate = random.getstate()
        random.seed(point)
        ret = aprox * random.randint(75, 100) / 100
        random.setstate(rstate)

        return ret

    def get_historical_data(self, start=None, end=None, step=None):
        return list(self._get_historical_data(start, end, step))

    def _get_historical_data(self, start=None, end=None, step=None):
        """
        Returns a random distribution of values for a series of intervals
        between start and end (size determined by step)
        Those values are random but fixed for each interval.
        Ex.
        _get_historical_data(0, 5, 1) ->
            [(0, 1, 0.4),
             (1, 2, 0.2),
             (2, 3, 0.7),
             (3, 4, 0.1),
             (4, 5, 0.8)]
        _get_historical_data(2, 7, 1) ->
            [(2, 3, 0.7),
             (3, 4, 0.1),
             (4, 5, 0.8),
             (5, 6, 0.3),
             (6, 7, 0.4)]
        """

        start = start or datetime.now()
        end = end or datetime.now()
        step = step or timedelta(minutes=10)

        start = min([start, end])
        end = max([start, end])

        reduction = 1635721200  # 2021-11-01 00:00:00
        start_value = int(start.timestamp()) - reduction
        end_value = int(end.timestamp()) - reduction
        n_blocks = int((end - start) / step)

        available = end_value - start_value

        curr = start_value
        available_per_block = available / n_blocks
        for x in range(n_blocks):
            p1 = start + (step * x)
            p2 = start + (step * (x + 1))

            value_for_block = self.calculate_value(
                p1.timestamp(), available_per_block
            )
            value_for_block = min([available, value_for_block])

            available = available - value_for_block
            curr = curr + value_for_block

            yield p1, p2, value_for_block
