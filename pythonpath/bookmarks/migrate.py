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

import re
from bookmarks.cmdparse import bk_urlencode

OLD_EXT_ID = "mytools.BookmarksMenu"
OLD_COMMAND = "mytools:BookmarskMenu"

OLD_BOOKMARKS_LIB = "BookmarksMenu"
OLD_SHELLCOMMANDS_MODULE = "ShellCommands"

OLD_MACRO_MODULE = OLD_BOOKMARKS_LIB + "." + OLD_SHELLCOMMANDS_MODULE

OLD_MACRO_SHELL = "ShellOpenFile"
OLD_MACRO_EXECUTE = "ExecuteCommand"
OLD_MACRO_OPEN = "OpenWithSpecifiedDirectory"
OLD_MACRO_SAVEAS = "SaveAsWithSpecifiedDirectory"


OLD_ADDTHIS = "mytools_BookmarksMenu.Module4.AddCurrentDocument"
OLD_EDIT = "mytools_BookmarksMenu.Module1.Main"


from bookmarks.bookmark import Separator, Item, Container
from bookmarks.command import BookmarksCommands

class Migration(object):
    """ Migrate from older bookmarks menu. """
    
    SUB_EXP = re.compile("Sub ([^\n]*)$(.*?)^End Sub", re.I + re.M + re.S)
    TWO_ARGS_EXP = re.compile("\"(.*?)\", \"(.*?)\"")
    ONE_ARG_EXP = re.compile("\"(.*?)\"")
    
    
    def __init__(self, ctx):
        self.ctx = ctx
    
    def create_service(self, name, args=None):
        if args:
            return self.ctx.getServiceManager().\
                createInstanceWithArgumentsAndContext(name, args, self.ctx)
        else:
            return self.ctx.getServiceManager().\
                createInstanceWithContext(name, self.ctx)
    
    def check(self):
        """ To find older bookmarks in the menu. """
        self.config_supplier = self.create_service(
            "com.sun.star.ui.ModuleUIConfigurationManagerSupplier")
        manager = self.config_supplier.getUIConfigurationManager(
            "com.sun.star.text.TextDocument")
        self.menu_settings = manager.getSettings(
            "private:resource/menubar/menubar", False)
        
        self.container = self.find_bookmarks(self.menu_settings)
        return not self.container is None
    
    def migrate(self):
        """ Starting to migrate and generate items. """
        self.macro = None
        self.macros = None
        self.commands = BookmarksCommands()
        self.load_macro()
        self.parse_macro()
        items = self.convert_item(self.container)
        return items
    
    def find_bookmarks(self, settings):
        """ Find older bookmarks top menu. """
        for i in range(self.menu_settings.getCount()):
            item = self.menu_settings.getByIndex(i)
            command, label, type, container = self.read_item(item)
            if command == OLD_COMMAND:
                return item
    
    def read_item(self, item):
        """ Get velue from menu item. """
        label = ""
        command = ""
        container = None
        type = None
        for value in item:
            if value.Name == "CommandURL":
                command = value.Value
            elif value.Name == "ItemDescriptorContainer":
                container = value.Value
            elif value.Name == "Label":
                label = value.Value
            elif value.Name == "Type":
                type = value.Value
            #else:
            #   print(value.Name)
            #print(value.Name)
        return command, label, type, container
    
    def load_macro(self):
        """ Load old bookmarks macro generated automatically. """
        lib = self.get_macro_lib()
        if lib:
            if lib.hasByName(OLD_SHELLCOMMANDS_MODULE):
                self.macro = lib.getByName(OLD_SHELLCOMMANDS_MODULE)
    
    def get_macro_lib(self):
        """ Load macro source from application library. """
        libs = self.create_service(
            "com.sun.star.script.ApplicationScriptLibraryContainer")
        if libs.hasByName(OLD_BOOKMARKS_LIB):
            libs.loadLibrary(OLD_BOOKMARKS_LIB)
            return libs.getByName(OLD_BOOKMARKS_LIB)
        return None
    
    def parse_macro(self):
        """ Split macro in each subroutine. """
        if self.macro:
            macros = {}
            for m in self.SUB_EXP.finditer(self.macro):
                if m:
                    macros[m.group(1)] = m.group(2)
            self.macros = macros
    
    def convert_item(self, item):
        """ Convert entry to bookmarks item in new format. """
        command, label, type, container = self.read_item(item)
        if container:
            command, label, type, container = self.read_item(item)
            c = Container(label, "")
            children = c.children
            for i in range(container.getCount()):
                _child = self.convert_item(container.getByIndex(i))
                if _child:
                    children.append(_child)
            return c
        elif type == 0:
            try:
                return Item(label, "", self.convert_command(command))
            except:
                return None
        else:
            return Separator()
    
    def convert_command(self, command):
        """ Convert old command to new format. """
        if command.startswith(BookmarksCommands.PROTOCOL_SCRIPT):
            # check ShellCommands
            return self.convert_macro(command)
        
        elif command.startswith(BookmarksCommands.PROTOCOL_MACRO):
            return command
        
        elif command.startswith(".uno"):
            if command.startswith(".uno:Open"):
                parts = command.split("?", 1)
                if len(parts) == 2:
                    queries = [i.split("=") for i in parts[1].split("&")]
                    d = {}
                    d["type"] = "document"
                    for key, value in queries:
                        if key == self.commands.QUERY_NAME_URL:
                            d["path"] = value
                    return self.commands.generate_command(d)
            
            elif command.find("?") >= 0:
                parts = command.split("?", 1)
                if len(parts) == 2:
                    queries = [i.split("=") for i in parts[1].split("&")]
                    q = bk_urlencode(dict(queries))
                    return parts[0] + q
            return command
    
    def convert_macro(self, command):
        """ Convert macro entry with data from macros. """
        parts = command.split(":", 1)
        if len(parts) == 2:
            parts = parts[1].split("?", 1)
            if len(parts) == 2:
                path = parts[0]
                if path in (OLD_ADDTHIS, OLD_EDIT):
                    raise Exception("This item is ignored: %s" % command)
                elif path.startswith(OLD_MACRO_MODULE):
                    _path = path[len(OLD_MACRO_MODULE)+1:]
                    try:
                        return self.generate_command_from_macro(
                                            _path, self.macros[_path])
                    except:
                        pass
        return command
    
    def generate_command_from_macro(self, path, macro):
        """ Generate command from type and its macro. """
        if path.startswith(OLD_MACRO_SHELL):
            path, args = self.get_arguments_pair(OLD_MACRO_SHELL, macro)
            d = {"type": "something", "flag": "file"}
            d["path"] = path
            return self.commands.generate_command(d)
        
        elif path.startswith(OLD_MACRO_EXECUTE):
            prog, args = self.get_arguments_pair(OLD_MACRO_EXECUTE, macro)
            if prog in ("xdg-open", "open", "kfmclient openURL", "explorer.exe"):
                d = {"type": "something", "flag": "folder"}
                d["path"] = args
            else:
                d = {"type": "program"}
                d["path"] = prog
                d["arguments"] = args
            return self.commands.generate_command(d)
        
        elif path.startswith(OLD_MACRO_OPEN):
            path = self.get_argument(OLD_MACRO_OPEN, macro)
            d = {"type": "special", "flag": "open_from_folder"}
            d["path"] = path
            return self.commands.generate_command(d)
        
        elif path.startswith(OLD_MACRO_SAVEAS):
            path = self.get_argument(OLD_MACRO_SAVEAS, macro)
            d = {"type": "special", "flag": "saveas_into_folder"}
            d["path"] = path
            return self.commands.generate_command(d)
    
    def get_arguments_pair(self, name, macro):
        """ Get arguments from macro. """
        index = macro.find(name)
        if index >= 0:
            found = macro[index+len(name):]
            m = self.TWO_ARGS_EXP.search(found)
            if m:
                return m.group(1), m.group(2)
        return "", ""
    
    def get_argument(self, name, macro):
        """ Get an argument from macro. """
        index = macro.find(name)
        if index >= 0:
            found = macro[index+len(name):]
            m = self.ONE_ARG_EXP.search(found)
            if m:
                return m.group(1)
        return ""

