#!/usr/bin/env python

import os, os.path

# Generates resource file from each po file.
# And also other configuration stuff too.

# LibreOffice-minimal-version can not be used in compatible package 
# with AOO.

desc_h = """<?xml version='1.0' encoding='UTF-8'?>
<description xmlns="http://openoffice.org/extensions/description/2006"
xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns:d="http://openoffice.org/extensions/description/2006">
<!-- xmlns:l="http://libreoffice.org/extensions/description/2011"> -->
<identifier value="mytools.bookmarks.BookmarksMenu" />
<version value="{VERSION}" />
<dependencies>
<d:OpenOffice.org-minimal-version value="3.4" d:name="OpenOffice.org 3.4" />
<!-- <l:LibreOffice-minimal-version value="4.0" l:name="LibreOffice 4.0" /> -->
</dependencies>
<registration>
<simple-license accept-by="admin" default-license-id="this" suppress-on-update="true" suppress-if-required="true">
<license-text xlink:href="LICENSE" lang="en" license-id="this" />
</simple-license>
</registration>
<display-name>
{NAMES}
</display-name>
<extension-description>
{DESCRIPTIONS}
</extension-description>
<update-information>
<src xlink:href="https://raw.github.com/hanya/BookmarksMenu/master/files/BookmarksMenu.update.xml"/>
</update-information>
</description>"""


update_feed = """<?xml version="1.0" encoding="UTF-8"?>
<description xmlns="http://openoffice.org/extensions/update/2006" 
xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns:d="http://openoffice.org/extensions/description/2006">
<identifier value="mytools.bookmarks.BookmarksMenu" />
<version value="{VERSION}" />
<dependencies>
<d:OpenOffice.org-minimal-version value="3.4" d:name="OpenOffice.org 3.4" />
</dependencies>
<update-download>
<src xlink:href="https://github.com/downloads/hanya/BookmarksMenu/BookmarksMenu-{VERSION}.oxt"/>
</update-download>
</description>
"""


def genereate_description(d):
    version = read_version()
    
    names = []
    for lang, v in d.items():
        name = v["id.OptionsTop.label_title.Label"]
        names.append("<name lang=\"{LANG}\">{NAME}</name>".format(LANG=lang, NAME=name.encode("utf-8")))
    
    descs = []
    for lang, v in d.items():
        desc = v["id.extension.description"]
        with open("descriptions/desc_{LANG}.txt".format(LANG=lang), "w") as f:
            f.write(desc.encode("utf-8"))
        descs.append("<src lang=\"{LANG}\" xlink:href=\"descriptions/desc_{LANG}.txt\"/>".format(LANG=lang))
    
    return desc_h.format(
        VERSION=version, NAMES="\n".join(names), DESCRIPTIONS="\n".join(descs))


def read_version():
    version = ""
    with open("VERSION") as f:
        version = f.read().strip()
    return version


config_h = """<?xml version='1.0' encoding='UTF-8'?>
<oor:component-data 
  xmlns:oor="http://openoffice.org/2001/registry" 
  xmlns:xs="http://www.w3.org/2001/XMLSchema" 
  oor:package="{PACKAGE}" 
  oor:name="{NAME}">"""
config_f = "</oor:component-data>"


class XCUData(object):
    
    PACKAGE = ""
    NAME = ""
    
    def __init__(self):
        self.lines = []
    
    def append(self, line):
        self.lines.append(line)
    
    def add_node(self, name, op=None):
        if op:
            self.append("<node oor:name=\"{NAME}\" oor:op=\"{OP}\">".format(NAME=name, OP=op))
        else:
            self.append("<node oor:name=\"{NAME}\">".format(NAME=name))
    
    def close_node(self):
        self.append("</node>")
    
    def add_prop(self, name, value):
        self.append("<prop oor:name=\"{NAME}\">".format(NAME=name))
        self.append("<value>{VALUE}</value>".format(VALUE=value))
        self.append("</prop>")
    
    def open_prop(self, name):
        self.append("<prop oor:name=\"{NAME}\">".format(NAME=name))
    
    def close_prop(self):
        self.append("</prop>")
    
    def add_value(self, v, locale=None):
        if locale:
            self.append("<value xml:lang=\"{LANG}\">{VALUE}</value>".format(VALUE=v.encode("utf-8"), LANG=locale))
        else:
            self.append("<value>{VALUE}</value>".format(VALUE=v.encode("utf-8")))
    
    def add_value_for_localse(self, name, k, d):
        self.open_prop(name)
        locales = list(d.keys())
        locales.sort()
        for lang in locales:
            _d = d[lang]
            self.add_value(_d[k], lang)
        self.close_prop()
    
    #def _generate(self, d): pass
    
    def generate(self, d):
        self.lines.append(config_h.format(PACKAGE=self.PACKAGE, NAME=self.NAME))
        self._generate(d)
        self.lines.append(config_f)
        return "\n".join(self.lines)


class CommandsXCU(XCUData):
    
    PACKAGE = "org.openoffice.Office.UI"
    NAME = "BookmarksCommands"
    
    def _generate(self, d):
        
        keys = [k for k in d["en-US"] if k.startswith("id.command.")]
        keys.sort()
        
        self.add_node("UserInterface")
        self.add_node("Commands")
        
        for k in keys:
            self.add_node("mytools.bookmarks:" + k[11:], "replace")
            self.add_value_for_localse("Label", k, d)
            self.close_node()
        
        self.close_node()
        self.close_node()


class AddonsTopXCU(XCUData):
    
    PACKAGE = "org.openoffice.Office"
    NAME = "Addons"
    
    def _generate(self, d):
        
        self.add_node("AddonUI")
        self.add_node("OfficeMenuBarMerging")
        self.add_node("mytools.bookmarks.BookmarksMenu", "fuse")
        self.add_node("mytools.bookmarks.BookmarksMenu:top", "replace")
        
        self.add_prop("MergePoint", ".uno:HelpMenu")
        self.add_prop("MergeCommand", "AddBefore")
        self.add_prop("MergeFallback", "AddPath")
        self.add_prop("MergeContext", "")
        
        self.add_node("MenuItems")
        self.add_node("child", "replace")
        
        self.add_value_for_localse("Title", "id.label.bookmarks", d)
        self.add_prop("URL", "mytools.bookmarks.BookmarksMenu:top")
        self.add_prop("Target", "_self")
        self.add_prop("Context", "")
        
        self.close_node()
        self.close_node()
        
        self.close_node()
        self.close_node()
        self.close_node()
        self.close_node()
        

class ToolbarXCU(XCUData):
    
    PACKAGE = "org.openoffice.Office.UI"
    NAME = "BookmarksWindowState"
    
    def _generate(self, d):
        
        keys = [k for k in d["en-US"] if k.startswith("id.toolbar.")]
        keys.sort()
        
        self.add_node("UIElements")
        self.add_node("States")
        
        for i, key in enumerate(keys):
            self.add_node("private:resource/toolbar/{NAME}".format(NAME=key[11:]), "replace")
            self.add_value_for_localse("UIName", key, d)
            self.add_prop("Docked", "true")
            self.add_prop("Visible", "true")
            self.add_prop("ContextSensitive", "false")
            self.add_prop("DockingArea", "0")
            self.add_prop("HideFromToolbarMenu", "false")
            self.add_prop("Locked", "false")
            self.add_prop("NoClose", "false")
            self.add_prop("SoftClose", "false")
            self.add_prop("Style", "0")
            self.add_prop("Pos", "-1,-1")
            if key[11:] == "standardbar":
                v = 0
            elif key[11:] == "insertbar":
                v = 303
            else:
                v = 385
            self.add_prop("DockPos", str(v) + ",0")
            
            self.close_node()
        
        self.close_node()
        self.close_node()


class OptionsXCU(XCUData):
    
    PACKAGE = "org.openoffice.Office"
    NAME = "OptionsDialog"
    
    def _generate(self, d):
        
        self.add_node("Modules")
        self.add_node("mytools.bookmarks.BookmarksMenu", "fuse")
        self.add_node("Nodes")
        self.add_node("mytools.bookmarks.BookmarksMenu.1", "fuse")
        self.close_node()
        self.close_node()
        self.close_node()
        self.close_node()
        
        self.add_node("Nodes")
        self.add_node("mytools.bookmarks.BookmarksMenu.1", "fuse")
        
        self.add_value_for_localse("Label", "id.OptionsTop.label_title.Label", d)
        self.add_prop("OptionsPage", "%origin%/dialogs/OptionsTop.xdl")
        self.add_prop("AllModules", "false")
        
        self.add_node("Leaves")
        self.add_node("mytools.bookmarks.BookmarksMenu:Data", "fuse")
        self.add_prop("Id", "mytools.bookmarks.BookmarksMenu.Data")
        self.add_value_for_localse("Label", "id.options.data", d)
        self.add_prop("OptionsPage", "%origin%/dialogs/OptionsData.xdl")
        self.add_prop("EventHandlerService", "bookmarks.OptionsPageHandler")
        self.add_prop("GroupId", "bookmarks")
        self.add_prop("GroupIndex", "0")
        
        self.close_node()
        
        self.add_node("mytools.bookmarks.BookmarksMenu:Settings", "fuse")
        self.add_prop("Id", "mytools.bookmarks.BookmarksMenu.Settings")
        self.add_value_for_localse("Label", "id.options.settings", d)
        self.add_prop("OptionsPage", "%origin%/dialogs/Options.xdl")
        self.add_prop("EventHandlerService", "bookmarks.OptionsPageHandler")
        self.add_prop("GroupId", "bookmarks")
        self.add_prop("GroupIndex", "1")
        
        self.close_node()
        self.close_node()
        self.close_node()
        self.close_node()


def extract(d, locale, lines):
    msgid = msgstr = id = ""
    for l in lines:
        #if l[0] == "#":
        #    pass
        if l[0:2] == "#,":
            pass
        elif l[0:2] == "#:":
            id = l[2:].strip()
        if l[0] == "#":
            continue
        elif l.startswith("msgid"):
            msgid = l[5:]
        elif l.startswith("msgstr"):
            msgstr = l[6:].strip()
            #print(id, msgid, msgstr)
            if msgstr and id:
                d[id] = msgstr[1:-1].decode("utf-8").replace('\\"', '"')
        _l = l.strip()
        if not _l:
            continue


def as_resource(d):
    lines = []
    
    for k, v in d.items():
        cs = []
        for c in v:
            a = ord(c)
            if a > 0x7f:
                cs.append("\\u%04x" % a)
            else:
                cs.append(c)
        lines.append("%s=%s" % (k, "".join(cs)))
    lines.sort()
    return "\n".join(lines)


def write_options_resource(d):
    name = "dialogs/OptionsTop_{LANG}.properties"
    key1 = "id.OptionsTop.label_description.Label"
    key2 = "id.OptionsTop.label_title.Label"
    for lang, v in d.items():
        _d = {}
        _d[key1] = v[key1]
        _d[key2] = v[key2]
        write_resource(name.format(LANG=lang.replace("-", "_")), _d)


def write_update_feed():
    version = read_version()
    s = update_feed.format(VERSION=version)
    with open("./files/BookmarksMenu.update.xml", "w") as f:
        f.write(s.encode("utf-8"))


def main():
    prefix = "strings_"
    res_dir = "resources"
    
    locales = {}
    
    po_dir = os.path.join(".", "po")
    for po in os.listdir(po_dir):
        if po.endswith(".po"):
            locale = po[:-3]
            try:
                lines = open(os.path.join(po_dir, po)).readlines()
            except:
                print("%s can not be opened")
            d = {}
            extract(d, locale, lines)
            locales[locale] = d
    
    resources_dir = os.path.join(".", res_dir)
    
    for locale, d in locales.items():
        write_resource(os.path.join(resources_dir, 
            "%s%s.properties" % (prefix, locale.replace("-", "_"))), d)
    
    s = AddonsTopXCU().generate(locales)
    with open("Addons_top.xcu", "w") as f:
        f.write(s)#.encode("utf-8"))
    
    s = ToolbarXCU().generate(locales)
    with open("BookmarksWindowState.xcu", "w") as f:
        f.write(s)#.encode("utf-8"))
    s = CommandsXCU().generate(locales)
    with open("BookmarksCommands.xcu", "w") as f:
        f.write(s)#.encode("utf-8"))
    s = OptionsXCU().generate(locales)
    with open("Options.xcu", "w") as f:
        f.write(s)#.encode("utf-8"))
    s = genereate_description(locales)
    with open("description.xml", "w") as f:
        f.write(s)#.encode("utf-8"))
    
    write_options_resource(locales)
    write_update_feed()
    

def write_resource(res_path, d):
    lines = as_resource(d)
    with open(res_path, "w") as f:
        f.write("# comment\n")
        f.write(lines.encode("utf-8"))


if __name__ == "__main__":
    main()
