# region Default Configuration Objects
from .kkLib import MetaConfigObj


class SyncConfig(metaclass=MetaConfigObj):
    class Meta:
        __store_location__ = MetaConfigObj.StoreLocation.MediaFolder
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


class UserConfig(metaclass=MetaConfigObj):
    class Meta:
        __store_location__ = MetaConfigObj.StoreLocation.MediaFolder
        __config_file__ = "webquery_user_cfg.json"

    load_on_question = True
    image_quality = 50
    provider_urls = [
        ("Bing", "http://cn.bing.com/images/search?q=%s&ensearch=1"),
        ("Wiki", "https://en.wikipedia.org/wiki/?search=%s"),
    ]
    preload = True
    load_when_ivl = ">=0"


class ProfileConfig(metaclass=MetaConfigObj):
    class Meta:
        __store_location__ = MetaConfigObj.StoreLocation.Profile

    is_first_webq_run = True
    wq_current_version = ''


class ModelConfig(metaclass=MetaConfigObj):
    class Meta:
        __store_location__ = MetaConfigObj.StoreLocation.MediaFolder
        __config_file__ = "webquery_model_cfg.json"

    visibility = {}  # MID: [ { PROVIDER URL NAME: VISIBLE }]


# endregion