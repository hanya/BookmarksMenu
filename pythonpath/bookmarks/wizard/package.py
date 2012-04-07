# -*- coding: utf-8 -*-
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

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest>
%s
</manifest:manifest>"""

CONFIG_DATA = """<manifest:file-entry manifest:full-path="%s" 
 manifest:media-type="application/vnd.sun.star.configuration-data"/>"""


SETTINGS = """<?xml version='1.0' encoding='UTF-8'?>
<oor:component-data 
xmlns:oor="http://openoffice.org/2001/registry" 
xmlns:xs="http://www.w3.org/2001/XMLSchema" 
oor:package="mytools" 
oor:name="Bookmarks">
<node oor:name="Controllers">
<node oor:name="%s" oor:op="replace">
<prop oor:name="Name"><value>%s</value></prop>
<prop oor:name="TreeState"><value></value></prop>
<prop oor:name="WindowState"><value></value></prop>
<prop oor:name="DataURL"><value></value></prop>
<prop oor:name="BackupDirectory"><value></value></prop>
</node></node></oor:component-data>"""


CONTROLLER = """<?xml version='1.0' encoding='UTF-8'?>
<oor:component-data 
xmlns:oor="http://openoffice.org/2001/registry" 
xmlns:xs="http://www.w3.org/2001/XMLSchema" 
oor:package="org.openoffice.Office.UI" 
oor:name="Controller">
<node oor:name="Registered">
<node oor:name="PopupMenu">
<node oor:name="%s" oor:op="replace">
<prop oor:name="Command"><value>%s</value></prop>
<prop oor:name="Module"><value></value></prop>
<prop oor:name="Controller"><value>%s</value></prop>
</node></node></node></oor:component-data>"""


ADDONS = """<?xml version='1.0' encoding='UTF-8'?>
<oor:component-data 
xmlns:oor="http://openoffice.org/2001/registry" 
xmlns:xs="http://www.w3.org/2001/XMLSchema" 
oor:name="Addons" 
oor:package="org.openoffice.Office">
<node oor:name="AddonUI"><node oor:name="OfficeMenuBarMerging">
<node oor:name="%s" oor:op="fuse">
<node oor:name="%s" oor:op="replace">
<prop oor:name="MergePoint"><value>%s</value></prop>
<prop oor:name="MergeCommand"><value>%s</value></prop>
<prop oor:name="MergeFallback"><value>%s</value></prop>
<prop oor:name="MergeContext"><value>%s</value></prop>
<node oor:name="MenuItems">
<node oor:name="%s" oor:op="replace">
<prop oor:name="Title">
%s
</prop>
<prop oor:name="URL" oor:type="xs:string"><value>%s</value></prop>
<prop oor:name="Target"><value>_self</value></prop>
<prop oor:name="Context"><value>%s</value></prop>
</node></node></node></node></node></node></oor:component-data>"""


DESCRIPTIONS = """<?xml version="1.0" encoding="UTF-8"?>
<description xmlns="http://openoffice.org/extensions/description/2006"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:d="http://openoffice.org/extensions/description/2006">
    <identifier value="%s" />
    <version value="1.0.0" />
    <display-name>
        <name lang="en">%s</name>
    </display-name>
    <extension-description>
        <src lang="en" xlink:href="descriptions/desc.txt"/>
    </extension-description>
</description>"""

TITLE_VALUE = """<value xml:lang="%s">%s</value>"""

ARC_MANIFEST = "META-INF/manifest.xml"
ARC_DESCRIPTION = "description.xml"
ARC_DESCRIPTIONS = "descriptions/desc.txt"
ARC_ADDONS = "Addons.xcu"
ARC_CONTROLLER = "Controller.xcu"
ARC_SETTINGS = "Settings.xcu"

import uno
import zipfile
import random


def escape(u):
    u = u.replace("&", "&amp;")
    u = u.replace("<", "&lt;")
    u = u.replace(">", "&gt;")
    return u


def get_id():
    random.seed()
    return "%07x" % random.randint(0, 99999999)


from bookmarks import EXT_ID, IMPLE_NAME, PROTOCOL_BOOKMARKS
from bookmarks.manager import BookmarksManager

class Package(object):
    """ Generate and install extension package. """
    
    Encoding = "UTF-8"
    
    FILE_NAME = "BookmarksMenu-%s.oxt"
    
    def __init__(self, ctx):
        self.ctx = ctx
        self.package_url = ""
        self.sfa = self.create_service("com.sun.star.ucb.SimpleFileAccess")
        
        self.temp_url = self.get_temp()
    
    def create_service(self, name):
        return self.ctx.getServiceManager().\
                createInstanceWithContext(name, self.ctx)
    
    def get_temp(self):
        temp = self.create_service("com.sun.star.util.PathSettings").Temp
        if self.sfa.isReadOnly(temp):
            temp = self.create_service("com.sun.star.util.PathSubstitution").\
                substituteVariables("$(user)/temp", True)
            if self.sfa.isReadOnly(temp):
                raise StandardError("Temp file can not be created.")
        if not temp.endswith("/"):
            temp += "/"
        return temp
    
    def delete_package(self):
        try:
            if self.sfa.exists(self.package_url):
                self.sfa.kill(self.package_url)
        except:
            pass
    
    def file_exists(self, file_url):
        return self.sfa.exists(file_url)
    
    def get_package_url(self):
        while True:
            file_url = self.temp_url + (self.FILE_NAME % get_id())
            if not self.sfa.exists(file_url):
                return file_url
    
    def generate(self, name, _titles, 
        merge_point, merge_command, merge_context, description, data=None, another=False, ext_id=None):
        """ Generate extension package. """
        self.delete_package()
        self.package_url = self.get_package_url()
        file_path = uno.fileUrlToSystemPath(self.package_url)
        
        merge_fallback = "AddPath"
        
        if ext_id:
            id = ext_id[len(EXT_ID)+1:]
        if another:
            url = PROTOCOL_BOOKMARKS + id
            #node_name = url
            node_name = url + "_" + get_id()
            # different ext_id (and node name) with the same url
            id = get_id()
            ext_id = EXT_ID + "." + id
        else:
            if not ext_id:
                id = get_id()
                ext_id = EXT_ID + "." + id
            url = PROTOCOL_BOOKMARKS + id
            node_name = url
        
        arc_data = BookmarksManager.FILE_NAME % id
        
        titles = []
        for locale, title in _titles:
            titles.append(TITLE_VALUE % (
                locale, title))
        
        # url is used as node name
        addons = ADDONS % (
            EXT_ID, 
            node_name, 
            merge_point, 
            merge_command, 
            merge_fallback, 
            merge_context, 
            "child", 
            "\n".join(titles), 
            url, 
            merge_context
        )
        
        manifests = []
        manifests.append(CONFIG_DATA % ARC_ADDONS)
        if not another:
            manifests.append(CONFIG_DATA % ARC_CONTROLLER)
            manifests.append(CONFIG_DATA % ARC_SETTINGS)
        manifest = MANIFEST % ("\n".join(manifests))
        
        descriptions = DESCRIPTIONS % (
            ext_id, 
            "Bookmarks Menu %s" % escape(name)
        )
        
        desc = description #"%s" % name
        
        if not another:
            controller = CONTROLLER % (
                node_name, 
                url, 
                IMPLE_NAME
            )
            settings = SETTINGS % (
                node_name, 
                escape(name)
            )
        
        encoding = self.Encoding
        z = zipfile.ZipFile(file_path, "w")
        z.writestr(ARC_MANIFEST, manifest.encode(encoding))
        z.writestr(ARC_DESCRIPTION, descriptions.encode(encoding))
        z.writestr(ARC_DESCRIPTIONS, desc.encode(encoding))
        z.writestr(ARC_ADDONS, addons.encode(encoding))
        if not another:
            z.writestr(ARC_CONTROLLER, controller.encode(encoding))
            z.writestr(ARC_SETTINGS, settings.encode(encoding))
        if data:
            z.writestr(arc_data, data.encode(encoding))
        z.close()
    
    def export(self, url):
        if not self.file_exists(self.package_url):
            raise StandardError("Extension package lost.")
        if self.file_exists(url):
            self.sfa.kill(url)
        self.sfa.copy(self.package_url, url)
    
    def install(self, command_env):
        if not self.file_exists(self.package_url):
            raise StandardError("Extension package lost.")
        manager = self.ctx.getByName(
            "/singletons/com.sun.star.deployment.ExtensionManager")
        ac = manager.createAbortChannel()
        try:
            package = manager.addExtension(
                self.package_url, 
                (), 
                "user", 
                ac, 
                command_env
            )
        except Exception, e:
            print(e)
            return False
        return True

