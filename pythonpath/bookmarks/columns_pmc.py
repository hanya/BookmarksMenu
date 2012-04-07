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
    return ShownColumnsPopupMenu(ctx, args)

import unohelper

from com.sun.star.awt import XMenuListener

from bookmarks import EXT_ID
import bookmarks.base

class ShownColumnsPopupMenu(unohelper.Base, 
    bookmarks.base.PopupMenuControllerBase, XMenuListener):
    """ Pop-up controller for columns menu on edit window. """
    
    from bookmarks import SHOWN_COLUMNS_IMPLE_NAME as IMPLE_NAME, \
        SERVICE_NAMES
    
    def __init__(self, ctx, args):
        self.ctx = ctx
        self.valid = False
        self.frame = None
        self.popup = None
        self.labels = ("Name", "Tags", "Value", "Description")
        from bookmarks import RES_DIR, RES_FILE
        from bookmarks.tools import get_current_resource
        res = get_current_resource(ctx, RES_DIR, RES_FILE)
        self.translated = [res.get(label, label) 
                            for label in self.labels]
        self.initialize(args)
    
    # XInitialization
    def initialize(self, args):
        for arg in args:
            if arg.Name == "Frame":
                self.frame = arg.Value
            elif arg.Name == "CommandURL":
                self.command = arg.Value
            elif arg.Name == "ModuleName":
                self.valid = arg.Value == EXT_ID
    
    # XPopupMenuController
    def setPopupMenu(self, popup):
        if self.valid:
            self.popup = popup
            self.fill_menu(popup)
            popup.addMenuListener(self)
            self.update_state()
        
    def updatePopupMenu(self):
        if self.valid:
            self.update_state()
    
    # XMenuListener
    def activate(self, ev): pass
    def deactivate(self, ev): pass
    def highlight(self, ev): pass
    def select(self, ev):
        if self.valid:
            command = ev.Source.getCommand(ev.MenuId)
            view_settings = self.frame.getController().getViewSettings()
            if view_settings:
                name = "Show" + command
                view_settings.setPropertyValue(
                    name, 
                    not view_settings.getPropertyValue(name))
    
    def update_state(self):
        view_settings = self.frame.getController().getViewSettings()
        if view_settings:
            self.popup.checkItem(2, 
                view_settings.getPropertyValue("ShowTags"))
            self.popup.checkItem(3, 
                view_settings.getPropertyValue("ShowValue"))
            self.popup.checkItem(4, 
                view_settings.getPropertyValue("ShowDescription"))
    
    def fill_menu(self, popup):
        for i, label in enumerate(self.labels):
            popup.insertItem(i + 1, self.translated[i], 1, i)
            popup.setCommand(i + 1, label)
        # Name is always True and disabled to choose
        popup.checkItem(1, True)
        popup.enableItem(1, False)

