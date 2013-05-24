#  Copyright 2013 Tsutomu Uchino
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

from bookmarks import tools

ANOTHER_MANAGER_FACTORY_SERVICE = "bookmarks.BookmarksPopupManagerFactory"

installed = None

def set_modified(ctx, command):
    global installed
    if installed is None:
        try:
            es = ctx.getServiceManager().createContentEnumeration(
                                    ANOTHER_MANAGER_FACTORY_SERVICE)
            if es:
                installed = es.hasMoreElements()
            else:
                installed = False
        except:
            pass
    if installed:
        try:
            factory = tools.create_service(ctx, ANOTHER_MANAGER_FACTORY_SERVICE)
            manager = factory.getByUniqueID(command)
            if manager:
                manager.setModified(True)
        except:
            installed = False # not installed
