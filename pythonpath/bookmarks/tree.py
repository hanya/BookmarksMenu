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

from com.sun.star.awt.tree import \
    XTreeDataModel, XTreeNode, TreeDataModelEvent
from com.sun.star.beans import XMaterialHolder


class CustomTreeNode(unohelper.Base, XTreeNode, XMaterialHolder):
    """ Customized tree node which allows to access by Python directly. """
    
    def __init__(self, data_model, name, ondemand):
        self.data_model = data_model
        self.name = name
        self.ondemand = ondemand
        self.parent = None
        self.children = []
        self.data = None
        self.id = 0
        data_model.register_node(self)
    
    def __repr__(self):
        return "<%s.%s: %s>" % (self.__class__.__module__, 
            self.__class__.__name__, self.name)

    def clear(self):
        """ Clear data. """
        self.data_model = data_model
        self.data = None
    
    # XMaterialHolder
    def getMaterial(self):
        """ Returns internal node ID. """
        return self.id
    
    # XTreeNode
    def getChildAt(self, index):
        return self.children[index]
    
    def getChildCount(self):
        return len(self.children)
    
    def getParent(self):
        return self.parent
    
    def getIndex(self, node):
        index = -1
        try:
            index = self.children.index(node)
        except:
            pass
        return index
    
    def hasChildrenOnDemand(self):
        return self.ondemand
    
    def getDisplayValue(self):
        return self.name
    
    def getNodeGraphicURL(self):
        return ""
    
    def getExpandedGraphicURL(self):
        return ""
    
    def getCollapsedGraphicURL(self):
        return ""
    
    def set_name(self, text):
        """ Set display text. """
        self.name = text
        self.data_model.changed((self, ), self.parent)
    
    def get_parent(self):
        """ Get parent node. """
        return self.parent
    
    def set_parent(self, parent):
        """ Set parent node. """
        self.parent = parent
    
    def has_parent(self):
        """ Check node has parent. """
        return not self.parent is None
    
    def get_child_count(self):
        """ Returns number of children. """
        return len(self.children)
    
    def has_children(self):
        """ Check is children. """
        return len(self.children)
    
    def get_children(self):
        """ Retuns list of children. """
        return self.children
    
    def get_child_at(self, index):
        """ Get child by its position. """
        return self.children[index]
    
    def append_child(self, node, broadcast=True):
        """ Append child node. """
        if not node.has_parent():
            self.children.append(node)
            node.set_parent(self)
            if broadcast:
                self.data_model.inserted((node, ), self)
    
    def insert_child(self, index, node):
        """ Insert node at index. """
        self.children.insert(index, node)
        node.set_parent(self)
        self.data_model.inserted((node, ), self)
    
    def remove_child_at(self, index):
        """ Remove specific node at index. """
        try:
            self.children.pop(index)
            self.data_model.removed((node, ), self)
        except:
            pass
    
    def remove_child(self, node):
        """ Remove child node. """
        try:
            self.children.remove(node)
            self.data_model.removed((node, ), self)
        except:
            pass
    
    def get_data(self):
        """ Get data value. """
        return self.data
    
    def set_data(self, data):
        """ Set data value. """
        self.data = data
    
    def find_node_by_data(self, data):
        """ Find node having data as its data. """
        if self.data == data:
            return self
        for child in self.children:
            if child.get_data() == data:
                return child
            if child.has_children():
                found = child.find_node_by_data(data)
                if found:
                    return found
        return None
    
    def in_children(self, node):
        """ Check node is sub node of this node. """
        for child in self.children:
            if child == node:
                return True
            if child.has_children():
                found = child.in_children(node)
                if found:
                    return True
        return False
    
    def in_parent(self, node):
        """ Check node is one of parent in tree. """
        parent = self.parent
        while parent:
            if parent == node:
                return True
            parent = parent.get_parent()
        return False
    
    def move_child(self, source_index, dest_index):
        """ Move inner child container. """
        if 0 <= source_index < len(self.children) and \
            0 <= dest_index < len(self.children) and \
            source_index != dest_index:
            item = self.children[source_index]
            if source_index < dest_index:
                dest_index += 1
            self.children.insert(dest_index, item)
            if source_index > dest_index:
                source_index += 1
            self.children.pop(source_index)
    
    def request_structure_update(self):
        self.data_model.structure_changed(self)


class TreeRootNode(CustomTreeNode):
    """ Root. """
    from bookmarks import EXT_DIR


from com.sun.star.lang import XComponent
class Component(XComponent):
    """ For life-time management. """
    def __init__(self):
        self.event_listeners = []
    
    def dispose(self):
        for listener in self.event_listeners:
            try:
                listener.disposing(self)
            except:
                pass
    
    def addEventListener(self, listener):
        try:
            self.event_listeners.index(listener)
        except:
            self.event_listeners.append(listener)
    
    def removeEventListener(self, listener):
        try:
            self.event_listeners.remove(listener)
        except:
            pass


class CustomTreeDataModel(unohelper.Base, Component, XTreeDataModel):
    """ Keeps CustomTreeNode as nodes. """
    
    def __init__(self):
        Component.__init__(self)
        self.listeners = []
        self.root = None
        self.node_counter = 0
        self.nodes = {} # all child nodes
    
    def register_node(self, node):
        node.id = self.create_node_id()
        self.nodes[node.id] = node
    
    def create_node_id(self):
        self.node_counter += 1
        return self.node_counter
    
    def get_node(self, tree_node):
        try:
            return self.nodes[tree_node.getMaterial()]
        except:
            return None
    
    # XTreeDataModel
    def getRoot(self):
        return self.root
    
    def addTreeDataModelListener(self, listener):
        self.listeners.insert(0, listener)
    
    def removeTreeDataModelListener(self, listener):
        try:
            while True:
                self.listeners.remove(listener)
        except:
            pass
    
    def get_root(self):
        """ Get root node. """
        return self.root
    
    def set_root(self, node):
        """ Set root node. """
        self.root = node
        self.structure_changed(node)
    
    def create_node(self, name, ondemand=False):
        """ Create new node. """
        return CustomTreeNode(self, name, ondemand)
    
    def create_root(self, name, ondemand=False):
        """ Create new root. """
        return TreeRootNode(self, name, ondemand)
    
    def changed(self, nodes, parent):
        self.broadcast("treeNodesChanged", nodes, parent)
    
    def inserted(self, nodes, parent):
        self.broadcast("treeNodesInserted", nodes, parent)
    
    def removed(self, nodes, parent):
        self.broadcast("treeNodesRemoved", nodes, parent)
    
    def structure_changed(self, node):
        self.broadcast("treeStructureChanged", (), node)
    
    def broadcast(self, type, nodes, parent):
        ev = TreeDataModelEvent(self, nodes, parent)
        for listener in self.listeners:
            try:
                getattr(listener, type)(ev)
            except Exception as e:
                print(e)


from bookmarks import ICONS_DIR
is_high_contrast = False

def get_icon_name(name):
    suffix = ".png"
    if is_high_contrast:
        suffix = "_h" + suffix
    return ICONS_DIR + name + suffix


class NodeIcon(object):
    
    def __init__(self):
        self._graphic_url = get_icon_name(self.GRAPHIC_URL)
    
    def getNodeGraphicURL(self):
        return self._graphic_url


class BookmarksNode(object):
    pass


class BookmarksMenuTreeContainerNode(NodeIcon, CustomTreeNode, BookmarksNode):
    
    GRAPHIC_URL = "folder_16"
    
    def __init__(self, datamodel, name, ondemand=True):
        CustomTreeNode.__init__(self, datamodel, name, ondemand)
        NodeIcon.__init__(self)


class BookmarksMenuTreeRootNode(NodeIcon, TreeRootNode, BookmarksNode):
    
    GRAPHIC_URL = "bookmarks_16"
    
    def __init__(self, datamodel, name, ondemand=True):
        CustomTreeNode.__init__(self, datamodel, name, ondemand)
        NodeIcon.__init__(self)


class TagNode(object):
    pass


class TagsTreeContainerNode(NodeIcon, CustomTreeNode, TagNode):
    
    GRAPHIC_URL = "tag_16"
    
    def __init__(self, datamodel, name, ondemand=True):
        CustomTreeNode.__init__(self, datamodel, name, ondemand)
        NodeIcon.__init__(self)


class TagsTreeRootNode(NodeIcon, TreeRootNode, TagNode):
    
    GRAPHIC_URL = "tags_16"
    
    def __init__(self, datamodel, name, ondemand=True):
        TreeRootNode.__init__(self, datamodel, name, ondemand)
        NodeIcon.__init__(self)


class HistoryRootNode(NodeIcon, CustomTreeNode):
    
    GRAPHIC_URL = "history_16"
    
    def __init__(self, datamodel, name, ondemand=True):
        CustomTreeNode.__init__(self, datamodel, name, ondemand)
        NodeIcon.__init__(self)


class UnsortedBookmarksRootNode(NodeIcon, TreeRootNode):
    
    GRAPHIC_URL = "unsorted_16"
    
    def __init__(self, datamodel, name, ondemand=True):
        TreeRootNode.__init__(self, datamodel, name, ondemand)
        NodeIcon.__init__(self)


class BookmarksMenuTreeDataModel(CustomTreeDataModel):
    
    def create_node(self, name, ondemand=True):
        return BookmarksMenuTreeContainerNode(self, name)
    
    def create_root(self, name, ondemand=True):
        return TreeRootNode(self, name, ondemand)
    
    def create_bookmarks_root(self, name, ondemand=True):
        return BookmarksMenuTreeRootNode(self, name, ondemand)
    
    def create_tag_node(self, name, ondemand=False):
        return TagsTreeContainerNode(self, name, ondemand)
    
    def create_tags_root(self, name, ondemand=False):
        return TagsTreeRootNode(self, name, ondemand)
    
    def create_history_root(self, name, ondemand=False):
        return HistoryRootNode(self, name, False)
    
    def create_unsorted_root(self, name, ondemand=True):
        return UnsortedBookmarksRootNode(self, name, True)

