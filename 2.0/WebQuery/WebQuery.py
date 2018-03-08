# -*- coding: utf-8 -*-
# Copyright: kuangkuang <upday7@163.com>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""
Project : WebQuery
Created: 12/24/2017
"""
import json
import re
import time
from functools import partial

from DonateWidget20 import DialogDonate
from PyQt4 import QtNetwork
from PyQt4.QtNetwork import QNetworkRequest, QNetworkAccessManager
from PyQt4.QtWebKit import QWebPluginFactory
from uuid import uuid4

from anki.cards import Card
# noinspection PyArgumentList
from anki.lang import _
from anki.notes import Note
from aqt import *
from aqt.downloader import download
from aqt.models import Models
from aqt.utils import tooltip, restoreGeom, showInfo

# region Bytes
items_bytes = bytearray(
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f'
    b'\xf3\xffa\x00\x00\x00\x04sBIT\x08\x08\x08\x08|\x08d\x88\x00\x00\x00\tpHYs\x00\x00\x0b\x13'
    b'\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00MIDAT8\x8d\xd5\x91\xc1\t\xc00\x0c\xc4TO'
    b'\x96\rL6\xf2F\x877\xc8d\xa6\xafB\x9f!P\xd2\xe8\x7fpB\xb0\x9b\x0b\xa0\xf7\x1e\x92\xc2\xdd'
    b'\x9b\x99\xb5\xd9\xb1\xa4\xb0\xaf\x9eM\xb3\xa4PU#3\x07\xc0\xa1\n\x0f\x87Vx\x17\x80?T\xd8'
    b'\xcf\r\xa5\x9e(\r0\x19&\xcc\x00\x00\x00\x00IEND\xaeB`\x82')

gear_bytes = bytearray(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10'
                       b'\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04sBIT\x08\x08\x08'
                       b'\x08|\x08d\x88\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b'
                       b'\x13\x01\x00\x9a\x9c\x18\x00\x00\x01PIDAT8\x8d}\xd3MKVQ\x14\x05'
                       b'\xe0\xc7\xab\xf9A\x86\xf9AX"\xf5+D"\x10\xfa\x13\x82\x93\x10'
                       b'\xc4\x89\x08\x82\x88`?A\x0b\x9c\xd8$P\x82h\xd0 B\x85\xd0\x818s*'
                       b"\x89\x8a\xa2\x98P\x13'\xa2)\x0e\xf2cp\xf7\x85\x83\xdd\xf7]p"
                       b'8\x9b\xb3\xd6Yg\xef\xbb\xef\xaeQ\x19\xb7\xb8\x8e\xb8\x165U\xb4'
                       b'\xa5\xf8\x17{]\x98\x95"\x8b\xbd\x1bSh\x8c5^\xa2\x1dC\x03'
                       b'\x9a\xf0\x16\xcfR\xf2\x0b\xb6q\x88\x1d|Eo\xc2\xbf\xc47l\xe1(4\x9f\n'
                       b'\xf2\x15~\x85s\x1f\xdeT)k0\xf4\xcd\xf8]<\xf2\x03\xab\xe8'
                       b'H\x84\x8d\xf8\x80s\xfc\xc5\\\xa4_\xe0\t\xd6\xb1\x98\xa1\x1f?\xb1'
                       b'\x9b\xd4\xf5.D/\xf0\x1c\x9d\x98\t\xae;J\xd8\xc0@\x9a\xde\x15'
                       b'\xea#>\r\x83\xf4\xc5\xd3\x88\x9bqY\x10\x99r\xdc\xefy\x86\x9b2a\x86V'
                       b'\xcc\xe2\x0c\xedq>\x8f\x8fQRW\xc4\xf3\xc1=\xc6\x05\xde\xa3\x85'
                       b'\xfc#\xae\xa0-1\xae\x0f\xc1I\xaci<H\xf8\x0e\xaca\x89\xbc'
                       b'\xc7\xc7x\x88\xd7\x18\xaaP\x16\x0c\xcb[\xfd\x08\x7f\xd0'
                       b'S\x10\x9f\xb1\x87}\xf9\xcf\xf2]\xde\xef\x02}X\xc6&\x0eB\xbb\x90:wa'
                       b'"Ro\xc0\xa8\xffga$\xe1\'\xf1\xb4J\xa6\x84A]\\\xa88L\xd5F'
                       b'\xf4\xfe\xa5R\xed\x1d\xd81A\xc9\x94\x9bY}\x00\x00\x00\x00IEND\xaeB'
                       b'`\x82')

# endregion

# region Globals
have_setup = False
this_addon_folder = os.path.split(__file__)[0]
webq_model_config_json_file = os.path.join(this_addon_folder, "web_query_model_config.json")


# endregion

# region Meta classes

# noinspection PyPep8Naming
class _MetaConfigObj(type):
    """
    Meta class for reading/saving config.json for anki addon
    """
    metas = {}

    class StoreLocation:
        Profile = 0
        AddonFolder = 1
        MediaFolder = 3

    # noinspection PyArgumentList
    def __new__(mcs, name, bases, attributes):

        config_dict = {k: attributes[k] for k in attributes.keys() if not k.startswith("_") and k != "Meta"}
        attributes['config_dict'] = config_dict

        for k in config_dict.keys():
            attributes.pop(k)
        c = super(_MetaConfigObj, mcs).__new__(mcs, name, bases, attributes)

        # region Meta properties
        # meta class
        meta = attributes.get('Meta', type("Meta", (), {}))
        # meta values
        setattr(meta, "config_dict", config_dict)
        setattr(meta, "__store_location__", getattr(meta, "__store_location__", 0))
        setattr(meta, "__config_file__", getattr(meta, "__config_file__", None))

        _MetaConfigObj.metas[c.__name__] = meta
        # endregion

        if not config_dict:
            return c

        mcs.attributes = attributes  # attributes that is the configuration items

        if _MetaConfigObj.metas[name].__store_location__ == _MetaConfigObj.StoreLocation.MediaFolder:
            if not _MetaConfigObj.metas[name].__config_file__:
                raise Exception("If StoreLocation is Media Folder, __config_file__ must be provided!")
            setattr(c, "media_json_file",
                    mcs.MediaConfigJsonFile("_{}".format(_MetaConfigObj.metas[name].__config_file__).lower()))

        return c

    def __getattr__(cls, item):
        if item == "meta":
            return _MetaConfigObj.metas[cls.__name__]
        else:
            load_config = lambda: cls.get_config(cls.metas[cls.__name__].__store_location__)
            config_obj = load_config()
            return config_obj.get(item)

    def __setattr__(cls, key, value):
        """
        when user set values to addon config obj class, will be passed to anki's addon manager and be saved.
        :param key:
        :param value:
        :return:
        """
        try:
            config_obj = cls.get_config(cls.metas[cls.__name__].__store_location__)
            config_obj[key] = value
            store_location = cls.metas[cls.__name__].__store_location__
            if store_location == cls.StoreLocation.AddonFolder:
                if cls.IsAnki21:
                    mw.addonManager.writeConfig(cls.AddonModelName, config_obj)
                else:
                    with open(cls.ConfigJsonFile(), "w") as f:
                        json.dump(config_obj, f)
            elif store_location == cls.StoreLocation.MediaFolder:
                with open(cls.media_json_file, "w") as f:
                    json.dump(config_obj, f)
            elif store_location == _MetaConfigObj.StoreLocation.Profile:
                if _MetaConfigObj.IsAnki21():
                    mw.pm.profile.update(config_obj)
                else:
                    mw.pm.meta.update(config_obj)
        except:
            super(_MetaConfigObj, cls).__setattr__(key, value)

    def get_config(cls, store_location):
        """

        :param store_location:
        :rtype: dict
        """

        def _get_json_dict(json_file):
            if not os.path.isfile(json_file):
                with open(json_file, "w") as f:
                    json.dump(cls.config_dict, f)
            with open(json_file, 'r') as ff:
                return json.load(ff)

        if store_location == _MetaConfigObj.StoreLocation.Profile:
            if _MetaConfigObj.IsAnki21():
                disk_config_obj = mw.pm.profile
            else:
                disk_config_obj = mw.pm.meta
            cls.config_dict.update(disk_config_obj)
        elif store_location == _MetaConfigObj.StoreLocation.AddonFolder:
            # ensure json file
            obj = _get_json_dict(_MetaConfigObj.ConfigJsonFile())

            if _MetaConfigObj.IsAnki21():
                disk_config_obj = mw.addonManager.getConfig(_MetaConfigObj.AddonModelName())
            else:
                disk_config_obj = obj
            cls.config_dict.update(disk_config_obj)
        elif store_location == _MetaConfigObj.StoreLocation.MediaFolder:
            disk_config_obj = _get_json_dict(cls.media_json_file)
            cls.config_dict.update(disk_config_obj)
            with open(cls.media_json_file, "w") as f:
                json.dump(cls.config_dict, f)
        return cls.config_dict

    @staticmethod
    def IsAnki21():
        from anki import version
        return eval(version[:3]) >= 2.1

    @staticmethod
    def ConfigJsonFile():
        return os.path.join(_MetaConfigObj.AddonsFolder(), "config.json")

    @staticmethod
    def MediaConfigJsonFile(file_nm):
        return os.path.join(_MetaConfigObj.MediaFolder(), file_nm)

    @staticmethod
    def AddonsFolder():
        if _MetaConfigObj.IsAnki21():
            _ = os.path.join(mw.addonManager.addonsFolder(), _MetaConfigObj.AddonModelName())
        else:
            _ = mw.pm.addonFolder()
        if aqt.isWin:
            _ = _.encode(aqt.sys.getfilesystemencoding()).decode("utf-8")
        return _.lower()

    @staticmethod
    def AddonModelName():
        return __name__.split(".")[0]

    @staticmethod
    def MediaFolder():
        try:
            return os.path.join(mw.pm.profileFolder(), "collection.media")
        except:
            return ""


# endregion

# region Auto-Update

try:
    import urllib2 as web
    from urllib import urlretrieve
except ImportError:
    from urllib import request as web
    from urllib.request import urlretrieve


class AddonUpdater(QThread):
    """
    Class for auto-check and upgrade source codes, uses part of the source codes from ankiconnect.py : D
    """
    update_success = pyqtSignal(bool)
    new_version = pyqtSignal(bool)

    def __init__(self, parent,
                 addon_name,
                 version_py,
                 source_zip,
                 local_dir, current_version, version_key_word="__version__"):
        """
        :param parent: QWidget
        :param addon_name: addon name
        :param version_key_word: version variable name, should be in format "X.X.X", this keyword should be stated in the first lines of the file
        :param version_py: remote *.py file possibly on github where hosted __version__ variable
        :param source_zip: zip file to be downloaded for upgrading
        :param local_dir: directory for extractions from source zip file
        :param current_version: current version string in format "X.X.X"

        :type parent: QWidget
        :type addon_name: str
        :type version_key_word: str
        :type version_py: str
        :type source_zip: str
        :type local_dir: str
        :type current_version: str
        """
        super(AddonUpdater, self).__init__(parent)
        self.source_zip = source_zip
        self.version_py = version_py
        self.local_dir = local_dir
        self.version_key_word = version_key_word
        self.addon_name = addon_name
        self.current_version = current_version

    @property
    def has_new_version(self):
        try:
            cur_ver = self._make_version_int(self.current_version)
            remote_ver = self._make_version_int(
                [l for l in self._download(self.version_py).split("\n") if l.startswith(self.version_key_word)][
                    0].split("=")[1])
            return cur_ver < remote_ver
        except:
            return False

    @staticmethod
    def _download(url):
        if url.lower().endswith(".py"):
            try:
                resp = web.urlopen(url, timeout=10)
            except web.URLError:
                return None

            if resp.code != 200:
                return None
            if sys.version[0] == '2':
                return resp.read()
            else:
                return resp.read().decode()
        else:
            with open(urlretrieve(url)[0], "rb") as f:
                if sys.version[0] == '2':
                    return f.read()
                else:
                    return f.read().decode()

    @staticmethod
    def _make_version_int(ver_string):
        ver_str = "".join([n for n in str(ver_string) if n in "1234567890"])
        return int(ver_str)

    @staticmethod
    def _make_data_string(data):
        return data.decode('utf-8')

    def ask_update(self):
        return QMessageBox.question(
            self.parent(),
            self.addon_name,
            'Upgrade to the latest version?',
            QMessageBox.Yes | QMessageBox.No
        )

    def alert_update_failed(self):
        QMessageBox.critical(self.parent(),
                             self.addon_name, 'Failed to download latest version.')

    def alert_update_success(self):
        QMessageBox.information(self.parent(), self.addon_name,
                                'Upgraded to the latest version, please restart Anki.')

    def upgrade_using_anki(self):
        addon_code = '627484806'
        if _MetaConfigObj.IsAnki21():
            ret = download(mw, addon_code)
            if ret[0] == "error":
                # err = "Error downloading %(id)s: %(error)s" % dict(id=addon_code, error=ret[1])
                return
            else:
                # err = ''
                data, fname = ret
                fname = fname.replace("_", " ")
                mw.addonManager.install(str(addon_code), data, fname)
                # name = os.path.splitext(fname)[0]
                mw.progress.finish()

            # mw.addonManager.downloadIds([addon_code, ])
        else:
            ret = download(mw, addon_code)
            if not ret:
                return
            data, fname = ret
            mw.addonManager.install(data, fname)
            mw.progress.finish()

    def upgrade(self):
        try:
            self.upgrade_using_anki()
            self.update_success.emit(True)
        except:
            try:
                data = self._download(self.source_zip)
                if data is None:
                    QMessageBox.critical(self.parent(),
                                         self.addon_name, 'Failed to download latest version.')
                else:
                    zip_path = os.path.join(self.local_dir,
                                            uuid4().hex + ".zip")
                    with open(zip_path, 'wb') as fp:
                        fp.write(data)

                    # unzip
                    from zipfile import ZipFile
                    zip_file = ZipFile(zip_path)
                    if not os.path.isdir(self.local_dir):
                        os.makedirs(self.local_dir, exist_ok=True)
                    for names in zip_file.namelist():
                        zip_file.extract(names, self.local_dir)
                    zip_file.close()

                    # remove zip file
                    os.remove(zip_path)

                    self.update_success.emit(True)
            except:
                self.update_success.emit(False)

    def run(self):
        if self.has_new_version:
            self.new_version.emit(True)


class UpgradeButton(QPushButton):

    def __init__(self, parent):
        super(UpgradeButton, self).__init__(parent)
        pix = QPixmap()
        pix.loadFromData(bytearray(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10'
                                   b'\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x02\xb6IDATx^U'
                                   b'\xcb\xdf\x8bUU\x18\xc7\xe1\xcf\xbb\xf6\xda{w\xce\xd9s\x8e3v'
                                   b'\x1a\xc4\xb4)db\x18R\xec\x17\x06\x11H\x84\x97\xe1M\xa0\x12\xd1'
                                   b'\xcd\x14\x98?\x12\x9c\x9bp\xbc\xe8\x0f\xb0D\xbc0\xa1 B\x8dB'
                                   b'\x98\x02\xc5\x1b\xd3r\x0c,\xa2\x8b\xca\x10\x0f\xd3 \x88'
                                   b'\x03\xce\x19l\xe6\xcc9{\xaf\xb5\xde\x86\xb3\xa1\xf2\x81'
                                   b'\xef\xcd\xfb\xf2\x91\xa5\xe9\x97\xf9?\x11\xc1\xc6\x86\x99K'
                                   b'\xad\xc7\xb2\xcct\x8a_\xfe"\x1d6\xb5\xda\xf6=\xf7\xf0KH\xf0'
                                   b"\x80\x02\x02\x80u\xf7\xef\xf20\xc5\x8b>\xdb\x1c\xae\x9e\xa9Xw'"
                                   b'\x1f\x80\xb5\x9b\x92\xc7\xaf\\\xfdaG,n\xd6\xa0\x00h9\xec\xad'
                                   b'\x999\x04E(i\x80\x90\x87\xa9\xa7\xf7\xbc>\xea\xdbs\xa3\x8b7'
                                   b'\xa0\xb1\x06Lk\xf6h\x1c\xf3\xb61e\x18\x028\x15\xec\x90/X'
                                   b'\xaa$\x18\x01\xe9?\x14\xe7\xf1\x95*\xe4\xf5-d\x9b\xff$\xc9\x97'
                                   b'QD\xc4\x82\x18!(8`\xfbS\x1e\x83\x81\r\xe3\x8fB\xee\xc1{\xc4y\xc8'
                                   b'\x837\xbd\x07\xd4\xb6\x9d\xa6\xf9\xdew\xd0SB\x11\xbcz\xc5{\xa5'
                                   b'\xc8\x95WF}?\xb1\xaa\xa0AqbH\xba\x0eQEV@{\x8b\x94\nH'
                                   b'\xc1\x15\xe8\xeaP\xa3\xaco(.@P0\x94\x10\x81^G\xf1\x058\x87#\xef'
                                   b'\xd0\x17\xa5P\x11\\\x8e+\nedP\xfb\xa1*(`\x8d\x011\x94\x14\xda\xf7'
                                   b'\x01O\xdb\x86.%\x03NX\xeeh{\xecI\xf0\x014\x94\x8d\x8d\xc0\xa6)M'
                                   b'\x1b\xe9n\x82\xbe\xebs\xee\x15]\xe6\x93a3N\xe8\xd1\x17W\xe9'
                                   b'\xcd\x05\xc6\x1a\xac[\xe9q31\x0c\x11\xd1L\x12\xdeZ\xddy\x8e'
                                   b'>\xc1\xd0\xf7\x07\x87?\xff\xf5\x83A\xd5\xd6N\xd5Kc\xaa_oP=U\xd3'
                                   b'\xe2\xdc\x88\xe6\x1f\xa2:\x89\xea\xf1H\xf5\x8b\x01\xd5o'
                                   b'\x1b\xda\xda+z\xfa%\xcel\x14\x9a6KYHSy\xf3\xf6\xb5\xf6\x82_\xbc'
                                   b'\xb8\x7f\xeb\xc4s\xb00\x0f\xdd\x9cn=\xc5\xfb\x88j\xc7\x13\xff\xed'
                                   b'![\xe2\xe6y\x98\xf9I?\xa9\xafebK\r\x8c5`\xad\xf0HE\x0eL_X9v'
                                   b'\xfd\xe3\x1b\xd0\x8c!\x8e\xc8\xde\xf8\x83\xc6T\xc1\xf2"'
                                   b'\x10\xc1\xecu\xe5\xe4\xb4\x9e\xacU\x98Hb\xa8F`\x10\x10\x11\x92'
                                   b'\x18\x063\x0e\x1d\xf9\xb2\xf7\xd1\x8f\x9f\xceCV\x10\xae'
                                   b'\xbc\xca\x83\xe3k\x88\x07\xe0\xf2\x0c\xec\xfc\x8c\x13\xcd\x8c'
                                   b'\xbdi\x0cF\xcaY\x00\x04\xc4@\x92\x08\x1b\xeb\xbc\xbf\xfbl(\xce'
                                   b'\xe5\x1c~\xe1\x99\xcb\xc8\x1c|\xf3;\xec\xba\xc6\x89]'
                                   b'\x83\xec\xab\x961\x08}\x86\x12\x02D\x06\xb2\x046\xd7\x99|\xf1+'
                                   b'\x8e\xfd\xfc\x1b\\m\xf5\xe3S\xc0\xbez\x02\x91\x80\x08'
                                   b'\xff\xb2\x86\xff\x88\x94\x87F\x02\xafe\x1cz\xfe,u\xa0\x02\xbc3'
                                   b'\x1e\x83-\xe3\x87\xfc\x03.\x87/\xdd\x8a[\xdf\x84\x00\x00\x00\x00I'
                                   b'END\xaeB`\x82'))
        icon = QIcon(pix)
        self.setIcon(icon)
        self.setToolTip("There's new version, please click here to download")
        self.updator = AddonUpdater(
            self,
            "Web Query",
            "https://raw.githubusercontent.com/upday7/WebQuery/master/2.0/webquery.py",
            "https://github.com/upday7/WebQuery/blob/master/2.0.zip?raw=true",
            mw.pm.addonFolder(),
            WebQryAddon.version
        )
        self.updator.new_version.connect(self.on_addon_new_version)
        self.updator.update_success.connect(self.on_addon_updated)
        self.setVisible(False)
        self.clicked.connect(self.on_clicked)

    def on_addon_new_version(self):
        self.setVisible(True)

    def on_addon_updated(self, success):
        if success:
            self.updator.alert_update_success()
            self.setVisible(False)
        else:
            self.updator.alert_update_failed()

    def on_clicked(self):
        if self.updator.ask_update() == QMessageBox.Yes:
            self.updator.upgrade()


# endregion

# region Config Objects
class SyncConfig:
    __metaclass__ = _MetaConfigObj

    class Meta:
        __store_location__ = _MetaConfigObj.StoreLocation.MediaFolder
        __config_file__ = "webquery_config.json"

    doc_size = (405, 808)
    image_field_map = {}
    qry_field_map = {}
    txt_field_map = {}
    visible = True
    append_mode = False
    auto_save = False

    txt_edit_current_after_saving = False
    auto_img_find = True


class ProfileConfig:
    __metaclass__ = _MetaConfigObj

    class Meta:
        __store_location__ = _MetaConfigObj.StoreLocation.Profile

    is_first_webq_run = True
    wq_current_version = ''


class UserConfig:
    __metaclass__ = _MetaConfigObj

    class Meta:
        __store_location__ = _MetaConfigObj.StoreLocation.MediaFolder
        __config_file__ = "webquery_user_cfg.json"

    load_on_question = True
    image_quality = 50
    provider_urls = [
        ("Bing", "https://www.bing.com/images/search?q=%s"),
        ("Wiki", "https://en.wikipedia.org/wiki/?search=%s"),
    ]
    preload = True
    load_when_ivl = ">=0"

    proxy_settings = {
        "enabled": False,
        "type": "HTTP",
        "host": "",
        "port": "",
        "user": "",
        "password": ""
    }


class ModelConfig:
    __metaclass__ = _MetaConfigObj

    class Meta:
        __store_location__ = _MetaConfigObj.StoreLocation.MediaFolder
        __config_file__ = "webquery_model_cfg.json"

    visibility = {}  # MID: [ { PROVIDER URL NAME: VISIBLE }]


# endregion

# region Qt Widgets

class WebPluginFactory(QWebPluginFactory):
    def __init__(self, parent=None):
        QWebPluginFactory.__init__(self, parent)

    def create(mimeType):
        if mimeType == "x-pyqt/widget":
            return WebQueryWidget()

    def plugins(self):
        plugin = QWebPluginFactory.Plugin()
        plugin.name = "PyQt Widget"
        plugin.description = "An example Web plugin written with PyQt."
        mimeType = QWebPluginFactory.MimeType()
        mimeType.name = "x-pyqt/widget"
        mimeType.description = "PyQt widget"
        mimeType.fileExtensions = []
        plugin.mimeTypes = [mimeType]
        print("plugins")
        return [plugin]


class _Page(QWebPage):
    has_selector_contents = pyqtSignal(bool)

    def __init__(self, parent, keyword=None, provider_url=''):
        super(_Page, self).__init__(parent)
        self.clicked_img_url = None
        self.keyword = keyword
        self._provider_url = provider_url

        self.event_looptime = 0.01
        self._load_status = None
        self.loadFinished.connect(self._on_load_finished)
        self.plug_factory = WebPluginFactory()
        self.setPluginFactory(self.plug_factory)
        self.try_proxy()


    def try_proxy(self):
        if not UserConfig.proxy_settings.get("enabled", False):
            return
        proxy = QtNetwork.QNetworkProxy()
        proxy.setType(QtNetwork.QNetworkProxy.HttpProxy)
        host = UserConfig.proxy_settings.get("host", "")
        port = UserConfig.proxy_settings.get("port", 0)
        user = UserConfig.proxy_settings.get("user_name", "")
        password = UserConfig.proxy_settings.get("password", "")
        proxy.setHostName(host)
        proxy.setPort(int(port))
        proxy.setUser(user)
        proxy.setPassword(password)
        mgr = self.networkAccessManager()
        assert isinstance(mgr, QNetworkAccessManager)
        mgr.setProxy(proxy)

    def userAgentForUrl(self, url):
        return "Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, " \
               "like Gecko) Version/9.0 Mobile/13B143 Safari/601.1"

    @property
    def provider(self):
        return self._provider_url

    @provider.setter
    def provider(self, val):
        self._provider_url = val

    @property
    def selector(self):
        if self.provider.find("~~") >= 0:
            return self.provider[self.provider.find("~~") + 2:]
        return ''

    # noinspection PyArgumentList
    def get_url(self):
        # remove selector
        url = self.provider % self.keyword
        if url.find("~~") >= 0:
            url = url[:url.find("~~")]
        return QUrl(url)

    def load(self, keyword):
        self.keyword = keyword
        if not keyword:
            url = QUrl('about:blank')
        else:
            url = self.get_url()

        req = QNetworkRequest(QUrl(url))

        self.mainFrame().load(req)
        self._wait_load(10)

    def _events_loop(self, wait=None):
        if wait is None:
            wait = self.event_looptime
        QApplication.instance().processEvents()
        time.sleep(wait)

    def _on_load_finished(self, successful):
        self._load_status = successful
        if successful:
            if self.selector:
                mf = self.mainFrame()
                tag_cmd = u"document.querySelector('{}').outerHTML".format(self.selector)
                tag_html = mf.evaluateJavaScript(tag_cmd)
                if tag_html:
                    mf.setHtml(tag_html)
                    self.has_selector_contents.emit(True)
                    return
                self.has_selector_contents.emit(False)

    def _wait_load(self, timeout=None):
        self._events_loop(0.0)
        if self._load_status is not None:
            load_status = self._load_status
            self._load_status = None
            return load_status
        itime = time.time()
        while self._load_status is None:
            if timeout and time.time() - itime > timeout:
                break
                # raise Exception("Timeout reached: %d seconds" % timeout)
            self._events_loop()
        self._events_loop(0.0)
        if self._load_status:
            # self.load_js()
            self.setViewportSize(self.mainFrame().contentsSize())
        load_status = self._load_status
        self._load_status = None
        return load_status


class _WebView(QWebView):
    element_captured = pyqtSignal(QRect)

    def __init__(self, parent, txt_option_menu):
        super(_WebView, self).__init__(parent)
        self.qry_page = None
        self.txt_option_menu = txt_option_menu
        self._web_element_rect = None
        self.settings().setAttribute(QWebSettings.PluginsEnabled, True)

    def add_query_page(self, page):
        if not self.qry_page:
            self.qry_page = page
        self.setPage(self.qry_page)

    def load_page(self):
        if self.qry_page:
            self.qry_page.load()

    def contextMenuEvent(self, evt):
        if self.selectedText():
            self.txt_option_menu.set_selected(self.selectedText())
            self.txt_option_menu.exec_(mw.cursor().pos())
        else:
            super(_WebView, self).contextMenuEvent(evt)

    def selectedText(self):
        return self.page().selectedText()

    @property
    def mf(self):
        return self.page().mainFrame()

    @property
    def web_elements_coord(self):
        _ = []
        try:
            for el in self.mf.findAllElements("img"):
                rect = el.geometry()
                if rect.getCoords() != (0, 0, -1, -1):
                    _.append((el, rect))
        except AttributeError:
            pass

        return _

    def mousePressEvent(self, evt):
        """

        :type evt: QMouseEvent
        :return:
        """
        if SyncConfig.auto_img_find and evt.button() == Qt.RightButton:
            cursor_pos = evt.pos()
            scroll_pos = self.mf.scrollPosition()
            for el, q_rect in self.web_elements_coord[::-1]:
                rect = QRect(
                    q_rect.left(),
                    q_rect.top() - scroll_pos.y(),
                    q_rect.width(),
                    q_rect.height()
                )
                if rect.contains(cursor_pos, True) and rect != self._web_element_rect:
                    self._web_element_rect = rect
                    break
            if self._web_element_rect:
                self.element_captured.emit(self._web_element_rect)
        else:
            super(_WebView, self).mousePressEvent(evt)

class ImageLabel(QLabel):
    cropMode = True
    mouse_released = pyqtSignal()
    canceled = pyqtSignal(bool)

    def __init__(self):
        super(ImageLabel, self).__init__()
        self._image = None

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, img):
        self._image = img
        self.setPixmap(QPixmap.fromImage(img))

    def mouseReleaseEvent(self, event):
        self.crop()
        self.mouse_released.emit()

    def mousePressEvent(self, event):
        """

        :type event: QMouseEvent
        :return:
        """
        if event.button() == Qt.LeftButton:
            print("ImageHolder: " + str(event.pos()))
            self.mousePressPoint = event.pos()
            if self.cropMode:
                if hasattr(self, "currentQRubberBand"):
                    self.currentQRubberBand.hide()
                self.currentQRubberBand = QRubberBand(QRubberBand.Rectangle, self)
                self.currentQRubberBand.setGeometry(QRect(self.mousePressPoint, QSize()))
                self.currentQRubberBand.show()
        else:
            if self.currentQRubberBand:
                self.currentQRubberBand.hide()
            self.canceled.emit(True)

    def mouseMoveEvent(self, event):
        # print("mouseMove: " + str(event.pos()))
        if self.cropMode:
            self.currentQRubberBand.setGeometry(QRect(self.mousePressPoint, event.pos()).normalized())

    def paintEvent(self, event):
        if not self.image:
            return
        self.painter = QPainter(self)
        self.painter.setPen(QPen(QBrush(QColor(255, 241, 18, 100)), 15, Qt.SolidLine, Qt.RoundCap))
        self.painter.drawImage(0, 0, self.image)
        self.painter.end()

    def crop(self):
        rect = self.currentQRubberBand.geometry()
        self.image = self.image.copy(rect)
        self.setMinimumSize(self.image.size())
        self.resize(self.image.size())
        # QApplication.restoreOverrideCursor()
        self.currentQRubberBand.hide()
        self.repaint()


class TxtOptionsMenu(QMenu):
    default_txt_field_changed = pyqtSignal(int)
    txt_saving = pyqtSignal()
    edit_current = pyqtSignal(bool)

    def __init__(self, parent):

        super(TxtOptionsMenu, self).__init__("Text Capture", parent)
        self.default_txt_action_grp = None
        self.default_txt_field_index = 1

        self.selected_txt = ''
        self.action_save_to_default = None
        self.options_menu = None

        self.setup_other_actions()
        self.setup_options_actions()

        # slots
        self.aboutToShow.connect(self.onAboutToShow)
        self.aboutToHide.connect(self.onAboutToHide)

    def set_selected(self, txt):
        self.selected_txt = txt

    def setup_options_actions(self):
        if self.options_menu:
            return
        self.options_menu = QMenu("Options", self)
        action_open_editor = QAction("Trigger Edit", self.options_menu)
        action_open_editor.setToolTip("Open editor of current note after saving.")
        action_open_editor.setCheckable(True)
        action_open_editor.setChecked(SyncConfig.txt_edit_current_after_saving)
        action_open_editor.toggled.connect(lambda toggled: self.edit_current.emit(toggled))
        self.options_menu.addAction(action_open_editor)

        self.addMenu(self.options_menu)

    def setup_other_actions(self):
        self.action_save_to_default = QAction("Save Text (T)", self)
        self.action_save_to_default.setShortcut(QKeySequence("T"))
        self.addAction(self.action_save_to_default)
        self.action_save_to_default.triggered.connect(self.onSaving)

    def onSaving(self, triggered):
        self.txt_saving.emit()
        self.selected_txt = ''

    def setup_txt_field(self, fld_names, selected_index=1):

        if not self.default_txt_action_grp:
            self.default_txt_action_grp = QActionGroup(self)
            self.default_txt_action_grp.triggered.connect(self.default_txt_action_triggered)

        if fld_names:
            list(map(
                self.default_txt_action_grp.removeAction,
                self.default_txt_action_grp.actions()
            ))
            added_actions = list(map(
                self.default_txt_action_grp.addAction,
                fld_names
            ))
            if added_actions:
                if selected_index not in list(range(added_actions.__len__())):
                    selected_index = 1
                list(map(lambda action: action.setCheckable(True), added_actions))
                selected_action = added_actions[selected_index]
                selected_action.setChecked(True)
                self.default_txt_field_index = selected_index
        self.addSeparator().setText("Fields")
        self.addActions(self.default_txt_action_grp.actions())

    def default_txt_action_triggered(self, action):
        """

        :type action: QAction
        :return:
        """
        self.default_txt_field_index = self.default_txt_action_grp.actions().index(action)
        action.setChecked(True)
        self.default_txt_field_changed.emit(self.default_txt_field_index)
        if self.action_save_to_default.isVisible():
            self.action_save_to_default.trigger()

    def onAboutToShow(self):
        if self.action_save_to_default:
            self.action_save_to_default.setVisible(True if self.selected_txt else False)
            self.action_save_to_default.setText(
                "Save to field [{}] (T)".format(self.default_txt_field_index))
        if self.options_menu:
            self.options_menu.setEnabled(False if self.selected_txt else True)
            for child in self.options_menu.children():
                child.setEnabled(False if self.selected_txt else True)

    def onAboutToHide(self):
        self.selected_txt = ''


class OptionsMenu(QMenu):
    img_field_changed = pyqtSignal(int)
    query_field_change = pyqtSignal(int)

    def __init__(self, parent, txt_option_menu):
        super(OptionsMenu, self).__init__('Options', parent)

        self.selected_img_index = 1

        # init objects before setting up
        self.menu_img_config = None
        self.menu_txt_options = txt_option_menu
        self.img_field_menu = None
        self.field_action_grp = None
        self.qry_field_menu = None
        self.qry_field_action_grp = None
        self.txt_field_action_grp = None

        # setup option actions
        self.setup_all()

    def setup_all(self):

        self.setup_image_field([])
        self.addMenu(self.menu_txt_options)
        self.setup_query_field([])
        self.setup_option_actions()

    def setup_query_field(self, fld_names, selected_index=0):
        self.query_fld_names = fld_names
        if not self.qry_field_menu:
            pix = QPixmap()
            pix.loadFromData(items_bytes)
            icon = QIcon(pix)
            self.qry_field_menu = QMenu("Query Field", self)
            self.qry_field_menu.setIcon(icon)
        if not self.qry_field_action_grp:
            self.qry_field_action_grp = QActionGroup(self.qry_field_menu)
            self.qry_field_action_grp.triggered.connect(self.qry_field_action_triggered)
        if self.query_fld_names:
            list(map(
                self.qry_field_action_grp.removeAction,
                self.qry_field_action_grp.actions()
            ))
            added_actions = list(map(
                self.qry_field_action_grp.addAction,
                self.query_fld_names
            ))
            if added_actions:
                list(map(lambda action: action.setCheckable(True), added_actions))
                selected_action = added_actions[selected_index]
                selected_action.setChecked(True)

        self.qry_field_menu.addActions(self.qry_field_action_grp.actions())
        self.addSeparator().setText("Fields")
        self.addMenu(self.qry_field_menu)

    def setup_image_field(self, fld_names, selected_index=1):
        if not self.menu_img_config:
            self.menu_img_config = QMenu("Image Capture", self)
            self.addMenu(self.menu_img_config)

            # region image options
            menu_img_options = QMenu("Options", self.menu_img_config)

            action_img_append_mode = QAction("Append Mode", menu_img_options)
            action_img_append_mode.setCheckable(True)
            action_img_append_mode.setToolTip("Append Mode: Check this if you need captured image to be APPENDED "
                                              "to field instead of overwriting it")
            action_img_append_mode.setChecked(SyncConfig.append_mode)

            action_img_auto_save = QAction("Auto Save", menu_img_options)
            action_img_auto_save.setCheckable(True)
            action_img_auto_save.setToolTip("Auto-Save: If this is checked, image will be saved "
                                            "immediately once completed cropping.")
            action_img_auto_save.setChecked(SyncConfig.auto_save)

            action_right_click_mode = QAction("Right-Click Mode", menu_img_options)
            action_right_click_mode.setCheckable(True)
            action_right_click_mode.setToolTip("Right-Click Mode: If this is checked, image which has "
                                               "curor hovered will be captured.")
            action_right_click_mode.setChecked(SyncConfig.auto_img_find)

            action_img_append_mode.toggled.connect(self.on_append_mode)
            action_img_auto_save.toggled.connect(self.on_auto_save)
            action_right_click_mode.toggled.connect(self.on_action_right_click_mode)

            menu_img_options.addAction(action_img_append_mode)
            menu_img_options.addAction(action_img_auto_save)
            menu_img_options.addAction(action_right_click_mode)

            # endregion

            self.menu_img_config.addMenu(menu_img_options)

        if not self.field_action_grp:
            self.field_action_grp = QActionGroup(self.menu_img_config)
            self.field_action_grp.triggered.connect(self.field_action_triggered)

        if fld_names:
            list(map(
                self.field_action_grp.removeAction,
                self.field_action_grp.actions()
            ))
            added_actions = list(map(
                self.field_action_grp.addAction,
                fld_names
            ))
            if added_actions:
                list(map(lambda action: action.setCheckable(True), added_actions))
                selected_action = added_actions[selected_index]
                selected_action.setChecked(True)
                self.selected_img_index = selected_index

            self.menu_img_config.addSeparator().setText("Fields")
            self.menu_img_config.addActions(self.field_action_grp.actions())

    def setup_option_actions(self):

        # region txt options

        # endregion

        # region general
        pix = QPixmap()
        pix.loadFromData(gear_bytes)
        self.action_open_user_cfg = QAction("User Config", self)
        self.action_open_user_cfg.setIcon(QIcon(pix))

        # bind action slots
        self.action_open_user_cfg.triggered.connect(lambda: ConfigEditor(mw, UserConfig.media_json_file).exec_())

        self.addAction(self.action_open_user_cfg)

        # endregion

    def qry_field_action_triggered(self, action):
        """

        :type action: QAction
        :return:
        """
        self.qry_selected_index = self.qry_field_action_grp.actions().index(action)
        action.setChecked(True)
        # self.setText(self.qry_field_action_grp.actions()[self.qry_selected_index].text())
        self.query_field_change.emit(self.qry_selected_index)

    def field_action_triggered(self, action):
        """

        :type action: QAction
        :return:
        """
        self.selected_img_index = self.field_action_grp.actions().index(action)
        action.setChecked(True)
        # self.setText(self.field_action_grp.actions()[self.selected_index].text())
        self.img_field_changed.emit(self.selected_img_index)

    def on_append_mode(self, checked):
        SyncConfig.append_mode = True if checked else False

    def on_action_right_click_mode(self, checked):
        SyncConfig.auto_img_find = True if checked else False

    def on_auto_save(self, checked):
        SyncConfig.auto_save = True if checked else False


# noinspection PyMethodMayBeStatic
class CaptureOptionButton(QPushButton):

    def __init__(self, parent, options_menu, icon=None):
        if icon:
            super(CaptureOptionButton, self).__init__(icon, "", parent)
        else:
            super(CaptureOptionButton, self).__init__("Options", parent)

        # set style
        # self.setFlat(True)
        self.setToolTip("Capture Options")

        self.setMenu(options_menu)
        self.setText('Options')


class ResizeButton(QPushButton):
    def __init__(self, parent, dock_widget):
        super(ResizeButton, self).__init__("<>", parent)
        self.start_resize = False
        self.dock_widget = dock_widget
        self.setFixedWidth(10)
        self.setToolTip("Hold and Drag to change the width of this dock!")

    def mouseReleaseEvent(self, evt):
        self.start_resize = False

    def mousePressEvent(self, evt):
        self.start_resize = True

    def mouseMoveEvent(self, evt):
        if self.start_resize:
            new_width = QApplication.desktop().rect().right() - QCursor().pos().x()
            self.dock_widget.setFixedWidth(new_width)
            doc_size = (new_width, self.dock_widget.height())
            SyncConfig.doc_size = doc_size
            self.dock_widget.resize(QSize(new_width, self.dock_widget.height()))
        evt.accept()


class SupportButton(QPushButton):
    def __init__(self, parent, dock_widget):
        super(SupportButton, self).__init__(parent)
        self.start_resize = False
        self.dock_widget = dock_widget
        self.setToolTip("Support!")
        self.setFixedWidth(25)
        self.clicked.connect(self.on_clicked)
        self.setIcon(QIcon(QPixmap(":/Icon/icons/dollar.png")))

    def on_clicked(self):
        DialogDonate(mw).exec_()


class ConfigEditor(QDialog):
    class Ui_Dialog(object):
        def setupUi(self, Dialog):
            Dialog.setObjectName("Dialog")
            Dialog.setWindowModality(Qt.ApplicationModal)
            Dialog.resize(631, 521)
            self.verticalLayout = QVBoxLayout(Dialog)
            self.verticalLayout.setObjectName("verticalLayout")
            self.editor = QPlainTextEdit(Dialog)
            sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            sizePolicy.setHorizontalStretch(0)
            sizePolicy.setVerticalStretch(3)
            sizePolicy.setHeightForWidth(self.editor.sizePolicy().hasHeightForWidth())
            self.editor.setSizePolicy(sizePolicy)
            self.editor.setObjectName("editor")
            self.verticalLayout.addWidget(self.editor)
            self.buttonBox = QDialogButtonBox(Dialog)
            self.buttonBox.setOrientation(Qt.Horizontal)
            self.buttonBox.setStandardButtons(
                QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
            self.buttonBox.setObjectName("buttonBox")
            self.verticalLayout.addWidget(self.buttonBox)

            self.retranslateUi(Dialog)
            self.buttonBox.accepted.connect(Dialog.accept)
            self.buttonBox.rejected.connect(Dialog.reject)
            QMetaObject.connectSlotsByName(Dialog)

        def retranslateUi(self, Dialog):
            _translate = QCoreApplication.translate
            Dialog.setWindowTitle(_("Configuration"))

    def __init__(self, dlg, json_file):
        super(ConfigEditor, self).__init__(dlg)
        self.json = json_file
        self.conf = None
        self.form = self.Ui_Dialog()
        self.form.setupUi(self)
        self.updateText()
        self.show()

    def updateText(self):
        with open(self.json, "r") as f:
            self.conf = json.load(f)
        self.form.editor.setPlainText(
            json.dumps(self.conf, sort_keys=True, indent=4, separators=(',', ': ')))

    def accept(self):
        txt = self.form.editor.toPlainText()
        try:
            self.conf = json.loads(txt)
        except Exception as e:
            showInfo(_("Invalid configuration: ") + repr(e))
            return

        with open(self.json, "w") as f:
            json.dump(self.conf, f)

        super(ConfigEditor, self).accept()


class WebQueryWidget(QWidget):
    img_saving = pyqtSignal(QImage)
    capturing = pyqtSignal()
    viewing = pyqtSignal()

    def add_query_page(self, page):
        self._view.add_query_page(page)

        self.show_grp(self.loading_grp, False)
        self.show_grp(self.view_grp, True)
        self.show_grp(self.capture_grp, False)

    def reload(self):
        self._view.reload()

    def __init__(self, parent, options_menu):
        super(WebQueryWidget, self).__init__(parent)

        # all widgets
        self._view = _WebView(self, options_menu.menu_txt_options)
        self._view.element_captured.connect(self.on_web_element_capture)
        self.lable_img_capture = ImageLabel()
        self.lable_img_capture.mouse_released.connect(self.cropped)
        self.lable_img_capture.canceled.connect(self.crop_canceled)

        self.loading_lb = QLabel()
        self.capture_button = QPushButton('Capture (C)', self)
        self.capture_button.setShortcut(QKeySequence(Qt.Key_C))
        self.capture_button.clicked.connect(self.on_capture)

        self.return_button = QPushButton('Return', self)
        self.return_button.setMaximumWidth(100)
        self.return_button.setShortcut(QKeySequence("ALT+Q"))
        self.return_button.clicked.connect(self.on_view)

        # region Save Image Button and Combo Group
        self.save_img_button = QPushButton('Save (C)', self)
        self.save_img_button.setShortcut(QKeySequence(Qt.Key_C))
        self.save_img_button.setShortcutEnabled(Qt.Key_C, False)
        self.save_img_button.clicked.connect(self.save_img)

        # just in case dock cannot be resized properly
        dock_widget = self.parent()
        assert isinstance(dock_widget, QDockWidget)
        dock_widget.setFixedWidth(SyncConfig.doc_size[0])
        self.resize_btn = ResizeButton(self, dock_widget)
        self.support_btn = SupportButton(self, dock_widget)

        self.update_btn = UpgradeButton(self)
        self.update_btn.setMaximumWidth(20)

        self.capture_option_btn = CaptureOptionButton(self, options_menu)
        self.capture_option_btn.setMaximumWidth(100)
        self.img_btn_grp_ly = QHBoxLayout()
        self.img_btn_grp_ly.addWidget(self.resize_btn)
        self.img_btn_grp_ly.addWidget(self.update_btn)
        self.img_btn_grp_ly.addSpacing(5)
        self.img_btn_grp_ly.addWidget(self.support_btn)
        self.img_btn_grp_ly.addWidget(self.capture_option_btn)
        self.img_btn_grp_ly.addWidget(self.return_button)
        self.img_btn_grp_ly.addWidget(self.save_img_button)
        self.img_btn_grp_ly.addWidget(self.capture_button)

        # endregion

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.loading_lb, alignment=Qt.AlignCenter)
        self.layout.addWidget(self._view)
        self.layout.addWidget(self.lable_img_capture, alignment=Qt.AlignCenter)
        self.layout.addItem(self.img_btn_grp_ly)

        # widget groups
        self.loading_grp = [self.loading_lb]
        self.view_grp = [self._view, self.capture_button, self.capture_option_btn]
        self.capture_grp = [self.lable_img_capture, self.return_button, self.save_img_button, ]
        self.misc_grp = [
            self.resize_btn, self.support_btn
        ]

        # Visible
        self.show_grp(self.loading_grp, False)
        self.show_grp(self.view_grp, False)
        self.show_grp(self.capture_grp, False)
        self.show_grp(self.misc_grp, False)

        # other slots
        self._view.loadStarted.connect(self.loading_started)
        self._view.loadFinished.connect(self.load_completed)

        self.setLayout(self.layout)

        # variable
        self._loading_url = ''

    def loading_started(self):
        self.loading_lb.setText("<b>Loading ... </b>")
        self.show_grp(self.loading_grp, True)
        self.show_grp(self.view_grp, False)
        self.show_grp(self.capture_grp, False)
        self.show_grp(self.misc_grp, False)

    def load_completed(self, *args):
        self.show_grp(self.loading_grp, False)
        self.show_grp(self.view_grp, True)
        self.show_grp(self.capture_grp, False)
        self.show_grp(self.misc_grp, True)

    def show_grp(self, grp, show):
        for c in grp:
            c.setVisible(show)

    def on_web_element_capture(self, rect):
        self.lable_img_capture.image = QImage(QPixmap.grabWindow(self._view.winId(), rect.x(),
                                                                 rect.y(), rect.width(), rect.height()))
        self.lable_img_capture.adjustSize()
        scroll_pos = self._view.mf.scrollPosition()
        self.cropped()
        self._view.mf.setScrollPosition(scroll_pos)

    def on_capture(self, *args):
        QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))

        self._view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.lable_img_capture.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        rect = self._view.rect()
        self.lable_img_capture.image = QImage(QPixmap.grabWindow(self._view.winId(), rect.x(),
                                                                 rect.y()))
        self.lable_img_capture.adjustSize()

        self.show_grp(self.loading_grp, False)
        self.show_grp(self.view_grp, False)
        self.show_grp(self.capture_grp, True)

        # self.lable_img_capture.setVisible(True)

    def on_view(self, *args):
        QApplication.restoreOverrideCursor()

        self.show_grp(self.loading_grp, False)
        self.show_grp(self.view_grp, True)
        self.show_grp(self.capture_grp, False)

        self.viewing.emit()
        self._view.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.lable_img_capture.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

    def save_img(self, *args):
        self.img_saving.emit(self.lable_img_capture.image)
        self.show_grp(self.loading_grp, False)
        self.show_grp(self.view_grp, True)
        self.show_grp(self.capture_grp, False)
        self._view.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.lable_img_capture.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

    def cropped(self):
        QApplication.restoreOverrideCursor()
        self.show_grp(self.loading_grp, False)
        self.show_grp(self.view_grp, False)
        self.show_grp(self.capture_grp, True)
        if SyncConfig.auto_save:
            self.save_img()
            self.save_img_button.setShortcutEnabled(Qt.Key_C, False)
        else:
            self.save_img_button.setShortcutEnabled(Qt.Key_C, True)

    def crop_canceled(self):
        self.return_button.click()

    @property
    def selectedText(self):
        return self._view.selectedText()


class ModelDialog(Models):
    # noinspection PyUnresolvedReferences
    def __init__(self, mw, parent=None, fromMain=False):
        # region copied from original codes in aqt.models.Models
        self.mw = mw
        self.parent = parent or mw
        self.fromMain = fromMain
        QDialog.__init__(self, self.parent, Qt.Window)
        self.col = mw.col
        self.mm = self.col.models
        self.mw.checkpoint(_("Note Types"))
        self.form = aqt.forms.models.Ui_Dialog()
        self.form.setupUi(self)
        self.form.buttonBox.helpRequested.connect(lambda: openHelp("notetypes"))
        self.setupModels()
        restoreGeom(self, "models")
        # endregion

        # add additional button
        self.button_tab_visibility = QPushButton("Web Query Tab Visibility", self)
        self.button_tab_visibility.clicked.connect(self.onWebQueryTabConfig)
        self.button_tab_visibility.setEnabled(False)
        self.form.modelsList.itemClicked.connect(
            partial(lambda item: self.button_tab_visibility.setEnabled(True if item else False)))
        self.form.gridLayout_2.addWidget(self.button_tab_visibility, 2, 0, 1, 1)

    @property
    def mid(self):
        return self.model['id']

    @property
    def default_visibility(self):
        return {n: True for n, u in UserConfig.provider_urls}

    def onWebQueryTabConfig(self, clicked):
        _ = ModelConfig.visibility
        if not ModelConfig.visibility.get(str(self.mid)):
            _[str(self.mid)] = self.default_visibility
        else:
            for k in self.default_visibility.keys():
                if k not in _[str(self.mid)].keys():
                    _[str(self.mid)][k] = self.default_visibility[k]
                    print k, "not in ", _[str(self.mid)].keys()
                    print _[str(self.mid)][k]

        _pop_keys = []
        for ok in _[str(self.mid)].keys():
            if ok not in self.default_visibility.keys():
                _pop_keys.append(ok)
        for k in _pop_keys:
            _[str(self.mid)].pop(k)
        ModelConfig.visibility = _

        class _dlg(QDialog):
            def __init__(inner_self):
                super(_dlg, inner_self).__init__(self)
                inner_self.setWindowTitle("Toggle Visibility")

                inner_self.provider_url_visibility_dict = ModelConfig.visibility.get(str(self.mid), {})

                # shown check boxes
                inner_self.checkboxes = list(map(
                    lambda provider_url_nm: QCheckBox("{}".format(provider_url_nm), inner_self),
                    sorted(inner_self.provider_url_visibility_dict.keys()))
                )

                list(map(lambda cb: cb.setChecked(inner_self.provider_url_visibility_dict[cb.text()]),
                         inner_self.checkboxes))
                list(map(lambda cb: cb.toggled.connect(partial(inner_self.on_visibility_checked, cb.text())),
                         inner_self.checkboxes))

                ly = QVBoxLayout(inner_self)
                list(map(ly.addWidget, inner_self.checkboxes))
                inner_self.setLayout(ly)

            def on_visibility_checked(inner_self, provider_url_nm, checked):
                inner_self.provider_url_visibility_dict[provider_url_nm] = checked
                _ = ModelConfig.visibility
                _[str(self.mid)].update(inner_self.provider_url_visibility_dict)
                ModelConfig.visibility = _

        _dlg().exec_()


# endregion

class WebQryAddon:
    version = ''
    update_logs = ()

    def __init__(self, version, update_logs):
        self.shown = False

        # region variables
        self.current_index = 0
        self._first_show = True
        WebQryAddon.version = version
        WebQryAddon.update_logs = update_logs

        # endregion

        self.dock = None
        self.pages = []
        self.webs = []
        self._display_widget = None
        self.main_menu = None
        self.main_menu_action = None

    def perform_hooks(self, hook_func):
        self.destroy_dock()

        # Menu setup
        hook_func("showQuestion", self.init_menu)

        # others
        hook_func("showQuestion", self.start_query)
        hook_func("showAnswer", self.show_widget)
        hook_func("deckClosing", self.destroy_dock)
        hook_func("reviewCleanup", self.destroy_dock)
        hook_func("profileLoaded", self.profileLoaded)

    def cur_tab_index_changed(self, tab_index):
        self.current_index = tab_index
        if not UserConfig.preload:
            self.show_widget()
        self.web.update_btn.updator.start()

    @property
    def page(self):
        return self.pages[self.current_index]

    @property
    def web(self):
        return self.webs[self.current_index]

    def init_menu(self):
        if self.main_menu:
            self.main_menu_action = mw.form.menuTools.addMenu(self.main_menu)
        else:
            self.main_menu = QMenu("WebQuery", mw.form.menuTools)
            action = QAction(self.main_menu)
            action.setText("Toggle WebQuery")
            action.setShortcut(QKeySequence("ALT+W"))
            self.main_menu.addAction(action)
            action.triggered.connect(self.toggle)
            self.options_menu = OptionsMenu(self.main_menu, TxtOptionsMenu(self.main_menu))
            self.main_menu.addMenu(self.options_menu)
            self.main_menu_action = mw.form.menuTools.addMenu(self.main_menu)

    def profileLoaded(self):
        # region owverwrite note type management
        def onNoteTypes():
            ModelDialog(mw, mw, fromMain=True).exec_()

        mw.form.actionNoteTypes.triggered.disconnect()
        mw.form.actionNoteTypes.triggered.connect(onNoteTypes)
        # eng region

    # endregion
    @property
    def reviewer(self):
        """

        :rtype: Reviewer
        """
        return mw.reviewer

    @property
    def card(self):
        """

        :rtype: Card
        """
        return self.reviewer.card

    @property
    def note(self):
        """

        :rtype: Note
        """
        return self.reviewer.card.note()

    @property
    def word(self):
        if not mw.reviewer:
            return None
        qry_field = SyncConfig.qry_field_map.get(str(self.note.mid), 0)
        word = re.sub('<[^<]+?>', '', self.note.fields[qry_field]).strip()
        return word

    @property
    def model_hidden_tab_index(self):
        visibilities = ModelConfig.visibility.get(str(self.note.mid))
        if visibilities:
            keys = [k for k, v in visibilities.items() if not v]
            model_hidden_tab_index = [i for i, args in enumerate(UserConfig.provider_urls) if args[0] in keys]
        else:
            model_hidden_tab_index = []
        return model_hidden_tab_index

    def add_dock(self, title):
        config = SyncConfig

        class DockableWithClose(QDockWidget):
            closed = pyqtSignal()

            def __init__(self, title, parent):
                super(DockableWithClose, self).__init__(title, parent)

            def closeEvent(self, evt):
                self.closed.emit()
                QDockWidget.closeEvent(self, evt)

            def resizeEvent(self, evt):
                assert isinstance(evt, QResizeEvent)
                doc_size = (evt.size().width(),
                            evt.size().height())
                config.doc_size = doc_size
                super(DockableWithClose, self).resizeEvent(evt)
                evt.accept()

            # def sizeHint(self):
            #    return QSize(config.doc_size[0], config.doc_size[1])

        dock = DockableWithClose(title, mw)
        # dock.setObjectName(title)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)

        # region dock widgets
        available_urls = [url for i, (n, url) in enumerate(UserConfig.provider_urls)
                          if i not in self.model_hidden_tab_index]
        self.webs = list(
            map(lambda x: WebQueryWidget(dock, self.options_menu),
                range(available_urls.__len__()))
        )
        self.pages = list(
            map(lambda params: _Page(parent=self.webs[params[0]], provider_url=params[1]),
                enumerate(available_urls))
        )

        for web in self.webs:
            web.img_saving.connect(self.save_img)

        # region main / tab widgets
        if UserConfig.provider_urls.__len__() - self.model_hidden_tab_index.__len__() > 1:
            self._display_widget = QTabWidget(dock)
            self._display_widget.setVisible(False)
            self._display_widget.setTabPosition(self._display_widget.East)
            added_web = 0
            for i, (nm, url) in [(i, (n, url)) for i, (n, url) in enumerate(UserConfig.provider_urls)
                                 if i not in self.model_hidden_tab_index]:
                self.webs[added_web].setVisible(False)
                if i in self.model_hidden_tab_index:
                    continue
                try:
                    self._display_widget.addTab(self.webs[added_web], nm)
                    added_web += 1
                except IndexError:
                    continue
            self._display_widget.currentChanged.connect(self.cur_tab_index_changed)
        else:
            self._display_widget = QWidget(dock)
            self._display_widget.setVisible(False)
            l = QVBoxLayout(self._display_widget)
            try:
                l.addWidget(self.web)
            except IndexError:
                QMessageBox.warning(
                    mw, "No Provider URL", "You have no <em>[Provider URL]</em>"
                                           " selected<br><br>Go to Tools > Manage Note Types > Web Query Tab Visibility")
                return
            self._display_widget.setLayout(l)

        # endregion
        dock.setWidget(self._display_widget)
        self.hide_widget()
        mw.addDockWidget(Qt.RightDockWidgetArea, dock)

        return dock

    def start_query(self, from_toggle=False):
        if (not from_toggle) and (not eval(str(self.card.ivl) + UserConfig.load_when_ivl)):
            self.destroy_dock()
            return

        if not self.ensure_dock():
            return
        if not self.word:
            return

        if not UserConfig.load_on_question:
            self.hide_widget()
        else:
            self.show_widget()

        if UserConfig.preload:
            self.start_pages()

        self.bind_slots()

    def start_pages(self):
        QApplication.restoreOverrideCursor()
        for wi, web in enumerate(self.webs, ):
            page = self.pages[wi]
            if page.selector:
                page.has_selector_contents.connect(partial(self.onSelectorWeb, wi))
            page.load(self.word)
            web.add_query_page(page)

    def onSelectorWeb(self, wi, has):
        if isinstance(self._display_widget, QTabWidget):
            tab = self._display_widget.widget(wi)
            tab.setVisible(has)
            self._display_widget.setTabEnabled(wi, has)
            if not has:
                tab.setToolTip("No Contents")
            else:
                tab.setToolTip("")

    def bind_slots(self):
        if self.reviewer:
            image_field = SyncConfig.image_field_map.get(str(self.note.mid), 1)
            qry_field = SyncConfig.qry_field_map.get(str(self.note.mid), 0)
            items = [(f['name'], ord) for ord, f in sorted(self.note._fmap.values())]
            self.options_menu.setup_image_field([i for i, o in items], image_field)
            self.options_menu.setup_query_field([i for i, o in items], qry_field)
            self.options_menu.menu_txt_options.setup_txt_field([i for i, o in items],
                                                               SyncConfig.txt_field_map.get(str(self.note.mid), 1))
            self.options_menu.img_field_changed.connect(self.img_field_changed)
            self.options_menu.query_field_change.connect(self.qry_field_changed)
            assert isinstance(self.options_menu.menu_txt_options, TxtOptionsMenu)
            self.options_menu.menu_txt_options.txt_saving.connect(self.save_txt)
            self.options_menu.menu_txt_options.edit_current.connect(self.edit_current)
            self.options_menu.menu_txt_options.default_txt_field_changed.connect(self.txt_field_changed)

    def hide_widget(self):
        if self._display_widget:
            self._display_widget.setVisible(False)

    def show_widget(self, from_toggle=False):
        if (not from_toggle) and (not eval(str(self.card.ivl) + UserConfig.load_when_ivl)):
            self.destroy_dock()
            return
        if not self.dock:
            return

        self._display_widget.setVisible(True)
        # list(map(lambda web: web.setVisible(True), self.webs))
        if self._first_show:
            self.web.update_btn.updator.start()
            self._first_show = False

        if not UserConfig.preload:
            self.start_pages()

    def destroy_dock(self):
        if self.dock:
            mw.removeDockWidget(self.dock)
            self.dock.destroy()
            self.dock = None

        if self.main_menu_action:
            mw.form.menuTools.removeAction(self.main_menu_action)

    def hide(self):
        if self.dock:
            self.dock.setVisible(False)

    def show_dock(self):
        if self.dock:
            self.dock.setVisible(True)

    def ensure_dock(self):
        if ProfileConfig.is_first_webq_run:
            QMessageBox.warning(
                mw, "Web Query", """
                <p>
                    <b>Welcome !</b>
                </p>
                <p>This is your first run of <EM><b>Web Query</b></EM>, please read below items carefully:</p>
                <ul>
                    <li>
                        Choose proper <em>[Image]</em> field in "Options" button in right dock widget 
                        BEFORE YOU SAVING ANY IMAGES, by default its set to the 2nd
                        field of your current note.
                    </li>
                    <li>
                        You are able to change the <em>[Query]</em> field in "Options" also, 
                        which is set to the 1st field by default.
                    </li>
                </ul>
                """)
            ProfileConfig.is_first_webq_run = False

        if ProfileConfig.wq_current_version != self.version:
            for _ in self.update_logs:
                cur_log_ver, cur_update_msg = _
                if cur_log_ver != self.version:
                    continue
                QMessageBox.warning(mw, "Web Query", """
                <p><b>v{} Update:</b></p>
                <p>{}</p>
                """.format(cur_log_ver, cur_update_msg))
            ProfileConfig.wq_current_version = self.version

        if not self.dock:
            self.dock = self.add_dock('Web Query', )
            if not self.dock:
                return False
            self.dock.closed.connect(self.on_closed)
        self.dock.setVisible(SyncConfig.visible)
        return True

    def toggle(self):
        if eval(str(self.card.ivl) + UserConfig.load_when_ivl):
            if not self.ensure_dock():
                return
            if self.dock.isVisible():
                SyncConfig.visible = False
                self.hide()
            else:
                SyncConfig.visible = True
                self.show_dock()
        else:
            if self.dock and self.dock.isVisible():
                self.hide()
            else:
                self.start_query(True)
                self.show_widget(True)
                self.show_dock()

    def on_closed(self):
        mw.progress.timer(100, self.hide, False)

    def img_field_changed(self, index):
        if index == -1:
            return
        _mp = SyncConfig.image_field_map
        _mp[str(self.note.mid)] = index
        SyncConfig.image_field_map = _mp

        items = [(f['name'], ord) for ord, f in sorted(self.note._fmap.values())]
        self.options_menu.setup_image_field([i for i, o in items], index)

    def txt_field_changed(self, index):
        if index == -1:
            return
        _mp = SyncConfig.txt_field_map
        _mp[str(self.note.mid)] = index
        SyncConfig.txt_field_map = _mp

        items = [(f['name'], ord) for ord, f in sorted(self.note._fmap.values())]
        self.options_menu.menu_txt_options.setup_txt_field([i for i, o in items], index)

    def qry_field_changed(self, index):
        if index == -1:
            return
        _mp = SyncConfig.qry_field_map
        _mp[str(self.note.mid)] = index
        SyncConfig.qry_field_map = _mp

        items = [(f['name'], ord) for ord, f in sorted(self.note._fmap.values())]
        self.options_menu.setup_query_field([i for i, o in items], index)

    def edit_current(self, toggled):
        SyncConfig.txt_edit_current_after_saving = toggled

    def save_txt(self):
        txt = self.web.selectedText
        if not txt:
            return
        index = self.options_menu.menu_txt_options.default_txt_field_index
        self.note.fields[index] = txt
        self.card.flush()
        self.note.flush()
        if SyncConfig.txt_edit_current_after_saving:
            aqt.dialogs.open("EditCurrent", mw)
        else:
            tooltip(u"Saved image to current card: {}".format(txt), 5000)

    def save_img(self, img):
        """

        :type img: QImage
        :return:
        """
        img = img.convertToFormat(QImage.Format_RGB32, Qt.ThresholdDither | Qt.AutoColor)
        if not self.reviewer:
            return
        fld_index = self.options_menu.selected_img_index
        anki_label = '<img src="{}">'
        fn = "web_qry_{}.jpg".format(uuid4().hex.upper())
        if SyncConfig.append_mode:
            self.note.fields[fld_index] += anki_label.format(fn)
        else:
            self.note.fields[fld_index] = anki_label.format(fn)
        if img.save(fn, 'jpg', UserConfig.image_quality):
            self.note.flush()
            self.card.flush()
            tooltip("Saved image to current card: {}".format(fn), 5000)
