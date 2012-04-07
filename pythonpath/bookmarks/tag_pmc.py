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
    return TagPopup(ctx, args)

import bookmarks.bookmarks_pmc

class TagPopup(bookmarks.bookmarks_pmc.BookmarksPopupBase):
    """ Shows tagged items in popup menu. """
    
    from bookmarks import TAG_POPUP_IMPLE_NAME as IMPLE_NAME, \
        SERVICE_NAMES
    
    def __init__(self, ctx, args):
        bookmarks.bookmarks_pmc.BookmarksPopupBase.__init__(self, ctx, args)
        self.valid = False
        self.tag_name = None
        self.controller = None
        self.initialize(args)
    
    def set_controller(self, controller):
        self.controller = controller
        self.manager = controller.manager
        self.commands = controller.commands
        try:
            d, tag_name, d = self.commands.extract_from_command(self.command)
            self.tag_name = tag_name
            if self.tag_name:
                self.valid = True
        except:
            pass
        self.update_last_checked()
    
    def get_container(self):
        if self.valid:
            if self.manager.has_tag(self.tag_name):
                return self.manager.get_tag(self.tag_name)
    
    # XPopupMenuController
    def updatePopupMenu(self):
        if self.manager.is_modified_since(self.last_checked):
            self.prepare_menu(clear=True)

