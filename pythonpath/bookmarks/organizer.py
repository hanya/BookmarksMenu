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

import uno
import unohelper

def create(ctx, *args):
    return BookmarksMenuManager(ctx, args)

from com.sun.star.task import XJobExecutor

from bookmarks import RES_DIR, RES_FILE
from bookmarks.tools import get_current_resource
from bookmarks.base import ServiceInfo


class BookmarksMenuManager(unohelper.Base, ServiceInfo, XJobExecutor):
    
    from bookmarks import MANAGER_IMPLE_NAME as IMPLE_NAME, \
        MANAGER_SERVICE_NAMES as SERVICE_NAMES
    
    def __init__(self, ctx, args):
        self.ctx = ctx
    
    # XJobExecutor
    def trigger(self, arg):
        if arg == "Wizard":
            self.execute_wizard()
        elif arg.startswith("Edit&"):
            self.execute_editor("mytools.bookmarks.BookmarksMenu:%s" % arg[5:])
    
    def execute_wizard(self):
        """ Start wizrad. """
        try:
            import bookmarks.wizard.wizard
            bookmarks.wizard.wizard.BookmarksMenuWizard(
                self.ctx, 
                get_current_resource(self.ctx, RES_DIR, RES_FILE)
            ).execute()
        except Exception as e:
            print(e)
    
    def execute_editor(self, command):
        """ Start editor. """
        from bookmarks.command import EditWindowThread
        EditWindowThread(self.ctx, command).run()

