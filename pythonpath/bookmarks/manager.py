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

import os
import time
import json
import traceback
import uno

from bookmarks.bookmark import BookmarksManagerBase, \
    BaseItem, Item, Separator, Container, TagContainer

import sys
is_python3 = sys.version_info.major >= 3
del sys


class BookmarksManager(BookmarksManagerBase):
    """ Keeps JSON based bookmarks. """
    
    FILE_NAME = "bookmarks_%s.json"
    FILE_BASE_URL = "%%s/%s" % FILE_NAME
    DEFAULT_NAME = "Bookmarks"
    UNSORTED_DEFAULT_NAME = "Unsorted Bookmarks"
    
    BACKUP_DIR  = "bookmarks"
    DATE_FORMAT = "%Y-%m-%d"
    
    NAME_TAGS = "tags"
    NAME_BOOKMARKS = "bookmarks"
    NAME_UNSORTED = "unsorted"
    
    Managers = {}
    
    def get(ctx, id, name=""):
        """ Request to get container for command. """
        klass = BookmarksManager
        managers = klass.Managers
        if not id in managers:
            managers[id] = klass(ctx, id, name)
        return managers[id]
    
    def remove(id):
        klass = BookmarksManager
        try:
            klass.Managers.pop(id)
        except:
            pass
    
    get = staticmethod(get)
    remove = staticmethod(remove)
    
    def __init__(self, ctx, command, name=""):
        BookmarksManagerBase.__init__(self)
        self.unsorted = None
        self.ctx = ctx
        self.command = command
        self.last_modified = 0
        self.modified = False
        self.file_url = self.command_to_path(ctx, command)
        self.bookmark_name = name
        if self.file_url:
            self.open(self.file_url)
    
    def __repr__(self):
        return "<%s.%s %s at %s>" % (
            self.__class__.__module__, 
            self.__class__.__name__, self.file_url, id(self))
    
    def set_modified(self, state=True):
        """ Update modified state. """
        self.modified = state
        self.last_modified = time.time()
    
    def is_modified_since(self, value):
        return value < self.last_modified
    
    def get_last_modified(self):
        return self.last_modified
    
    def has_location(self):
        """ Check the file exists. """
        return os.path.exists(uno.fileUrlToSystemPath(self.file_url))
    
    def create_base(self, name):
        """ Create base container. """
        obj = Container(name)
        obj.set_id(1)
        return obj
    
    def _read_from_file(self, file_url):
        """ Read string from the file. """
        import bookmarks.tools
        sfa = bookmarks.tools.create_service(
                self.ctx, "com.sun.star.ucb.SimpleFileAccess")
        io = sfa.openFileRead(file_url)
        ret = None
        if is_python3:
            try:
                text = bytes()
                while True:
                    n, data = io.readBytes(None, 0xffff)
                    text += data.value
                    if n < 0xffff:
                        break
            except Exception as e:
                print(e)
            ret = text.decode("utf-8")
        else:
            try:
                text = []
                while True:
                    n, data = io.readBytes(None, 0xffff)
                    text.append(data.value)
                    if n < 0xffff:
                        break
            except Exception as e:
                print(e)
            ret = "".join(text).decode("utf-8")
        io.closeInput()
        return ret
    
    def _write_to_file(self, file_url, text):
        """ Write text to the file. """
        import bookmarks.tools
        import uno
        sfa = bookmarks.tools.create_service(
                self.ctx, "com.sun.star.ucb.SimpleFileAccess")
        if sfa.exists(file_url):
            sfa.kill(file_url)
        io = sfa.openFileWrite(file_url)
        try:
            total = len(text)-1
            n = 0
            while True:
                io.writeBytes(uno.ByteSequence(text[n:n+0xffff]))
                n += 0xffff
                if n >= total:
                    break
        except Exception as e:
            print(e)
        io.closeOutput()
    
    def open(self, file_url=None, fallback=True):
        """ Open and load data. """
        def load_res():
            from bookmarks import RES_DIR, RES_FILE
            from bookmarks.tools import get_current_resource
            return get_current_resource(self.ctx, RES_DIR, RES_FILE)
        
        obj = None
        if file_url is None:
            file_url = self.file_url
        if self.has_location():
            s = self._read_from_file(file_url)
            obj = self.__class__.load(s)
        if not obj:
            if fallback:
                # search in extension package
                file_url = self.command_to_path(
                    self.ctx, self.command, fallback=True)
                if file_url:
                    s = self._read_from_file(file_url)
                    obj = self.__class__.load(s)
            if not obj:
                res = load_res()
                obj = self.create_simple_base(res)
        if file_url:
            self.file_url = file_url
        self.data = obj
        
        if self.NAME_BOOKMARKS in obj:
            self.base = obj[self.NAME_BOOKMARKS]
        else:
            res = load_res()
            self.base = self.create_base(res)
        
        if self.NAME_TAGS in obj:
            self.tags.update(obj[self.NAME_TAGS])
        
        if self.NAME_UNSORTED in obj:
            self.unsorted = obj[self.NAME_UNSORTED]
        else:
            res = load_res()
            self.unsorted = self.create_unsorted(res)
        
        self.reassign_all() # reduce id problem
        self.assign_id(self.unsorted)
        self.containers[self.unsorted.get_id()] = self.unsorted
        self.last_modified = time.time()
        self.update_tags(self.base)
        self.update_tags(self.unsorted)
    
    def store(self):
        """ Store into file. """
        if self.modified:
            self.backup() # ToDo configuration to enable/disable backup
            obj = {
                self.NAME_TAGS: self.tags, 
                self.NAME_BOOKMARKS: self.base, 
                self.NAME_UNSORTED: self.unsorted
            }
            s = self.__class__.dump(obj)
            self._write_to_file(self.file_url, s)
        #self.reassign_all()
        self.last_modified = time.time()
        self.modified = False
    
    def backup(self):
        """ Copy current file to backup. """
        from bookmarks.tools import get_config
        config = get_config(
            self.ctx, "/org.openoffice.Office.Common/Save/Document")
        if not config.CreateBackup:
            return
        from bookmarks import CONFIG_NODE_CONTROLLERS, NAME_BACKUP_DIRECTORY
        from bookmarks.tools import get_user_backup, join_url, copy_file
        try:
            backup_dir = None
            config = get_config(self.ctx, CONFIG_NODE_CONTROLLERS)
            if config.hasByName(self.command):
                _config = config.getByName(self.command)
                backup_dir = _config.getPropertyValue(NAME_BACKUP_DIRECTORY)
            
            if not backup_dir:
                backup_dir = join_url(get_user_backup(self.ctx), self.BACKUP_DIR)
            file_name = self.FILE_NAME % (
                    time.strftime(self.DATE_FORMAT) + \
                        "_" + self.command.split(":")[-1])
            copy_file(
                self.ctx, 
                self.file_url, 
                join_url(backup_dir, file_name)
            )
        except Exception as e:
            print(e)
    
    def load(s):
        """ Load JSON file as bookmarks from string. """
        obj = None
        try:
            if s:
                decoder = BookmarksJSONDecoder
                obj = json.loads(
                    s, 
                    cls=decoder, 
                    object_hook=decoder.obj_hook)
        except Exception as e:
            print(e)
            traceback.print_exc()
        return obj
    
    load = staticmethod(load)
    
    def dump(obj):
        """ Store bookmarks as JSON. """
        s = None
        try:
            encoder = BookmarksJSONEncoder
            s = json.dumps(
                obj, 
                ensure_ascii=False, 
                cls=encoder, 
                #indent=4, 
                sort_keys=True)
        except Exception as e:
            print(e)
        return s.encode("utf-8")
    
    dump = staticmethod(dump)
    
    def command_to_path(ctx, command, fallback=False):
        """ Command to file path in config. """
        parts = command.split(":", 1)
        if len(parts) == 2:
            if fallback:
                from bookmarks.tools import get_extension_dirurl, join_url
                dir_url = get_extension_dirurl(
                                ctx, command.replace(":", "."))
                if dir_url:
                    return join_url(
                        dir_url, 
                        BookmarksManager.FILE_NAME % parts[1].lower())
            else:
                from bookmarks import CONFIG_NODE_CONTROLLERS, NAME_DATA_URL
                from bookmarks.tools import get_config, get_user_config
                config = get_config(ctx, CONFIG_NODE_CONTROLLERS)
                if config.hasByName(command):
                    _config = config.getByName(command)
                    data_url = _config.getByName(NAME_DATA_URL)
                    if data_url:
                        return data_url
                
                return BookmarksManager.FILE_BASE_URL % (
                        get_user_config(ctx), parts[1].lower())
        return ""
    
    command_to_path = staticmethod(command_to_path)
    
    def create_unsorted(res):
        klass = BookmarksManager
        def _(name):
            return res.get(name, name)
        unsorted = Container(_(klass.UNSORTED_DEFAULT_NAME))
        unsorted.id = -1
        return unsorted
    
    create_unsorted = staticmethod(create_unsorted)
    
    def create_base(res):
        klass = BookmarksManager
        from bookmarks import PROTOCOL_BOOKMARKS
        def _(name):
            return res.get(name, name)
        
        base = Container(_(klass.DEFAULT_NAME))
        children = base.children
        children += [
            Item(_("Bookmark ~This Document..."), 
                "", PROTOCOL_BOOKMARKS + "AddThis"), 
            Item(_("~Edit Bookmarks..."), 
                "", PROTOCOL_BOOKMARKS + "Edit"), 
            Separator()
        ]
        base.id = 1
        for i, child in enumerate(children):
            child.id = i +1
            child.parent = 1
        return base
    
    create_base = staticmethod(create_base)
    
    def create_simple_base(res):
        """ Create initial container. """
        klass = BookmarksManager
        
        return klass.pack(
            {}, 
            klass.create_base(res), 
            klass.create_unsorted(res))
    
    create_simple_base = staticmethod(create_simple_base)
    
    def pack(tags, base, unsorted):
        klass = BookmarksManager
        return {
            klass.NAME_TAGS: tags, 
            klass.NAME_BOOKMARKS: base, 
            klass.NAME_UNSORTED: unsorted
        }
    
    pack = staticmethod(pack)


class BookmarksJSONBase(object):
    pass


class BookmarksJSONDecoder(BookmarksJSONBase, json.JSONDecoder):
    """ Customized decoder for bookmarks. """
    def obj_hook(o):
        try:
            return BaseItem.create(o)
        except:
            try:
                return TagContainer.create(o)
            except:
                return dict(o)
    
    obj_hook = staticmethod(obj_hook)


class BookmarksJSONEncoder(BookmarksJSONBase, json.JSONEncoder):
    """ Customized encoder for bookmarks. """
    def default(self, o):
        if isinstance(o, BaseItem) or isinstance(o, TagContainer):
            return o.as_json()
        else:
            return json.JSONEncoder.default(self, o)

