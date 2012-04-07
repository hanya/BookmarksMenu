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

import unohelper

from com.sun.star.container import NoSuchElementException
from com.sun.star.frame import XModel, XModule, XTitle, \
    XTitleChangeBroadcaster, XStorable
from com.sun.star.util import XModifiable, XCloseable

from bookmarks.base import ComponentBase, ServiceInfo
from bookmarks.controller import UIController

class Model(unohelper.Base, ComponentBase, 
        XModel, XModule, XModifiable, XStorable, 
        XTitle, XTitleChangeBroadcaster, ServiceInfo):
    
    from bookmarks import DOCUMENT_IMPLE_NAME as IMPLE_NAME, \
        DOCUMENT_SERVICE_NAMES as SERVICE_NAMES
    
    def __init__(self, ctx, imple):
        ComponentBase.__init__(self)
        self.ctx = ctx
        self.imple = imple
        self.id = self.IMPLE_NAME
        self.controller = None
        self.controllers = []
    
    # XModel2
    def getControllers(self):
        return None
    
    def getAvailableViewControllerNames(self):
        return ("Default", )
    
    def createDefaultViewController(self, frame):
        return UIController(self.ctx, self.imple, frame)
    
    def createViewController(self, name, args, frame):
        return UIController(self.ctx, self.imple, frame, args)
    
    # XModel
    def attachResource(self, url, arguments):
        pass
    
    def getURL(self):
        if self.controller:
            return self.controller.imple.manager.file_url
        return ""
    
    def getArgs(self):
        return ()
    
    def connectController(self, controller):
        try:
            self.controllers.index(controller)
        except:
            self.controllers.append(controller)
    
    def disconnectController(self, controller):
        try:
            self.controllers.remove(controller)
            if self.controller == controller:
                self.controller = None
        except:
            pass
    
    def lockControllers(self):
        pass
    
    def unlockControllers(self):
        pass
    
    def hasControllersLocked(self):
        return False
    
    def getCurrentController(self):
        return self.controller
    
    def setCurrentController(self, controller):
        if controller in self.controllers:
            self.controller = controller
        else:
            raise NoSuchElementException("controller not found", self)
    
    def getCurrentSelection(self):
        return None
    
    # XModule
    def setIdentifier(self, id):
        self.id = id
    
    def getIdentifier(self):
        return self.id
    
    # XTitle
    def getTitle(self):
        if self.controller:
            return self.controller.getTitle()
    
    def setTitle(self, title):
        if self.controller:
            self.controller.setTitle(title)
    
    # XTitleChangeBroadcaster
    def addTitleChangeListener(self, listener): pass
    
    def removeTitleChangeListener(self, listener): pass
    
    # XModifiable
    def addModifyListener(self, listener): pass
    
    def removeModifyListener(self, listener): pass
    
    def isModified(self):
        return self.imple.manager.modified
    
    def setModified(self, state):
        self.imple.manager.set_modified(state)
        if self.controller:
            self.controller.update_save_state()
    
    # XStorable
    def hasLocation(self):
        return True
    
    def getLocation(self):
        return self.getURL()
    
    def isReadonly(self):
        return False
    
    def store(self):
        self.imple.do_Save()
    
    def storeAsURL(self, url, args):
        pass
    
    def storeToURL(self, url, args):
        pass
    
    # XCloseable
    def close(self, ownership):
        if self.controller:
            self.controller.do_action_by_name(".uno:CloseWin")
    
    def addCloseListener(self, listener):
        pass
    
    def removeCloseListener(self, listener):
        pass
    
    from bookmarks import NAME_DATA_URL, NAME_BACKUP_DIRECTORY
    
    # XPropertySet
    def getPropertySetInfo(self):
        try:
            string_type = uno.getTypeByName("string")
            return PropertySetInfo(
                (
                    (self.NAME_DATA_URL, -1, string_type, 0), 
                    (self.NAME_BACKUP_DIRECTORY, -1, string_type, 0), 
                )
            )
        except Exception, e:
            print(e)
        return None
    
    def setPropertyValue(self, name, value):
        if name == self.NAME_DATA_URL or \
            name == self.NAME_BACKUP_DIRECTORY:
            config = self.get_controller_config(True)
            if config:
                config.setPropertyValue(name, value)
                config.getParent().commitChanges()
    
    def getPropertyValue(self, name):
        if name == self.NAME_DATA_URL or \
            name == self.NAME_BACKUP_DIRECTORY:
            config = self.get_controller_config()
            if config:
                return config.getPropertyValue(name)
        from com.sun.star.beans import UnknownPropertyException
        raise UnknownPropertyException(name, self)
    
    def addPropertyChangeListener(self, name, listener): pass
    def removePropertyChangeListener(self, name, listener): pass
    def addVetoableChangeListener(self, name, listener): pass
    def removeVetoableChangeListener(self, name, listener): pass
    
    def get_controller_config(self, modifiable=False):
        """ Get controller specific configuration. """
        from bookmarks.tools import get_config
        from bookmarks import CONFIG_NODE_CONTROLLERS
        config = get_config(self.ctx, CONFIG_NODE_CONTROLLERS, modifiable)
        command = self.imple.command
        if config.hasByName(command):
            return config.getByName(command)

