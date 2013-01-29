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
    return BookmarksPopup.create(ctx, *args)

import unohelper

from com.sun.star.awt import XMenuListener
from com.sun.star.beans import PropertyValue

from bookmarks import \
    CONFIG_NODE_CONTROLLERS, NAME_NAME
from bookmarks.tools import get_config, \
    get_module_name, get_popup_names
import bookmarks.base
from bookmarks import TAG_POPUP_IMPLE_NAME


def load_controller_name(ctx, command):
    """ Get controller specific settings. """
    config = get_config(ctx, CONFIG_NODE_CONTROLLERS)
    if config.hasByName(command):
        return config.getByName(command).getPropertyValue(NAME_NAME)
    return ""


class BookmarksPopupBase(unohelper.Base, 
    bookmarks.base.PopupMenuControllerBase, XMenuListener):
    
    OPEN_ALL_ID = -0xff
    
    def __init__(self, ctx, args):
        self.ctx = ctx
        self._res = None
        self.commands = None
        self.manager = None
        self.sub_popups = {}
        self.popup_menus = get_popup_names(self.ctx)
        self.controllers = {}
        self.command = None
        self.frame = None
        self.menu = None
        self.last_checked = 0
        
        from bookmarks.resource import CurrentStringResource
        self.res = CurrentStringResource.get(ctx)
        self._label_open_all = self.res.get("Open ~All")
    
    def update_last_checked(self):
        """ Read last modified time from the manager. """
        if self.manager:
            self.last_checked = self.manager.get_last_modified()
    
    # XInitialization
    def initialize(self, args):
        for arg in args:
            if arg.Name == "Frame":
                self.frame = arg.Value
            elif arg.Name == "CommandURL":
                self.command = arg.Value
        self.init()
    
    def init(self): pass
    
    # XPopupMenuController
    def setPopupMenu(self, popup):
        self.menu = popup
        self.prepare_menu()
    
    # XMenuListener
    def activate(self, ev): pass
    def deactivate(self, ev): pass
    
    def highlight(self,ev):
        self.itemHighlighted(ev)
    
    def select(self, ev):
        self.itemSelected(ev)
    
    # since AOO 4.0
    def itemActivated(self, ev): pass
    def itemDeactivated(self, ev): pass
    
    def itemSelected(self, ev):
        command = ev.Source.getCommand(ev.MenuId)
        if command:
            self.execute_command(command)
        
        elif ev.MenuId == self.OPEN_ALL_ID:
            popup = ev.Source
            for pos in range(popup.getItemCount()):
                command = popup.getCommand(popup.getItemId(pos))
                # ignore popup
                if command and not command in self.popup_menus:
                    try:
                        self.execute_command(command)
                    except:
                        pass
    
    def itemHighlighted(self, ev):
        id = ev.MenuId
        try:
            item = self.sub_popups[id]
            popup = ev.Source.getPopupMenu(id)
            if popup:
                if item.is_container():
                    if not popup.getItemCount():
                        self.fill_popup(popup, self.sub_popups[id])
                        popup.addMenuListener(self)
                elif item.get_command_only() in self.popup_menus and \
                    (item.get_command().startswith("mytools.frame") or 
                    not item.has_arguments()):
                    self.treat_popup(item, popup)
        except:
            pass
    
    def fill_popup(self, popup, container, open_all=True):
        """ Fill popupmenu from container. """
        has_item = False
        for position, child in enumerate(container.get_children()):
            id = child.get_id()
            if child.is_item():
                command = child.get_command_only()
                popup.insertItem(
                    id, child.get_name(), 0, position)
                popup.setCommand(id, child.get_command())
                desc = child.get_description()
                if desc:
                    popup.setTipHelpText(id, desc)
                
                if command in self.popup_menus and \
                   (command.startswith("mytools.frame") or \
                    not child.has_arguments()):
                    sub_popup = self.create_sub_popup()
                    popup.setPopupMenu(id, sub_popup)
                    self.sub_popups[id] = child
                has_item = True
            
            elif child.is_container():
                popup.insertItem(
                    id, child.get_name(), 0, position)
                desc = child.get_description()
                if desc:
                    popup.setTipHelpText(id, desc)
                sub_popup = self.create_sub_popup()
                popup.setPopupMenu(id, sub_popup)
                self.sub_popups[id] = child
            
            elif child.is_separator():
                popup.insertSeparator(position)
        
        if open_all and has_item:
            n = popup.getItemCount()
            popup.insertSeparator(n)
            popup.insertItem(-0xff, self._label_open_all, 0, n+1)
    
    def prepare_menu(self, clear=False, open_all=True):
        """ Fill menu with entries. """
        try:
            if clear:
                self.menu.clear()
                self.sub_popups.clear()
                self.controllers.clear()
            container = self.get_container()
            if container:
                self.fill_popup(self.menu, container, open_all)
            if not clear:
                self.menu.addMenuListener(self)
        except Exception as e:
            print(e)
        self.update_last_checked()
    
    def get_container(self):
        pass
    
    def treat_popup(self, item, popup):
        """ Create registered popup menu. """
        command = item.get_command()
        name = self.popup_menus[item.get_command_only()]
        try:
            controller = self.controllers.get(item.get_id(), None)
            if not controller:
                args = (
                    PropertyValue("ModuleName", -1, get_module_name(self.ctx, self.frame), 1), 
                    PropertyValue("Frame", -1, self.frame, 1), 
                    PropertyValue("CommandURL", -1, command, 1), 
                )
                controller = self.ctx.getServiceManager().\
                    createInstanceWithArgumentsAndContext(name, tuple(args), self.ctx)
                if name == TAG_POPUP_IMPLE_NAME:
                    controller.set_controller(self)
                controller.setPopupMenu(popup)
                self.controllers[item.get_id()] = controller
            controller.updatePopupMenu()
        except Exception as e:
            print(e)
    
    def message(self, message, title, error=False):
        """ Shows message. """
        from bookmarks.tools import show_message
        box_type = "messbox"
        if error:
            box_type = "warningbox"
        show_message(
                self.ctx, 
                self.frame, 
                self.res.get(message, message), 
                self.res.get(title, title), 
                box_type)
    
    def execute_command(self, command):
        """ Execute bookmark command. """
        try:
            self.commands.execute_command(command)
        except Exception as e:
            self.message(str(e), "Error")


class BookmarksPopup(BookmarksPopupBase):
    """ Pop-up controller for bookmarks menu. """
    
    def create(ctx, *args):
        return BookmarksPopup(ctx, args)
    create = staticmethod(create)
    
    from bookmarks import IMPLE_NAME, SERVICE_NAMES
    
    def __init__(self, ctx, args):
        BookmarksPopupBase.__init__(self, ctx, args)
        self.has_location = False
        self.initialize(args)
    
    def disposing(self, ev):
        for v in self.controllers.values():
            try:
                if hasattr(v, "dispose"):
                    v.dispose()
            except:
                pass
    
    def init(self):
        import bookmarks.manager
        import bookmarks.command
        
        self.manager = bookmarks.manager.BookmarksManager.get(
            self.ctx, 
            self.command, 
            load_controller_name(self.ctx, self.command)
        )
        self.update_last_checked()
        self.has_location = self.check_has_location()
        self.commands = bookmarks.command.BookmarksCommandExecutor(
                self, self.ctx, self.frame, self.command)
    
    def get_container(self):
        return self.manager.get_root()
    
    def check_has_location(self):
        if self.frame:
            controller = self.frame.getController()
            if controller:
                model = controller.getModel()
                if model and hasattr(model, "hasLocation"):
                    return model.hasLocation()
        return False
    
    # XPopupMenuController
    def setPopupMenu(self, popup):
        self.menu = popup
        self.prepare_menu(open_all=False)
    
    def updatePopupMenu(self):
        if self.manager.is_modified_since(self.last_checked):
            self.prepare_menu(clear=True, open_all=False)
        if not self.has_location:
            self.has_location = self.check_has_location()

