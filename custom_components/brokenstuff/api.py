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

import random


class AsyncBrokenAPI:
    ON_AUTHENTICATE = True

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def authenticate(self, *args, **kwargs):
        if isinstance(self.ON_AUTHENTICATE, Exception):
            raise self.ON_AUTHENTICATE

        return self.ON_AUTHENTICATE

    async def get_data(self):
        return random.randint(0, 100)

    @property
    def device_info(self):
        return {
            'name': 'device'
        }


class BrokenAPI:
    ON_AUTHENTICATE = True

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def authenticate(self, *args, **kwargs):
        if isinstance(self.ON_AUTHENTICATE, Exception):
            raise self.ON_AUTHENTICATE

        return self.ON_AUTHENTICATE

    def get_data(self):
        return None


class APIError(Exception):
    pass
