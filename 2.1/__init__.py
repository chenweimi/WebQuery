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


__version__ = '1.2.45'

__update_logs__ = (
    ('1.2.44', """
    <ol>
    <li>Added <b>'Right-Click Mode'</b> option which enables user to save images more quickly,
     tool will locate images automatically.</li>
    <li>Fixed<a href="https://github.com/upday7/WebQuery/issues/7">#7</a> 
    error of multiple menus and docks when profile has been switched.</li>
    </ol>
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
