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

import traceback
import uno

from bookmarks.cmdparse import \
    bk_urlencode, bk_parse_qsl, bk_parse_qs, bk_command_parse


from bookmarks import \
            CONFIG_NODE_CONTROLLERS, NAME_NAME

def load_controller_name(ctx, command):
    """ Get controller specific settings. """
    config = get_config(ctx, CONFIG_NODE_CONTROLLERS)
    if config.hasByName(command):
        return config.getByName(command).getPropertyValue(NAME_NAME)
    return ""


class BookmarksCommands(object):
    
    from bookmarks import PROTOCOL_BOOKMARKS, DIRECTORY_POPUP_URI, \
        TAG_POPUP_URI
    
    PROTOCOL_SCRIPT = "vnd.sun.star.script:"
    PROTOCOL_MACRO = "macro:"
    PROTOCOL_FILE = "file:"
    PROTOCOL_COMMAND = ".uno:"
    
    QUERY_NAME_URL = "URL:string"
    QUERY_NAME_PATH = "Path:string"
    QUERY_NAME_FRAME_NAME = "FrameName:string"
    QUERY_NAME_ARGUMENTS = "Arguments:string"
    QUERY_NAME_FILTER = "Filter:string"
    QUERY_NAME_FILTER_NAME = "FilterName:string"
    QUERY_NAME_FOLDER_NAME = "FolderName:string"
    QUERY_NAME_TAG = "Tag:string"
    QUERY_NAME_SUGGESTED_SAVE_AS_NAME = "SuggestedSaveAsName:string"
    
    COMMAND_OPEN_DOCUMENT = ".uno:Open"
    COMMAND_OPEN_DOCUMENT_WITH_URL = ".uno:Open?FrameName:string=_default&URL:string=%s"
    COMMAND_PROGRAM = "%sProgram" % PROTOCOL_BOOKMARKS
    COMMAND_SOMETHING = "%s%%s" % PROTOCOL_BOOKMARKS
    
    COMMAND_OPEN_FROM = ".uno:Open"
    COMMAND_SAVE_AS_INTO = ".uno:SaveAs"
    
    TYPE_DOCUMENT = "document"
    TYPE_COMMAND = "command"
    TYPE_MACRO = "macro"
    TYPE_EDIT = "edit"
    TYPE_PROGRAM = "program"
    TYPE_FILE = "file"
    TYPE_FOLDER = "folder"
    TYPE_WEB = "web"
    TYPE_DIRECTORY_POPUP = "directory_popup"
    TYPE_TAG = "tag"
    
    def bk_parse_qs(text):
        return bk_parse_qs(text)
    
    bk_parse_qs = staticmethod(bk_parse_qs)
    
    def bk_parse_qsl(text):
        return bk_parse_qsl(text)
    
    bk_parse_qsl = staticmethod(bk_parse_qsl)
    
    def bk_urlencode(qs):
        return bk_urlencode(qs)
    
    bk_urlencode = staticmethod(bk_urlencode)
    
    def get_query_value(self, command, name):
        parts = command.split("?", 1)
        if len(parts) == 2:
            qs = self.bk_parse_qs(parts[1])
            if name in qs:
                return qs[name]
        return ""
    
    def bk_command_parse(self, command):
        return bk_command_parse(command)
    
    
    def extract_from_command(self, command):
        """ Extract data from command and detect command type. """
        def get_qs(name):
            try:
                return qs[name]
            except:
                return ""
        
        item_type = ""
        value1 = ""
        value2 = ""
        main, protocol, path, query = self.bk_command_parse(command)
        qs = self.bk_parse_qs(query)
        protocol = protocol + ":"
        
        if protocol == self.PROTOCOL_COMMAND:
            if command.startswith(self.COMMAND_OPEN_DOCUMENT) and \
                qs and self.QUERY_NAME_URL in qs:
                value1 = get_qs(self.QUERY_NAME_URL)
                item_type = self.TYPE_DOCUMENT
                value2 = get_qs(self.QUERY_NAME_FILTER_NAME)
            else:
                value1 = main#path
                value2 = query
                item_type = self.TYPE_COMMAND
        
        elif protocol == self.PROTOCOL_SCRIPT or \
            protocol == self.PROTOCOL_MACRO:
            value1 = command
            item_type = self.TYPE_MACRO
        
        elif protocol == self.PROTOCOL_BOOKMARKS:
            flag = path
            if flag == "Program":
                if qs and self.QUERY_NAME_PATH in qs:
                    value1 = get_qs(self.QUERY_NAME_PATH)
                if self.QUERY_NAME_ARGUMENTS in qs:
                    value2 = get_qs(self.QUERY_NAME_ARGUMENTS)
                item_type = self.TYPE_PROGRAM
            elif flag in ("File", "Folder", "Web"):
                value1 = get_qs(self.QUERY_NAME_PATH)
                item_type = flag.lower()
            elif flag == "Edit" or flag == "AddThis":
                item_type = flag.lower()
            else:
                item_type = "bookmarks"
                value1 = command
        
        elif main == self.TAG_POPUP_URI:
            if qs:
                item_type = self.TYPE_TAG
                value1 = get_qs(self.QUERY_NAME_TAG)
        
        elif main == self.DIRECTORY_POPUP_URI:
            if qs:
                item_type = self.TYPE_DIRECTORY_POPUP
                value1 = get_qs(self.QUERY_NAME_URL)
                value2 = get_qs(self.QUERY_NAME_FILTER)
                
        else:
            value1 = command
        
        return item_type, value1, value2
    
    def extract(self, item):
        """ Extract values from item. """
        item_type, value1, value2 = self.extract_from_command(item.get_command())
        return (item_type, (item.get_name(), item.get_description(), 
                value1, value2, ",".join(item.get_tags())))
    
    def extract_as_row(self, res, item, graphics, show_value=True, show_description=True, show_tags=True):
        """ Command to strings for grid view. """
        def _(name):
            return res.get(name, name)
        
        def get_qs(name):
            try:
                return qs[name]
            except:
                return ""
        command = item.get_command()
        value = ""
        args = ""
        icon = None
        
        main, protocol, path, query = self.bk_command_parse(command)
        qs = self.bk_parse_qs(query)
        protocol = protocol + ":"
        
        if protocol == self.PROTOCOL_COMMAND:
            if qs and main.startswith(self.COMMAND_OPEN_FROM) and \
                self.QUERY_NAME_URL in qs:
                value = get_qs(self.QUERY_NAME_URL)
                icon = graphics["document"]
                try:
                    if value.startswith(self.PROTOCOL_FILE):
                        value = uno.fileUrlToSystemPath(value)
                except:
                    pass
            else:
                value = command
                icon = graphics["command"]
        
        elif protocol == self.PROTOCOL_SCRIPT:
            language = get_qs("language")
            value = "%s: %s" % (language, main[20:])
            icon = graphics["macro"]
        
        elif protocol == self.PROTOCOL_MACRO:
            value = "Basic: %s" % main[6:]
        
        elif protocol == self.PROTOCOL_BOOKMARKS:
            item_type = path.lower()
            if item_type == "program":
                arguments = get_qs(self.QUERY_NAME_ARGUMENTS)
                if arguments:
                    value = "%s: %s, \n%s: %s" % (
                        _("Program"), get_qs(self.QUERY_NAME_PATH), 
                        _("Arguments"), arguments)
                else:
                    value = "%s: %s" % (_("Program"), 
                        get_qs(self.QUERY_NAME_PATH))
            elif item_type == "file":
                # icon indicates its type, isnt enough?
                #value = "%s: %s" % (_("File"), get_qs(self.QUERY_NAME_PATH))
                value = get_qs(self.QUERY_NAME_PATH)
            elif item_type == "folder":
                #value = "%s: %s" % (_("Folder"), get_qs(self.QUERY_NAME_PATH))
                value = get_qs(self.QUERY_NAME_PATH)
            elif item_type == "web":
                #value = "%s: %s" % (_("Web"), get_qs(self.QUERY_NAME_PATH))
                value = get_qs(self.QUERY_NAME_PATH)
            elif item_type == "edit" or item_type == "addthis":
                value = ""
            
            else:
                value = command
            
            icon = graphics[path.lower()]
        
        elif main == self.TAG_POPUP_URI:
            if qs:
                value = get_qs(self.QUERY_NAME_TAG)
            else:
                value = command
            icon = graphics["tag"]
        
        elif main == self.DIRECTORY_POPUP_URI:
            if qs:
                value = get_qs(self.QUERY_NAME_URL)
                try:
                    value = uno.fileUrlToSystemPath(value)
                except:
                    pass
            else:
                value = command
            icon = graphics["directory_popup"]
        
        else:
            value = command
            icon = graphics["command"]
            
        data = [icon, item.get_name()]
        if show_tags:
            data.append(",".join(item.get_tags()))
        if show_value:
            data.append(value)
        if show_description:
            data.append(item.get_description())
        return tuple(data)
    
    def generate_command(self, d):
        """ Generate commmnd from new value. """
        qs = {}
        type = d["type"]
        if type == "document":
            path = d["path"]
            try:
                if not path.startswith(self.PROTOCOL_FILE):
                    path = uno.systemPathToFileUrl(path)
            except:
                pass
            qs[self.QUERY_NAME_FRAME_NAME] ="_default"
            filter = d.get("filter", None)
            main = self.COMMAND_OPEN_DOCUMENT
            qs[self.QUERY_NAME_URL] = path
            if filter:
                qs[self.QUERY_NAME_FILTER_NAME] = filter
        
        elif type == "macro":
            command = d["command"]
        
        elif type == "command":
            if d["arguments"]:
                command = "%s?%s" % (d["command"], d["arguments"])
                #main = d["command"]
            else:
                command = d["command"]
        
        elif type == "program":
            path = d["path"]
            if path.startswith(self.PROTOCOL_FILE):
                try:
                    path = uno.fileUrlToSystemPath(path)
                except:
                    pass
            main = self.COMMAND_PROGRAM
            qs[self.QUERY_NAME_PATH] = path
            qs[self.QUERY_NAME_ARGUMENTS] = d["arguments"]
        
        elif type == "something":
            main = self.COMMAND_SOMETHING % d["flag"].capitalize()
            qs[self.QUERY_NAME_PATH] = d["path"]
        
        elif type == "special":
            flag = d["flag"]
            path = d["path"]
            try:
                path = uno.systemPathToFileUrl(path)
            except:
                pass
            if flag == "open_from_folder":
                main = self.COMMAND_OPEN_FROM
                qs[self.QUERY_NAME_FOLDER_NAME] = path
            
            elif flag == "saveas_into_folder":
                main = self.COMMAND_SAVE_AS_INTO
                qs[self.QUERY_NAME_FOLDER_NAME] = path
            
            elif flag == "directory_popup":
                main = self.DIRECTORY_POPUP_URI
                if "create" in d:
                    qs[self.QUERY_NAME_URL] = d["path"]
                    if "filter" in d:
                        qs[self.QUERY_NAME_FILTER] = d["filter"]
                else:
                    command = d["path"]
        
        elif type == "tag":
            main = self.TAG_POPUP_URI
            qs[self.QUERY_NAME_TAG] = d["tag_name"]
        
        else:
            command = "ERRROR"
        
        if qs:
            command = main + "?" + self.bk_urlencode(qs)
        
        return command


from bookmarks import CONFIG_NODE_SETTINGS, \
    NAME_WEB_BROWSER, NAME_FILE_MANAGER, NAME_OPEN_COMMAND, \
    NAME_USE_CUSTOM_WEB_BROWSER, NAME_USE_CUSTOM_FILE_MANAGER, \
    NAME_USE_CUSTOM_OPEN_COMMAND
from bookmarks.tools import get_config


class DispatchExecutor(BookmarksCommands):
    
    def __init__(self, ctx):
        BookmarksCommands.__init__(self)
        self.ctx = ctx
        self.helper = None
    
    def dispatch(self, frame, command, target_frame="_self", flag=0, args=()):
        if self.helper is None:
            self.helper = self.ctx.getServiceManager().\
                createInstanceWithContext("com.sun.star.frame.DispatchHelper", self.ctx)
        self.helper.executeDispatch(frame, command, target_frame, flag, args)


class IllegalDocumentException(Exception):
    """ This document does not have own location to bookmark. """

import threading

class EditWindowThread(threading.Thread):
    """ Start edit window in another thread. 
        When Bookmarks PMC tries to open edit window through sub entry of 
        the menu, the pmc removed during to create the edit window. 
        It cause crash the office.
    """
    def __init__(self, ctx, command):
        threading.Thread.__init__(self)
        self.ctx = ctx
        self.command = command
    
    def run(self):
        from bookmarks.imple import BookmarksControllerImple
        imple = BookmarksControllerImple.get(self.ctx, self.command)
        imple.move_to_front()


class ExecuteAddThis(DispatchExecutor):
    
    class DocumentNotStoredException(Exception):
        """ This document is not stored. """
        pass
    
    def __init__(self, ctx, frame, command):
        DispatchExecutor.__init__(self, ctx)
        self.frame = frame
        self.command = command
    
    def execute_command(self, command):
        self.dispatch(self.frame, command)
    
    def _get_title(self):
        """ Check the document has valid URL and stored, 
        returns title and filter name. """
        model = None
        try:
            model = self.frame.getController().getModel()
        except:
            pass
        if model is None or not hasattr(model, "getURL"):
            # or not hasattr(model, "hasLocation"):
            raise IllegalDocumentException("Unable to bookmark this document.")
        
        file_url = model.getURL()
        if not file_url:
            self.execute_command(".uno:SaveAs")
            file_url = model.getURL()
            if not file_url:
                raise DocumentNotStoredException("Not stored.")
        
        title = ""
        try:
            if hasattr(model, "getDocumentProperties"):
                props = model.getDocumentProperties()
                if hasattr(props, "Title"):
                    title = props.Title
            if not title:
                title = model.getTitle()
                if title[-4] == ".":
                    title = title[0:-4]
        except:
            pass
        
        filter_name = ""
        try:
            if hasattr(model, "getArgs"):
                args = model.getArgs()
                for arg in args:
                    if arg.Name == "FilterName":
                        filter_name = arg.Value
                        break
        except:
            pass
        
        return file_url, filter_name, title
    
    def run(self):
        try:
            file_url, filter_name, title = self._get_title()
        except Exception as e:
            print(e)
            return
        
        # res, manager
        import bookmarks.manager
        from bookmarks.resource import CurrentStringResource
        res = CurrentStringResource.get(self.ctx)
        
        manager = bookmarks.manager.BookmarksManager.get(
            self.ctx,  self.command, 
            load_controller_name(self.ctx, self.command)
        )
        
        from bookmarks.imple import BookmarksControllerImple
        BookmarksControllerImple.lock(self.command)
        try:
            import bookmarks.dialogs
            bookmarks.dialogs.BookmarkThisDialog(
                self.ctx, res, 
                manager=manager, 
                command=self.command, 
                file_url=file_url, 
                name=title, 
                filter_name=filter_name
            ).execute()
        except Exception as e:
            print(e)
            traceback.print_exc()
        BookmarksControllerImple.unlock(self.command)


class BookmarksCommandExecutor(DispatchExecutor):
    
    OPEN_COMMAND = None
    FILE_MANAGER = None
    WEB_BROWSER = None
    
    def __init__(self, parent, ctx, frame, command):
        DispatchExecutor.__init__(self, ctx)
        self.parent = parent
        self.frame = frame
        self.command = command
        self.executor = None
        env = self.detect_env()
        self.is_win32 = env == "win32"
        
        self.load_config()
        
        c = self.__class__
        if c.OPEN_COMMAND is None or c.FILE_MANAGER is None or c.WEB_BROWSER is None:
            try:
                mod = getattr(__import__("bookmarks.env.%s" % env).env, env)
                if c.OPEN_COMMAND is None:
                    self.__class__.OPEN_COMMAND = mod.OPEN
                if c.FILE_MANAGER is None:
                    self.__class__.FILE_MANAGER = mod.FILE_MANAGER
                if c.WEB_BROWSER is None:
                    self.__class__.WEB_BROWSER = self.__class__.OPEN_COMMAND
            except:
                pass
    
    def popen_execute(self, path, args):
        import subprocess
        if isinstance(path, list):
            _args = list(path)
            if args:
                _args.append(args)
        else:
            if args:
                _args = [path, args]
            else:
                _args = [path]
        subprocess.Popen(_args).pid
    
    def win_execute(self, path, args):
        self.ctx.getServiceManager().createInstanceWithContext( 
                "com.sun.star.system.SystemShellExecute", self.ctx).\
                    execute(path, args, 1)
    
    def other_execute(self, path, args):
        import os
        try:
            import thread
        except:
            import _thread as thread
        if args:
            command = "%s %s"
        else:
            command = path
        thread.start_new_thread(lambda command: os.system(command), (command,))
    
    def detect_env(self):
        """ Detect environment type. """
        import sys
        type = ""
        platform = sys.platform
        if platform == "win32":
            type = platform
        elif platform == "darwin":
            type = platform
        else:
            import os
            try:
                type = os.environ["DESKTOP_SESSION"]
            except:
                try:
                    type = os.environ["GDMSESSION"]
                except:
                    try:
                        type = os.environ["XDG_SESSION_DESKTOP"]
                    except:
                        pass
        if type == "default" or type.lower() == "kde":
            try:
                if os.environ["KDE_SESSION_VERSION"] >= "4":
                    type = "kde4"
                else:
                    type = "kde3"
            except:
                type = None
        if not type:
            # how about other session
            type = "other"
        return type
    
    def execute_item(self, item):
        """ Execute command on dispatch framework of the frame. """
        self.execute_command(item.get_command())
    
    def execute_command(self, command):
        """ Exec command. """
        if command.startswith(self.PROTOCOL_BOOKMARKS):
            command_type, value1, value2 = self.extract_from_command(command)
            self.execute_bookmarks_command(command_type, value1, value2)
        else:
            _command = self.decode_command(command)
            self.dispatch(self.frame, _command)
    
    def decode_command(self, command):
        try:
            main, protocol, path, query = self.bk_command_parse(command)
            qs = self.bk_parse_qsl(query)
            _qs = []
            for name, value in qs:
                _qs.append(name + "=" + value)
            if _qs:
                return main + "?" + "&".join(_qs)
            else:
                return main
        except:
            return command
    
    def execute_bookmarks_command(self, type, value1, value2):
        """ Execute command in category bookmarks. """
        try:
            fn = getattr(self, "exec_%s" % type)
            fn(value1, value2)
        except Exception as e:
            raise e
    
    def exec_edit(self, value1, value2):
        # allow to edit other bookmarks
        EditWindowThread(self.ctx, self.command).start()
    
    def exec_addthis(self, value1, value2):
        ExecuteAddThis(self.ctx, self.frame, self.command).run()
    
    def _get_executor(self):
        try:
            from subprocess import Popen
            self.executor = self.popen_execute
        except:
            import os
            if os.sep == "\\":
                self.executor = self.win_execute
            else:
                self.executor = self.other_execute
    
    def _execute(self, value1, value2):
        if self.executor is None:
            self._get_executor()
        self.executor(value1, value2)
    
    def exec_program(self, value1, value2):
        self._execute(value1, value2)
    
    def exec_file(self, value1, value2):
        if self.is_win32:
            value1 = self.escape_win32_path(value1)
        if not self.OPEN_COMMAND is None:
            self._execute(self.OPEN_COMMAND, value1)
    
    def exec_folder(self, value1, value2):
        if self.is_win32:
            value1 = self.escape_win32_path(value1)
        if not self.FILE_MANAGER is None:
            self._execute(self.FILE_MANAGER, value1)
    
    def exec_web(self, value1, value2):
        if not self.WEB_BROWSER is None:
            self._execute(self.WEB_BROWSER, value1)
        # ToDo webbrowser module
    
    def escape_win32_path(self, value):
        value = value.replace("&", "^&")
        value = value.replace("|", "^|")
        value = value.replace("(", "^(")
        value = value.replace(")", "^)")
        return value
    
    def get_config_settings(self):
        return get_config(self.ctx, CONFIG_NODE_SETTINGS)
    
    def load_config(self):
        config = self.get_config_settings()
        if config.getPropertyValue(NAME_USE_CUSTOM_OPEN_COMMAND):
            self.__class__.OPEN_COMMAND = config.getPropertyValue(NAME_OPEN_COMMAND)
        
        if config.getPropertyValue(NAME_USE_CUSTOM_FILE_MANAGER):
            self.__class__.FILE_MANAGER = config.getPropertyValue(NAME_FILE_MANAGER)
        
        if config.getPropertyValue(NAME_USE_CUSTOM_WEB_BROWSER):
            self.__class__.WEB_BROWSER = config.getPropertyValue(NAME_WEB_BROWSER)
