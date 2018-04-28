# -*- coding:utf-8 -*-
#
# Copyright © 2016–2017 KuangKuang <upday7@163.com>
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version; http://www.gnu.org/copyleft/gpl.html.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
from anki.hooks import addHook, remHook

from .WebQuery import *

# region Entry Part


__version__ = '2.1.1'

__update_logs__ = (
    ('2.0.1', """
    WebQuery will no longer support Anki2.0.X anymore as whose QtWebKit is quite buggy.
    """),
)


def start():
    global have_setup
    if have_setup:
        return
    wq = WebQryAddon(version=__version__, update_logs=__update_logs__)
    addHook("profileLoaded", lambda: wq.perform_hooks(addHook))
    addHook("unloadProfile", lambda: wq.perform_hooks(remHook))
    have_setup = True


addHook("profileLoaded", start)

# endregion
