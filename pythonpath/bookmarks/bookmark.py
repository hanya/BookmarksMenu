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

import copy

class BookmarksDefs(object):
    """ Definition of bookmarks attributes. """
    NAME_ID = "id"
    NAME_TYPE = "type"
    NAME_PARENT = "parent"
    NAME_NAME = "name"
    NAME_COMMAND = "command"
    NAME_DESCRIPTION = "description"
    NAME_CHILDREN = "children"
    NAME_TAGS = "tags"
    
    TYPE_ITEM = "item"
    TYPE_SEPARATOR = "separator"
    TYPE_CONTAINER = "container"


class TypedItem(object):
    
    def is_separator(self):
        """ Check item is separator. """
        return False
    
    def is_container(self):
        """ Check this item is container. """
        return False
    
    def is_item(self):
        """ Check this item is item. """
        return False
    
    def is_tag(self):
        return False
    
    def is_tag_container(self):
        return False


class TagManager(TypedItem):
    
    TAGS_DEFALUT_NAME = "Tags"
    
    def __init__(self):
        self.tags = {}
        self.name = self.TAGS_DEFALUT_NAME
    
    def set_name(self, name):
        self.name = name
    
    def get_name(self):
        return self.name
    
    def get_description(self):
        return ""
    
    def is_tag_container(self):
        return True
    
    def get_children(self):
        tags = [(name, tag) for name, tag in self.tags.iteritems()]
        tags.sort()
        return [item[1] for item in tags]
    
    def get_child_at(self, index):
        return self.get_children()[index]
    
    def get_tag_names(self):
        return list(self.tags.iterkeys())
    
    def get_tags(self):
        return self.tags.iteritems()
    
    def get_tag(self, name, create=False):
        tag = self.tags.get(name, None)
        if create and not tag:
            tag = self.add_tag_group(name)
        return tag
    
    def has_tag(self, name):
        return name in self.tags
    
    def rename_tag(self, old_name, new_name):
        tag = self.tags.pop(old_name, None)
        tag.set_name(new_name)
        self.tags[new_name] = tag
    
    def add_tag_group(self, name, description=""):
        if name:
            tag = self.get_tag(name)
            if not tag:
                tag = TagContainer(name, description)
                self.tags[name] = tag
            return tag
    
    def add_tag_container(self, tag):
        self.tags[tag.get_name()] = tag
    
    def remove_tag(self, name):
        tag = self.tags.pop(name, None)
        if tag:
            for child in tag.get_children():
                child.remove_tag(name)
    
    def update_tags(self, item, add=True):
        if item.is_item():
            self.check_tag(item, add)
        elif item.is_container():
            for child in item.get_children():
                if child.is_item():
                    self.check_tag(child, add)
                elif child.is_container():
                    self.update_tags(child)
    
    def check_tag(self, item, add=True):
        for name in item.get_tags():
            if name:
                tag = self.get_tag(name)
                if add:
                    if not tag:
                        tag = self.add_tag_group(name)
                    tag.append_child(item)
                elif tag:
                    if not tag.remove_child(item):
                        self.remove_tag(name)
    
    def check_tag_for_remove(self, names, item):
        for name in names:
            tag = self.get_tag(name)
            if tag:
                if not tag.remove_child(item):
                    self.remove_tag(name)
    
    def check_tag_containers(self):
        """ Find empty container and remove them, returns removed. """
        removed = []
        for tag in self.tags.itervalues():
            if not tag.check_children():
                removed.append(tag)
        for tag in removed:
            self.tags.pop(tag.get_name())
        return removed


class DescriptiveItem(object):
    """ Item having name and description. """
    def __init__(self, name="", description=""):
        self.name = name
        self.description = description
    
    def __repr__(self):
        return "<%s>" % self.name
        """
        return "<%s.%s: %s, %s, %s at 0x%x>" % (
            self.__class__.__module__, 
            self.__class__.__name__, 
            self.name, 
            self.parent, self.id, id(self))
        """
    def get_name(self):
        """ Returns name of this item. """
        return self.name
    
    def get_description(self):
        """ Returns description of this item. """
        return self.description
    
    def set_name(self, name):
        """ Set name of this item. """
        self.name = name
    
    def set_description(self, description):
        """ Set description of this item. """
        self.description = description


class BaseContainer(TypedItem):
    
    def __init__(self):
        self.children = []
    
    def is_container(self):
        return True
    
    def get_children(self):
        return self.children
    
    def get_child_count(self):
        return len(self.children)
    
    def get_child_at(self, index):
        """ Get child at index. """
        if 0 <= index < self.get_child_count():
            return self.children[index]
        return None
    
    def get_child_index(self, item):
        try:
            return self.children.index(item)
        except:
            return -1


class TagContainer(BaseContainer, DescriptiveItem):
    
    def __init__(self, name, description=""):
        BaseContainer.__init__(self)
        DescriptiveItem.__init__(self, name, description)
    
    def create(o):
        return TagContainer(o["name"], o["description"])
    
    create = staticmethod(create)
    
    def __repr__(self):
        return "<Tag %s>" % self.name
    
    def is_tag(self):
        return True
    
    def is_container(self):
        return False
    
    def set_name(self, name):
        _name = self.name
        self.name = name
        # update tag name
        for item in self.children:
            tags = item.get_tags()
            try:
                tags[tags.index(_name)] = name
            except:
                pass
    
    def append_child(self, item):
        if not item in self.children:
            self.children.append(item)
    
    def remove_child(self, item):
        if item in self.children:
            self.children.remove(item)
        return len(self.children)
    
    def check_children(self):
        """ Check all children and remove child if it has not tag. """
        removing = []
        name = self.name
        for child in self.children:
            if not name in child.get_tags():
                removing.append(child)
        for child in removing:
            self.remove_child(child)
        return len(self.children)
    
    def as_json(self):
        """ Returns JSON-able object. """
        return {
            BookmarksDefs.NAME_NAME: self.name, 
            BookmarksDefs.NAME_DESCRIPTION: self.description
        }


class BookmarksManagerBase(TagManager):
    """ Manages bookmarks. """
    
    def __init__(self):
        TagManager.__init__(self)
        self._id = 0
        self.base = None
        self.containers = {} # id: container
    
    def next_id(self):
        """ Returns next identical number. """
        self._id += 1
        return self._id
    
    def reset_id(self):
        """ Set id to 0. """
        self._id = 0
    
    def get_root(self):
        """ Get root container. """
        return self.base
    
    def clear_containers(self):
        """ Clear containers. """
        self.containers.clear()
    
    def get_parent_container(self, item):
        """ Get parent container of the item. """
        return self.containers.get(item.get_parent(), None)
    
    def duplicate_item(self, item):
        """ Create copy of item. """
        copied = copy.deepcopy(item)
        copied.set_parent(None)
        copied.set_id(self.next_id())
        if copied.is_container():
            self.assign_id(copied)
        return copied
    
    def assign_id(self, container):
        """ Reassin id for container without registering containers. 
            This function is used by duplication.
        """
        parent_id = container.get_id()
        for child in container.get_children():
            child.set_id(self.next_id())
            child.set_parent(parent_id)
            if child.is_container():
                self.assign_id(child)
    
    def reassign_all(self):
        """ Reassign id for base. """
        self.reset_id()
        self.clear_containers()
        base = self.base
        base.set_id(self.next_id())
        self.assign_id(base)
        self.register_container(base, True)
    
    def register_container(self, container, recursive=False):
        """ Register container which can be easily accessed. """
        id = container.get_id()
        if not id is None:
            self.containers[id] = container
        # recursive?
        if container.is_container() and recursive:
            for child in container.get_children():
                if child.is_container():
                    self.register_container(child, True)
    
    def unregister_container(self, container, recursive=False):
        """ Unresiter container from this dict. """
        id = container.get_id()
        if not id is None and id in self.containers:
            self.containers.pop(id)
        if container.is_container() and recursive:
            for child in container.get_children():
                if child.is_container():
                    self.unregister_container(child, True)
    
    def create_separator(self):
        return Separator()
    
    def create_container(self, name="", description=""):
        return Container(name, description)
    
    def create_item(self, name="", description="", command=""):
        return Item(name, description, command)


class BaseItem(BookmarksDefs, TypedItem):
    """ Individual bookmark item. """
    
    ITEM_TYPE = ""
    
    def __init__(self, id=None, parent=None):
        self.id = id
        self.parent = parent
    
    def create(o):
        """ Create new instance from dict. """
        self = BaseItem
        item = None
        type = o[self.NAME_TYPE]
        if type == self.TYPE_ITEM:
            item = Item()
            item.set_command(o.get(self.NAME_COMMAND, ""))
        elif type == self.TYPE_SEPARATOR:
            item = Separator()
        elif type == self.TYPE_CONTAINER:
            item = Container()
            item.children = o.get(self.NAME_CHILDREN, [])#\
            #   [child for child in o.get(self.NAME_CHILDREN, [])]
        else:
            raise TypeError()
        if type == self.TYPE_ITEM or \
            type == self.TYPE_CONTAINER:
            item.set_name(o.get(self.NAME_NAME, ""))
            item.set_description(o.get(self.NAME_DESCRIPTION, ""))
            item.tags = o.get(self.NAME_TAGS, [])
        
        item.set_id(o[self.NAME_ID])
        item.set_parent(o[self.NAME_PARENT])
        return item
    
    create = staticmethod(create)
    
    def get_id(self):
        """ Get item id. """
        return self.id
    
    def get_parent(self):
        """ Get item parent id. """
        return self.parent
    
    def get_type(self):
        """ Get item type. """
        return self.ITEM_TYPE
    
    def set_id(self, id):
        """ Set item id. """
        self.id = id
    
    def set_parent(self, id):
        """ Set parent id. """
        self.parent = id
    
    def has_id(self):
        return not self.id is None
    
    def has_parent(self):
        return not self.parent is None
    
    def as_json(self):
        """ Convert self to JSON-able object. """
        pass


class Separator(BaseItem):
    """ Separator item. """
    ITEM_TYPE = BookmarksDefs.TYPE_SEPARATOR
    
    def __str__(self):
        return "<%s.%s: %s,%s at 0x%x>" % (
            self.__class__.__module__, 
            self.__class__.__name__, self.parent, self.id, id(self))
    
    def is_separator(self):
        """ Check item is separator. """
        return True
    
    def as_json(self):
        return {
            self.NAME_ID: self.id, 
            self.NAME_PARENT: self.parent, 
            self.NAME_TYPE: self.ITEM_TYPE
        }


class Item(BaseItem, DescriptiveItem):
    """ Bookmark entry. """
    
    ITEM_TYPE = BookmarksDefs.TYPE_ITEM
    
    def __init__(self, name="", description="", command="", tags=[]):
        BaseItem.__init__(self)
        DescriptiveItem.__init__(self, name, description)
        self.command = command
        self.options = {}
        self.tags = tags
    
    def is_item(self):
        return True
    
    def has_tag(self, name):
        return name in self.tags
    
    def get_tags(self):
        return self.tags
    
    def set_tags(self, names):
        try:
            while True:
                names.remove("")
        except:
            pass
        self.tags = names
    
    def add_tag(self, name):
        if not name in self.tags:
            self.tags.append(name)
    
    def remove_tag(self, name):
        try:
            self.tags.remove(name)
        except:
            pass
    
    def get_command(self):
        """ Returns item command. """
        return self.command
    
    def set_command(self, text):
        """ Set item commmand. """
        self.command = text
    
    def get_command_only(self):
        """ Returns command without arguments. """
        return self.command.split("?", 1)[0]
    
    def has_arguments(self):
        parts = self.command.split("?", 1)
        return len(parts) == 2 and len(parts[1]) > 0
    
    def as_json(self):
        """ Returns JSON-able object. """
        return {
            self.NAME_ID: self.id, 
            self.NAME_TYPE: self.TYPE_ITEM, 
            self.NAME_PARENT: self.parent, 
            self.NAME_NAME: self.name, 
            self.NAME_COMMAND: self.command, 
            self.NAME_DESCRIPTION: self.description, 
            self.NAME_TAGS: self.tags
        }


class Container(BaseItem, DescriptiveItem, BaseContainer):
    """ Container entry of bookmark can be hold children. """
    
    ITEM_TYPE = BookmarksDefs.TYPE_CONTAINER
    
    def __init__(self, name="", description=""):
        BaseItem.__init__(self)
        DescriptiveItem.__init__(self, name, description)
        self.children = []
    
    def get_child_container_index(self, item):
        if item.is_container():
            n = 0
            for child in self.children:
                if child == item:
                    return n
                if child.is_container():
                    n += 1
        return -1
    
    def get_child_by_id(self, id):
        """ Find child by id. """
        if self.id == id:
            return self
        for child in self.children:
            if child.get_id() == id:
                return child
            if child.is_container():
                found = child.get_child_by_id(id)
                if found:
                    return found
        return None
    
    def insert_child(self, manager, position, item):
        """ Insert item at potision of this container. """
        if item.get_id() is None:
            # do not change item id if it has
            item.set_id(manager.next_id())
        item.set_parent(self.get_id())
        if len(self.children) <= position:
            self.children.append(item)
        else:
            self.children.insert(position, item)
            #self.children[position] = item
        # check the item is already inserted
        if item.is_container():
            manager.register_container(item)
        manager.update_tags(item)
        return self
    
    def insert_children(self, manager, position, items):
        """ Insert items starting at position. """
        #parent_id = self.get_id()
        for i, item in enumerate(items):
            self.insert_child(manager, position + i, item)
        return self
    
    def append_child(self, manager, item):
        """ Append item at last. """
        self.insert_child(manager, self.get_child_count(), item)
        return self
    
    def remove_child(self, manager, item, update_tag=True):
        """ Remove item from this child container if found. """
        self.children.remove(item)
        if item.is_container():
            manager.unregister_container(item, True)
        if update_tag:
            manager.update_tags(item, add=False)
        return item
    
    def remove_child_at(self, manager, index, update_tag=True):
        """ Remove item at index. """
        item = self.get_child_at(index)
        if item:
            self.remove_child(manager, item, update_tag)
        return item
    
    def remove_children_at(self, manager, index, count):
        """ Remove number of children from index. """
        for i in range(count):
            position = index + count - 1 - i
            item = self.get_child_at(position)
            if item:
                self.remove_child(manager, item)
            #if item:
            #    self.children.pop(position)
            #    if item.is_container():
            #        manager.unregister_container(item, True)
    
    def move_child(self, source_index, dest_index):
        """ Move child in the cihldren container. """
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
    
    def swap_children(self, index_a, index_b):
        """ Swap item positions. """
        if 0 <= index_a < len(self.children) and \
            0 <= index_b < len(self.children):
            children = self.children
            item_a = children[index_a]
            item_b = children[index_b]
            children[index_a] = item_b
            children[index_b] = item_a
    
    def as_json(self):
        """ Returns JSON compatible object. """
        return {
            self.NAME_ID: self.id, 
            self.NAME_TYPE: self.TYPE_CONTAINER, 
            self.NAME_PARENT: self.parent, 
            self.NAME_NAME: self.name, 
            self.NAME_DESCRIPTION: self.description, 
            self.NAME_CHILDREN: [child.as_json() for child in self.children]
        }

