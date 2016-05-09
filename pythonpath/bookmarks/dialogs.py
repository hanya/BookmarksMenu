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
import os.path
import uno
import unohelper

from bookmarks.dialog import DialogBase, FileOpenDialog, FolderDialog
from bookmarks.layouter import DialogLayout, \
    VBox, HBox, GridLayout, \
    Control, Label, Button, List, Edit, CheckBox, Line, Option
from bookmarks.values import ListenerBase, \
    ActionListenerBase, ItemListenerBase
from bookmarks.control import TreeWindow, ExtendedTreeWindow
from bookmarks import EXT_DIR
DIALOG_DIR = EXT_DIR + "dialogs/"
from bookmarks import anotherpmc


class LayoutedDialog(DialogBase):
    """ Dialog elements are layouted by layouter. """
    
    def __init__(self, ctx, res=None, reuse=False, **kwds):
        DialogBase.__init__(self, ctx, res, reuse, **kwds)
    
    def _(self, name):
        return self.res.get(name, name)
    
    def create_dialog(self):
        self.dialog = self._create_dialog(self.DIALOG_URI)
        self.translate_labels()
    
    def _create_dialog(self, uri):
        """ Instantiate dialog specified by URI. """
        return self.create_service(
            "com.sun.star.awt.DialogProvider").createDialog(uri)
    
    def translate_labels(self):
        _ = self._
        dialog_model = self.dialog.getModel()
        dialog_model.Title = _(dialog_model.Title)
        for control in self.dialog.getControls():
            model = control.getModel()
            if hasattr(model, "Label"):
                model.Label = _(model.Label)
            # ToDo HelpText
    
    TYPE_LABEL = 1
    TYPE_BUTTON = 2
    TYPE_EDIT = 3
    TYPE_CHECKBOX = 4
    TYPE_LIST = 6
    TYPE_LINE = 7
    TYPE_OPTION = 8
    TYPE_TREE = 20
    
    TYPE_CONTROL = 64
    
    def create_layout(self, type, name, attrs={}):
        if type == self.TYPE_LABEL:
            klass = Label
        elif type == self.TYPE_BUTTON:
            klass = Button
        elif type == self.TYPE_EDIT:
            klass = Edit
        elif type == self.TYPE_CHECKBOX:
            klass = CheckBox
        elif type == self.TYPE_LIST:
            klass = List
        elif type == self.TYPE_LINE:
            klass = Line
        elif type == self.TYPE_OPTION:
            klass = Option
        else:
            klass = Control
        
        return klass(name, self.get(name), attrs)
    
    def _init_ui(self):
        pass
    
    def _init(self):
        self._init_ui()
        self.layouter = self._init_layout()
        self.layouter.layout()
    
    def get_size(self):
        return self.layouter.elements.get_size()
    
    
    ID_BTN_OK = "btn_ok"
    ID_BTN_CANCEL = "btn_cancel"
    ID_BTN_HELP = "btn_help"
    
    
    def get_buttons_layout(self):
        return HBox(
            "buttons", 
            {
                "margin_top": 4, 
                "halign": "fill", "hexpand": True
            }, 
            (
                self.create_layout(
                    self.TYPE_BUTTON, 
                    self.ID_BTN_HELP, 
                    {"width_request": 80, }
                ), 
                HBox(
                    "okcancel", 
                    {
                        "spacing": 4, 
                        "halign": "end", "hexpand": True
                    }, 
                    (
                        self.create_layout(
                            self.TYPE_BUTTON, 
                            self.ID_BTN_OK, 
                            {"width_request": 80, }
                        ), 
                        self.create_layout(
                            self.TYPE_BUTTON, 
                            self.ID_BTN_CANCEL, 
                            {"width_request": 80, }
                        ), 
                    )
                )
            )
        )


class AboutDialog(LayoutedDialog):
    """ Shows about this extension. """
    
    DIALOG_URI = DIALOG_DIR + "About.xdl"
    
    def _init_ui(self):
        from bookmarks import EXT_ID
        from bookmarks.tools import get_package_info
        name, version = get_package_info(self.ctx, EXT_ID)
        
        self.set_label("label_name", name)
        self.set_label("label_version", version)
        self.set_text("edit_text", self.args.get("text"))
        self.get("edit_text").getModel().setPropertyValues(
            ("ReadOnly", "PaintTransparent"), 
            (True, True)
        )
    
    def _init_layout(self):
        return DialogLayout(
      "window1", 
      self.dialog, 
      {"margin_right": 8, "margin_top": 8, "margin_left": 8, "margin_bottom": 8}, 
      (
        VBox(
          "box1", 
          {}, 
          (
            self.create_layout(
              self.TYPE_LABEL, 
              "label_name", 
              {}
            ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_version", 
              {}
            ), 
            self.create_layout(
              self.TYPE_EDIT, 
              "edit_text", 
              {"width_request": 280, "height_request": 250}
            ), 
            self.create_layout(
              self.TYPE_BUTTON, 
              "btn_ok", 
              {"halign": "center"}
            )
          )
        )
      )
    )


from com.sun.star.awt import XAdjustmentListener, XTextListener

class ArgumentsDialog(LayoutedDialog):
    """ Let user to input arguments for UNO commands. """
    
    DIALOG_URI = DIALOG_DIR + "Arguments.xdl"
    
    NAME_PREFIX = "edit_key"
    VALUE_PREFIX = "edit_value"
    BTN_PREFIX = "btn_value"
    
    def _result(self):
        self.read_values()
        d = {}
        for key, value in self.data:
            if key:
                if value is None:
                    value = ""
                d[key] = value
        return d
    
    class ButtonListener(ActionListenerBase):
        def actionPerformed(self, ev):
            self.act.button_pushed(ev.ActionCommand)
    
    class ScrollBarListener(ListenerBase, XAdjustmentListener):
        def adjustmentValueChanged(self, ev):
            self.act.scrolled(ev.Value)
    
    class TextListener(ListenerBase, XTextListener):
        def textChanged(self, ev):
            self.act.text_changed(ev.Source)
    
    def text_changed(self, ctrl):
        if ctrl == self.get(self.NAME_PREFIX + "1") or \
            ctrl == self.get(self.VALUE_PREFIX + "1"):
            n = 0
        elif ctrl == self.get(self.NAME_PREFIX + "2") or \
            ctrl == self.get(self.VALUE_PREFIX + "2"):
            n = 1
        elif ctrl == self.get(self.NAME_PREFIX + "3") or \
            ctrl == self.get(self.VALUE_PREFIX + "3"):
            n = 2
        else:
            return
        self.modified[n] = True
    
    def button_pushed(self, command):
        from bookmarks.dialog import FileOpenDialog
        result = FileOpenDialog(self.ctx, {}).execute()
        if result:
            self.set_text(self.VALUE_PREFIX + command, result)
            self.modified[int(command) -1] = True
    
    def scrolled(self, value):
        self.update_value(value)
    
    def read_values(self):
        for i in range(3):
            if self.modified[i]:
                key = self.get_text(self.NAME_PREFIX + str(i+1))
                value = self.get_text(self.VALUE_PREFIX + str(i+1))
                self.data[self.pos + i] = (key, value)
    
    def update_value(self, pos, read=True):
        if read:
            self.read_values()
        
        for i in range(3):
            data = self.data[pos + i]
            key = data[0]
            value = data[1]
            if key is None:
                key = ""
            if value is None:
                value = ""
            self.set_text(self.NAME_PREFIX + str(i+1), key)
            self.set_text(self.VALUE_PREFIX + str(i+1), value)
        
        self.pos = pos
        self.reset_modified()
    
    def reset_modified(self):
        self.modified[0] = False
        self.modified[1] = False
        self.modified[2] = False
    
    def _init(self):
        self.modified = [False, False, False]
        self.pos = 0
        self.data = [(None, None) for i in range(10)]
        
        d = self.args["query"]
        self.length = len(d)
        
        for i, (k, v) in enumerate(d.items()):
            self.data[i] = (k, v)
        
        self._init_ui()
        try:
            self.layouter = self._init_layout()
            self.layouter.layout()
        except Exception as e:
            print(e)
        self.update_value(self.pos, read=False)
    
    def _init_ui(self):
        self.get("scroll").addAdjustmentListener(self.ScrollBarListener(self))
        listener = self.ButtonListener(self)
        text_listener = self.TextListener(self)
        for i in range(3):
            btn = self.get("btn_value" + str(i+1))
            btn.addActionListener(listener)
            btn.setActionCommand(str(i+1))
            self.get("edit_key" + str(i+1)).addTextListener(text_listener)
            self.get("edit_value" + str(i+1)).addTextListener(text_listener)
    
    def _init_layout(self):
        return DialogLayout(
        "window1", 
        self.dialog, 
        {"margin_right": 8, "margin_top": 8, "margin_left": 8, "margin_bottom": 8}, 
        VBox(
        "vert", 
        {}, 
        (
          HBox(
            "grid1", 
            {"n_rows": 2, "column_spacing": 4, "row_spacing": 4, "n_columns": 2}, 
            (
              self.create_layout(
                self.TYPE_LABEL, 
                "label_key", 
                {"halign": "start", "width_request": 150}
              ), 
              self.create_layout(
                self.TYPE_LABEL, 
                "label_value", 
                {"hexpand": True, "width_request": 150}
              ), 
            )
          ), 
          HBox(
            "data", 
            {"spacing": 4}, 
            (
                GridLayout(
                    "data grid", 
                    {"n_rows": 3, "column_spacing": 4, "row_spacing": 4, "n_columns": 3}, 
                    (
                        self.create_layout(
                            self.TYPE_EDIT, 
                            "edit_key1", 
                            {}
                        ), 
                        self.create_layout(
                            self.TYPE_EDIT, 
                            "edit_value1", 
                            {}
                        ), 
                        self.create_layout(
                            self.TYPE_BUTTON, 
                            "btn_value1", 
                            {}
                        ), 
                        self.create_layout(
                            self.TYPE_EDIT, 
                            "edit_key2", 
                            {}
                        ), 
                        self.create_layout(
                            self.TYPE_EDIT, 
                            "edit_value2", 
                            {}
                        ), 
                        self.create_layout(
                            self.TYPE_BUTTON, 
                            "btn_value2", 
                            {}
                        ), 
                        self.create_layout(
                            self.TYPE_EDIT, 
                            "edit_key3", 
                            {}
                        ), 
                        self.create_layout(
                            self.TYPE_EDIT, 
                            "edit_value3", 
                            {}
                        ), 
                        self.create_layout(
                            self.TYPE_BUTTON, 
                            "btn_value3", 
                            {}
                        ), 
                    )
                ), 
                self.create_layout(
                    0, 
                    "scroll", 
                    {"width_request": 20}
                )
            )
          ), 
          self.get_buttons_layout()
          )
        )
      )


from com.sun.star.view import XSelectionChangeListener

class BookmarkTreeDialog(LayoutedDialog, ExtendedTreeWindow):
    
    class TreeSelectionListener(ListenerBase, XSelectionChangeListener):
        def selectionChanged(self, ev):
            self.act.tree_selection_changed()
    
    def tree_selection_changed(self):
        node = self.tree_get_selection()
        if node:
            state = True
            if isinstance(node, self.UnsortedBookmarksRootNode):
                state = False
            self.set_enable(self.NAME_BTN_FOLDER, state)
    
    def tree_get_bookmarks_root(self):
        return self.data_model.get_root().get_child_at(1)
    
    def init_tree(self):
        from bookmarks.tree import BookmarksMenuTreeDataModel, UnsortedBookmarksRootNode
        from bookmarks.util import fill_tree, restore_tree_node_expanded_state
        self.UnsortedBookmarksRootNode = UnsortedBookmarksRootNode
        
        self.tree = self.get(self.NAME_TREE_FOLDER)
        self.data_model = BookmarksMenuTreeDataModel()
        self.tree.getModel().DataModel = self.data_model
        
        tree_root_node = self.tree_create_root_node("ROOT", True)
        self.tree_set_root(tree_root_node)
        
        unsorted_root_node = self.tree_create_unsorted_root(
            self._(self.manager.UNSORTED_DEFAULT_NAME))
        self.tree_get_root_node().append_child(unsorted_root_node)
        fill_tree(self, self.manager.unsorted, unsorted_root_node)
        
        bookmarks_root_node = self.tree_create_bookmarks_root(
            self._(self.manager.DEFAULT_NAME))
        self.tree_get_root_node().append_child(bookmarks_root_node)
        fill_tree(self, self.manager.get_root(), bookmarks_root_node)
        
        self.tree_show_root(True)
        self.tree_show_root(False)
        
        self.tree_set_selection(self.tree_get_root_node().get_child_at(1))
        restore_tree_node_expanded_state(
            self, 
            self.tree_get_bookmarks_root(), 
            self.args.get("node_state", ""))
        self.tree.addSelectionChangeListener(self.TreeSelectionListener(self))


class BookmarkThisDialog(BookmarkTreeDialog):
    """ Bookmark current document. """
    
    DIALOG_URI = DIALOG_DIR + "BookmarkThis.xdl"

    NAME_LABEL_NAME = "label_name"
    NAME_EDIT_NAME = "edit_name"
    NAME_LABEL_FOLDER = "label_folder"
    NAME_LIST_FOLDER = "list_folder"
    NAME_BTN_FOLDER = "btn_folder"
    NAME_TREE_FOLDER = "tree_folder"
    NAME_LABEL_DESCRIPTION = "label_description"
    NAME_EDIT_DESCRIPTION = "edit_description"
    NAME_LABEL_TAGS = "label_tags"
    NAME_EDIT_TAGS = "edit_tags"
    
    EDIT_HEIGHT = 25
    
    class DummyController(object):
        def __init__(self, window, manager):
            self.window = window
            self.manager = manager
        
        def check_is_current(self, obj):
            return False
        
        def update_tag_tree(self):
            pass
        
        def change_display_item(self):
            pass
        
        def insert_items_to_current(self, pos, items):
            pass
        
        def get_node_by_data(self, data):
            p = self.window.tree_get_bookmarks_root()
            node = p.find_node_by_data(data)
            if not node:
                p = self.window.tree_get_unsorted_root()
                node = p.find_node_by_data(data)
            return node
    
    class ButtonListener(ActionListenerBase):
        def actionPerformed(self, ev):
            try:
                self.act.button_pushed()
            except Exception as e:
                print(e)
                traceback.print_exc()
    
    def _get_tags(self):
        return [item.strip() 
            for item in self.get_text(self.NAME_EDIT_TAGS).split(",")]
    
    def _result(self):
        container = self.tree_get_selection().get_data()
        #print(container)
        if container:
            from bookmarks.imple import InsertTask
            from bookmarks.command import BookmarksCommands
            
            filter_name = self.args.get("filter_name", "")
            parent = self.tree_get_selection().get_data()
            
            command = BookmarksCommands().generate_command(
                {"type": "document", "path": self.args["file_url"], 
                "filter": filter_name}
            )
            item = self.manager.create_item(
                self.get_text(self.NAME_EDIT_NAME), 
                self.get_text(self.NAME_EDIT_DESCRIPTION), 
                command)
            item.set_tags(self._get_tags())
            
            task = InsertTask(
                self._("Insert item"), 
                container, parent.get_child_count(), (item,))
            controller = self.find_controller()
            if controller:
                controller.push_task(task)
            else:
                task.redo(self.DummyController(self, self.manager))
                self.manager.modified = True
                self.manager.store()
                anotherpmc.set_modified(self.ctx, self.command)
    
    def button_pushed(self):
        result = NewFolderDialog(self.ctx, res=self.res).execute()
        if result:
            tree_node = self.tree_get_selection()
            
            if isinstance(tree_node, self.UnsortedBookmarksRootNode):
                return
            
            parent = tree_node.get_data()
            item = self.manager.create_container(result["name"], result["description"])
            from bookmarks.imple import InsertTask
            task = InsertTask("Insert folder", parent, parent.get_child_count(), (item,))
            controller = self.find_controller()
            if controller:
                controller.push_task(task)
                tree_new_node = self.tree_create_node(item.get_name(), True)
                tree_new_node.set_data(item)
                tree_node.append_child(tree_new_node)
                self.tree_make_visible(tree_new_node)
            else:
                task.redo(self.DummyController(self, self.manager))
                self.tree_make_visible(tree_node.get_child_at(tree_node.get_child_count() -1))
    
    def find_controller(self):
        """ Get controller if living. """
        from bookmarks.imple import BookmarksControllerImple
        return BookmarksControllerImple.CONTROLLERS.get(self.command, None)
    
    def _init(self):
        from bookmarks.util import restore_tree_node_expanded_state
        
        self.manager = self.args["manager"]
        self.command = self.args["command"]
        self.set_text(self.NAME_EDIT_NAME, self.args.get("name", ""))
        self._init_ui()
        self.layouter = self._init_layout()
        self.layouter.layout()
    
    def _init_ui(self):
        self.set_focus(self.NAME_EDIT_NAME)
        self.select_text(self.NAME_EDIT_NAME)
        self.get(self.NAME_BTN_FOLDER).addActionListener(self.ButtonListener(self))
        self.init_tree()
    
    def _init_layout(self):
        return DialogLayout(
      "window1", 
      self.dialog, 
      {"margin_right": 8, "margin_top": 8, "margin_left": 8, "margin_bottom": 8}, 
      VBox(
      "vert", 
      {}, 
      (
        GridLayout(
          "grid1", 
          {"n_rows": 4, "column_spacing": 4, "n_columns": 2, "row_spacing": 4, "hexpand": True}, 
          (
            self.create_layout(
              self.TYPE_LABEL, 
              "label_name", 
              {"halign": "start"}
            ), 
            self.create_layout(
              self.TYPE_EDIT, 
              "edit_name", 
              {"hexpand": True}
            ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_folder", 
              {"valign": "start", "halign": "start"}
            ), 
            VBox(
              "box1", 
              {"spacing": 4}, 
              (
                self.create_layout(
                  self.TYPE_TREE, 
                  "tree_folder", 
                  {"height_request": 180, "width_request": 280}
                ), 
                self.create_layout(
                  self.TYPE_BUTTON, 
                  "btn_folder", 
                  {"halign": "start"}
                )
              )
            ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_tags", 
              {"valign": "start", "halign": "start"}
            ), 
            self.create_layout(
              self.TYPE_EDIT, 
              "edit_tags", 
              {"hexpand": True}
            ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_description", 
              {"valign": "start", "halign": "start"}
            ), 
            self.create_layout(
              self.TYPE_EDIT, 
              "edit_description", 
              {"height_request": 50}
            )
          )
        ), 
        self.get_buttons_layout()
        )
      )
    )


class CommandsDialog(LayoutedDialog):
    """ Let user to choose a command. """
    
    DIALOG_URI = DIALOG_DIR + "Commands.xdl"
    
    NAME_LABEL_CATEGORIES = "label_categories"
    NAME_LABEL_COMMANDS = "label_commands"
    NAME_LIST_CATEGORIES = "list_categories"
    NAME_LIST_COMMANDS = "list_commands"
    NAME_CHECK_COMMANDS = "check_commands"
    NAME_LINE_DESCRIPTION = "line_description"
    NAME_LABEL_DESCRIPTIONRIPTION = "label_description"
    
    LIST_CATEGORIES_WIDTH = 190
    LIST_COMMANDS_WIDTH = 300
    LIST_HEIGHT = 200
    LABEL_DESCRIPTION_HEIGHT = 60
    
    DESCRIPTION_MARGIN = 5
    
    NODE_CATEGORIES = "/org.openoffice.Office.UI.GenericCategories/Commands/Categories"
    NODE_SFX = "/org.openoffice.Office.SFX"
    NODE_HELP = "/org.openoffice.Office.Common/Help"
    NODE_LOCALE = "/org.openoffice.Setup/L10N"
    NODE_LINGU = "/org.openoffice.Office.Linguistic/General"
    
    PROP_HELP = "Help"
    PROP_SYSTEM = "System"
    PROP_LOCALE = "ooLocale"
    PROP_DEFAULT_LOCALE = "DefaultLocale"
    
    HELP_URI = "vnd.sun.star.help://swriter/%%s?Language=%s&System=%s&Active=true"
    
    CATEGORY_SCRIPT_LANGUAGES = 230
    CATEGORY_BOOKMARKS_MENU = 256
    
    SCRIPT_ORGANIZER_URI = ".uno:ScriptOrganizer?ScriptOrganizer.Language:string=%s"
    
    class CategoriesStateListener(ItemListenerBase):
        def itemStateChanged(self, ev):
            self.act.categories_changed()
    
    class CommandsStateListener(ItemListenerBase):
        def itemStateChanged(self, ev):
            self.act.command_changed()
    
    class ShowCommandsStateListener(ItemListenerBase):
        def itemStateChanged(self, ev):
            self.act.show_commands_changed()
    
    def show_commands_changed(self):
        """ When state of the show commands checkbox changed. """
        self.show_command = not not self.get(self.NAME_CHECK_COMMANDS).getModel().State
        list_commands = self.get(self.NAME_LIST_COMMANDS)
        index = list_commands.getSelectedItemPos()
        self.categories_changed()
        if 0 <= index:
            list_commands.selectItemPos(index, True)
    
    def command_changed(self):
        """ When selected command is changed. """
        list_commands = self.get(self.NAME_LIST_COMMANDS)
        list_commands_model = list_commands.getModel()
        index = list_commands.getSelectedItemPos()
        if 0 <= index:
            description = ""
            try:
                command = list_commands_model.getItemData(index)
                description = self.get_active_help_text(command)
            except Exception as e:
                print(e)
            self.set_description(description)
    
    def categories_changed(self):
        """ When selected category is changed. """
        list_categories = self.get(self.NAME_LIST_CATEGORIES)
        list_categories_model = list_categories.getModel()
        index = list_categories.getSelectedItemPos()
        if 0 <= index:
            category = list_categories_model.getItemData(index)
            try:
                self.update_commands(category)
                self.get(self.NAME_LIST_COMMANDS).selectItemPos(0, True)
            except Exception as e:
                print(e)
    
    def update_scripts_category(self):
        """ Fill script category according to installed scripting engine. """
        languages = []
        provider_enume = self.ctx.getServiceManager().createContentEnumeration(
            "com.sun.star.script.provider.LanguageScriptProvider")
        while provider_enume.hasMoreElements():
            provider = provider_enume.nextElement()
            for name in provider.getSupportedServiceNames():
                if name.startswith("com.sun.star.script.provider.ScriptProviderFor"):
                    languages.append(name[46:])
        languages = languages
        try:
            languages.remove("Basic")
            languages.remove("Java")
        except Exception as e:
            pass
            print(e)
        languages = tuple(languages)
        # ToDo add .uno:MacroDialog for basic
        self.commands[self.CATEGORY_SCRIPT_LANGUAGES] = languages
        self.command_names[self.CATEGORY_SCRIPT_LANGUAGES] = languages
    
    def update_bookmarks_category(self):
        """ Fill bookmarks menu category. """
        self.commands[self.CATEGORY_BOOKMARKS_MENU] = (
            "mytools.BookmarksMenu:AddThis", 
            "mytools.BookmarksMenu:Edit", 
        )
        self.command_names[self.CATEGORY_BOOKMARKS_MENU] = (
            self._("Bookmark ~This Document..."), 
            self._("~Edit Bookmarks..."), 
        )
    
    def update_commands(self, category):
        """ Fill specific category. """
        list_commands = self.get(self.NAME_LIST_COMMANDS)
        list_commands_model = list_commands.getModel()
        list_commands_model.removeAllItems()
        self.set_description("")
        if not category in self.commands:
            # update special categories
            if category == self.CATEGORY_SCRIPT_LANGUAGES:
                self.update_scripts_category()
            elif category == self.CATEGORY_BOOKMARKS_MENU:
                self.update_bookmarks_category()
            else:
                return
        
        self.update_names(category)
        if self.show_command:
            list_commands_model.StringItemList = uno.Any(uno.getTypeByName("[]string"), self.commands[category])
        else:
            list_commands_model.StringItemList = uno.Any(uno.getTypeByName("[]string"), self.command_names[category])
        for index, command in enumerate(self.commands[category]):
            list_commands_model.setItemData(index, command)
    
    def update_names(self, category):
        """ Fill command names. """
        if not category in self.command_names:
            def find_name(items):
                for item in items:
                    if item.Name == "Name":#"Label":
                        return item.Value
                return "ERROR"
            
            command_sets = [(find_name(self.command_description.getByName(command)), command) 
                                for command in self.commands[category]]
            command_sets.sort()
            
            self.commands[category] = tuple([item[1] for item in command_sets])
            self.command_names[category] = tuple([item[0] for item in command_sets])
    
    def get_active_help_text(self, command):
        """ Get active help for command. """
        uri = self.help_uri % command.replace(":", "%3A")
        s = None
        try:
            text_input = self.ctx.getServiceManager().createInstanceWithContext(
                "com.sun.star.io.TextInputStream", self.ctx)
            f = self.sfa.openFileRead(uri)
            text_input.setInputStream(f)
            #dummy, s = f.readBytes(None, 32768)
            s = text_input.readString((), False)
            f.closeInput()
            return s
        except Exception as e:
            print(e)
        #if isinstance(s, uno.ByteSequence):
        #   return s.value.encode("UTF-8")
        return ""
    
    def set_description(self, text):
        """ Set description about command. """
        self.set_label(self.NAME_LABEL_DESCRIPTIONRIPTION, text)
    
    def _result(self):
        """ Returns tuple of command name and command. 
        None is returned if canceled. """
        list_commands = self.get(self.NAME_LIST_COMMANDS)
        list_commands_model = list_commands.getModel()
        index = list_commands.getSelectedItemPos()
        if 0 <= index:
            name = list_commands.getSelectedItem()
            result = list_commands_model.getItemData(index)
            list_categories = self.get(self.NAME_LIST_CATEGORIES)
            list_categories_model = list_categories.getModel()
            index = list_categories.getSelectedItemPos()
            if 0 <= index:
                category = list_categories_model.getItemData(index)
                if category == self.CATEGORY_SCRIPT_LANGUAGES:
                    result = self.SCRIPT_ORGANIZER_URI % result
            return name, result
        return None
    
    def _dispose(self):
        self.command_description = None
        self.commands.clear()
        self.command_names.clear()
        self.commands = None
        self.command_names = None
    
    def _init(self):
        def create(name):
            return self.ctx.getServiceManager().createInstanceWithContext(
                name, self.ctx)
        
        self._init_help(create)
        self._init_categories(create)
        self._init_ui(create)
        self.layouter = self._init_layout()
        self.layouter.layout()
        self.get("list_categories").selectItemPos(0, True)
    
    def _init_help(self, create):
        # check help system is installed
        self.help_exists = False
        try:
            from bookmarks.tools import get_config_value
            self.help_exists = not not get_config_value(
                self.ctx, self.NODE_SFX, self.PROP_HELP)
        except:
            traceback.print_exc()
        if self.help_exists:
            self.sfa = create("com.sun.star.ucb.SimpleFileAccess")
            
            system = get_config_value(self.ctx, self.NODE_HELP, self.PROP_SYSTEM)
            if not system:
                system = "WIN"
            lang = get_config_value(self.ctx, self.NODE_LOCALE, self.PROP_LOCALE)
            self.help_uri = self.HELP_URI % (lang, system)
    
    def _init_categories(self, create):
        from bookmarks import DOCUMENT_IMPLE_NAME
        from bookmarks.tools import get_config
        module_manager = create("com.sun.star.frame.ModuleManager")
        desktop = create("com.sun.star.frame.Desktop")
        component = None
        frames = desktop.getFrames()
        for i in range(frames.getCount())[::-1]:
            try:
                frame = frames.getByIndex(i)
                type_name = module_manager.identify(frame)
                if type_name != DOCUMENT_IMPLE_NAME:
                    component = frame.getController().getModel()
                    break
            except Exception as e:
                print(e)
        if not component:
            try:
                type_name = component.getIdentifier()
            except:
                pass
        
        commands = {}
        try:
            controller = component.getCurrentController()
            for group in controller.getSupportedCommandGroups():
                _group = int(group)
                supported_commands = set([info.Command 
                    for info in controller.getConfigurableDispatchInformation(group)])
                if _group in commands:
                    commands[_group].add(supported_commands)
                else:
                    commands[_group] = supported_commands
        except:
            pass
        # category names
        config_categories = get_config(self.ctx, self.NODE_CATEGORIES)
        categories = [(int(category), config_categories.getByName(category).Name) 
                for category in config_categories.getElementNames() if category != "0"]
        # remove unused categories
        for category in categories[::-1]:
            if not category[0] in commands:
                categories.remove(category)
        
        # add special categories
        categories.append((self.CATEGORY_SCRIPT_LANGUAGES, self._("Script organizer")))
        categories.append((self.CATEGORY_BOOKMARKS_MENU, self._("Bookmarks Menu")))
        
        self.categories = categories
        self.show_command = False
        self.commands = commands
        self.command_names = {}
        
        self.command_description = None
        try:
            self.command_description = create(
                "com.sun.star.frame.UICommandDescription").\
                    getByName(type_name)
        except:
            pass
    
    def _init_ui(self, create):
        categories = self.categories
        list_categories = self.get(self.NAME_LIST_CATEGORIES)
        list_categories_model = list_categories.getModel()
        list_categories_model.StringItemList = \
            uno.Any(uno.getTypeByName("[]string"), 
                tuple([category[1] for category in categories]))
        for index, category in enumerate(categories):
            list_categories_model.setItemData(index, category[0])
        
        list_categories.addItemListener(self.CategoriesStateListener(self))
        self.get(self.NAME_LIST_COMMANDS).addItemListener(self.CommandsStateListener(self))
        check_commands = self.get(self.NAME_CHECK_COMMANDS)
        check_commands.addItemListener(self.ShowCommandsStateListener(self))
        check_commands.getModel().State = 0
    
    def _init_layout(self):
        return DialogLayout(
      "window1", 
      self.dialog, 
      {"margin_right": 8, "margin_top": 8, "margin_left": 8, "margin_bottom": 8}, 
      VBox(
      "vert", 
      {}, 
      (
        VBox(
          "box1", 
          {}, 
          (
          GridLayout(
            "grid1", 
            {"n_rows": 2, "column_spacing": 4, "row_spacing": 4, "n_columns": 2}, 
            (
              self.create_layout(
                self.TYPE_LABEL, 
                "label_categories", 
                {"halign": "start"}
              ), 
              self.create_layout(
                self.TYPE_LABEL, 
                "label_commands", 
                {"halign": "start"}
              ), 
              self.create_layout(
                self.TYPE_LIST, 
                "list_categories", 
                {"height_request": 200, "width_request": 190}
              ), 
              self.create_layout(
                self.TYPE_LIST, 
                "list_commands", 
                {"height_request": 200, "width_request": 280}
              )
            )
          ), 
            self.create_layout(
              self.TYPE_CHECKBOX, 
              "check_commands", 
              {"margin_top": 4, "halign": "end"}
            ), 
            self.create_layout(
              self.TYPE_LINE, 
              "line_description", 
              {}
            ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_description", 
              {"height_request": 75, "margin_left": 8}
            )
          )
        ), 
        self.get_buttons_layout()
        )
      )
    )


class DirectoryPopupDialog(LayoutedDialog):
    """ Dialog to input data for place menu. """
    
    DIALOG_URI = DIALOG_DIR + "DirectoryPopup.xdl"
    
    ID_EDIT_DIRECTORY = "edit_directory"
    ID_EDIT_FILTER = "edit_filter"
    ID_BTN_SELECT = "btn_select"
    
    ARG_URL = "URL:string"
    ARG_FILE_FILTER = "Filter:string"
    
    def _result(self):
        from bookmarks import DIRECTORY_POPUP_URI
        from bookmarks.cmdparse import bk_urlencode
        return DIRECTORY_POPUP_URI + "?" + bk_urlencode(
            {
                self.ARG_URL: self.get_text(self.ID_EDIT_DIRECTORY), 
                self.ARG_FILE_FILTER: self.get_text(self.ID_EDIT_FILTER)
            }
        )
    
    class ButtonListener(ActionListenerBase):
        def actionPerformed(self, ev):
            self.act.button_pushed()
    
    def button_pushed(self):
        from bookmarks.dialog import FolderDialog
        result = FolderDialog(self.ctx, self.res).execute()
        if result:
            self.set_text(self.ID_EDIT_DIRECTORY, result)
    
    def _init(self):
        self.layouter = self._init_layout()
        self.layouter.layout()
        self.get(self.ID_BTN_SELECT).addActionListener(self.ButtonListener(self))
        
        if "default" in self.args:
            command = self.args["default"]
            from bookmarks import DIRECTORY_POPUP_URI
            from bookmarls.cmdparse import bk_parse_qs
            
            if command.startswith(DIRECTORY_POPUP_URI):
                parts = command.split("?", 1)
                if len(parts) == 2:
                    qs = bk_parse_qs(parts[1])
                    if self.ARG_URL in qs:
                        self.set_text(
                            self.ID_EDIT_DIRECTORY, qs[self.ARG_URL][0])
                    if self.ARG_FILE_FILTER in qs:
                        self.set_text(
                            self.ID_EDIT_FILTER, qs[self.ARG_FILE_FILTER][0])
    
    def _init_layout(self):
        return DialogLayout(
      "window1", 
      self.dialog, 
      {"margin_right": 8, "margin_top": 8, "margin_left": 8, "margin_bottom": 8}, 
      VBox(
      "vert", 
      {}, 
      (
        GridLayout(
          "grid1", 
          {"n_rows": 2, "column_spacing": 4, "row_spacing": 4, "n_columns": 2}, 
          (
            self.create_layout(
              self.TYPE_LABEL, 
              "label_directory", 
              {"halign": "start"}
            ), 
          HBox(
            "box1", 
            {"spacing": 4}, 
            (
              self.create_layout(
                self.TYPE_EDIT, 
                "edit_directory", 
                {"width_request": 200, }
              ), 
              self.create_layout(
                self.TYPE_BUTTON, 
                "btn_select", 
                {}
              )
            )
          ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_filter", 
              {"halign": "start"}
            ), 
            self.create_layout(
              self.TYPE_EDIT, 
              "edit_filter", 
              {}
            )
          )
        ), 
        self.get_buttons_layout()
        )
      )
    )


from com.sun.star.awt import XItemListener

class FileFilterDialog(LayoutedDialog):
    """ Let user to choose a file filter. """
    
    DIALOG_URI = DIALOG_DIR + "FileFilter.xdl"
    
    GROUP_SEP = "------------------------"
    NAME_FILTER_MANAGER = "filter_manager"
    NAME_DEFAULT = "default"
    
    def _result(self):
        return self.get("list_filter").getSelectedItem()
    
    class ItemListener(ListenerBase, XItemListener):
        def itemStateChanged(self, ev):
            self.act.item_changed()
    
    def item_changed(self):
        item = self.get("list_filter").getSelectedItem()
        state = item != self.GROUP_SEP and item != ""
        self.set_enable(self.ID_BTN_OK, state)
    
    def appendFilterGroup(self, title, filters):
        list_filter = self.get("list_filter")
        if list_filter.getItemCount():
            list_filter.addItem(
                self.GROUP_SEP, 
                list_filter.getItemCount())
        list_filter.addItems(
            tuple([f.First for f in filters]), 
            list_filter.getItemCount())
    
    def get_item(self, n):
        try:
            return self.get("list_filter").getItem(0)
        except:
            return ""
    
    def _init(self):
        self._init_ui()
        
        if self.NAME_FILTER_MANAGER in self.args:
            self.args[self.NAME_FILTER_MANAGER].set_filters(self)
        
        if self.NAME_DEFAULT in self.args:
            name = self.args[self.NAME_DEFAULT]
        else:
            try:
                name = self.get_item()
            except:
                name = ""
        if name:
            self.get("list_filter").selectItem(name, True)
        else:
            self.get("list_filter").selectItemPos(0, True)
        
        self.layouter = self._init_layout()
        self.layouter.layout()
    
    def _init_ui(self):
        self.get("list_filter").addItemListener(self.ItemListener(self))
    
    def _init_layout(self):
        return DialogLayout(
        "window1", 
        self.dialog, 
        {"margin_right": 8, "margin_top": 8, "margin_left": 8, "margin_bottom": 8}, 
        VBox(
        "vert", 
        {}, 
        (
          self.create_layout(
            self.TYPE_LABEL, 
            "label_filter", 
            {"halign": "start"}
          ), 
          self.create_layout(
            self.TYPE_LIST, 
            "list_filter", 
            {"hexpand": True, "width_request": 380}
          ), 
          self.get_buttons_layout()
          )
        )
      )


from com.sun.star.view import XSelectionChangeListener
from com.sun.star.awt.tree import XTreeExpansionListener

class MacroSelectorDialog(LayoutedDialog):
    """ Let user to choose a macro. """
    
    DIALOG_URI = DIALOG_DIR + "Selector.xdl"
    
    IMAGE_SCRIPT = "private:graphicrepository/res/im30821.png"
    IMAGE_CONTAINER = "private:graphicrepository/res/im30820.png"
    IMAGE_ROOT = "private:graphicrepository/res/harddisk_16.png"
    IMAGE_DOCUMENT = "private:graphicrepository/res/sc05500.png"
    
    BASIC_MODULE_NAME = "mytools_bookmarks"
    SCRIPT_URI = "vnd.sun.star.script:mytools_bookmarks.Selector.MacroSelector?language=Basic&location=application"
    
    VALID_INVOCATION = None
    
    class NodeWrapper(object):
        def __init__(self, act, node):
            self.act = act
            self._node = node
        
        def getName(self):
            return self.act._node_get_name(self._node)
        
        def getChildNodes(self):
            return self.act._node_get_child_nodes(self._node)
        
        def hasChildNodes(self):
            return self.act._node_has_child_nodes(self._node)
        
        def getType(self):
            return self.act._node_get_type(self._node)
        
        def getPropertyValue(self, name):
            return self.act._node_get_property_value(self._node, name)
    
    
    class MacroSelectorTreeExpansionListener(ListenerBase, XTreeExpansionListener):
        def treeExpanding(self, ev): pass
        def treeCollapsing(self, ev): pass
        def treeExpanded(self, ev): pass
        def treeCollapsed(self, ev): pass
        def requestChildNodes(self, ev):
            tree_node = ev.Source.getSelection()
            if tree_node.getChildCount() <= 0:
                self.act.create_children(tree_node)
    
    class MacroSelectorTreeSelectionListener(ListenerBase, XSelectionChangeListener):
        def selectionChanged(self, ev):
            self.act.fill_description(None)
            tree_node = ev.Source.getSelection()
            if tree_node:
                self.act.fill_macro_names(tree_node)
    
    class MacroSelectorItemListener(ItemListenerBase):
        def itemStateChanged(self, ev):
            pos = ev.Selected
            if pos >= 0:
                self.act.fill_description(ev.Source.getModel().getItemData(pos))
    
    def _result(self):
        uri = None
        list_names = self.get("list_names")
        pos = list_names.getSelectedItemPos()
        if pos >= 0:
            uri = self.NodeWrapper(
                self, list_names.getModel().getItemData(pos)).getPropertyValue("URI")
        return uri
    
    def create_children(self, tree_parent, top=False):
        _wrapper = self.NodeWrapper
        parent_node = _wrapper(self, tree_parent.DataValue)
        for _child in parent_node.getChildNodes():
            child = _wrapper(self, _child)
            if child.getType():
                item_name = child.getName()
                tree_child_node = self.tree_data_model.createNode(
                                        item_name, child.hasChildNodes())
                tree_parent.appendChild(tree_child_node)
                tree_child_node.DataValue = _child
                if top:
                    if item_name == "user" or item_name == "share":
                        icon = self.IMAGE_ROOT
                    else:
                        icon = self.IMAGE_DOCUMENT
                else:
                    icon = self.IMAGE_CONTAINER
                tree_child_node.setNodeGraphicURL(icon)
    
    def fill_macro_names(self, tree_parent):
        _wrapper = self.NodeWrapper
        parent_node = _wrapper(self, tree_parent.DataValue)
        image_script = self.IMAGE_SCRIPT
        list_names_model = self.get("list_names").getModel()
        list_names_model.removeAllItems()
        
        for pos, _child in enumerate(parent_node.getChildNodes()):
            child = _wrapper(self, _child)
            if not child.getType():
                list_names_model.insertItem(
                            pos, child.getName(), image_script)
                list_names_model.setItemData(pos, _child)
    
    def fill_description(self, node):
        text = ""
        if node:
            try:
                text = self.NodeWrapper(self, node).getPropertyValue("Description")
            except:
                pass
        self.set_label("label_description", text)
    
    def _init(self):
        self.tree_data_model = None
        self._init_idl_methods()
        self._init_tree()
        
        self.layouter = self._init_layout()
        self.layouter.layout()
    
    def _init_tree(self):
        root_node = self._create_selector_node()
        
        self.tree_data_model = self.create_service(
                    "com.sun.star.awt.tree.MutableTreeDataModel")
        tree_libraries = self.get("tree_libraries")
        tree_libraries_model = tree_libraries.getModel()
        
        tree_root_node = self.tree_data_model.createNode("ROOT", False)
        tree_root_node.DataValue = root_node
        self.tree_data_model.setRoot(tree_root_node)
        tree_libraries_model.SelectionType = uno.Enum(
                    "com.sun.star.view.SelectionType", "SINGLE")
        tree_libraries_model.DataModel = self.tree_data_model
        
        self.create_children(tree_root_node, True)
        tree_libraries_model.RootDisplayed = False
        
        tree_libraries.addSelectionChangeListener(
                self.MacroSelectorTreeSelectionListener(self))
        tree_libraries.addTreeExpansionListener(
                self.MacroSelectorTreeExpansionListener(self))
        self.get("list_names").addItemListener(self.MacroSelectorItemListener(self))
        
        tree_libraries.makeNodeVisible(tree_root_node.getChildAt(0))
    
    def _create_selector_node(self):
        root_node = None
        if hasattr(self, "_selector_root_node"):
            root_node = self._selector_root_node
        else:
            nf = self.ctx.getValueByName(
                "/singletons/com.sun.star.script.browse.theBrowseNodeFactory")
            root_node = nf.createView(uno.getConstantByName(
                "com.sun.star.script.browse.BrowseNodeFactoryViewTypes.MACROSELECTOR"))
        return root_node
    
    def _init_idl_methods(self):
        """ Workaround for invocation problem, i120458. """
        cr = self.create_service("com.sun.star.reflection.CoreReflection")
        idl_XPropertyValue = cr.forName("com.sun.star.beans.XPropertySet")
        self._idl_getPropertyValue = idl_XPropertyValue.getMethod("getPropertyValue").invoke
        idl_XBrowseNode = cr.forName("com.sun.star.script.browse.XBrowseNode")
        for name in ("getName", "getChildNodes", "hasChildNodes", "getType"):
            setattr(self, "_idl_" + name, idl_XBrowseNode.getMethod(name).invoke)
    
    def _node_get_name(self, node):
        return self._idl_getName(node, ())[0]
    
    def _node_get_child_nodes(self, node):
        return self._idl_getChildNodes(node, ())[0]
    
    def _node_has_child_nodes(self, node):
        return self._idl_hasChildNodes(node, ())[0]
    
    def _node_get_type(self, node):
        return self._idl_getType(node, ())[0]
    
    def _node_get_property_value(self, node, name):
        return self._idl_getPropertyValue(node, (name,))[0]
    
    def execute(self):
        if self.__class__.VALID_INVOCATION is None:
            self.__class__.VALID_INVOCATION = self._check_invocation_valid()
        
        if self.__class__.VALID_INVOCATION:
            return LayoutedDialog.execute(self)
        else:
            return self._execute()
    
    def _execute(self):
        from bookmarks.tools import create_script
        type_string = uno.getTypeByName("string")
        m = None
        if self.res:
            m = self.create_service("com.sun.star.container.EnumerableMap")
            m.initialize((type_string, type_string))
            for k, v in self.res.items():
                m.put(k, v)
        script = create_script(self.ctx, self.SCRIPT_URI)
        result, dummy, dummy = script.invoke((m,), (), ())
        return result
    
    def _check_invocation_valid(self):
        """ Check the invocation bridge works well. """
        root_node = self._create_selector_node()
        try:
            nodes = root_node.getChildNodes()
            for context_node in nodes:
                for sub_node in context_node.getChildNodes():
                    if sub_node.getName() == self.__class__.BASIC_MODULE_NAME:
                        for module_node in sub_node.getChildNodes():
                            for routine_node in module_node.getChildNodes():
                                break
        except:
            return False
        return True
    
    def _init_layout(self):
        return DialogLayout(
      "window1", 
      self.dialog, 
      {"margin_right": 8, "margin_top": 8, "margin_left": 8, "margin_bottom": 8}, 
      VBox(
      "vert", 
      {}, 
      (
        VBox(
          "box1", 
          {"spacing": 4}, 
          (
          GridLayout(
            "grid1", 
            {"n_rows": 2, "column_spacing": 4, "row_spacing": 2, "n_columns": 2}, 
            (
              self.create_layout(
                self.TYPE_LABEL, 
                "label_libraries", 
                {"halign": "start"}
              ), 
              self.create_layout(
                self.TYPE_LABEL, 
                "label_names", 
                {"halign": "start"}
              ), 
              self.create_layout(
                self.TYPE_LIST, 
                "tree_libraries", 
                {"height_request": 240, "width_request": 240}
              ), 
              self.create_layout(
                self.TYPE_LIST, 
                "list_names", 
                {"height_request": 240, "width_request": 240}
              )
            )
          ), 
            self.create_layout(
              self.TYPE_LINE, 
              "line_description", 
              {}
            ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_description", 
              {"height_request": 50, "margin_left": 8}
            )
          )
        ), 
        self.get_buttons_layout()
        )
      )
    )


class MoveDialog(BookmarkTreeDialog):
    """ Move item to somewhere. """
    
    DIALOG_URI = DIALOG_DIR + "Move.xdl"
    
    NAME_LABEL_MOVE = "label_move"
    NAME_TREE_FOLDER = "tree_folder"
    NAME_BTN_FOLDER = "btn_folder"
    
    TREE_WIDTH = 250
    TREE_HEIGHT = 200
    
    def _result(self):
        """ Returns container for direction to move. """
        return self.tree_get_selection().get_data()
    
    class ButtonListener(ActionListenerBase):
        def actionPerformed(self, ev):
            try:
                self.act.button_pushed()
            except Exception as e:
                print(e)
    
    def button_pushed(self):
        result = NewFolderDialog(
            self.ctx, self.res, 
            default=self._("New Folder")
        ).execute()
        if result:
            tree_node = self.tree_get_selection()
            parent = tree_node.get_data()
            item = self.controller.manager.create_container(
                        result["name"], result["description"])
            if item:
                import bookmarks.imple
                task = bookmarks.imple.InsertTask(
                    "insert folder", parent, parent.get_child_count(), (item,))
                self.controller.push_task(task)
                # add tree node for this tree too
                tree_new_node = self.tree_create_node(item.get_name())
                tree_new_node.set_data(item)
                tree_node.append_child(tree_new_node)
                self.tree_make_visible(tree_new_node)
    
    def _init(self):
        self.controller = self.args["controller"]
        self.manager = self.controller.manager
        self._init_ui()
        
        self.layouter = self._init_layout()
        self.layouter.layout()
    
    def _init_ui(self):
        self.get(self.NAME_BTN_FOLDER).addActionListener(self.ButtonListener(self))
        self.init_tree()
    
    def _init_layout(self):
        return DialogLayout(
      "window1", 
      self.dialog, 
      {"margin_right": 8, "margin_top": 8, "margin_left": 8, "margin_bottom": 8}, 
      VBox(
      "vert", 
      {}, 
      (
        HBox(
          "box1", 
          {"spacing": 4}, 
          (
            self.create_layout(
              self.TYPE_LABEL, 
              "label_move", 
              {"valign": "start"}
            ), 
          VBox(
            "box2", 
            {"spacing": 4}, 
            (
              self.create_layout(
                self.TYPE_TREE, 
                "tree_folder", 
                {"height_request": 200, "width_request": 250}
              ), 
              self.create_layout(
                self.TYPE_BUTTON, 
                "btn_folder", 
                {"halign": "start"}
              )
            )
          )
          )
        ), 
        self.get_buttons_layout()
        )
      )
    )


class NewBookmarkDialog(LayoutedDialog):
    """ Generate new bookmark values. """
    
    DIALOG_URI = DIALOG_DIR + "NewBookmark.xdl"
    
    URI_GRAPHICS = "private:graphicrepository/"
    
    NAME_LABEL_NAME = "label_name"
    NAME_EDIT_NAME = "edit_name"
    NAME_LABEL_VALUE1 = "label_value1"
    NAME_EDIT_VALUE1 = "edit_value1"
    NAME_LABEL_VALUE2 = "label_value2"
    NAME_EDIT_VALUE2 = "edit_value2"
    NAME_LABEL_DESCRIPTION = "label_description"
    NAME_EDIT_DESCRIPTION = "edit_description"
    NAME_BTN_VALUE1 = "btn_value1"
    NAME_BTN_VALUE2 = "btn_value2"
    NAME_LABEL_TYPE = "label_type"
    NAME_OPTION_FILE = "option_file"
    NAME_OPTION_FOLDER = "option_folder"
    NAME_OPTION_WEB = "option_web"
    NAME_LIST_SPECIAL = "list_special"
    NAME_EDIT_TAGS = "edit_tags"
    NAME_LABEL_TAGS = "label_tags"
    
    NAME_HORILAYOUT_TYPE = "horilayout_type"
    
    ARG_FILTER_MANAGER = "filter_manager"
    
    PAGES = ("document", "macro", "command", 
                "program", "something", "special")
    
    DIALOG_MIN_WIDTH = 450
    HEIGHT_EDIT = 25
    
    def _result(self):
        result = {}
        result["name"] = self.get_text(self.NAME_EDIT_NAME)
        result["description"] = self.get_text(self.NAME_EDIT_DESCRIPTION)
        result["tags"] = self.get_tags()
        type = self.PAGES[self.chooser.get_active()]
        result["type"] = type
        value1 = self.get_text(self.NAME_EDIT_VALUE1)
        value2 = self.get_text(self.NAME_EDIT_VALUE2)
        if type == "document":
            result["path"] = value1
            if self.filter_manager:
                result["filter"] = self.filter_manager.get_internal_name(value2)
        elif type == "macro":
            result["command"] = value1
        elif type == "command":
            result["command"] = value1
            result["arguments"] = value2
        elif type == "program":
            result["path"] = value1
            result["arguments"] = value2
        elif type == "something":
            result["path"] = value1
            flag = ""
            if self.is_selected(self.NAME_OPTION_FILE):
                flag = "file"
            elif self.is_selected(self.NAME_OPTION_FOLDER):
                flag = "folder"
            elif self.is_selected(self.NAME_OPTION_WEB):
                flag = "web"
            result["flag"] = flag
        elif type == "special":
            result["path"] = value1
            flag = ""
            index = self.get_special_type()
            if index == 0:
                flag = "open_from_folder"
            elif index == 1:
                flag = "saveas_into_folder"
            elif index == 2:
                flag = "directory_popup"
            result["flag"] = flag
        return result
    
    class ButtonListener(ActionListenerBase):
        def actionPerformed(self, ev):
            try:
                cmd = ev.ActionCommand
                if cmd == "value1":
                    self.act.button_pushed()
                elif cmd == "value2":
                    self.act.button_pushed_value2()
                elif cmd == "reset":
                    self.act.reset_fields()
            except:
                pass
    
    def chooser_item_changed(self, index):
        """ Item type is changed. """
        label_value1 = ""
        label_value2 = self._("Arguments")
        state_value2 = False
        visible_value2 = True
        state_type = False
        
        if index == 0 or index == 1:
            if index == 0:
                label_value1 = self._("Document")
                label_value2 = self._("File filter")
                state_value2 = True
            else:
                label_value1 = self._("Macro")
        elif index == 2 or index == 3:
            if index == 2:
                label_value1 = self._("Command")
            else:
                label_value1 = self._("Program")
            state_value2 = True
        elif index == 4 or index == 5:
            state_type = True
            visible_value2 = False
            if self.get_special_type() == 2:
                label_value1 = self._("Arguments")
            else:
                label_value1 = self._("Path")
        
        self.grid_layout.set_row_visible(3, visible_value2)
        self.get(self.NAME_LABEL_VALUE2).setEnable(state_value2)
        self.get(self.NAME_EDIT_VALUE2).setEnable(state_value2)
        
        self.types_layout.set_visible(state_type)
        self.grid_layout.set_row_visible(1, state_type)
        if index == 4:
            self.types_layout.get_element("list_special").\
                set_visible(False)
        elif index == 5:
            self.hbox_something.set_visible(False)
            self.types_layout.set_element_visible("list_special", True)
        self.set_label(self.NAME_LABEL_VALUE1, label_value1)
        self.set_label(self.NAME_LABEL_VALUE2, label_value2)
        self.layouter.layout()
        
        state_btn_value2 = index in (0, 2)
        self.get(self.NAME_BTN_VALUE2).setEnable(state_btn_value2)
    
    def focus_movement_requested(self, shift):
        if shift:
            self.set_focus(self.NAME_BTN_HELP)
        else:
            self.set_focus(self.NAME_EDIT_NAME)
    
    def reset_fields(self):
        """ Make all fields empty. """
        self.set_name("", True)
        self.set_value1("")
        self.set_value2("")
        self.set_text(self.NAME_EDIT_DESCRIPTION, "")
        self.set_text(self.NAME_EDIT_TAGS, "")
    
    def button_pushed_value2(self):
        """ Input button event. """
        try:
            getattr(self, "choose_value2_%s" % self.PAGES[self.chooser.get_active()])()
        except Exception as e:
            print(e)
    
    def button_pushed(self):
        """ Select button event. """
        try:
            getattr(self, "choose_%s" % self.PAGES[self.chooser.get_active()])()
        except:
            pass
    
    def to_system_path(self, url):
        """ Convert url to system path if required. """
        if url.startswith("file:"):
            try:
                return uno.fileUrlToSystemPath(url)
            except:
                pass
        return url
    
    def get_file_name(self, file_path):
        name = os.path.basename(file_path)
        index = name.rfind(".")
        if index >= 0:
            return name[0:index]
        return name
    
    def get_tags(self):
        """ Get tags as list of tag names. """
        return [item.strip() 
            for item in self.get_text(self.NAME_EDIT_TAGS).split(",")]
    
    def set_name(self, name, force=False):
        """ Set name value. """
        if self.get_text(self.NAME_EDIT_NAME) == "" or force:
            self.set_text(self.NAME_EDIT_NAME, name)
    
    def set_value1(self, value):
        """ Set value to value1 field. """
        self.set_text(self.NAME_EDIT_VALUE1, value)
    
    def set_value2(self, value):
        """ Set value to value2 field. """
        self.set_text(self.NAME_EDIT_VALUE2, value)
    
    def choose_value2_document(self):
        current = self.get_text(self.NAME_EDIT_VALUE2)
        result = FileFilterDialog(
                self.ctx, self.res, 
                filter_manager=self.filter_manager, 
                default=current
        ).execute()
        if result:
            self.set_text(self.NAME_EDIT_VALUE2, result)
    
    def choose_value2_command(self):
        from bookmarks.command import BookmarksCommands
        commands = BookmarksCommands()
        arguments = self.get_text(self.NAME_EDIT_VALUE2)
        qs = commands.bk_parse_qs(arguments)
        
        result = ArgumentsDialog(
                self.ctx, self.res, query=qs
        ).execute()
        if result:
            _arguments = commands.bk_urlencode(result)
            self.set_text(self.NAME_EDIT_VALUE2, _arguments)
    
    def choose_document(self):
        d = FileOpenDialog(
            self.ctx, 
            self.res, 
            filter_manager=self.filter_manager
        )
        result = d.execute()
        if result:
            file_path = self.to_system_path(result)
            self.set_value1(file_path)
            self.set_value2(d.get_filter())
            self.set_name(self.get_file_name(file_path))
    
    def choose_macro(self):
        result = MacroSelectorDialog(self.ctx, self.res).execute()
        if result:
            self.set_value1(result)
            # name should be taken by specific script provider
            parts = result.split(":", 1)
            if len(parts) == 2:
                parts = parts[1].split("?", 1)
                if len(parts) == 2:
                    parts = parts[0].split("$", 1)
                    if len(parts) == 2:
                        path = parts[1]
                    else:
                        parts = parts[0].split(".")
                        path = parts[-1]
                    self.set_name(path)
    
    def choose_command(self):
        result = CommandsDialog(self.ctx, self.res).execute()
        if result:
            self.set_value1(result[1])
            self.set_name(result[0])
    
    def choose_program(self):
        result = FileOpenDialog(self.ctx, self.res).execute()
        if result:
            file_path = self.to_system_path(result)
            self.set_value1(file_path)
            self.set_name(self.get_file_name(file_path))
    
    def choose_something(self):
        if self.get(self.NAME_OPTION_FOLDER).getModel().State == 1:
            dialog = FolderDialog
        else:
            dialog = FileOpenDialog
        result = dialog(self.ctx, self.res).execute()
        if result:
            file_path = self.to_system_path(result)
            self.set_value1(self.to_system_path(result))
            self.set_name(self.get_file_name(file_path))
    
    def choose_special(self):
        special_type = self.get_special_type()
        if special_type == 2:
            dialog = DirectoryPopupDialog
            text = self.get_text("edit_value1")
            if text:
                args["default"] = text
        else:
            dialog = FolderDialog
        
        result = dialog(self.ctx, self.res).execute()
        if result:
            value = result
            if special_type != 2:
                value = self.to_system_path(value)
                file_path = self.to_system_path(value)
                self.set_name(self.get_file_name(file_path))
            self.set_value1(value)
            
    
    def is_selected(self, name):
        """ Get option button is selected. """
        return self.get(name).getModel().State == 1
    
    class SpecialTypeListener(ItemListenerBase):
        def itemStateChanged(self, ev):
            self.act.special_type_changed()
    
    def special_type_changed(self):
        """ When type of special item is changed. """
        self.chooser_item_changed(self.chooser.get_active())
    
    def get_special_type(self):
        """ Returns type of special item. """
        return self.get(self.NAME_LIST_SPECIAL).getSelectedItemPos()
    
    def _init(self):
        self._init_ui()
        chooser_ps = self.chooser.get_pos_size()
        self.layouter = self._init_layout()
        self.layouter.elements.margin_top = chooser_ps[3] + 8
        self.grid_layout = self.layouter.get_element("grid_data")
        self.grid_layout.set_row_visible(1, False)
        #self.grid_layout.width_request = chooser_ps[2] - \
        #    self.layouter.elements.margin_left - self.layouter.elements.margin_right
        self.grid_layout.width_request = self.chooser.get_total_width()#chooser_ps[2]
        
        self.types_layout = self.grid_layout.get_element("vbox_type")
        self.hbox_something = self.grid_layout.get_element("vbox_type").get_element("hbox_something")
        #self.layouter.layout()
        self.chooser.set_active(0)
        
        self.filter_manager = None
        if self.ARG_FILTER_MANAGER in self.args:
            self.filter_manager = self.args[self.ARG_FILTER_MANAGER]
        
        self.layouter.layout()
        ps = self.dialog.getPosSize()
        self.chooser.set_width(ps.Width)
    
    def _init_ui(self):
        import bookmarks.chooser
        from bookmarks import ICONS_DIR
        _ = self._
        URI_GRAPHICS = self.URI_GRAPHICS
        
        suffix = ".png"
        if self.dialog.StyleSettings.HighContrastMode:
            suffix = "_h" + suffix
        
        panel_defs = (
            (_("Document"), 
                ICONS_DIR + "document_32" + suffix, _("Open document in the office")), 
            (_("Macro"), 
                ICONS_DIR + "paper_32" + suffix, _("Execute macro")), 
            (_("Command"), 
                ICONS_DIR + "gear_32" + suffix, _("General menu entry")), 
            (_("Program"), 
                ICONS_DIR + "command_32" + suffix, _("Execute program")), 
            (_("Something"), 
                ICONS_DIR + "something_32" + suffix, _("Open something")), 
            (_("Special"), 
                ICONS_DIR + "special_32" + suffix, _("Create special entry"))
        )
        chooser = bookmarks.chooser.Chooser(self.ctx, self.dialog)
        chooser.create("chooser", panel_defs)
        chooser.set_item_listener(self.chooser_item_changed)
        chooser.set_tab_listener(self.focus_movement_requested)
        self.chooser = chooser
        self.chooser.fit_to_contents()
        
        listener = self.ButtonListener(self)
        btn_value1 = self.get(self.NAME_BTN_VALUE1)
        btn_value1.addActionListener(listener)
        btn_value1.setActionCommand("value1")
        btn_value2 = self.get(self.NAME_BTN_VALUE2)
        btn_value2.addActionListener(listener)
        btn_value2.setActionCommand("value2")
        
        list_model = self.get(self.NAME_LIST_SPECIAL).getModel()
        list_model.StringItemList = uno.Any(
            "[]string", 
            tuple([_(item) for item in list_model.StringItemList]))
        list_model.SelectedItems = (0,)
        self.get(self.NAME_LIST_SPECIAL).addItemListener(self.SpecialTypeListener(self))
        
        btn_reset = self.get("btn_reset")
        btn_reset.addActionListener(listener)
        btn_reset.setActionCommand("reset")
    
    def _init_layout(self):
        return DialogLayout(
      "window1", 
      self.dialog, 
      {}, 
      VBox(
      "vert", 
      {"margin_right": 8, "margin_top": 8, "margin_left": 8, "margin_bottom": 8}, 
      (
        GridLayout(
          "grid_data", 
          {"n_rows": 6, "column_spacing": 4, "row_spacing": 4, "n_columns": 2}, 
          (
            self.create_layout(
              self.TYPE_LABEL, 
              "label_name", 
              {"halign": "start"}
            ), 
            self.create_layout(
              self.TYPE_EDIT, 
              "edit_name", 
              {"hexpand": True}
            ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_type", 
              {"halign": "start"}
            ), 
          VBox(
            "vbox_type", 
            {}, 
            (
            HBox(
              "hbox_something", 
              {"spacing": 4}, 
              (
                self.create_layout(
                  self.TYPE_OPTION, 
                  "option_file", 
                  {}
                ), 
                self.create_layout(
                  self.TYPE_OPTION, 
                  "option_folder", 
                  {}
                ), 
                self.create_layout(
                  self.TYPE_OPTION, 
                  "option_web", 
                  {}
                )
              )
            ), 
              self.create_layout(
                self.TYPE_LIST, 
                "list_special", 
                {}
              )
            )
          ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_value1", 
              {"halign": "start"}
            ), 
          HBox(
            "box2", 
            {"spacing": 4}, 
            (
              self.create_layout(
                self.TYPE_EDIT, 
                "edit_value1", 
                {"hexpand": True}
              ), 
              self.create_layout(
                self.TYPE_BUTTON, 
                "btn_value1", 
                {"width_request": 80, }
              )
            )
          ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_value2", 
              {"halign": "start"}
            ), 
            HBox(
                "", 
                {"spacing": 4}, 
                (
                self.create_layout(
                  self.TYPE_EDIT, 
                  "edit_value2", 
                  {"hexpand": True}
                ), 
                self.create_layout(
                self.TYPE_BUTTON, 
                "btn_value2", 
                {"width_request": 80, }
              )
              )
            ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_tags", 
              {"valign": "start", "halign": "start"}
            ), 
            self.create_layout(
              self.TYPE_EDIT, 
              "edit_tags", 
              {}
            ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_description", 
              {"valign": "start", "halign": "start"}
            ), 
            self.create_layout(
              self.TYPE_EDIT, 
              "edit_description", 
              {"height_request": 50}
            )
          )
        ), 
        self.get_buttons_layout()
        )
      )
    )
    
    def get_buttons_layout(self):
        return HBox(
            "buttons", 
            {
                "margin_top": 4, 
                "halign": "fill", "hexpand": True
            }, 
            (
                self.create_layout(
                    self.TYPE_BUTTON, 
                    self.ID_BTN_HELP, 
                    {"width_request": 80}
                ), 
                HBox(
                    "okcancel", 
                    {
                        "spacing": 4, 
                        "halign": "end", "hexpand": True
                    }, 
                    (
                        self.create_layout(
                            self.TYPE_BUTTON, 
                            self.ID_BTN_OK, 
                            {"width_request": 80}
                        ), 
                        self.create_layout(
                            self.TYPE_BUTTON, 
                            self.ID_BTN_CANCEL, 
                            {"width_request": 80}
                        ), 
                        self.create_layout(
                            self.TYPE_BUTTON, 
                            "btn_reset", 
                            {"width_request": 80}
                        )
                    )
                )
            )
        )


class NewFolderDialog(LayoutedDialog):
    """ Let user to input data for new folder. """
    
    DIALOG_URI = DIALOG_DIR + "NewFolder.xdl"
    
    def _result(self):
        result = {}
        result["name"] = self.get_text("edit_name")
        result["description"] = self.get_text("edit_description")
        return result
    
    def _init_ui(self):
        try:
            name = self.args["default"]
            self.set_text("edit_name", name)
            self.select_text("edit_name")
        except:
            pass
    
    def _init_layout(self):
        return DialogLayout(
        "window1", 
        self.dialog, 
        {"margin_right": 8, "margin_top": 8, "margin_left": 8, "margin_bottom": 8}, 
        VBox(
        "vert", 
        {}, 
        (
          GridLayout(
            "grid1", 
            {"n_rows": 2, "column_spacing": 4, "row_spacing": 4, "n_columns": 2}, 
            (
              self.create_layout(
                self.TYPE_LABEL, 
                "label_name", 
                {"halign": "start"}
              ), 
              self.create_layout(
                self.TYPE_EDIT, 
                "edit_name", 
                {"hexpand": True, "width_request": 280}
              ), 
              self.create_layout(
                self.TYPE_LABEL, 
                "label_description", 
                {"valign": "start", "halign": "start"}
              ), 
              self.create_layout(
                self.TYPE_EDIT, 
                "edit_description", 
                {"height_request": 75}
              )
            )
          ), 
          self.get_buttons_layout()
          )
        )
      )


class TagNameListDialog(LayoutedDialog):
    """ Let user to choose a tag name. """
    
    DIALOG_URI = DIALOG_DIR + "TagName.xdl"
    
    ID_LIST_TAGNAME = "list_tagname"
    
    def _result(self):
        return self.get(self.ID_LIST_TAGNAME).getSelectedItem()
    
    def _init_ui(self):
        tag_name = self.args["default"]
        tag_names = self.args["tags"]
        
        list_tagname = self.get(self.ID_LIST_TAGNAME)
        list_tagname.addItems(tuple(tag_names), 0)
        list_tagname.selectItem(tag_name, True)
    
    def _init_layout(self):
        return DialogLayout(
        "window1", 
        self.dialog, 
        {"margin_right": 8, "margin_top": 8, "margin_left": 8, "margin_bottom": 8}, 
        VBox(
        "vert", 
        {}, 
        (
          HBox(
            "hbox1", 
            {"spacing": 4, }, 
            (
              self.create_layout(
                self.TYPE_LABEL, 
                "label_tagname", 
                {"halign": "start"}
              ), 
              self.create_layout(
                self.TYPE_LIST, 
                "list_tagname", 
                {"hexpand": True, "width_request": 200}
              ), 
            )
          ), 
          self.get_buttons_layout()
          )
        )
      )

