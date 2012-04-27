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
from com.sun.star.beans import PropertyValue, StringPair
from com.sun.star.lang import Locale
from com.sun.star.task import XInteractionHandler


def create_service(ctx, name, args=None):
    """ Create service with args if required. """
    smgr = ctx.getServiceManager()
    if args:
        return smgr.createInstanceWithArgumentsAndContext(name, args, ctx)
    else:
        return smgr.createInstanceWithContext(name, ctx)


def get_desktop(ctx):
    """ Get instance of css.frame.Destkop"""
    return create_service(ctx, "com.sun.star.frame.Desktop")


def get_config(ctx, nodepath, modifiable=False):
    """ Get configuration node. """
    cp = create_service(ctx, "com.sun.star.configuration.ConfigurationProvider")
    node = PropertyValue("nodepath", -1, nodepath, 0)
    if modifiable:
        name = "com.sun.star.configuration.ConfigurationUpdateAccess"
    else:
        name = "com.sun.star.configuration.ConfigurationAccess"
    return cp.createInstanceWithArguments(name, (node,))


def get_config_value(ctx, nodepath, name):
    """ Get value from specific configuration node. """
    config = get_config(ctx, nodepath)
    return config.getPropertyValue(name)


def get_current_locale(ctx):
    """ Get current locale. """
    config = get_config(ctx, "/org.openoffice.Setup/L10N")
    locale = config.getPropertyValue("ooLocale")
    parts = locale.split("-")
    lang = parts[0]
    country = ""
    if len(parts) == 2:
        country = parts[1]
    return Locale(lang, country, "")


def get_user_config(ctx):
    """ Get writable user's config. """
    return create_service(ctx, "com.sun.star.util.PathSettings").UserConfig_writable

def get_user_backup(ctx):
    """ Get writable user's backup. """
    return create_service(ctx, "com.sun.star.util.PathSettings").Backup_writable


def get_extension_dirurl(ctx, extid):
    """Get extension directory url from the extension id."""
    pip_name = "/singletons/com.sun.star.deployment.PackageInformationProvider"
    if ctx.hasByName(pip_name):
        pip = ctx.getByName(pip_name)
        try:
            return pip.getPackageLocation(extid)
        except:
            pass # ubuntu-2d
    return ""


def load_resource(ctx, dir_url, file_name, locale, read_only=True):
    """ Load resource file. """
    class DummyHandler(unohelper.Base, XInteractionHandler):
        def handle(self, request): pass
    
    res = create_service(ctx, 
        "com.sun.star.resource.StringResourceWithLocation")
    res.initialize((dir_url, read_only, locale, file_name, "", DummyHandler()))
    return res


def load_resource_as_dict(ctx, dir_url, file_name, locale, include_id=False):
    """ Load resource as dict. """
    res = load_resource(ctx, dir_url, file_name, locale)
    strings = {}
    default_locale = res.getDefaultLocale()
    for id in res.getResourceIDs():
        str_id = res.resolveStringForLocale(id, default_locale)
        resolved = res.resolveString(id)
        strings[str_id] = resolved
        if include_id:
            strings[id] = resolved
    return strings


def get_current_resource(ctx, dir_url, file_name):
    """ Get resource for current locale. """
    return load_resource_as_dict(ctx, dir_url, file_name, get_current_locale(ctx))

from com.sun.star.awt import Rectangle
def show_message(ctx, frame, message, title="", type="messbox", buttons=1, labels=None):
    """ Show text in message box. """
    #from com.sun.star.awt import Rectangle
    try:
        peer = frame.getContainerWindow()
    except:
        peer = frame
    box = peer.getToolkit().createMessageBox(
        peer, Rectangle(), type, buttons, title, message)
    
    ws = box.getWindows()
    if labels and len(ws) == len(labels):
        for label, w in zip(labels, ws):
            w.Label = label
    
    n = box.execute()
    box.dispose()
    return n


def create_script(ctx, uri):
    """ Create script object. """
    return ctx.getValueByName(
        "/singletons/com.sun.star.script.provider.theMasterScriptProviderFactory").\
            createScriptProvider("").getScript(uri)


def get_module_name(ctx, obj):
    """ Get document module name. """
    try:
        return create_service(ctx, "com.sun.star.frame.ModuleManger").identify(obj)
    except:
        pass
    return ""


# VclResourceLoader is gone on LibreOffice 3.5.
#def get_resource(ctx, module, method, id):
#    """ Load something from resource file. """
#    # helper basic code required, because of VclResourceLoader has problem with PyUNO
#    RES_LOADER_URI = "vnd.sun.star.script:mytools_bookmarks.Res.LoadResource?language=Basic&location=application"
#    script = create_script(ctx, RES_LOADER_URI)
#    resources, dummy, dummy = script.invoke((module, method, id), (), ())
#    return resources


def get_popup_names(ctx):
    """ Get list of popup menu controller names. """
    config = get_config(ctx, 
        "/org.openoffice.Office.UI.Controller/Registered/PopupMenu")
    popup_menus = {}
    for name in config.getElementNames():
        item = config.getByName(name)
        popup_menus[item.Command] = item.Controller
    return popup_menus


def create_graphic(ctx, url):
    """ Create graphic instance for image URL. """
    return create_service(
        ctx, "com.sun.star.graphic.GraphicProvider").\
            queryGraphic((PropertyValue("URL", -1, url, 0),))


def join_url(dir_url, *names):
    """ Append names with directory URL. """
    if dir_url.endswith("/"):
        return dir_url + "/".join(names)
    else:
        return dir_url + "/" + "/".join(names)

def dir_url(file_url):
    """ Get directory URL. """
    n = file_url.rfind("/")
    if n > -1:
        return file_url[0:n]
    return file_url


def copy_file(ctx, source, dest, overwrite=False):
    """ Copy files to destination. """
    try:
        sfa = create_service(ctx, "com.sun.star.ucb.SimpleFileAccess")
        if sfa.exists(dest):
            if not overwrite:
                return
        if sfa.exists(source):
            sfa.copy(source, dest)
    except Exception, e:
        if not sfa.exists(dir_url(dest)):
            sfa.createFolder(dir_url(dest))
        if sfa.exists(source):
            sfa.copy(source, dest)


def get_text_content(ctx, file_url, encoding="utf-8"):
    sfa = create_service(ctx, "com.sun.star.ucb.SimpleFileAccess")
    if sfa.exists(file_url):
        textio = create_service(ctx, "com.sun.star.io.TextInputStream")
        try:
            io = sfa.openFileRead(file_url)
            textio.setInputStream(io)
            textio.setEncoding(encoding)
            lines = []
            while not textio.isEOF():
                lines.append(textio.readLine())
            io.closeInput()
            return "\n".join(lines)
        except:
            pass
    return None


def check_interface(ctx, interface_name, method_names):
    """ Check the interface is implemented or methods are implemented. """
    cr = create_service(ctx, "com.sun.star.reflection.CoreReflection")
    try:
        idl = cr.forName(interface_name)
        for name in method_names:
            r = idl.getMethod(name)
            if r is None:
                return False
    except:
        return False
    return True


def get_extension_package(ctx, ext_id):
    """ Get extension package for extension id. """
    repositories = ("user", "shared", "bundle")
    manager_name = "/singletons/com.sun.star.deployment.ExtensionManager"
    manager = None
    if ctx.hasByName(manager_name):
        # 3.3 is required
        manager = ctx.getByName(manager_name)
    else:
        return None
    package = None
    for repository in repositories:
        package = manager.getDeployedExtension(repository, ext_id, "", None)
        if package:
            break
    return package


def get_package_info(ctx, ext_id):
    """ Returns package name and version. """
    package = get_extension_package(ctx, ext_id)
    if package:
        return package.getDisplayName(), package.getVersion()
    return "", ""


class FileFilterManager(object):
    """ Generate list of filters and fills file picker with it. """
    
    FILTER_QUERY = "getSortedFilterList():module=:iflags=1:eflags=266248"
    
    TYPES = "/org.openoffice.TypeDetection.Types/Types"
    CLASSIFICATION = "/org.openoffice.Office.UI/FilterClassification"
    LOCAL_CATEGORIES = "/org.openoffice.Office.UI/FilterClassification/LocalFilters/Classes"
    
    FORMULA_NAME1 = "com.sun.star.formula.FormularProperties"
    FORMULA_NAME2 = "com.sun.star.formula.FormulaProperties"
    
    def __init__(self, ctx, all_files="All files (*.*)"):
        self.ctx = ctx
        self.all_files = all_files
        self.filter_groups = None
    
    def set_filters(self, fp):
        """ Fill list of file type of file picker dialog. """
        if not self.filter_groups:
            self._init()
        
        sp = StringPair
        fp.appendFilterGroup("all", (sp(self.all_files, "*.*"),))
        for group in self.filter_groups:
            fp.appendFilterGroup(group[0], tuple([sp(uiname, filter) 
					for uiname, name, filter in group[1]]))
    
    def get_internal_name(self, uiname):
        """ Get internal name of the filter from its UI name. """
        if not self.filter_groups:
            self._init()
        
        if uiname == self.all_files:
            return ""
        for group in self.filter_groups:
            for f in group[1]:
                if f[0] == uiname:
                    return f[1]
        return None
    
    def get_ui_name(self, name):
        """ Get UI name from its internal name. """
        if not self.filter_groups:
            self._init()
        
        if name == "":
            return self.all_files
        for group in self.filter_groups:
            for f in group[1]:
                if f[1] == name:
                    return f[0]
        return None
    
    def _init(self):
        if not self.filter_groups:
            self._init_filters()
    
    def _init_filters(self):
        def get_values(item):
            name = ""
            uiname = ""
            type = ""
            service = ""
            for i in item:
                if i.Name == "Name":
                    name = i.Value
                elif i.Name == "UIName":
                    uiname = i.Value
                elif i.Name == "Type":
                    type = i.Value
                elif i.Name == "DocumentService":
                    service = i.Value
            return name, uiname, type, service
        ctx = self.ctx
        
        ff = ctx.getServiceManager().createInstanceWithContext(
                        "com.sun.star.document.FilterFactory", ctx)
        filters_enume = ff.createSubSetEnumerationByQuery(self.FILTER_QUERY)
        
        types = get_config(ctx, self.TYPES)
        ordered_filter_names = []
        filters = {}
        while filters_enume.hasMoreElements():
            f = filters_enume.nextElement()
            name, uiname, type, service = get_values(f)
            try:
                ext = ";".join(["*." + ext 
                    for ext in types.getByName(type).Extensions])
            except:
                ext = ()
            filters[name] = (uiname, ext, service)
            ordered_filter_names.append(name)
        
        classification = get_config(ctx, self.CLASSIFICATION)
        # order to show filters in the listbox
        module_order = list(classification.getHierarchicalPropertyValue("GlobalFilters/Order"))
        try:
            module_order[module_order.index(self.FORMULA_NAME1)] = self.FORMULA_NAME2
        except:
            pass
        modules = {}
        for name in module_order:
            modules[name] = []
        modules["other"] = []
        
        for name in ordered_filter_names:
            try:
                v = filters[name]
            except:
                continue
            try:
                mod = modules[v[2]]
            except: 
                mod = modules["other"]
            uiname = v[0]
            file_filter = v[1]
            if file_filter:
                uiname = v[0] + (" (%s)" % file_filter)
            mod.append((uiname, name, file_filter))
        
        # categories
        classify = classification.getHierarchicalPropertyValue("GlobalFilters/Classes")
        
        group_names = {}
        for name in classify.getElementNames():
            if name == self.FORMULA_NAME1:
                _name = self.FORMULA_NAME2
            else:
                _name = name
            group_names[_name] = classify.getByName(name).DisplayName
        
        filter_groups = [(group_names[name], modules[name]) 
                            for name in module_order]
        if modules["other"]:
            filter_groups.append(("other", modules["other"]))
        self.filter_groups = filter_groups

