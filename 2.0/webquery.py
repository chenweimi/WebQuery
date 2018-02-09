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

import imp
import os
import sys
import zipfile
from glob import glob

from anki.hooks import addHook, remHook

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


# USER PLEASE READ
# YOU MUST NOT CHANGE THE ORDER OF ** PROVIDER URLS **
# ONLY IF THE VISIBILITY OF TABS OF A MODEL IS TO BE RE-TOGGLED

class PyRender:
    """
    Import and Render *.py or *.zip file into object
    """

    def __init__(self, mod_file, ):
        """

        :type mod_file: str
        """
        self.py_file = mod_file
        self.module_nm, ext = os.path.splitext(os.path.basename(mod_file))
        self.pkg_dir = ''
        if ext.lower() == '.zip':
            with zipfile.ZipFile(mod_file, "r") as zip_ref:
                self.pkg_dir = os.path.splitext(mod_file)[0]
                if not os.path.isdir(self.pkg_dir):
                    os.mkdir(self.pkg_dir)
                zip_ref.extractall(self.pkg_dir)
        self.imported = self.load()

    def load(self, ):
        def _set_self_mod_attribute(mod):
            setattr(self, self.module_nm, mod)
            setattr(self, self.module_nm.lower(), mod)
            setattr(self, self.module_nm.upper(), mod)
            for mod_attr in [attr for attr in dir(mod) if attr not in ['__builtins__', '__doc__',
                                                                       '__file__', '__name__', '__package__']]:
                setattr(self, mod_attr, getattr(mod, mod_attr))

        if self.py_file.lower().endswith('.py'):
            module = imp.load_source(self.module_nm, self.py_file)
            _set_self_mod_attribute(module)
            module = imp.load_source(self.module_nm.lower(), self.py_file)
            _set_self_mod_attribute(module)
            module = imp.load_source(self.module_nm.upper(), self.py_file)
            _set_self_mod_attribute(module)

        elif self.py_file.lower().endswith('.pyc'):
            module = imp.load_compiled(self.module_nm, self.py_file)
            _set_self_mod_attribute(module)
            module = imp.load_compiled(self.module_nm.lower(), self.py_file)
            _set_self_mod_attribute(module)
            module = imp.load_compiled(self.module_nm.upper(), self.py_file)
            _set_self_mod_attribute(module)
        else:
            module = imp.load_package(self.module_nm, self.pkg_dir)

            def _load_sub_mod(parent_mod, parent_pkg_dir):
                for py_file in glob(os.path.join(parent_pkg_dir, "*")):
                    if py_file.endswith(".pyc"):
                        if not py_file.endswith("__init__.pyc"):
                            sub_mod_nm = os.path.basename(py_file).split(".")[0]
                            sub_mod = imp.load_compiled(sub_mod_nm, py_file)
                            setattr(parent_mod, sub_mod_nm, sub_mod)
                    else:
                        pkg_nm = os.path.basename(py_file)
                        sub_pkg = imp.load_package(pkg_nm, py_file)
                        setattr(parent_mod, pkg_nm, sub_pkg)
                        _load_sub_mod(sub_pkg, py_file)

            _load_sub_mod(module, self.pkg_dir)
        _set_self_mod_attribute(module)
        return self.module_nm in sys.modules


def start():
    # kklc = PyRender(os.path.join(os.path.split(__file__)[0], "kkcl.zip"))
    import WebQuery
    # WebQuery = kklc.PyRenderX(
    #     "https://github.com/upday7/LiveCodeHub/blob/master/AnkiAddonDists/WebQuery.zip?raw=true"
    # )
    if WebQuery.have_setup:
        return
    wq = WebQuery.WebQryAddon(version=__version__, update_logs=__update_logs__)
    addHook("profileLoaded", lambda: wq.perform_hooks(addHook))
    addHook("unloadProfile", lambda: wq.perform_hooks(remHook))
    WebQuery.have_setup = True


addHook("profileLoaded", start)
