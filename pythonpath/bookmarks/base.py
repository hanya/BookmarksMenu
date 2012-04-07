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

from com.sun.star.lang import XComponent, EventObject, XServiceInfo

class ComponentBase(XComponent):
    
    def __init__(self):
        self._listeners = []
    
    def dispose(self):
        ev = EventObject(self)
        for listener in self._listeners:
            try:
                listener.disposing(ev)
            except:
                pass
    
    def addEventListener(self, listener):
        self._listeners.append(listener)
    
    def removeEventListener(self, listener):
        try:
            while True:
                self._listeners.remove(listener)
        except:
            pass


class ServiceInfo(XServiceInfo):
    
    # XServiceInfo
    def getImplementationName(self):
        return self.IMPLE_NAME
    
    def getSupportedServiceNames(self):
        return self.SERVICE_NAMES
    
    def supportsService(self, name):
        return name in self.SERVICE_NAMES


from com.sun.star.lang import XInitialization
from com.sun.star.frame import \
	XDispatchProvider, XPopupMenuController, XStatusListener


class PopupMenuControllerBase(XPopupMenuController, XInitialization, 
                        XDispatchProvider, XStatusListener, ServiceInfo):
	
	# XPopupMenuController
	def setPopupMenu(self, popup): pass
	def updatePopupMenu(self): pass
	
	# XInitialization
	def initialize(self, args): pass
	
	# XDispatchProvider
	def queryDispatch(self, url, name, flags): pass
	def queryDispatches(self, requests): pass
	
	# XStatusListener
	def statusChanged(self, ev): pass
	
	def create_sub_popup(self):
		""" Create popupmenu instance. """
		return self.ctx.getServiceManager().\
			createInstanceWithContext("com.sun.star.awt.PopupMenu", self.ctx)

