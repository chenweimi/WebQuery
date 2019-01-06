import json
import re
from functools import partial
from uuid import uuid4

from PyQt5.QtGui import QImage
from PyQt5.QtWebEngineWidgets import QWebEngineProfile

import aqt.models
# noinspection PyArgumentList
from anki.lang import _
from aqt import *
from aqt.reviewer import Reviewer
from aqt.utils import openHelp, showInfo
from aqt.utils import restoreGeom
from aqt.utils import tooltip
from .Config import *
from .Const import *
from .kkLib import getTrans

trans = lambda s: getTrans(s, TRANS)
# region Globals
global have_setup
have_setup = False
_TOOL_NAME = trans("Web Query")


# endregion


class _ImageLabel(QLabel):
    cropMode = True
    mouse_released = pyqtSignal()
    canceled = pyqtSignal(bool)

    def __init__(self):
        super(_ImageLabel, self).__init__()
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


class _Page(QWebEnginePage):
    has_selector_contents = pyqtSignal(bool)
    image_rect_fire = pyqtSignal(list)
    fire_tag_hover = pyqtSignal(str)

    class Bridge(QObject):

        @pyqtSlot(list)
        def onImageRect(self, rect):
            self.fire_image_rect(rect)

        @pyqtSlot(str)
        def onMouseHover(self, tag_type):
            self.fire_tag_hovered(tag_type)

    def __init__(self, parent, keyword=None, provider_url=''):
        super(_Page, self).__init__(parent)
        self.clicked_img_url = None
        self.keyword = keyword
        self._provider_url = provider_url

        # profile set
        self.profile.setHttpUserAgent(self.agent)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)

        # attribute
        self.settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.settings.setAttribute(QWebEngineSettings.ScreenCaptureEnabled, True)
        self.settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        self.settings.setAttribute(QWebEngineSettings.AllowGeolocationOnInsecureOrigins, True)

        # set scripts

        self._channel = QWebChannel(self)
        self._bridge = _Page.Bridge()
        self._bridge.fire_image_rect = self.image_rect_fire.emit
        self._bridge.fire_tag_hovered = self.fire_tag_hover.emit
        self._channel.registerObject("pyjs", self._bridge)
        self.setWebChannel(self._channel)

        js = QFile(':/qtwebchannel/qwebchannel.js')
        assert js.open(QIODevice.ReadOnly)
        js = bytes(js.readAll()).decode('utf-8')

        js_init = js + """
            // Right-Click Mode
            document.oncontextmenu = function (e) {
                new QWebChannel(qt.webChannelTransport, function (channel) {
                        window.pyjs = channel.objects.pyjs;
            
                        let el = e.target;
                        if (el.tagName === "IMG") {
                            let el_rect = el.getBoundingClientRect();
                            pyjs.onImageRect([el_rect.left, el_rect.top,
                                el.width, el.height]);
                        }
                    }
                );
            };
            
            document.onmouseover = function (e) {
                new QWebChannel(qt.webChannelTransport, function (channel) {
                        window.pyjs = channel.objects.pyjs;
            
                        let el = e.target;
                        pyjs.onMouseHover(el.tagName);
                    }
                );
            };
        
        """
        scripts = QWebEngineScript()
        scripts.setSourceCode(js_init)
        scripts.setWorldId(QWebEngineScript.MainWorld)
        scripts.setInjectionPoint(QWebEngineScript.DocumentReady)
        scripts.setRunsOnSubFrames(False)
        self.scripts().insert(scripts)

    @property
    def agent(self):
        return """
        Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1
        """

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

    @property
    def profile(self):
        """

        :rtype: QWebEngineProfile
        """
        return super(_Page, self).profile()

    @property
    def settings(self):
        return super(_Page, self).settings()

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
        self.loadFinished.connect(self.on_loadFinished)
        super(_Page, self).load(url)

    def on_loadFinished(self, bool):
        if not bool:
            return
        if self.selector:
            def found(html):
                if not html:
                    return
                self.setHtml(html, self.get_url())
                self.has_selector_contents.emit(True)

            self.runJavaScript("$('{}').html()".format(self.selector), found)
            return
        self.has_selector_contents.emit(False)


class _WebView(QWebEngineView):
    element_captured = pyqtSignal(QRect)

    def __init__(self, parent, txt_option_menu):
        super(_WebView, self).__init__(parent)
        self.qry_page = None
        self.txt_option_menu = txt_option_menu

        self.hovered_element_tag_name = None

    def add_query_page(self, page):
        if not self.qry_page:
            self.qry_page = page
            self.setPage(self.qry_page)
            self.qry_page.image_rect_fire.connect(self.on_right_image_corp)
            self.qry_page.fire_tag_hover.connect(lambda tg_name:
                                                 setattr(self, "hovered_element_tag_name", tg_name))

    def load_page(self):
        if self.qry_page:
            self.qry_page.load()

    def contextMenuEvent(self, evt):
        if self.selectedText():
            self.txt_option_menu.set_selected(self.selectedText())
            self.txt_option_menu.exec_(mw.cursor().pos())
        else:
            if self.hovered_element_tag_name != "IMG":
                super(_WebView, self).contextMenuEvent(evt)

    def selectedText(self):
        return self.page().selectedText()

    def on_right_image_corp(self, image_rect):
        if SyncConfig.auto_img_find:
            self.element_captured.emit(QRect(*image_rect))


class TxtOptionsMenu(QMenu):
    default_txt_field_changed = pyqtSignal(int)
    txt_saving = pyqtSignal()
    edit_current = pyqtSignal(bool)

    def __init__(self, parent):

        super(TxtOptionsMenu, self).__init__(trans("TEXT CAPTURE"), parent)
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
        self.options_menu = QMenu(trans("OPTIONS"), self)
        action_open_editor = QAction(trans("Trigger Edit"), self.options_menu)
        action_open_editor.setToolTip("Open editor of current note after saving.")
        action_open_editor.setCheckable(True)
        action_open_editor.setChecked(SyncConfig.txt_edit_current_after_saving)
        action_open_editor.toggled.connect(lambda toggled: self.edit_current.emit(toggled))
        self.options_menu.addAction(action_open_editor)

        self.addMenu(self.options_menu)

    def setup_other_actions(self):
        self.action_save_to_default = QAction(trans("Save Text (T)"), self)
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
                trans("Save to field [{}] (T)").format(self.default_txt_field_index))
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
        super(OptionsMenu, self).__init__(trans("OPTIONS"), parent)

        self.selected_img_index = 1

        # init objects before setting up
        self.menu_img_config = None
        self.menu_txt_options = txt_option_menu
        self.img_field_menu = None
        self.field_action_grp = None
        self.qry_field_menu = None
        self.qry_field_action_grp = None

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
            pix.loadFromData(BYTES_ITEMS)
            icon = QIcon(pix)
            self.qry_field_menu = QMenu(trans("Query Field"), self)
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
            self.menu_img_config = QMenu(trans("IMAGE CAPTURE"), self)
            self.addMenu(self.menu_img_config)

            # region image options
            menu_img_options = QMenu(trans("OPTIONS"), self.menu_img_config)

            action_img_append_mode = QAction(trans("APPEND MODE"), menu_img_options)
            action_img_append_mode.setCheckable(True)
            action_img_append_mode.setToolTip("Append Mode: Check this if you need captured image to be APPENDED "
                                              "to field instead of overwriting it")
            action_img_append_mode.setChecked(SyncConfig.append_mode)

            action_img_auto_save = QAction(trans("Auto Save"), menu_img_options)
            action_img_auto_save.setCheckable(True)
            action_img_auto_save.setToolTip("Auto-Save: If this is checked, image will be saved "
                                            "immediately once completed cropping.")
            action_img_auto_save.setChecked(SyncConfig.auto_save)

            action_right_click_mode = QAction(trans("Right-Click Mode"), menu_img_options)
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
        pix.loadFromData(BYTES_GEAR)
        self.action_open_user_cfg = QAction(trans("User Config"), self)
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
            super(CaptureOptionButton, self).__init__(trans("OPTIONS"), parent)

        # set style
        # self.setFlat(True)
        self.setToolTip("Capture Options")

        self.setMenu(options_menu)
        self.setText(trans("Options"))


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
        super(WebQueryWidget, self).__init__(parent, )

        # all widgets
        self._view = _WebView(self, options_menu.menu_txt_options)
        self._view.element_captured.connect(self.on_web_element_capture)
        self.lable_img_capture = _ImageLabel()
        self.lable_img_capture.mouse_released.connect(self.cropped)
        self.lable_img_capture.canceled.connect(self.crop_canceled)

        self.loading_lb = QLabel()
        self.capture_button = QPushButton(trans('Capture Image (C)'), self)
        self.capture_button.setShortcut(QKeySequence(Qt.Key_C))
        self.capture_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.capture_button.clicked.connect(self.on_capture)

        self.return_button = QPushButton(trans('Return'), self)
        self.return_button.setMaximumWidth(100)
        self.return_button.setShortcut(QKeySequence("ALT+Q"))
        self.return_button.clicked.connect(self.on_view)

        # region Save Image Button and Combo Group
        self.save_img_button = QPushButton(trans('Save (C)'), self)
        self.save_img_button.setShortcut(QKeySequence(Qt.Key_C))
        self.save_img_button.setShortcutEnabled(Qt.Key_C, False)
        self.save_img_button.clicked.connect(self.save_img)

        self.capture_option_btn = CaptureOptionButton(self, options_menu)
        self.capture_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.capture_option_btn.setMaximumWidth(100)
        self.img_btn_grp_ly = QHBoxLayout()
        self.img_btn_grp_ly.setSpacing(2)
        # self.img_btn_grp_ly.addWidget(self.resize_btn)
        self.img_btn_grp_ly.addSpacing(5)
        self.img_btn_grp_ly.addWidget(self.capture_option_btn)
        self.img_btn_grp_ly.addWidget(self.return_button)
        self.img_btn_grp_ly.addWidget(self.save_img_button)
        self.img_btn_grp_ly.addWidget(self.capture_button)

        # endregion

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.loading_lb, alignment=Qt.AlignCenter)
        self.layout.addWidget(self._view, 1)
        self.layout.addWidget(self.lable_img_capture, alignment=Qt.AlignCenter)
        self.layout.addItem(self.img_btn_grp_ly)

        # widget groups
        self.loading_grp = [self.loading_lb]
        self.view_grp = [self._view, self.capture_button, self.capture_option_btn]
        self.capture_grp = [self.lable_img_capture, self.return_button, self.save_img_button, ]
        self.misc_grp = [
            # self.resize_btn
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
        self.mv = None

    def loading_started(self):
        self.loading_lb.setText(trans("<b>Loading ... </b>"))
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
        # self.lable_img_capture.image = QImage(QPixmap.grabWindow(self._view.winId(), rect.x(),
        #                                                          rect.y(), rect.width(), rect.height()))
        self.lable_img_capture.image = QImage(self._view.grab(rect))
        self.lable_img_capture.adjustSize()
        self.cropped()

    def on_capture(self, *args):
        QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))

        self._view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.lable_img_capture.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.lable_img_capture.image = QImage(self._view.grab(self._view.rect()))
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


class ModelDialog(aqt.models.Models):
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
        self.button_tab_visibility = QPushButton(trans("Web Query Tab Visibility"), self)
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
                inner_self.setWindowTitle(trans("Toggle Visibility"))

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
            self.main_menu = QMenu(_TOOL_NAME, mw.form.menuTools)
            action = QAction(self.main_menu)
            action.setText(trans("Toggle WebQuery"))
            action.setShortcut(QKeySequence("ALT+W"))
            self.main_menu.addAction(action)
            action.triggered.connect(self.toggle)
            self.options_menu = OptionsMenu(self.main_menu, TxtOptionsMenu(self.main_menu))
            self.main_menu.addMenu(self.options_menu)
            mw.form.menuTools.addMenu(self.main_menu)

    # region replace mw onNoteTypes
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
        class DockableWithClose(QDockWidget):
            closed = pyqtSignal()

            def __init__(self, title, parent):
                super(DockableWithClose, self).__init__(title, parent)

            def closeEvent(self, evt):
                self.closed.emit()
                QDockWidget.closeEvent(self, evt)

            def resizeEvent(self, evt):
                assert isinstance(evt, QResizeEvent)
                SyncConfig.doc_size = (evt.size().width(),
                                       evt.size().height())
                super(DockableWithClose, self).resizeEvent(evt)
                evt.accept()

            def sizeHint(self):
                return QSize(SyncConfig.doc_size[0], SyncConfig.doc_size[1])

        dock = DockableWithClose(title, mw)
        dock.setObjectName(title)
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
            web.add_query_page(page)
            page.load(self.word)

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
            self.options_menu.setup_image_field(self.note.keys(), image_field)
            self.options_menu.setup_query_field(self.note.keys(), qry_field)
            self.options_menu.menu_txt_options.setup_txt_field(self.note.keys(),
                                                               SyncConfig.txt_field_map.get(str(self.note.mid), 1))
            self.options_menu.img_field_changed.connect(self.img_field_changed)
            self.options_menu.query_field_change.connect(self.qry_field_changed)
            assert isinstance(self.options_menu.menu_txt_options, TxtOptionsMenu)
            self.options_menu.menu_txt_options.txt_saving.connect(self.save_txt)
            self.options_menu.menu_txt_options.edit_current.connect(self.edit_current)
            self.options_menu.menu_txt_options.default_txt_field_changed.connect(self.txt_field_changed)

    def show_doc_widget_children(self, visibility):
        for ch in self._display_widget.children():
            ch.setVisible(visibility)

    def hide_widget(self):
        if self._display_widget:
            self.show_doc_widget_children(False)

    def show_widget(self, from_toggle=False):
        if (not from_toggle) and (not eval(str(self.card.ivl) + UserConfig.load_when_ivl)):
            self.destroy_dock()
            return
        if not self.dock:
            return

        self.show_doc_widget_children(True)

        if self._first_show:
            self._first_show = False

        if not UserConfig.preload:
            self.start_pages()

    def destroy_dock(self):
        if self.dock:
            mw.removeDockWidget(self.dock)
            self.dock.destroy()
            self.dock = None

    def hide(self):
        if self.dock:
            self.dock.setVisible(False)

    def show_dock(self):
        if self.dock:
            self.dock.setVisible(True)

    def ensure_dock(self):
        if ProfileConfig.is_first_webq_run:
            QMessageBox.warning(
                mw, _TOOL_NAME, """
                <p>
                    <b>Welcome !</b>
                </p>
                <p>This is your first run of <EM><b>Web Query</b></EM>, please read below items carefully:</p>
                <ul>
                    <li>
                        Choose proper <em>[Image]</em> field in trans("OPTIONS") button in right dock widget 
                        BEFORE YOU SAVING ANY IMAGES, by default its set to the 2nd
                        field of your current note.
                    </li>
                    <li>
                        You are able to change the <em>[Query]</em> field in trans("OPTIONS") also, 
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
                QMessageBox.warning(mw, _TOOL_NAME, """
                <p><b>v{} Update:</b></p>
                <p>{}</p>
                """.format(cur_log_ver, cur_update_msg))
            ProfileConfig.wq_current_version = self.version

        if not self.dock:
            self.dock = self.add_dock(_TOOL_NAME, )
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

        self.options_menu.setup_image_field(self.note.keys(), index)

    def txt_field_changed(self, index):
        if index == -1:
            return
        _mp = SyncConfig.txt_field_map
        _mp[str(self.note.mid)] = index
        SyncConfig.txt_field_map = _mp

        self.options_menu.menu_txt_options.setup_txt_field(self.note.keys(), index)

    def qry_field_changed(self, index):
        if index == -1:
            return
        _mp = SyncConfig.qry_field_map
        _mp[str(self.note.mid)] = index
        SyncConfig.qry_field_map = _mp
        self.options_menu.setup_query_field(self.note.keys(), index)

    def edit_current(self, toggled):
        SyncConfig.txt_edit_current_after_saving = toggled

    def save_txt(self, ):
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
            tooltip("Saved image to current card: {}".format(txt), 5000)

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
