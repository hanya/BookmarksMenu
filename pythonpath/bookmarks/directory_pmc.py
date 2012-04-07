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
    return DirectoryPopup.create(ctx, *args)

import time
import unohelper
from bookmarks.cmdparse import bk_parse_qs
try:
    set()
except:
    from sets import Set as set
from os.path import basename
from fnmatch import filter as fnmatch_filter

from uno import fileUrlToSystemPath as unquote
from com.sun.star.awt import XMenuListener

import bookmarks.base

class DirectoryPopup(unohelper.Base, 
    bookmarks.base.PopupMenuControllerBase, XMenuListener):
    """ Shows directory structure and its file contents as menu entries. """
    
    def create(ctx, *args):
        return DirectoryPopup(ctx, args)
    create = staticmethod(create)
    
    from bookmarks import DIRECTORY_POPUP_IMPLE_NAME as IMPLE_NAME, \
        SERVICE_NAMES
    
    ARG_URL = "URL:string"
    ARG_FILE_FILTER = "Filter:string"
    ARG_UPDATE = "Update:int"
    ARG_HIDDEN = "Hidden:boolean"
    
    FILTER_SEP = ";"
    
    RELOAD = 30 #* 3
    
    OPEN_ALL_ID = -0xff
    
    def __init__(self, ctx, args):
        import bookmarks.command
        self.ctx = ctx
        self.base_url = None
        self.filter = None
        self.update = self.RELOAD
        self.last_read = 0
        self.hidden = False
        self.executor = bookmarks.command.DispatchExecutor(self.ctx)
        self.valid = False
        self.initialize(args)
        sfa = ctx.getServiceManager().createInstanceWithContext(
            "com.sun.star.ucb.SimpleFileAccess", self.ctx)
        if sfa.exists(self.base_url) and sfa.isFolder(self.base_url):
            self.sfa = sfa
            self.valid = True
        
        from bookmarks.resource import CurrentStringResource
        res = CurrentStringResource.get(ctx)
        self._label_open_all = res.get("Open ~All")
    
    # XInitialization
    def initialize(self, args):
        for arg in args:
            if arg.Name == "Frame":
                self.frame = arg.Value
            elif arg.Name == "CommandURL":
                self.command = arg.Value
        self.parse_command_url(self.command)
    
    def parse_command_url(self, command):
        """ Parse arguments of the command. """
        parts = command.split("?", 1)
        if len(parts) == 2:
            qs = bk_parse_qs(parts[1])
            def get_value(name):
                try:
                    return qs[name]
                except:
                    return ""
            
            if self.ARG_URL in qs:
                base_url = get_value(self.ARG_URL)
                if not base_url.endswith("/"):
                    base_url += "/"
                self.base_url = base_url
            if self.ARG_FILE_FILTER in qs:
                filter = get_value(self.ARG_FILE_FILTER)
                if filter:
                    self.filter = filter.split(self.FILTER_SEP)
            if self.ARG_HIDDEN in qs:
                try:
                    self.hidden = get_value(self.ARG_HIDDEN).lower() == "true"
                except:
                    pass
            if self.ARG_UPDATE in qs:
                try:
                    self.update = int(get_value(self.ARG_UPDATE))
                except:
                    pass
    
    def update_last_read(self):
        """ Update last read time with now. """
        self.last_read = time.time()
    
    def open_document(self, url):
        """ Open document by dispatch call. """
        try:
            self.executor.dispatch(
                self.frame, 
                self.executor.COMMAND_OPEN_DOCUMENT_WITH_URL % url)
        except:
            pass
    
    # XPopupMenuController
    def setPopupMenu(self, popup):
        self.menu = popup
        if self.valid:
            self.prepare_menu()
    
    def updatePopupMenu(self):
        if self.valid:
            self.prepare_menu(True)
    
    # XMenuListener
    def activate(self, ev): pass
    def deactivate(self, ev): pass
    def select(self, ev):
        command = ev.Source.getCommand(ev.MenuId)
        if command:
            self.open_document(command)
        
        elif ev.MenuId == self.OPEN_ALL_ID:
            popup = ev.Source
            for pos in range(popup.getItemCount()):
                command = popup.getCommand(popup.getItemId(pos))
                if command:
                    # ToDo open in each thread
                    self.open_document(command)
    
    def highlight(self, ev):
        menu = ev.Source
        id = ev.MenuId
        command = menu.getCommand(id)
        popup = menu.getPopupMenu(id)
        if not popup.getItemCount():
            try:
                self.fill_menu(popup, command)
                popup.addMenuListener(self)
            except:
                self.menu.insertItem(1, "ERROR", 0, 0)
                self.menu.enableItem(1, False)
    
    def prepare_menu(self, clear=False):
        """ Setting up the menu. """
        if time.time() < self.last_read + self.update:
            return
        try:
            if clear:
                self.menu.clear()
            self.fill_menu(self.menu, self.base_url)
            self.update_last_read()
            if not clear:
                self.menu.addMenuListener(self)
        except Exception, e:
            print(e)
    
    def fill_menu(self, popup, url):
        """ Fill menu entries with folder contents. """
        sfa = self.sfa
        base_url = url
        if not base_url.endswith("/"):
            base_url += "/"
        names = self.sfa.getFolderContents(base_url, True)
        if not self.hidden:
            names = set([name for name in names if not sfa.isHidden(name)])
        else:
            names = set(names)
        folders = set([name for name in names if sfa.isFolder(name)])
        files = names - folders
        if self.filter:
            _files = set()
            for _f in self.filter:
                _files.update(fnmatch_filter(files, _f))
            files = _files
        id = 1
        for name in folders:
            popup.insertItem(id, unquote(basename(name)), 0, id -1)
            popup.setCommand(id, name)
            popup.setPopupMenu(id, self.create_sub_popup())
            id += 1
        pos = len(folders)
        _files = list(files)
        _files.sort()
        for name in _files:
            popup.insertItem(id, unquote(basename(name)), 0,  id -1)
            popup.setCommand(id, name)
            id += 1
        
        if len(_files):
            n = popup.getItemCount()
            popup.insertSeparator(n)
            popup.insertItem(self.OPEN_ALL_ID, self._label_open_all, 0, n+1)

