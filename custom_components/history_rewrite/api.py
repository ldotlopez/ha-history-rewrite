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

import math
from datetime import datetime, timedelta
import random
from functools import lru_cache


class API:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    @property
    def device_info(self):
        return {"name": "Time machine device"}

    @lru_cache
    async def get_historical_data(self, start=None, end=None, step=None):
        def _fn():
            nonlocal start, end, step

            start = start or datetime.now()
            end = end or datetime.now()
            step = step or timedelta(minutes=10)

            start = start.replace(minute=0, second=0, microsecond=0)
            end = end.replace(minute=0, second=0, microsecond=0)

            start = min([start, end])
            end = max([start, end])

            reduction = 1635721200  # 2021-11-01 00:00:00
            start_value = int(start.timestamp()) - reduction
            end_value = int(end.timestamp()) - reduction
            n_blocks = int((end - start) / step)

            print(f"{start_value} -> {end_value} in {n_blocks}")

            available = end_value - start_value

            curr = start_value
            available_per_block = available / n_blocks
            for x in range(n_blocks):
                p1 = start + (step * x)
                p2 = start + (step * (x + 1))

                value_for_block = (
                    available_per_block * random.randint(75, 125) / 100
                )
                value_for_block = min([available, value_for_block])

                available = available - value_for_block
                curr = curr + value_for_block
                # print(
                #     f"{p1} -> {p2} {curr} (curr: {curr} incr: {value_for_block})"
                # )
                yield p1, p2, value_for_block

        return list(_fn())

    # async def get_historical_data(self, accumlated=False):
    #     def _fn():
    #         now = datetime.datetime.now()
    #         start = now.replace(
    #             minute=0, second=0, microsecond=0
    #         ) - datetime.timedelta(hours=1)

    #         pattern = [
    #             (0, 0),
    #             (5, 2),
    #             (10, 1),
    #             (15, 2),
    #             (20, 4),
    #             (25, 2),
    #             (30, 8),
    #             (35, 3),
    #             (40, 5),
    #             (45, 2),
    #             (50, 1),
    #             (55, 5)
    #         ]
    #         value = math.floor(start.timestamp()) - math.floor(
    #             datetime.datetime(year=2021, month=11, day=26).timestamp()
    #         )
    #         for (timeincr, valincr) in pattern:
    #             dt = start + datetime.timedelta(minutes=timeincr)

    #             if accumlated:
    #                 value = value + (valincr*100)
    #             else:
    #                 value = valincr

    #             yield (dt, float(value))

    #     return list(_fn())


class APIError(Exception):
    pass
