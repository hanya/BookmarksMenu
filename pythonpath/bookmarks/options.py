#  Copyright 2012 Tsutomu Uchino
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

def create(ctx, *args):
    return OptionsPageHandler(ctx, args)

import uno
import unohelper

from com.sun.star.awt import XContainerWindowEventHandler

from bookmarks.dialog import FileOpenDialog, FolderDialog
from bookmarks.dialogs import ActionListenerBase
from bookmarks.base import ServiceInfo
from bookmarks.tools import get_config, get_current_resource
from bookmarks import \
    CONFIG_NODE_SETTINGS, \
    NAME_WEB_BROWSER, NAME_FILE_MANAGER, NAME_OPEN_COMMAND, \
    NAME_USE_CUSTOM_WEB_BROWSER, \
    NAME_USE_CUSTOM_FILE_MANAGER, NAME_USE_CUSTOM_OPEN_COMMAND, \
    NAME_DATA_URL, NAME_BACKUP_DIRECTORY, \
    RES_DIR, RES_FILE

class OptionsPageHandler(unohelper.Base, 
        XContainerWindowEventHandler, ServiceInfo):
    
    from bookmarks import OPTION_PAGE_HANDLER_IMPLE_NAME as IMPLE_NAME
    SERVICE_NAMES = (IMPLE_NAME,)
    
    class ButtonListener(ActionListenerBase):
        def actionPerformed(self, ev):
            self.act.button_pushed(ev.Source)
    
    def __init__(self, ctx, args):
        self.ctx = ctx
        self.dialog = None
        self.res = get_current_resource(ctx, RES_DIR, RES_FILE)
    
    def _(self, name):
        return self.res.get(name, name)
    
    # XContainerWindowEventHandler
    def getSupportedMethodNames(self):
        return ("external_event", )
    
    def callHandlerMethod(self, window, ev, name):
        if name == "external_event":
            self.handle(window, ev)
    
    def handle(self, dialog, ev):
        self.dialog = dialog
        if ev == "ok":
            self.confirm()
        elif ev == "back":
            self.init()
        elif ev == "initialize":
            self.init(first_time=True)
        return True
    
    def get(self, name):
        return self.dialog.getControl(name)
    
    def get_text(self, name):
        return self.get(name).getModel().Text
    
    def set_text(self, name, text):
        if text is None:
            text = ""
        self.get(name).getModel().Text = text
    
    def get_state(self, name):
        return self.get(name).getModel().State
    
    def set_state(self, name, state):
        if state is None:
            state = False
        self.get(name).getModel().State = {True: 1, False: 0}[state]
    
    def translate_labels(self):
        _ = self._
        dialog_model = self.dialog.getModel()
        dialog_model.Title = _(dialog_model.Title)
        for control in self.dialog.getControls():
            model = control.getModel()
            if hasattr(model, "Label"):
                model.Label = _(model.Label)
    
    def to_system_path(self, url):
        """ Convert if the url specify on the local file system. """
        try:
            if url.startswith("file:"):
                return uno.fileUrlToSystemPath(url)
        except:
            return url
    
    def to_file_url(self, path):
        """ Convert if the path specifies local file. """
        try:
            return uno.systemPathToFileUrl(path)
        except:
            return path
    
    def init(self, first_time=False):
        getattr(self, "init_" + self.dialog.getModel().Name)(first_time)
    
    def init_Options(self, first_time=False):
        try:
            config = get_config(self.ctx, CONFIG_NODE_SETTINGS)
            cp = config.getPropertyValue
            self.set_text("edit_webbrowser", cp(NAME_WEB_BROWSER))
            self.set_text("edit_filemanager", cp(NAME_FILE_MANAGER))
            self.set_text("edit_opencommand", cp(NAME_OPEN_COMMAND))
            self.set_state("check_webbrowser", cp(NAME_USE_CUSTOM_WEB_BROWSER))
            self.set_state("check_filemanager", cp(NAME_USE_CUSTOM_FILE_MANAGER))
            self.set_state("check_opencommand", cp(NAME_USE_CUSTOM_OPEN_COMMAND))
            if first_time:
                self.translate_labels()
                listener = self.ButtonListener(self)
                self.get("btn_webbrowser").addActionListener(listener)
                self.get("btn_filemanager").addActionListener(listener)
                self.get("btn_opencommand").addActionListener(listener)
        except Exception, e:
            print(e)
    
    def init_OptionsData(self, first_time=False):
        try:
            self.model = self.get_current_bookmarks_model()
            if self.model:
                data_url = self.model.getPropertyValue(NAME_DATA_URL)
                backup_dir = self.model.getPropertyValue(NAME_BACKUP_DIRECTORY)
                self.set_text("edit_data", self.to_system_path(data_url))
                self.set_text("edit_backup", self.to_system_path(backup_dir))
                if first_time:
                    listener = self.ButtonListener(self)
                    self.get("btn_data").addActionListener(listener)
                    self.get("btn_backup").addActionListener(listener)
            else:
                self.dialog.setEnable(False)
            if first_time:
                self.translate_labels()
        except Exception, e:
            print(e)
    
    def get_current_bookmarks_model(self):
        from bookmarks import DOCUMENT_IMPLE_NAME
        import bookmarks.tools
        desktop = bookmarks.tools.get_desktop(self.ctx)
        model = desktop.getCurrentComponent()
        try:
            if model.getIdentifier() == DOCUMENT_IMPLE_NAME:
                return model
        except:
            pass
    
    def confirm(self):
        getattr(self, "confirm_" + self.dialog.getModel().Name)()
    
    def confirm_Options(self):
        config = get_config(self.ctx, CONFIG_NODE_SETTINGS, True)
        cs = config.setPropertyValue
        cs(NAME_WEB_BROWSER, self.get_text("edit_webbrowser"))
        cs(NAME_FILE_MANAGER, self.get_text("edit_filemanager"))
        cs(NAME_OPEN_COMMAND, self.get_text("edit_opencommand"))
        cs(NAME_USE_CUSTOM_WEB_BROWSER, bool(self.get_state("check_webbrowser")))
        cs(NAME_USE_CUSTOM_FILE_MANAGER, bool(self.get_state("check_filemanager")))
        cs(NAME_USE_CUSTOM_OPEN_COMMAND, bool(self.get_state("check_opencommand")))
        config.commitChanges()
    
    def confirm_OptionsData(self):
        if self.model:
            data_url = self.to_file_url(self.get_text("edit_data"))
            backup_dir = self.to_file_url(self.get_text("edit_backup"))
            
            _data_url = self.model.getPropertyValue(NAME_DATA_URL)
            _backup_url = self.model.getPropertyValue(NAME_BACKUP_DIRECTORY)
            if data_url != _data_url:
                self.model.setPropertyValue(NAME_DATA_URL, data_url)
            if backup_dir != _backup_url:
                self.model.setPropertyValue(NAME_BACKUP_DIRECTORY, backup_dir)
            
            if data_url != _data_url:
                from bookmarks.tools import show_message
                show_message(
                    self.ctx, 
                    self.dialog.getPeer(), 
                    self._("The change of bookmarks file is enabled after restarting the office."), 
                    "", 
                    "infobox"
                )
    
    def button_pushed(self, control):
        if control == self.get("btn_backup"):
            result = FolderDialog(self.ctx, self.res).execute()
        else:
            result = FileOpenDialog(self.ctx, self.res).execute()
        if result:
            path = self.to_system_path(result)
            name = None
            if control == self.get("btn_webbrowser"):
                name = "edit_webbrowser"
            elif control == self.get("btn_filemanager"):
                name = "edit_filemanager"
            elif control == self.get("btn_opencommand"):
                name = "edit_opencommand"
            elif control == self.get("btn_data"):
                name = "edit_data"
            elif control == self.get("btn_backup"):
                name = "edit_backup"
            
            if name:
                self.set_text(name, path)

