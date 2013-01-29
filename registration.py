
import bookmarks

imples = {
    bookmarks.IMPLE_NAME: 
        (bookmarks.SERVICE_NAMES, "bookmarks.bookmarks_pmc.create"), 
    bookmarks.SHOWN_COLUMNS_IMPLE_NAME: 
        (bookmarks.SERVICE_NAMES, "bookmarks.columns_pmc.create"), 
    bookmarks.OPTION_PAGE_HANDLER_IMPLE_NAME: 
        ((bookmarks.OPTION_PAGE_HANDLER_IMPLE_NAME,), "bookmarks.options.create"), 
    bookmarks.MANAGER_IMPLE_NAME: 
        (bookmarks.MANAGER_SERVICE_NAMES, "bookmarks.organizer.create"), 
    bookmarks.DIRECTORY_POPUP_IMPLE_NAME: 
        (bookmarks.SERVICE_NAMES, "bookmarks.directory_pmc.create"), 
    bookmarks.TAG_POPUP_IMPLE_NAME: 
        (bookmarks.SERVICE_NAMES, "bookmarks.tag_pmc.create"), 
}


def writeRegistryInfo(smgr, reg):
    for imple_name in imples.keys():
        key = reg.createKey("/%s/UNO/SERVICES" % imple_name)
        for name in imples[imple_name][0]:
            key.createKey(name)
    return True

def getComponentFactory(imple_name, smgr, reg):
    try:
        imple = imples[imple_name]
        names = imple[1].split(".")
        if names:
            mod = __import__(".".join(names[0:-1]))
            for name in names[1:]:
                mod = getattr(mod, name)
        else:
            mod = getattr(__module__, imple[1])
        return SingleComponentFactory(imple_name, imple[0], mod)
    except Exception as e:
        print(e)
        return None


import unohelper
from com.sun.star.lang import XServiceInfo, XSingleComponentFactory

class SingleComponentFactory(unohelper.Base, XSingleComponentFactory, XServiceInfo):
    
    def __init__(self, imple_name, service_names, ctor):
        self.imple_name = imple_name
        self.service_names = service_names
        self.ctor = ctor
    
    def createInstanceWithContext(self, ctx):
        return self.createInstanceWithArgumentsAndContext((), ctx)
    
    def createInstanceWithArgumentsAndContext(self, args, ctx):
        try:
            return self.ctor(ctx, *args)
        except Exception as e:
            print(e)
            import traceback
            traceback.print_exc()
    
    def getImplementationName(self):
        return self.imple_name
    
    def supportsService(self, name):
        return name in self.service_names
    
    def getSupportedServiceNames(self):
        return self.service_names

