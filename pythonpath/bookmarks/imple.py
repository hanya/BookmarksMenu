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

import traceback

try:
    set()
except:
    from sets import Set as set
from bookmarks import \
    CONFIG_NODE_CONTROLLERS, NAME_TREE_STATE, \
    NAME_WINDOW_STATE, NAME_NAME, DOCUMENT_IMPLE_NAME
from bookmarks.manager import BookmarksManager
from bookmarks.bookmark import TagContainer
from bookmarks.command import BookmarksCommandExecutor
from bookmarks.tools import get_config, get_config_value
from bookmarks.resource import Graphics
from bookmarks.values import Key, KeyModifier

import bookmarks.dispatch as COMMANDS
from bookmarks.tree import HistoryRootNode, \
    BookmarksNode, BookmarksMenuTreeContainerNode, \
    BookmarksMenuTreeRootNode, TagNode, TagsTreeContainerNode, \
    TagsTreeRootNode, UnsortedBookmarksRootNode, TreeRootNode


class History(object):
    """ History management. """
    
    def __init__(self):
        self.current = -1
        self.histories = []
    
    def __str__(self):
        return "<History: %s, %s>" % (self.current, self.histories)
    
    def push(self, item):
        if 0 <= self.current and item == self.histories[self.current]:
            return
        # remove following items
        self.histories[self.current+1:] = []
        self.current += 1
        self.histories.append(item)
    
    def has_next(self):
        """ Check next history is exists. """
        return (0 <= self.current < len(self.histories) -1)
    
    def has_previous(self):
        """ Check previous history is exists. """
        return (1 <= self.current < len(self.histories))
    
    def next(self):
        """ Get next place, current place is moved. """
        if -1 <= self.current < len(self.histories) -1:
            self.current += 1
            return self.histories[self.current]
        return None
    
    def previous(self):
        """ Get previous place, current place is moved. """
        if 1 <= self.current < len(self.histories):
            self.current -= 1
            return self.histories[self.current]
        return None
    
    def get_next_name(self):
        """ Get name of the next place. """
        if self.has_next():
            return self.histories[self.current +1].name
        return None
    
    def get_previous_name(self):
        """ Get name of the previous place. """
        if self.has_previous():
            return self.histories[self.current -1].name
        return None


class Clipboard(object):
    """ Manages copied data. """
    
    def __init__(self):
        self.data = None
    
    def push_data(self, data):
        """ Add copied data. """
        self.data = data
    
    def has_data(self):
        """ Data is kept. """
        return not self.data is None
    
    def get_data(self):
        """ Returns copied data. """
        return self.data


class UndoStack(object):
    """ Keeps task which do undo/redo. """
    
    def __init__(self):
        self.tasks = []
        self.current = -1
    
    def __str__(self):
        return "<UndoStack %s, %s>" % (self.current, self.tasks)
    
    def push(self, task, call=False, controller=None):
        """ Add new task and execute it if required. """
        if call and controller:
            task.redo(controller)
        self.tasks[self.current+1:] = []
        self.current += 1
        self.tasks.append(task)
    
    def can_undo(self):
        """ Check undo-able. """
        return 0 <= self.current < len(self.tasks)
    
    def can_redo(self):
        """ Check redo-able. """
        # next exists
        return -1 <= self.current < len(self.tasks) -1
    
    def do_undo(self, controller):
        """ Execute undo, the task position is moved to previous. """
        # get current and call undo
        if 0 <= self.current < len(self.tasks):
            task = self.tasks[self.current]
            task.undo(controller)
            self.current -= 1
    
    def do_redo(self, controller):
        """ Execute redo, the task position is moved to next. """
        # get next and call redo
        if -1 <= self.current < len(self.tasks) -1:
            task = self.tasks[self.current +1]
            task.redo(controller)
            self.current += 1
    
    def get_undo_name(self):
        """ Get task name of the undo task. """
        if self.can_undo():
            return self.tasks[self.current].name
    
    def get_redo_name(self):
        """ Get task name of the redo task. """
        if self.can_redo():
            return self.tasks[self.current +1].name

class Task(object):
    """ Somethig to do allows undo/redo. """
    
    def __init__(self, name):
        """ name is shown in the tooltip of undo and redo. """
        self.name = name
    
    def undo(self, controller):
        """ Back to previous state. """
        self._undo(controller)
    
    def redo(self, controller):
        """ Proceed processing. """
        self._redo(controller)
    
    def _undo(self, controller): pass
    def _redo(self, controller): pass


class DeleteTagTask(Task):
    """ Delete tag containers. """
    
    def __init__(self, name, tags):
        """ Remove tag containers, tags is removed. """
        Task.__init__(self, name)
        self.tags = tags
    
    def _undo(self, controller):
        # add tag and add tag to children
        manager = controller.manager
        for tag in self.tags:
            manager.add_tag_container(tag)
            name = tag.get_name()
            for child in tag.get_children():
                child.add_tag(name)
        controller.update_tag_tree()
        for tag in self.tags:
            controller.update_data_view(tag.get_children())
    
    def _redo(self, controller):
        # delete tag and remove tag from registered items
        manager = controller.manager
        for tag in self.tags:
            manager.remove_tag(tag.get_name())
        controller.update_tag_tree()
        for tag in self.tags:
            controller.update_data_view(tag.get_children())


class StructureTask(Task):
    """ Task which includes changing of the tree structure. """
    
    def _construct_tree(self, window, parent, container):
        for item in container.get_children():
            if item.is_container():
                node = window.tree_create_node(item.get_name(), True)
                node.set_data(item)
                parent.append_child(node)
                if item.get_child_count():
                    self._construct_tree(window, node, item)


class CutTask(StructureTask):
    """ Cut or delete items. """
    
    def __init__(self, name, parent, positions, items):
        """ The items in the positions are removed from parent. """
        Task.__init__(self, name)
        if not parent.is_container():
            raise TypeError()
        self.parent = parent
        _items = [(position, item) for position, item in zip(positions, items)]
        _items.sort()
        self.positions = [item[0] for item in _items]
        self.items = [item[1] for item in _items]
        self.removed_tags = None
    
    def _undo(self, controller):
        """ Add items to parent at each positions. """
        window = controller.window
        manager =  controller.manager
        parent = self.parent
        
        tree_node = window.tree_get_root_node()
        #parent_tree_node = tree_node.find_node_by_data(parent)
        parent_tree_node = controller.get_node_by_data(parent)
        for position, item in zip(self.positions, self.items):
            parent.insert_child(manager, position, item)
            if item.is_container():
                index = parent.get_child_container_index(item)
                if 0 <= index:
                    node = window.tree_create_node(item.get_name())
                    node.set_data(item)
                    window.tree_insert_node(parent_tree_node, index, node)
                    window.tree_make_visible(node)
                    if item.get_child_count():
                        self._construct_tree(window, node, item)
        
        if controller.check_is_current(parent):
            controller.insert_items_to_current(-1, self.items, self.positions)
            controller.change_display_item()
        controller.update_tag_tree()
        
        if self.removed_tags:
            for name, tag in self.removed_tags.iteritems():
                manager.get_tag(name).set_description(tag.get_description())
    
    def _redo(self, controller):
        """ Delete items from parent at each positions. """
        manager =  controller.manager
        parent = self.parent
        
        if not self.removed_tags:
            tags = dict(manager.tags)
        
        is_current = controller.check_is_current(parent)
        tree_node = controller.window.tree_get_bookmarks_root()
        #parent_tree_node = tree_node.find_node_by_data(parent)
        parent_tree_node = controller.get_node_by_data(parent)
        for position in self.positions[::-1]:
            item = parent.get_child_at(position)
            parent.remove_child_at(manager, position)
            node = parent_tree_node.find_node_by_data(item)
            if node:
                parent_tree_node.remove_child(node)
        
        if is_current:
            controller.remove_items_from_current(positions=self.positions)
            controller.change_display_item()
        controller.update_tag_tree()
        
        if not self.removed_tags:
            _tags = manager.tags
            self.removed_tags = []
            for name in _tags.iterkeys():
                if not name in tags:
                    self.removed_tags.append(tags[name])


class InsertTask(StructureTask):
    """ Insert items. """
    
    def __init__(self, name, parent, position, items):
        """ The items are inserted at position in the parent. """
        Task.__init__(self, name)
        if not parent.is_container():
            raise TypeError()
        self.parent = parent
        self.position = position
        self.items = items
        #self.added_tags = None
    
    def _undo(self, controller):
        """ Remove items from parent starting at position. """
        window = controller.window
        
        is_current = controller.check_is_current(self.parent)
        
        self.parent.remove_children_at(controller.manager, self.position, len(self.items))
        tree_node = window.tree_get_root_node()
        #parent_tree_node = tree_node.find_node_by_data(self.parent)
        parent_tree_node = controller.get_node_by_data(self.parent)
        for item in self.items:
            if item.is_container():
                node = parent_tree_node.find_node_by_data(item)
                if node:
                    parent_tree_node.remove_child(node)
        
        #if controller.check_is_current(self.parent):
        if is_current:
            controller.remove_items_from_current(self.position, len(self.items))
            controller.change_display_item()
        controller.update_tag_tree()
    
    def _redo(self, controller):
        """ Insert items to parent at position. """
        window = controller.window
        manager = controller.manager
        
        self.parent.insert_children(controller.manager, self.position, self.items)
        tree_node = window.tree_get_root_node()
        #parent_tree_node = tree_node.find_node_by_data(self.parent)
        parent_tree_node = controller.get_node_by_data(self.parent)
        for item in self.items:
            if item.is_container():
                index = self.parent.get_child_container_index(item)
                if 0 <= index:
                    node = window.tree_create_node(item.get_name())
                    node.set_data(item)
                    window.tree_insert_node(parent_tree_node, index, node)
                    if item.get_child_count():
                        self._construct_tree(window, node, item)
        
        if controller.check_is_current(self.parent):
            controller.insert_items_to_current(self.position, self.items)
            controller.change_display_item()
        controller.update_tag_tree()


class MoveTask(StructureTask):
    """ Move items to another parent. """
    
    def __init__(self, name, source_container, dest_container, positions_source, positions_dest):
        """ Move items from source_container to dest_container 
        specified their positions. """
        Task.__init__(self, name)
        if not source_container.is_container() or not dest_container.is_container():
            raise TypeError()
        self.source_container = source_container
        self.dest_container = dest_container
        self.positions_source = positions_source
        self.positions_dest = positions_dest
    
    def _undo(self, controller):
        if self.source_container == self.dest_container:
            self._move_inner(controller, self.source_container, self.positions_dest, self.positions_source, restore=True)
        else:
            self._move(controller, self.dest_container, self.source_container, self.positions_dest, self.positions_source)
    
    def _redo(self, controller):
        if self.source_container == self.dest_container:
            self._move_inner(controller, self.source_container, self.positions_source, self.positions_dest)
        else:
            self._move(controller, self.source_container, self.dest_container, self.positions_source, self.positions_dest)
    
    def _move_inner(self, controller, source_container, positions_source, positions_dest, restore=False):
        window = controller.window
        manager = controller.manager
        
        container_changed = False
        #container_node = window.tree_get_root_node().find_node_by_data(source_container)
        container_node = controller.get_node_by_data(source_container)
        
        if restore:
            _source = positions_source[::-1]
            _dest = positions_dest[::-1]
        else:
            _source = positions_source
            _dest = positions_dest
        
        for i, (index_in_source, index_in_dest) in enumerate(zip(_source, _dest)):
            if restore:
                m = len([True for v in positions_source[0:len(_source)-i-1] if index_in_dest < v])
            else:
                m = len([True for v in positions_dest[0:i] if index_in_source < v])
            index_in_source -= m
            index_in_dest -= m
            item_source = source_container.get_child_at(index_in_source)
            if item_source.is_container():
                index_as_container = source_container.get_child_container_index(item_source)
            
            source_container.move_child(index_in_source, index_in_dest)
            
            if item_source.is_container():
                new_index_as_container = source_container.get_child_container_index(item_source)
                if new_index_as_container != index_as_container:
                    container_node.move_child(index_as_container, new_index_as_container)
                container_changed = True
        
        if container_changed:
            container_node.request_structure_update()
        
        if controller.check_is_current(source_container):
            min_index = min((min(positions_source), min(positions_dest)))
            positions = range(min_index, source_container.get_child_count())
            controller.update_rows_in_current(positions)
            controller.change_display_item()
    
    def _move(self, controller, source_container, dest_container, positions_source, positions_dest):
        window = controller.window
        manager = controller.manager
        
        tree_root = window.tree_get_root_node()
        # remove from source
        #source_container_tree_node = tree_root.find_node_by_data(source_container)
        source_container_tree_node = controller.get_node_by_data(source_container)
        items = []
        for position in positions_source[::-1]:
            item = source_container.remove_child_at(manager, position, update_tag=False)
            items.append(item)
            tree_node = source_container_tree_node.find_node_by_data(item)
            if tree_node:
                source_container_tree_node.remove_child(tree_node)
        items.reverse()
        
        # add to dest
        #dest_container_tree_node = tree_root.find_node_by_data(dest_container)
        dest_container_tree_node = controller.get_node_by_data(dest_container)
        for position, item in zip(positions_dest, items):
            dest_container.insert_child(manager, position, item)
            if item.is_container():
                index = dest_container.get_child_container_index(item)
                if 0 <= index:
                    tree_node = window.tree_create_node(item.get_name())
                    tree_node.set_data(item)
                    window.tree_insert_node(dest_container_tree_node, index, tree_node)
                    if item.get_child_count():
                        self._construct_tree(window, tree_node, item)
        # update view
        if controller.check_is_current(source_container):
            try:
                controller.remove_items_from_current(positions=positions_source)
            except:
                pass
            controller.change_display_item()
            
        elif controller.check_is_current(dest_container):
            controller.insert_items_to_current(-1, items, positions_dest)
            controller.change_display_item()


class SetTagDataTask(Task):
    """ Set value to the tag container. """
    
    def __init__(self, name, tag_container, data_type, old_value, new_value):
        """ Set data to tye tag_container. """
        Task.__init__(self, name)
        self.container = tag_container
        self.data_type = data_type
        self.old_value = old_value
        self.new_value = new_value
    
    def _undo(self, controller):
        self._set_data(controller, self.data_type, self.old_value)
    
    def _redo(self, controller):
        self._set_data(controller, self.data_type, self.new_value)
    
    def _set_data(self, controller, data_type, value):
        if data_type == "name":
            manager = controller.manager
            manager.rename_tag(self.container.get_name(), value)
            
            controller.update_tag_tree()
            # update grid view too
            controller.update_data_view(self.container.get_children())
        
        elif data_type == "description":
            self.container.set_description(value)
            if controller.check_is_current(self.container):
                controller.change_display_container()


class ChangeTagTask(Task):
    """ Add or remove tags from items. """
    
    def __init__(self, name, items, added, removed):
        """ Change tags on items. """
        Task.__init__(self, name)
        self.items = items
        self.added = added
        self.removed = removed
        self.removed_tags = None
    
    def _undo(self, controller):
        self._set_tag(controller, self.removed, self.added)
    
    def _redo(self, controller):
        self._set_tag(controller, self.added, self.removed)
    
    def _set_tag(self, controller, added, removed):
        manager = controller.manager
        
        if self.removed_tags:
            #for name, tag in self.removed_tags.iteritems():
            for tag in self.removed_tags:
                manager.add_tag_group(
                    tag.get_name(), tag.get_description())
        
        for name in added:
            tag = manager.get_tag(name, create=True)
            for item in self.items:
                item.add_tag(name)
                tag.append_child(item)
        
        for name in removed:
            for item in self.items:
                item.remove_tag(name)
        # items are removed by the checking
        self.removed_tags = manager.check_tag_containers()
        controller.update_tag_tree()
        controller.update_data_view(self.items)


class SetDataTask(Task):
    """ Change data of item. """
    
    def __init__(self, name, item, data_type, old_value, new_value):
        """ Set data to item. """
        Task.__init__(self, name)
        self.item = item
        self.data_type = data_type
        self.old_value = old_value
        self.new_value = new_value
        self.tag_data = {}
    
    def _undo(self, controller):
        self._set_data(controller, self.data_type, self.old_value, undo=True)
    
    def _redo(self, controller):
        self._set_data(controller, self.data_type, self.new_value)
    
    def _set_data(self, controller, data_type, value, undo=False):
        window = controller.window
        item = self.item
        parent = controller.manager.get_parent_container(item)
        #tree_parent_node = window.tree_get_root_node().find_node_by_data(parent)
        tree_parent_node = controller.get_node_by_data(parent)
        
        if data_type == "name" and \
            (item.is_item() or item.is_container()):
            item.set_name(value)
            if item.is_container():
                tree_container_node = tree_parent_node.find_node_by_data(item)
                if tree_container_node:
                    tree_container_node.set_name(value)
        elif data_type == "command" and item.is_item():
            item.set_command(value)
        elif data_type == "description" and \
            (item.is_item() or item.is_container()):
            self.item.set_description(value)
        
        if controller.check_is_current(parent):
            index = parent.get_child_index(item)
            controller.update_rows_in_current((index,))
            controller.change_display_item()
            
        elif item.is_container():
            if controller.check_is_current(item):
                controller.change_display_item()
        
        controller.update_data_view([self.item])


from com.sun.star.beans import NamedValue
def create_task_frame(ctx, name, rect, title=None, append_to_desktop=False, create=False):
    """ Create system child window. """
    from bookmarks.tools import create_service, get_desktop
    frame = None
    if not create:
        frame = find_empty_frame(ctx)
    if frame is None:
        frame = create_service(ctx, "com.sun.star.frame.TaskCreator").\
            createInstanceWithArguments(
            (
                NamedValue("FrameName", name), 
                NamedValue("PosSize", rect)
            )
        )
    if title:
        frame.setTitle(title)
    if append_to_desktop:
        get_desktop(ctx).getFrames().append(frame)
    return frame


def find_empty_frame(ctx):
    """ Find empty frame. """
    from bookmarks.tools import create_service, get_desktop
    desktop = get_desktop(ctx)
    frames = desktop.getFrames()
    if frames.getCount() == 1:
        frame = desktop.getFrames().getByIndex(0)
        try:
            if frame.getController().supportsService(
                                "com.sun.star.frame.StartModule"):
                return frame
        except Exception, e:
            print(e)
    return None


def load_controller_settings(ctx, command):
    """ Get controller specific settings. """
    d = {}
    config = get_config(ctx, CONFIG_NODE_CONTROLLERS)
    if config.hasByName(command):
        node = config.getByName(command)
        
        tree_state = node.getPropertyValue(NAME_TREE_STATE)
        parts = tree_state.split(":")
        parts_length = len(parts)
        if parts_length:
            d["bookmarks_tree_state"] = parts[0]
        if parts_length > 1:
            d["unsorted_tree_state"] = parts[1]
        if parts_length > 2:
            try:
                d["tags_tree_state"] = int(parts[2])
            except:
                d["tags_tree_state"] = False
        
        # 0: window size, 1: tree width, 2: column state
        window_state = node.getPropertyValue(NAME_WINDOW_STATE)
        parts = window_state.split(";")
        parts_length = len(parts)
        
        if parts_length > 0:
            #d["window_size"] = parts[0]
            window_size = parts[0]
        else:
            window_size = "500,0,640,480"
        
        from com.sun.star.awt import Rectangle
        try:
            d["window_size"] = Rectangle(
                *[int(value) for value in window_size.split(",")]
            )
        except:
            d["window_size"] = Rectangle(500, 0, 640, 480)
        
        if parts_length > 1:
            try:
                d["tree_width"] = int(parts[1])
            except:
                pass
        if not "tree_width" in d:
            d["tree_width"] = 185
        
        if parts_length > 2:
            #d["columns"] = parts[2]
            column_state = parts[2]
        else:
            column_state = ""
        
        if parts_length > 3:
            try:
                d["column_width"] = [int(i) for i in parts[3].split(",")]
            except:
                d["column_width"] = None
        
        names = BookmarksControllerImple.COLUMN_NAMES
        default = {"Name": True, "Tags": True, 
            "Value": True, "Description": True}
        try:
            _parts = column_state.split(",")
            if len(_parts) == 4:
                for i, _part in enumerate(_parts):
                    name = names[i]
                    state = int(_part) == 1
                    default[name] = state
        except:
            pass
        d["columns"] = default
        
        d["name"] = node.getPropertyValue(NAME_NAME)
    return d

def store_controller_settings(ctx, command, window_state, tree_state):
    """ Store window state and tree state to the configuration. """
    config = get_config(ctx, CONFIG_NODE_CONTROLLERS, True)
    if config.hasByName(command):
        node = config.getByName(command)
        node.setPropertyValue(NAME_WINDOW_STATE, window_state)
        node.setPropertyValue(NAME_TREE_STATE, tree_state)#state["tree_state"])
        config.commitChanges()

def get_factory_config(ctx, name):
    return get_config(ctx, "/org.openoffice.Setup/Office/Factories").\
        getByName(DOCUMENT_IMPLE_NAME).getPropertyValue(name)


from bookmarks.bookmark import TypedItem

class HistoryItemManager(TypedItem):
    """ Mimics container to show history entries. """
    
    DEFAULT_NAME = "History"
    
    HISTORY_NODE = "/org.openoffice.Office.Common/History"
    HISTORIES_NODE = "/org.openoffice.Office.Histories/Histories/"
    INFO_TEMPLATE = "org.openoffice.Office.Histories:HistoryInfo['%s']"
    
    NAME_PICKLIST = "PickList"
    #NAME_URL = "URLHistory"
    NAME_ITEMLIST = "ItemList"
    NAME_ORDERLIST = "OrderList"
    #NAME_PICKLIST_SIZE = "PickListSize"
    #NAME_SIZE = "Size"
    
    def __init__(self, ctx, manager, commands, name="History"):
        self.ctx = ctx
        self.manager = manager
        self.commands = commands
        self.items = None
        self.name = name
    
    def get_name(self):
        return self.name
    
    def get_description(self):
        return ""
    
    def is_container(self):
        return True
    
    def get_children(self):
        try:
            manager = self.manager
            d = {"type": "document", "path": None, "filter": None}
            list_items = self.load_pick_list()
            items = []
            for item in list_items:
                d["path"] = item[0]
                d["filter"] = item[2]
                items.append(
                    manager.create_item(
                        item[1], "", self.commands.generate_command(d)))
            self.items = items
            return items
        except Exception, e:
            print(e)
        return ()
    
    def get_child_at(self, index):
        return self.items[index]
    
    def load_pick_list(self):
        """ Load history entry from PickList. """
        config = get_config(self.ctx, 
            self.HISTORIES_NODE + (self.INFO_TEMPLATE % self.NAME_PICKLIST))
        order = config.getPropertyValue(self.NAME_ORDERLIST)
        ordered_urls = [(int(name), order.getByName(name).HistoryItemRef) 
                            for name in order.getElementNames()]
        ordered_urls.sort()
        
        item_list = config.getPropertyValue(self.NAME_ITEMLIST)
        # url, title, filter
        items = []
        for n, url in ordered_urls:
            try:
                item = item_list.getByName(url)
                items.append((url, item.Title, item.Filter))
            except:
                pass
        return items


class BookmarksControllerImple(object):
    """ Controller for bookmarks window. """
    
    CONTROLLERS = {}
    LOCKS = {}
    
    def get(ctx, command):
        klass = BookmarksControllerImple
        controller = klass.CONTROLLERS.get(command, None)
        if controller is None:
            controller = klass(ctx, command)
            klass.CONTROLLERS[command] = controller
        return controller
    
    def find(command):
        return BookmarksControllerImple.CONTROLLERS.get(command, None)
    
    def remove(command):
        klass = BookmarksControllerImple
        klass.CONTROLLERS.pop(command, None)
    
    def lock(command):
        klass = BookmarksControllerImple
        klass.LOCKS[command] = 1
        controller = klass.find(command)
        if controller:
            controller._lock()
    
    def unlock(command):
        klass = BookmarksControllerImple
        klass.LOCKS.pop(command, 0)
        controller = klass.find(command)
        if controller:
            controller._unlock()
    
    def is_locked(command):
        return command in BookmarksControllerImple.LOCKS
    
    get = staticmethod(get)
    find = staticmethod(find)
    remove = staticmethod(remove)
    lock = staticmethod(lock)
    unlock = staticmethod(unlock)
    is_locked = staticmethod(is_locked)
    
    FACTORY_NAME = None
    COLUMN_NAMES = ("Name", "Tags", "Value", "Description")
    
    MODE_ROOT = 1
    MODE_HISTORY = 2
    MODE_BOOKMRAKS = 4
    MODE_TAG = 8
    MODE_UNSORTED = 16
    
    def __init__(self, ctx, command):
        import bookmarks.window
        window = bookmarks.window.BookmarksWindow.get(command)
        if window:
            raise StandardError()
        
        self.ctx = ctx
        self.command = command
        self._locked = False
        
        import bookmarks
        import bookmarks.tools
        import bookmarks.controller
        import bookmarks.model
        import bookmarks.util
        import bookmarks.tree
        self.res = bookmarks.tools.get_current_resource(
                            ctx, bookmarks.RES_DIR, bookmarks.RES_FILE)
        self.history = History()
        self.undostack = UndoStack()
        self.clipboard = Clipboard()
        
        self.filter_manager = bookmarks.tools.FileFilterManager(ctx, self._("All files (*.*)"))
        self._init_data_labels()
        settings = load_controller_settings(self.ctx, command)
        self.manager = BookmarksManager.get(self.ctx, command, settings["name"])
        self.manager.set_name(self.manager.TAGS_DEFALUT_NAME)
        
        if self.__class__.FACTORY_NAME is None:
            self.__class__.FACTORY_NAME = \
                get_factory_config(self.ctx, "ooSetupFactoryUIName")
        
        self.column_state = settings.get("columns")
        columns = [(label, self.column_state[label]) 
                        for label in self.COLUMN_NAMES]
        settings["columns"] = columns
        settings["title"] = "%s - %s" % (
            self.manager.bookmark_name, self.__class__.FACTORY_NAME)
        
        frame = create_task_frame(
            self.ctx, 
            self.__class__.__name__, 
            settings.get("window_size"), 
            settings.get("title", "Bookmarks"), 
            append_to_desktop=True, 
            create=False
        )
        is_high_contrast = frame.getContainerWindow().StyleSettings.HighContrastMode
        bookmarks.tree.is_high_contrast = is_high_contrast
        # do not instantiate before the frame
        self.graphics = Graphics.get(ctx, is_high_contrast)
        self.commands = BookmarksCommandExecutor(self, ctx, frame, command)
        self.histories = HistoryItemManager(
            self.ctx, 
            self.manager, 
            self.commands, 
            self._(HistoryItemManager.DEFAULT_NAME)
        )
        
        model = bookmarks.model.Model(self.ctx, self)
        self.controller = model.createDefaultViewController(frame)
        self.controller.attachModel(model)
        self.window = bookmarks.window.BookmarksWindow.create(
            ctx, frame, command, self.controller, self.res, settings)
        
        self._init_tree(settings)
        if self.__class__.is_locked(self.command):
            self._lock()
    
    def _init_tree(self, settings):
        """ Construct tree. """
        import bookmarks
        window = self.window
        window.regulator.enable_tree_change(False)
        
        # histories
        history_root_node = window.tree_create_history_root(
                self._(HistoryItemManager.DEFAULT_NAME))
        history_root_node.set_data(self.histories)
        window.tree_get_root_node().append_child(history_root_node)
        
        # fill tags in the tree
        tags_root_node = window.tree_create_tags_root(
            self._(self.manager.TAGS_DEFALUT_NAME))
        tags_root_node.set_data(self.manager)
        window.tree_get_root_node().append_child(tags_root_node)
        tags = [(name, tag) for name, tag in self.manager.tags.iteritems()]
        tags.sort()
        for name, tag in tags:
            tag_node = window.tree_create_tag_node(name)
            tag_node.set_data(tag)
            tags_root_node.append_child(tag_node)
        
        # fill unsorted
        unsorted_root_node = window.tree_create_unsorted_root(
            self._(self.manager.UNSORTED_DEFAULT_NAME))
        self.window.tree_get_root_node().append_child(unsorted_root_node)
        bookmarks.util.fill_tree(
            window, self.manager.unsorted, unsorted_root_node)
        
        # fill bookmarks in the tree
        bookmarks_root_node = window.tree_create_bookmarks_root(
            self._(self.manager.DEFAULT_NAME))
        window.tree_get_root_node().append_child(bookmarks_root_node)
        bookmarks.util.fill_tree(
            window, self.manager.get_root(), bookmarks_root_node, False)
        window.tree_get_bookmarks_root().set_name(self._(self.manager.DEFAULT_NAME))
        self.manager.base.set_name(self._(self.manager.DEFAULT_NAME))
        window.tree_show_root(True)
        window.tree_show_root(False)
        
        window.regulator.reset()
        #window.show_window_contents()
        window.regulator.update_tree_selection()
        window.regulator.enable_tree_change(True)
        
        window.tree_set_selection(
            window.tree_get_bookmarks_root())
        self.change_display_container()
        try:
            bookmarks.util.restore_tree_node_expanded_state(
                window, 
                window.tree_get_bookmarks_root(), 
                settings.get("bookmarks_tree_state", ""))
            bookmarks.util.restore_tree_node_expanded_state(
                window, 
                window.tree_get_unsorted_root(), 
                settings.get("unsorted_tree_state", ""))
        except Exception, e:
            print(e)
            traceback.print_exc()
        if settings.get("tags_tree_state", 0):
            window.tree_expand_node(tags_root_node)
        window.show_window_contents()
    
    def _(self, name):
        return self.res.get(name, name)
    
    def _lock(self):
        self._locked = True
        if self.window:
            self.window.lock()
        if self.controller:
            self.controller.lock()
    
    def _unlock(self):
        if self.window:
            self.window.unlock()
        if self.controller:
            self.controller.unlock()
        self._locked = False
    
    def move_to_front(self):
        self.window.move_to_front()
    
    def window_closed(self):
        """ When window closed. """
        try:
            from bookmarks.util import get_tree_node_expanded_state
            tree_state = (
                get_tree_node_expanded_state(
                    self.window, self.window.tree_get_bookmarks_root()), 
                get_tree_node_expanded_state(
                    self.window, self.window.tree_get_unsorted_root()), 
                str(int(self.window.tree_is_node_expanded(
                    self.window.tree_get_tags_root())))
            )
            store_controller_settings(
                self.ctx, 
                self.command, 
                self.controller.getViewData(), 
                ":".join(tree_state)
            )
        except Exception, e:
            print(e)
        self.window.closed()
        self.window = None
        self.manager = None
        self.ctx = None
        self.__class__.remove(self.command)
    
    def _init_data_labels(self):
        _ = self._
        # type name: (label for value 1, label for value 2)
        self.data_labels = {
            "document": (_("Document"), _("File filter")), 
            "macro": (_("Macro"), ""), 
            "command": (_("Command"), _("Arguments")), 
            "program": (_("Program"), _("Arguments")), 
            "file": (_("Path"), ""), 
            "folder": (_("Path"), ""), 
            "web": (_("Path"), ""), 
            "directory_popup": (_("Path"), _("File filter")), 
            "tag": (_("Tag name"), ""), 
        }
    
    def history_push(self, item):
        """ Proceed history. """
        self.history.push(item)
        self.controller.update_history_state()
    
    def push_task(self, task):
        """ New task and do it. """
        try:
            self.undostack.push(task, True, self)
            self.manager.set_modified()
            self.controller.update_undo_redo_state()
            self.controller.update_save_state()
        except Exception, e:
            print(e)
            traceback.print_exc()
    
    def check_is_current(self, container):
        """ Check container is current selected item on tree. """
        tree_node = self.window.tree_get_selection()
        return tree_node and tree_node.get_data() == container
    
    def check_item_is_container(self, index):
        """ Check specific item specified by index is container. """
        tree_node = self.window.tree_get_selection()
        if tree_node:
            parent = tree_node.get_data()
            if 0 <= index < parent.get_child_count():
                child = parent.get_child_at(index)
                return child.is_container()
        return False
    
    def change_display_container(self):
        """ Change container to show its contents. """
        window = self.window
        tree_node = window.tree_get_selection()
        if tree_node:
            try:
                container = tree_node.get_data()
                # show container data
                if self.get_view_mode() & self.MODE_ROOT:
                    type = window.TYPE_ROOT
                else:
                    type = window.TYPE_FOLDER
                window.update_data_state(type)
                window.update_data(container.get_name(), container.get_description())
                
                # set children in grid
                window.regulator.inhibit_grid_selection_change()
                self.insert_items_to_current(0, container.get_children(), replace=True)
                self.history_push(container)
                window.regulator.inhibit_grid_selection_change(False)
            except Exception, e:
                traceback.print_exc()
                print(e)
    
    def insert_items_to_current(self, position, items, positions=None, replace=False):
        """ Insert item into grid, not the container. """
        window = self.window
        graphics = self.graphics
        separator = self.get_separator_row()
        remaines = ["" for i in range(len(separator) -2)]
        commands = self.commands
        res = self.res
        
        state_tags = self.column_state["Tags"]
        state_value = self.column_state["Value"]
        state_desc = self.column_state["Description"]
        
        rows = []
        for item in items:
            if item.is_item():
                rows.append(
                    commands.extract_as_row(
                        res, item, graphics, 
                        state_value, state_desc, state_tags))
            elif item.is_separator():
                rows.append(separator)
            elif item.is_container():
                rows.append(tuple([graphics["container"], item.get_name()] + remaines))
            elif item.is_tag():
                data = [self.graphics["tag"], item.get_name()]
                if state_tags:
                    data.append("")
                if state_value:
                    data.append("")
                if state_desc:
                    data.append(item.get_description())
                rows.append(tuple(data))
        
        if replace:
            window.grid_set_rows(tuple(rows))
        else:
            if not positions is None:
                for position, row in zip(positions, rows):
                    window.grid_insert_row(position, row)
            else:
                window.grid_insert_rows(position, tuple(rows))
        window.grid_redraw()
        window.grid_reset_size()
    
    def remove_items_from_current(self, position=None, count=None, positions=None):
        """ Remove items from grid, not from the container. """
        self.window.grid_remove_rows(position, count, positions)
        self.window.grid_redraw()
    
    def update_rows_in_current(self, positions):
        """ Update rows. """
        window = self.window
        tree_node = window.tree_get_selection()
        container = tree_node.get_data()
        
        graphics = self.graphics
        separator = self.get_separator_row()
        remaines = ["" for i in range(len(separator) -2)]
        
        num_columns = 2
        if self.column_state["Tags"]:
            num_columns += 1
        if self.column_state["Value"]:
            num_columns += 1
        if self.column_state["Description"]:
            num_columns += 1
        columns = range(num_columns)
        for position in positions:
            item = container.get_child_at(position)
            if item:
                if item.is_item():
                    row = self.extract_as_grid_row(item)
                elif item.is_separator():
                    row = separator
                elif item.is_container():
                    row = tuple([graphics["container"], item.get_name()] + remaines)
                window.grid_update_row(tuple(columns), position, row)
        window.grid_redraw()
    
    
    def extract_as_grid_row(self, item):
        """ Command to strings for grid view. """
        return self.commands.extract_as_row(
            self.res, 
            item, 
            self.graphics, 
            self.column_state["Value"], 
            self.column_state["Description"], 
            self.column_state["Tags"]
        )
    
    def get_separator_row(self):
        long_sep = self.graphics["long_separator"]
        row = [self.graphics["separator"], long_sep]
        if self.column_state["Tags"]:
            row.append(long_sep)
        if self.column_state["Value"]:
            row.append(long_sep)
        if self.column_state["Description"]:
            row.append(long_sep)
        return tuple(row)
    
    def get_shared_tags(self, items):
        """ Get common tags among items. """
        if items:
            tags = set(items[0].get_tags())
            for item in items[1:]:
                tags = tags.intersection(item.get_tags())
        tags = list(tags)
        tags.sort()
        return tags
    
    def change_display_item(self, mode=None):
        """ Change item to show its data. """
        window = self.window
        is_root = False
        if mode is None:
            mode = window.regulator.get_mode()
        if mode == window.MODE_TREE:
            tree_node = window.tree_get_selection()
            item = tree_node.get_data()
            is_root = isinstance(tree_node, TreeRootNode)
        else:
            #item = self.get_single_selection()
            parent = window.tree_get_selection().get_data()
            item = self.get_selected_items(parent)
            if len(item) == 1:
                item = item[0]
        
        if not item:
            window.update_data_state(window.TYPE_NONE)
            window.update_data()
            return
        
        if isinstance(item, list):
            # multiple selection on the grid allows to change tag only
            #if all([i.is_item() for i in item]):
            if len([True for i in item if i.is_item()]) == len(item):
                # show only shared tags
                tags = self.get_shared_tags(item)
                window.update_data_state(window.TYPE_TAGS)
                window.update_data(tag=",".join(tags))
            else:
                window.update_data_state(window.TYPE_NONE)
                window.update_data()
        
        elif item.is_item():
            item_type, data = self.commands.extract(item)
            label_value1, label_value2 = \
                    self.data_labels.get(item_type, ("", ""))
            state_btn_value2 = item_type in ("command", "document")
            
            window.update_data_state(
                window.TYPE_ITEM, label_value1, label_value2, state_btn_value2)
            window.update_data(*data)
        
        elif item.is_separator():
            window.update_data_state(window.TYPE_NONE)
            window.update_data()
        else:
            name = item.get_name()
            description = item.get_description()
            if is_root:
                data_type = window.TYPE_ROOT
            else:
                data_type = window.TYPE_FOLDER
            window.update_data_state(data_type)
            window.update_data(name, description)
    
    def multiple_selection_tag_update(self):
        """ Update tag for multiple selections. """
        window = self.window
        regulator = window.regulator
        
        selections = regulator.get_grid_selection()
        if not selections:
            return
        parent = window.tree_get_selection().get_data()
        items = [parent.get_child_at(i) for i in selections]
        
        shared_tags = set(self.get_shared_tags(items))
        
        task_name = self._("Change tag")
        tags = regulator.get_data_value(window.ID_DATA_EDIT_TAGS).split(",")
        try:
            while True:
                tags.remove("")
        except:
            pass
        tags = set(tags)
        
        added_tags = tags.difference(shared_tags)
        removed_tags = shared_tags.difference(tags)
        
        task = ChangeTagTask(task_name, items, added_tags, removed_tags)
        self.push_task(task)
    
    def data_update_request(self, mode, update_mode):
        """ Update data of current item. """
        window = self.window
        regulator = window.regulator
        item = None
        if mode == window.MODE_TREE:
            item = window.tree_get_selection().get_data()
        else:
            selections = regulator.get_grid_selection()
            if not selections or len(selections) != 1:
                if update_mode == window.ID_DATA_EDIT_TAGS:
                    self.multiple_selection_tag_update()
                return
            current_node = window.tree_get_selection()
            container = current_node.get_data()
            item = container.get_child_at(selections[0])
            if item.is_item() and \
                (update_mode == window.ID_DATA_EDIT_VALUE1 or \
                update_mode == window.ID_DATA_EDIT_VALUE2):
                task_name = self._("Change bookmark")
                data_type = "command"
                value1 = regulator.get_data_value(window.ID_DATA_EDIT_VALUE1)
                value2 = regulator.get_data_value(window.ID_DATA_EDIT_VALUE2)
                
                item_type, row_data = self.commands.extract(item)
                d = {"type": item_type}
                if item_type == "document":
                    d["path"] = value1
                    d["filter"] = value2
                elif item_type == "command":
                    d["command"] = value1
                    d["arguments"] = value2
                elif item_type == "macro":
                    d["command"] = value1
                elif item_type == "program":
                    d["path"] = value1
                    d["arguments"] = value2
                elif item_type in ("file", "folder", "web"):
                    d["type"] = "something"
                    d["flag"] = item_type
                    d["path"] = value1
                elif item_type == "directory_popup":
                    d["type"] = "special"
                    d["flag"] = "directory_popup"
                    d["path"] = value1
                    if value2:
                        d["filter"] = value2
                    d["create"] = True
                elif item_type == "tag":
                    d["tag_name"] = value1
                #print(item_type)
                command = self.commands.generate_command(d)
                new_value = command
                old_value = item.get_command()
        if not item:
            return
        if update_mode == window.ID_DATA_EDIT_NAME:
            task_name = self._("Change name")
            data_type = "name"
            new_value = regulator.get_data_value(window.ID_DATA_EDIT_NAME)
            old_value = item.get_name()
        elif update_mode == window.ID_DATA_EDIT_DESCRIPTION:
            task_name = self._("Change description")
            data_type = "description"
            new_value = regulator.get_data_value(window.ID_DATA_EDIT_DESCRIPTION)
            old_value = item.get_description()
        elif update_mode == window.ID_DATA_EDIT_TAGS:
            task_name = self._("Change tag")
            data_type = "tag"
            tags = regulator.get_data_value(window.ID_DATA_EDIT_TAGS).split(",")
            try:
                while True:
                    tags.remove("")
            except:
                pass
            _new_value = set([name.strip() for name in tags])
            _old_value = set(item.get_tags())
            new_value = _new_value - _old_value
            old_value = _old_value - _new_value
        
        if new_value != old_value:
            if item.is_tag():
                task = SetTagDataTask(task_name, item, data_type, old_value, new_value)
            else:
                if update_mode == window.ID_DATA_EDIT_TAGS:
                    task = ChangeTagTask(task_name, [item], new_value, old_value)
                else:
                    task = SetDataTask(task_name, item, data_type, old_value, new_value)
            self.push_task(task)
    
    def get_value2(self):
        """ Input value2 by helping with dialog. """
        command = None
        window = self.window
        if window.get_mode() != window.MODE_GRID:
            return
        item = self.get_single_selection()
        if not item:
            return
        item_type, row_data = self.commands.extract(item)
        
        if item_type == "command":
            from bookmarks.dialogs import ArgumentsDialog
            
            main, protocol, path, query = \
                self.commands.bk_command_parse(item.get_command())
            qs = self.commands.bk_parse_qs(query)
            
            result = ArgumentsDialog(
                self.ctx, self.res, query=qs
            ).execute()
            if result:
                command = item.get_command_only() + "?" + \
                    self.commands.bk_urlencode(result)
        
        elif item_type == "document":
            from bookmarks.dialogs import FileFilterDialog
            
            default = self.filter_manager.get_ui_name(row_data[3])
            
            result = FileFilterDialog(
                self.ctx, self.res, 
                filter_manager=self.filter_manager, 
                default=default
            ).execute()
            if result:
                filter_name = self.filter_manager.get_internal_name(result)
                d = {"type": "document", "path": row_data[2], "filter": filter_name}
                command = self.commands.generate_command(d)
        
        else:
            return
        
        if command and command != item.get_command():
            task = SetDataTask(
                self._("Change bookmark"), 
                item, "command", item.get_command(), command)
            self.push_task(task)
    
    def get_value1(self):
        """ Input value1. """
        window = self.window
        if window.get_mode() != window.MODE_GRID:
            return
        item = self.get_single_selection()
        if not item:
            return
        command = None
        item_type, row_data = self.commands.extract(item)
        
        if item_type == "command":
            from bookmarks.dialogs import CommandsDialog
            result = CommandsDialog(self.ctx, self.res).execute()
            if result:
                d = {"command": result, "arguments": row_data[3]}
                command = self.commands.generate_command(d)
        
        elif item_type == "macro":
            from bookmarks.dialogs import MacroSelectorDialog
            result = MacroSelectorDialog(self.ctx, self.res).execute()
            if result:
                command = result
        
        elif item_type in ("document", "program"):
            from bookmarks.dialog import FileOpenDialog
            result = FileOpenDialog(
                self.ctx, self.res, 
                default=row_data[2]
            ).execute()
            if result:
                d = {"type": item_type, "path": result}
                if item_type == "document":
                    filter_name = self.commands.get_query_value(
                        item.get_command(), self.commands.QUERY_NAME_FILTER_NAME)
                    if filter_name:
                        d["filter"] = filter_name
                
                elif item_type == "program":
                    arguments = self.commands.get_query_value(
                        item.get_command(), self.commands.QUERY_NAME_ARGUMENTS)
                    if arguments:
                        d["arguments"] = arguments
                command = self.commands.generate_command(d)
        
        elif item_type in ("file", "folder", "web"):
            from bookmarks.dialog import FileOpenDialog, FolderDialog
            if item_type == "folder":
                result = FolderDialog(self.ctx, self.res, 
                    default=row_data[2]).execute()
            else:
                result = FileOpenDialog(self.ctx, self.res, 
                    directory=row_data[2]).execute()
            if result:
                d = {"type": "something", "flag": item_type, "path": result}
                command = self.commands.generate_command(d)
        
        elif item_type == "directory_popup":
            from bookmarks.dialog import FolderDialog
            result = FolderDialog(
                self.ctx, self.res, 
                directory=row_data[2]
            ).execute()
            if result:
                from bookmarks import DIRECTORY_POPUP_URI
                filter_name = self.commands.get_query_value(
                    item.get_command(), self.commands.QUERY_NAME_FILTER)
                qs = DIRECTORY_POPUP_URI + "?" + self.commands.bk_urlencode(
                    {
                        self.commands.QUERY_NAME_URL: result, 
                        self.commands.QUERY_NAME_FILTER: filter_name
                    }
                )
                d = {"type": "special", "flag": "directory_popup", 
                    "path": qs}
                command = self.commands.generate_command(d)
        
        elif item_type == "tag":
            from bookmarks.dialogs import TagNameListDialog
            result = TagNameListDialog(
                self.ctx, self.res, 
                default=row_data[2], 
                tags=self.manager.get_tag_names()
            ).execute()
            if result:
                d = {"type": "tag", "tag_name": result}
                command = self.commands.generate_command(d)
        
        else:
            return
        
        if command and command != item.get_command():
            task = SetDataTask(
                self._("Change bookmark"), item, "command", item.get_command(), command)
            self.push_task(task)
    
    def get_single_selection(self):
        """ Check and get item if only a row is selected. """
        window = self.window
        if window.grid_get_selection_count() == 1:
            tree_node = window.tree_get_selection()
            container = tree_node.get_data()
            index = window.grid_get_single_selection()
            if 0 <= index:
                item = container.get_child_at(index)
                if item:
                    return item
        return None
    
    def create_tag_item(self, data):
        """ Create new tag item from tag container. """
        tag_name = data.get_name()
        d = {
            "type": "tag", 
            "tag_name": tag_name
        }
        command = self.commands.generate_command(d)
        item = self.manager.create_item(tag_name)
        item.set_command(command)
        return item
    
    def move_from_tree(self, data_node, pos_type, dest_node=None, dest_index=None, is_copy=False):
        """ Move item inside tree, by drag and drop. 
            Not allowed to move tree to grid. """
        window = self.window
        if data_node == window.tree_get_root_node():
            return # root cannot be moved
        source_container_node = data_node.get_parent()
        source_container = source_container_node.get_data()
        
        if not dest_node:
            return
        # inside tree
        if dest_node == window.tree_get_root_node() and \
            pos_type != window.POSITION_ITEM:
            return # there is no above or below for root
        if not is_copy and \
            (data_node == dest_node or dest_node.in_parent(data_node)):
            return # cannot move itself
        if isinstance(dest_node, TagNode):
            return # bookmarks container can not move to the tag
        
        dest = dest_node.get_data()
        
        if pos_type == window.POSITION_ITEM:
            index_in_dest = dest.get_child_count()
            dest_container = dest
            if not is_copy and source_container == dest_container:
                index_in_dest -= 1
        else:
            dest_parent = dest_node.get_parent().get_data()
            index_in_dest = dest_parent.get_child_index(dest)
            if pos_type == window.POSITION_BELOW:
                index_in_dest += 1
            dest_container = dest_parent
        
        if isinstance(data_node, TagsTreeContainerNode):
            # drag and drop the tag node creates pop-pu menu for tag
            data = data_node.get_data()
            item = self.create_tag_item(data)
            task = InsertTask(
                self._("Insert item"), 
                dest_container, 
                index_in_dest, 
                (item,))
            self.push_task(task)
            return
        
        if is_copy:
            task = InsertTask(
                self._("Paste"), 
                dest_container, 
                index_in_dest, 
                (self.manager.duplicate_item(data_node.get_data()),))
        else:
            index_in_source = source_container.get_child_index(data_node.get_data())
            task = MoveTask(
                self._("Move"), 
                source_container, dest_container, 
                (index_in_source,), (index_in_dest,))
        self.push_task(task)
        # do not allow to copy from tree to grid
    
    
    def move_from_grid(self, data_positions, pos_type, dest_node=None, dest_index=None, is_copy=False):
        """ Move item from grid to somewhere, by drag and drop. """
        if not data_positions:
            return
        window = self.window
        data_positions = list(data_positions)
        data_positions.sort()
        
        source_container = window.tree_get_selection().get_data()
        if dest_node:
            # grid to tree
            dest = dest_node.get_data()
            if source_container == dest:
                return
            if isinstance(dest_node, HistoryRootNode) or \
                isinstance(dest_node, TagsTreeRootNode):
                return
            
            if not isinstance(dest_node, BookmarksMenuTreeContainerNode):
                pos_type = window.POSITION_ITEM
            if pos_type == window.POSITION_ITEM:
                dest_index = dest.get_child_count()
            else:
                # destination is parent of the dest_node
                dest_parent = dest_node.get_parent().get_data()
                dest_index = dest_parent.get_child_index(dest)
                if pos_type == window.POSITION_BELOW:
                    dest_index += 1
                dest = dest_parent
            
            if isinstance(dest_node, TagsTreeContainerNode):
                # set tag
                tag = dest_node.get_data()
                items = [item for item in self.get_selected_items(source_container) if item.is_item()]
                if items:
                    task = ChangeTagTask(self._("Change tag"), items, [tag.get_name()], ())
                    self.push_task(task)
                return
            
            if is_copy:
                items = [self.manager.duplicate_item(source_container.get_child_at(position)) 
                            for position in data_positions]
                task = InsertTask(self._("Copy"), dest, dest_index, items)
            else:
                dest_positions = range(dest_index, dest_index + len(data_positions))
                task = MoveTask(
                    self._("Move"), 
                    source_container, dest, 
                    data_positions, dest_positions)
            self.push_task(task)
        
        elif not dest_index is None:
            # inside grid
            if not (0 <= dest_index < source_container.get_child_count()):
                return 
            dest_container = source_container
            if pos_type == window.POSITION_ITEM:
                if dest_index in data_positions:
                    return # move into one of selected folder
                dest_container = source_container.get_child_at(dest_index)
                child_count = dest_container.get_child_count()
                dest_positions = range(child_count, child_count + len(data_positions))
            else:
                if pos_type == window.POSITION_BELOW and \
                    len([True for pos in data_positions if pos > dest_index]) > 0:
                    dest_index += 1
                
                dest_positions = range(
                    dest_index, dest_index + len(data_positions))
                
            if is_copy:
                items = [self.manager.duplicate_item(source_container.get_child_at(position)) 
                            for position in data_positions]
                task = InsertTask(
                    self._("Copy"), source_container, dest_index, items)
            else:
                if source_container == dest_container:
                    if dest_index in data_positions:
                        return # ignore dest position is in the source position
                
                task = MoveTask(
                    self._("Move"), 
                    source_container, dest_container, 
                    data_positions, dest_positions)
            self.push_task(task)
    
    def show_folder(self, item, history=True):
        """ Show contents of the folder by the selection change. """
        window = self.window
        #found = window.tree_get_root_node().find_node_by_data(item)
        found = self.get_node_by_data(item)
        if found:
            window.tree_set_selection(found)
    
    def open_items(self, items):
        """ Execute command of items. """
        if len(items) == 1 and items[0].is_item():
            item = items[0]
            command = item.get_command()
            controller = None
            imple_name = ""
            
            if command.startswith(self.commands.DIRECTORY_POPUP_URI):
                from bookmarks import DIRECTORY_POPUP_IMPLE_NAME
                imple_name = DIRECTORY_POPUP_IMPLE_NAME
                
            elif command.startswith(self.commands.TAG_POPUP_URI):
                from bookmarks import TAG_POPUP_IMPLE_NAME
                imple_name = TAG_POPUP_IMPLE_NAME
                controller = self
            
            if imple_name:
                try:
                    self.window.show_popup_controller_menu(
                        item.get_command(), imple_name, controller)
                except:
                    pass
            else:
                try:
                    self.commands.execute_command(command)
                except:
                    pass
        else:
            for item in items:
                if item.is_item():
                    try:
                        self.commands.execute_command(item.get_command())
                    except:
                        pass
    
    def column_state_changed(self):
        """ Update column state on the view. """
        try:
            self.window.visible_column(
                self.column_state["Value"], 
                self.column_state["Description"], 
                self.column_state["Tags"])
            self.change_display_container()
        except Exception, e:
            print(e)
    
    def update_data_view(self, items):
        """ Update view if items are shown. """
        view_mode = self.get_view_mode()
        if view_mode & self.MODE_HISTORY:
            return
        
        if view_mode & self.MODE_TAG:
            if view_mode & self.MODE_ROOT:
                return
            positions = []
            tree_selected_node = self.window.tree_get_selection()
            parent = tree_selected_node.get_data()
            name = parent.get_name()
            for item in items:
                if item.has_tag(name):
                    positions.append(parent.get_child_index(item))
            
        else:
            positions = []
            manager = self.manager
            tree_selected_node = self.window.tree_get_selection()
            parent = tree_selected_node.get_data()
            
            for item in items:
                if manager.get_parent_container(item) == parent:
                    positions.append(parent.get_child_index(item))
        
        if positions:
            self.update_rows_in_current(positions)
    
    
    def update_tag_tree(self):
        """ Check and update tags tree. """
        changed = False
        # check renamed
        tags_root_node = self.window.tree_get_tags_root()
        for node in tags_root_node.get_children():
            if node.name != node.get_data().get_name():
                node.set_name(node.get_data().get_name())
        
        # remove unused tags
        names = self.manager.get_tag_names()
        tags_root_node = self.window.tree_get_tags_root()
        for node in tags_root_node.get_children():
            if not node.name in names:
                tags_root_node.remove_child(node)
        
        # add new tags
        names = [child.name for child in tags_root_node.get_children()]
        for i, child in enumerate(self.manager.get_children()):
            name = child.get_name()
            if not name in names:
                node = self.window.tree_create_tag_node(name, False)
                node.set_data(child)
                tags_root_node.insert_child(i, node)
        
        # update if tags is selected
        current_node = self.window.tree_get_selection()
        if isinstance(current_node, TagNode):
            self.change_display_container()
    
    def get_view_mode(self):
        """ Returns view mode. """
        m = 0
        tree_node = self.window.tree_get_selection()
        if isinstance(tree_node, BookmarksNode):
            m = self.MODE_BOOKMRAKS
            if isinstance(tree_node, BookmarksMenuTreeRootNode):
                m |= self.MODE_ROOT
        elif isinstance(tree_node, TagNode):
            m = self.MODE_TAG
            if isinstance(tree_node, TagsTreeRootNode):
                m |= self.MODE_ROOT
        elif isinstance(tree_node, UnsortedBookmarksRootNode):
            m = self.MODE_UNSORTED | self.MODE_ROOT
        else:
            m = self.MODE_HISTORY | self.MODE_ROOT
        return m
    
    def get_insert_position(self):
        parent = self.window.tree_get_selection().get_data()
        position = parent.get_child_count()
        if self.window.get_mode() == self.window.MODE_GRID:
            selections = self.window.grid_get_selection()
            if selections:
                position = selections[-1]
        return position
    
    def get_current_container(self):
        """ Returns current data container from selected tree node. """
        return self.window.tree_get_selection().get_data()
    
    def get_selected_items(self, parent):
        items = [parent.get_child_at(i) for i in self.window.grid_get_selection()]
        try:
            while True:
                items.remove(None)
        except:
            pass
        return items
    
    def get_node_by_data(self, data):
        """ Find node bound to the data incluing unsorted. """
        p = self.window.tree_get_bookmarks_root()
        node = p.find_node_by_data(data)
        if not node:
            p = self.window.tree_get_unsorted_root()
            node = p.find_node_by_data(data)
        if not node:
            p = self.window.tree_get_tags_root()
            node = p.find_node_by_data(data)
        return node
    
    def query_saving(self):
        """ Let user to choose save or not. """
        message = self._("The bookmarks \"%s\" has been modified." + \
                "\\nDo you want to save your changes?")
        message = message.replace("\\n", "\n") % self.manager.bookmark_name
        try:
            n = self.window.query(
                message, 
                self._("Bookmarks Menu"), 
                labels=(self._("~Save"), self._("~Discard"), self._("Cancel"))
            )
        except Exception, e:
            print(e)
            return
        # 0: cancel, 2: Yes, 3: no
        if n == 2:
            self.do_Save()
        elif n == 0:
            return False
        return True
    
    def do_InsertBookmark(self):
        self.do_New(COMMANDS.CMD_INSERT_BOOKMRAK)
    
    def do_InsertSeparator(self):
        self.do_New(COMMANDS.CMD_INSERT_SEPARATOR)
    
    def do_InsertFolder(self):
        self.do_New(COMMANDS.CMD_INSERT_FOLDER)
    
    def do_New(self, command):
        """ Create new item. """
        container = self.get_current_container()
        if not container.is_container():
            return
        item = None
        if command == COMMANDS.CMD_INSERT_BOOKMRAK:
            from bookmarks.dialogs import NewBookmarkDialog
            result = NewBookmarkDialog(
                self.ctx, 
                self.res, 
                filter_manager=self.filter_manager, 
            ).execute()
            if result:
                item = self.manager.create_item(
                    result["name"], result["description"], 
                    self.commands.generate_command(result))
                if "tags" in result:
                    item.set_tags(result["tags"])
                task_name = self._("Insert item")
        
        elif command == COMMANDS.CMD_INSERT_FOLDER:
            from bookmarks.dialogs import NewFolderDialog
            result = NewFolderDialog(self.ctx, self.res, 
                default=self._("New Folder")
            ).execute()
            if result:
                item = self.manager.create_container(
                    result["name"], result["description"])
                task_name = self._("Insert folder")
            
        elif command == COMMANDS.CMD_INSERT_SEPARATOR:
            item = self.manager.create_separator()
            task_name = self._("Insert separator")
        
        if item:
            window = self.window
            position = window.grid_get_row_count()
            if window.get_mode() == window.MODE_GRID:
                selections = window.grid_get_selection()
                if selections:
                    position = selections[-1]
            
            task = InsertTask(task_name, container, position, (item,))
            self.push_task(task)
    
    def do_Open(self):
        """ Open folder to show its contents. """
        window = self.window
        if window.grid_get_selection_count() == 0:
            return
        container = self.get_current_container()
        grid_selections = window.grid_get_selection()
        
        if len(grid_selections) == 1:
            selected_item = container.get_child_at(grid_selections[0])
            if selected_item.is_container() or selected_item.is_tag():
                self.show_folder(selected_item, True)
                return
        
        items = [container.get_child_at(i) for i in grid_selections]
        try:
            self.open_items(items)
        except Exception, e:
            print(e)
            traceback.print_exc()
    
    def do_Cut(self):
        self.do_Copy(COMMANDS.CMD_CUT)
    
    def do_Delete(self):
        self.do_Copy(COMMANDS.CMD_DELETE)
    
    def do_Copy(self, command=COMMANDS.CMD_COPY):
        """ Copy selected items. """
        window = self.window
        view_mode = self.get_view_mode()
        
        tree_selected_node = window.tree_get_selection()
        if window.get_mode() == window.MODE_TREE:
            if view_mode & self.MODE_HISTORY:
                return
            if (tree_selected_node == window.tree_get_bookmarks_root() or \
                tree_selected_node == window.tree_get_tags_root()) and \
                (command == COMMANDS.CMD_CUT or command == COMMANDS.CMD_DELETE):
                return
            if view_mode & self.MODE_TAG:
                if command == COMMANDS.CMD_DELETE:
                    task = DeleteTagTask(self._("Delete tag"), [tree_selected_node.get_data()])
                    self.push_task(task)
                    return
                if command == COMMANDS.CMD_CUT:
                    return
                if view_mode & self.MODE_ROOT:
                    return
            
            tree_parent_node = tree_selected_node.get_parent()
            parent = tree_parent_node.get_data()
            
            if view_mode & self.MODE_TAG:
                data = tree_selected_node.get_data()
                items = (self.create_tag_item(data), )
                positions = []
            else:
                items = (tree_selected_node.get_data(), )
                positions = [parent.get_child_index(item) for item in items]
        
        else:
            if view_mode & self.MODE_HISTORY and command != COMMANDS.CMD_COPY:
                return # ToDo copyable
            if view_mode & self.MODE_TAG:
                if view_mode & self.MODE_ROOT:
                    if command == COMMANDS.CMD_DELETE:
                        manager = tree_selected_node.get_data()
                        items = self.get_selected_items(manager)
                        if items:
                            task = DeleteTagTask(self._("Delete tag"), items)
                            self.push_task(task)
                        return
                    elif command == COMMANDS.CMD_COPY:
                        pass
                    else:
                        return
                
                elif command == COMMANDS.CMD_DELETE:
                    # remove tag from item
                    tag = tree_selected_node.get_data()
                    items = self.get_selected_items(tag)
                    if items:
                        task = ChangeTagTask(self._("Change tag"), items, [], [tag.get_name()])
                        self.push_task(task)
                    return
            
            parent = tree_selected_node.get_data()
            positions = window.grid_get_selection()
            if not positions:
                return
            positions = list(positions)
            positions.sort()
            
            if view_mode & self.MODE_TAG:
                items = [self.create_tag_item(self.manager.get_child_at(index)) for index in positions]
            else:
                items = [parent.get_child_at(index) for index in positions]
        
        if command == COMMANDS.CMD_COPY or command == COMMANDS.CMD_CUT:
            self.clipboard.push_data(items)
        
        if command != COMMANDS.CMD_COPY:
            if command == COMMANDS.CMD_CUT:
                task_name = self._("Cut")
            else:
                task_name = self._("Delete")
            task = CutTask(task_name, parent, positions, items)
            self.push_task(task)
        else:
            self.controller.update_copy_state()
    
    def do_Paste(self):
        """ Paste in current selected. """
        window = self.window
        mode = window.get_mode()
        if not self.clipboard.has_data():
            return
        
        parent = self.get_current_container()
        if isinstance(parent, BookmarksManager):
           return
        if isinstance(parent, TagContainer):
            return # ToDo process like the dnd
        
        if window.get_mode() == window.MODE_TREE:
            position = parent.get_child_count() # append at last
        else:
            selections = window.grid_get_selection()
            if selections and len(selections) > 0:
                position = selections[-1]
            else:
                position = parent.get_child_count()
        items = [self.manager.duplicate_item(item) for item in self.clipboard.get_data()]
        task = InsertTask(self._("Paste"), parent, position, items)
        self.push_task(task)
    
    def do_Back(self):
        self.do_History(COMMANDS.CMD_BACK)
    
    def do_Forward(self):
        self.do_History(COMMANDS.CMD_FORWARD)
    
    def do_History(self, command):
        """ Move inside history. """
        item = None
        if command == COMMANDS.CMD_BACK and self.history.has_previous():
            item = self.history.previous()
        elif command == COMMANDS.CMD_FORWARD and self.history.has_next():
            item = self.history.next()
        if item:
            self.show_folder(item, False)
    
    def do_Undo(self):
        """ Execute undo function. """
        if self.undostack.can_undo():
            try:
                self.undostack.do_undo(self)
                self.manager.set_modified()
                self.controller.update_undo_redo_state()
                self.controller.update_save_state()
            except Exception, e:
                print(e)
                traceback.print_exc()
    
    def do_Redo(self):
        """ Execute redo function. """
        if self.undostack.can_redo():
            try:
                self.undostack.do_redo(self)
                self.manager.set_modified()
                self.controller.update_undo_redo_state()
                self.controller.update_save_state()
            except Exception, e:
                print(e)
                traceback.print_exc()
    
    def do_Move(self):
        """ Move selected. """
        view_mode = self.get_view_mode()
        if not (view_mode & self.MODE_BOOKMRAKS):
            return
        window = self.window
        mode = window.get_mode()
        # check movement is allowed
        if mode == window.MODE_TREE:
            if view_mode & self.MODE_ROOT:
                return
        elif mode == window.MODE_GRID:
            selections = window.grid_get_selection()
            if not selections:
                return # nothing selected
        else:
            return
        
        from bookmarks.util import get_tree_node_expanded_state
        from bookmarks.dialogs import MoveDialog
        result = MoveDialog(self.ctx, self.res, 
            controller=self, 
            node_state=get_tree_node_expanded_state(
                window, window.tree_get_bookmarks_root())
            ).execute()
        if result:
            parent_dest = result
            tree_node = window.tree_get_selection()
            if mode == window.MODE_TREE:
                tree_parent_node = tree_node.get_parent()
                if tree_parent_node is None:
                    return # top node is selected
                parent_source = tree_parent_node.get_data()
                item = tree_node.get_data()
                if item == parent_dest:
                    return # check item is the same with dest
                items = (item, )
                positions = [parent_source.get_child_index(item) for item in items]
            else:
                selections = window.grid_get_selection()
                parent_source = tree_node.get_data()
                positions = list(selections)
                positions.sort()
                items = [parent_source.get_child_at(position) for position in positions]
                if parent_dest in items:
                    return # cant move itself
                
            if parent_source == parent_dest:
                return # do noting
            
            count = parent_dest.get_child_count()
            positions_dest = range(count, count + len(positions))
            task = MoveTask(self._("Move"), parent_source, parent_dest, positions, positions_dest)
            self.push_task(task)
    
    def do_SelectAll(self):
        self.window.grid_select_all()
    
    def do_InsertDoc(self):
        view_mode = self.get_view_mode()
        if not (view_mode & self.MODE_BOOKMRAKS):
            return
        
        from bookmarks.dialog import FileOpenDialog
        result = FileOpenDialog(self.ctx, self.res, 
            filters=(("JSON (*.json)", "*.json"),)
        ).execute()
        if result:
            from bookmarks.manager import BookmarksManager
            try:
                import uno
                obj = BookmarksManager.load(uno.fileUrlToSystemPath(result))
                container = obj[BookmarksManager.NAME_BOOKMARKS]
                if isinstance(container, list):
                    items = container
                else:
                    items = [container]
                parent = self.window.tree_get_selection().get_data()
                position = self.get_insert_position()
                task = InsertTask(self._("Insert from file"), parent, position, items)
                self.push_task(task)
            except Exception, e:
                print(e)
    
    def do_ExportTo(self):
        from bookmarks.dialog import FileSaveAutoExtensionAndSelectionDialog
        dialog = FileSaveAutoExtensionAndSelectionDialog(
            self.ctx, self.res, 
            filters=(("JSON (*.json)", "*.json"), ), 
            default=self.manager.bookmark_name, 
        )
        result = dialog.execute()
        if result:
            is_selection_only = dialog.is_selection_only()
            if self.manager.has_location():
                file_url = self.manager.file_url
            else:
                file_url = self.manager.command_to_path(self.ctx, self.command, True)
            self.export_to(result, is_selection_only)
    
    def export_to(self, file_url, is_selection_only):
        """ Export to file_url. """
        if is_selection_only:
            unsorted = self.manager.create_container(
                    self._(self.manager.UNSORTED_DEFAULT_NAME))
            try:
                tags = self.manager.tags
                parent = self.window.tree_get_selection().get_data()
                if self.window.get_mode() == self.window.MODE_TREE:
                    view_mode = self.get_view_mode()
                    if view_mode & self.MODE_HISTORY:
                        items = self.manager.create_container(self._("History"))
                        items.children = parent.get_children()
                    elif view_mode & self.MODE_TAG:
                        if view_mode & self.MODE_ROOT:
                            items = []
                            for child in parent.get_children():
                                container = self.manager.create_container(child.get_name())
                                container.children = child.get_children()
                                items.append(container)
                        else:
                            items = self.manager.create_container(parent.get_name())
                            items.children = parent.get_children()
                    else:
                        items = parent
                else:
                    selections = self.window.grid_get_selection()
                    if selections:
                        items = [parent.get_child_at(i) for i in selections]
                    else:
                        items = parent
            except Exception, e:
                print(e)
                return
        else:
            tags = self.manager.tags
            items = self.manager.base
            unsorted = self.manager.unsorted
        
        if items:
            try:
                obj = self.manager.pack(tags, items, unsorted)
                s = self.manager.__class__.dump(obj)
                self.manager._write_to_file(file_url, s)
            except Exception, e:
                print(e)
    
    def do_Migration(self):
        from bookmarks.migrate import Migration
        m = Migration(self.ctx)
        if m.check():
            obj = m.migrate()
            parent = self.manager.base
            position = parent.get_child_count()
            task = InsertTask(self._("Migrate"), parent, position, obj.get_children())
            self.push_task(task)
        else:
            self.window.message(self._("Older bookmarks menu was not found."), "")
    
    def do_Save(self):
        if self.manager.modified:
            try:
                self.manager.store()
                self.controller.update_save_state()
            except Exception, e:
                print(e)
    
    def do_NewMenu(self):
        try:
            import bookmarks.wizard.wizard
            bookmarks.wizard.wizard.BookmarksMenuWizard(
                self.ctx, self.res).execute()
        except Exception, e:
            print(e)
    
    def do_About(self):
        import bookmarks
        from bookmarks.dialogs import AboutDialog
        from bookmarks.tools import get_text_content
        #credits = get_text_content(self.ctx, bookmarks.EXT_DIR + "NOTICE")
        translators = get_text_content(self.ctx, bookmarks.EXT_DIR + "Translators")
        #text = credits + "\n\n" + translators
        text = translators
        AboutDialog(self.ctx, self.res, text=text).execute()

