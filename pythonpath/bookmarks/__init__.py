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

EXT_ID = "mytools.bookmarks.BookmarksMenu"

IMPLE_NAME = "bookmarks.BookmarksPopup"
SERVICE_NAMES = ("com.sun.star.frame.PopupMenuController", )
PROTOCOL_BOOKMARKS = "%s:" % EXT_ID

OPTION_PAGE_HANDLER_IMPLE_NAME = "bookmarks.OptionsPageHandler"

SHOWN_COLUMNS_IMPLE_NAME = "bookmarks.ShownColumnsPopupMenu"

MANAGER_IMPLE_NAME = "bookmarks.BookmarksMenuManager"
MANAGER_SERVICE_NAMES = ()

DIRECTORY_POPUP_IMPLE_NAME = "bookmarks.DirectoryPopupMenu"
DIRECTORY_POPUP_URI = "mytools.frame:DirectoryPopupMenu"

TAG_POPUP_IMPLE_NAME = "bookmarks.TagPopupMenu"
TAG_POPUP_URI = "mytools.frame:TagPopupMenu"

DOCUMENT_IMPLE_NAME = EXT_ID
DOCUMENT_SERVICE_NAMES = (DOCUMENT_IMPLE_NAME, )
COMMAND_PROTOCOL = "mytools.bookmarks:"

VIEW_IMPLE_NAME = EXT_ID + "View"
VIEW_SERVICE_NAMES = (VIEW_IMPLE_NAME, 
    "com.sun.star.view.OfficeDocumentView")

EXT_DIR = "vnd.sun.star.extension://%s/" % EXT_ID
ICONS_DIR = "%sicons/" % EXT_DIR
RES_DIR = "%sresources" % EXT_DIR
RES_FILE = "strings"

CONFIG_NODE_SETTINGS = "/mytools.Bookmarks/Settings"
CONFIG_NODE_CONTROLLERS = "/mytools.Bookmarks/Controllers"
NAME_WEB_BROWSER = "WebBrowser"
NAME_FILE_MANAGER = "FileManger"
NAME_OPEN_COMMAND = "OpenCommand"
NAME_USE_CUSTOM_WEB_BROWSER = "UseCustomWebBrowser"
NAME_USE_CUSTOM_FILE_MANAGER = "UseCustomFileManager"
NAME_USE_CUSTOM_OPEN_COMMAND = "UseCustomOpenCommand"
NAME_NAME = "Name"
NAME_TREE_STATE = "TreeState"
NAME_WINDOW_STATE = "WindowState"
NAME_DATA_URL = "DataURL"
NAME_BACKUP_DIRECTORY = "BackupDirectory"

