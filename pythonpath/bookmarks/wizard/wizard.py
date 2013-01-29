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

import uno
import unohelper
import re
from com.sun.star.ui.dialogs import XWizardController, XWizardPage


class ComponentBase(object):
    def dispose(self): pass
    def addEventListener(self, ev): pass
    def removeEventListener(self, ev): pass


class WizardPage(ComponentBase, unohelper.Base, XWizardPage):
    def __init__(self, id, page):
        self.id = id
        self.page = page
    
    def dispose(self):
        self.page = None
    
    # XWizardPage
    def activatePage(self):
        self.page.getModel().Step = self.id
    
    def commitPage(self, reason):
        return True
    
    def canAdvance(self):
        return True
    
    @property
    def Window(self):
        return self.page
    
    @property
    def PageId(self):
        return self.id


class Wizard(object, unohelper.Base, XWizardController):
    
    def __init__(self, ctx, res={}, title=None, ids=(), titles={}, help_url=None):
        self.ctx = ctx
        self.res = res
        self.title = title
        self.titles = titles
        wizard = self.create_service("com.sun.star.ui.dialogs.Wizard")
        uno.invoke(wizard, "initialize", ((uno.Any("[]short", ids), self),))
        self.wizard = wizard
        if self.title:
            wizard.setTitle(self._(title))
        if help_url:
            wizard.HelpURL = help_url
    
    def _(self, text):
        return self.res.get(text, text)
    
    def create_service(self, name, args=None):
        if args:
            return self.ctx.getServiceManager().\
                createInstanceWithArgumentsAndContext(name, args, self.ctx)
        else:
            return self.ctx.getServiceManager().\
                createInstanceWithContext(name, self.ctx)
    
    def dispose(self):
        pass #self.wizard.dispose()
    
    def execute(self):
        if self.wizard.execute():
            return 
        return None
    
    def _create_page(self, parent, id):
        pass
    
    # XWizardController
    def createPage(self, parent, id):
        return WizardPage(id, self._create_page(parent, id))
    
    def getPageTitle(self, id):
        return self._(self.titles.get(id, ""))
    
    def canAdvance(self):
        return True
    
    def onActivatePage(self, id):
        pass
    
    def onDeactivatePage(self, id):
        pass
    
    def confirmFinish(self):
        # asked before close by OK. If False returned, dialog can not be closed.
        return True


from com.sun.star.awt import XMenuListener, Point
from com.sun.star.awt.grid import XGridSelectionListener
from com.sun.star.task import XInteractionHandler
from com.sun.star.ucb import XCommandEnvironment, XProgressHandler

from bookmarks import EXT_DIR, CONFIG_NODE_CONTROLLERS
from bookmarks.tools import get_config, get_current_locale, \
    load_resource, show_message#, get_resource
from bookmarks.control import GridWindow
from bookmarks.values import ActionListenerBase, \
    ListenerBase, ItemListenerBase, TextListenerBase, ItemListenerBase
from bookmarks.wizard.dialogs import LabelDialog

DIALOG_DIR = EXT_DIR + "dialogs/"

class BookmarksMenuWizard(Wizard, GridWindow):
    
    DIALOG_NAME = "Wizard%s.xdl"
    
    TITLE = "New Bookmarks Extension Package"
    TITLES = (
        "Define name", 
        "Define label", 
        "Choose position", 
        "Choose document types", 
        "Options", 
        "Save package", 
    )
    
    ID_BOOKMARKS = "id.label.bookmarks"
    
    ID_GRID = "grid"
    ID_BTN_POSITION = "btn_position"
    ID_OPTION_BEFORE = "option_before"
    ID_OPTION_AFTER = "option_after"
    ID_BTN_EDIT = "btn_label_edit"
    ID_BTN_ADD = "btn_label_add"
    ID_BTN_REMOVE = "btn_label_remove"
    ID_LIST_CONTEXT = "list_types"
    ID_LIST_TYPES_POSITION = "list_types_position"
    ID_CHECK_CONTEXT = "check_context"
    ID_OPTION_ALL = "option_types_all"
    ID_OPTION_SELECT = "option_types_select"
    ID_BTN_EXPORT = "btn_export"
    ID_BTN_INSTALL = "btn_install"
    ID_BTN_CLOSE = "btn_close"
    ID_COMBO_NAME = "combo_name"
    ID_CHECK_ANOTHER = "check_another"
    ID_LIST_MENU = "list_menu"
    ID_CHECK_IMPORT_OLDER = "check_import_older"
    ID_CHECK_REMOVE_OLDER = "check_remove_older"
    ID_CHECK_INCLUDE = "check_include"
    
    NODE_LINGU = "/org.openoffice.Office.Linguistic/General"
    NODE_INSTALLED_LOCALES = "/org.openoffice.Setup/Office/InstalledLocales"
    
    HELP_URL = "mytools.bookmarks.BookmarksMenu:wizard"
    
    def __init__(self, ctx, res):
        ids = (1, 2, 3, 4, 5, 6)
        titles = dict([(id, title) for id, title in zip(ids, self.TITLES)])
        Wizard.__init__(
            self, ctx, res, 
            self.TITLE, ids, titles, self.HELP_URL)
        self.grid = None
        self.pages = {}
        self.current = 0
        self.names = None
        self.name = ""
        self.ui_locale = ""
        self.position_button_label = ""
        self.position_context = ""
        self.menu = None
        self.menu_settings = None
        self.menu_containers = {}
        self.menu_listener = None
        self.generic_popups = None
        self.generic_commands = None
        self.category_commands = None
        self.category_popups = None
        self.package = None
        self.finished = False
        self.installed = None
        self.selected_position = "/.uno:Help"
        self.name_exp = re.compile("[A-Za-z0-9_]+$")
        
        import bookmarks.tools
        self.use_point = bookmarks.tools.check_method_parameter(
            ctx, "com.sun.star.awt.XPopupMenu", "execute", 1, "com.sun.star.awt.Point")
    
    def execute(self):
        if self.wizard.execute():
            pass
            # migrate or something to do
        if self.package:
            self.package.delete_package()
    
    def translate_labels(self, page):
        _ = self._
        #dialog_model = page.getModel()
        #dialog_model.Title = _(dialog_model.Title)
        for control in page.getControls():
            model = control.getModel()
            if hasattr(model, "Label"):
                model.Label = _(model.Label)
    
    def _create_page(self, parent, id):
        page = self.create_service(
            "com.sun.star.awt.ContainerWindowProvider").\
                createContainerWindow(
                    DIALOG_DIR + (self.DIALOG_NAME % str(id)), 
                    "", parent, None)
        self.pages[id] = page
        self.translate_labels(page)
        try:
            getattr(self, "_init_ui_%s" % id)(page)
        except Exception as e:
            print(e)
            import traceback
            traceback.print_exc()
        return page
    
    def onActivatePage(self, id):
        try:
            if self.current == 1:
                new_name = self.get_name()
                if new_name != self.name:
                    self.name = new_name
            
            self.current = id
            self.update_wizard_state()
            if id == 6:
                self.enable_button(1, id != 6)
            if id == 5:
                self.set_enable(5, self.ID_CHECK_INCLUDE, self.name in self.names)
        except Exception as e:
            print(e)
            import traceback
            traceback.print_exc()
    
    def canAdvance(self):
        return True
    
    def confirmFinish(self):
        return self.finished
    
    def get(self, id, name):
        return self.pages[id].getControl(name)
    
    def set_focus(self, id, name):
        self.get(id, name).setFocus()
    
    def set_enable(self, id, name, state):
        try:
            self.get(id, name).setEnable(state)
        except:
            pass
    
    def get_text(self, id, name):
        return self.get(id, name).getModel().Text
    
    def get_state(self, id, name):
        return self.get(id, name).getModel().State
    
    def enable_button(self, type, state):
        self.wizard.enableButton(type, state)
    
    # step 1
    class NameTextListener(TextListenerBase):
        def textChanged(self, ev):
            self.act.name_changed()
    
    def name_changed(self):
        try:
            self.update_wizard_state()
        except Exception as e:
            print(e)
    
    def get_name(self):
        return self.get_text(1, self.ID_COMBO_NAME)
    
    
    # step 2
    class GridSelectionListener(ListenerBase, XGridSelectionListener):
        def selectionChanged(self, ev):
            self.act.grid_selection_changed()
    
    class ButtonListener(ActionListenerBase):
        def actionPerformed(self, ev):
            try:
                self.act.button_pushed(ev.ActionCommand)
            except Exception as e:
                print(e)
                traceback.print_exc()
    
    def get_labels(self):
        if self.grid:
            data = []
            for i in range(self.grid_get_row_count()):
                data.append(
                    (
                        self.grid_get_row_heading(i), 
                        self.grid_get_row_data(i)[1]
                    )
                )
            return data
        self._init_labels()
        return [(key, value) for key, value in self.labels_for_locale.items()]
    
    def get_preffered_label(self):
        return self.labels_for_locale.get(self.ui_locale, self.labels["en-US"])
    
    def get_non_defined_locales(self):
        return [locale for locale in self.installed_locales if not locale in self.labels_for_locale]
    
    def grid_get_row_heading(self, index):
        return self.grid_get_data_model().getRowHeading(index)
    
    def grid_get_row_data(self, index):
        return self.grid_get_data_model().getRowData(index)
    
    def get_selected_row(self):
        index = self.grid_get_single_selection()
        if 0 <= index:
            return (
                self.grid_get_row_heading(index), 
                self.grid_get_row_data(index)
            )
        return None
    
    def get_selected_locale(self):
        index = self.grid_get_single_selection()
        if 0 <= index:
            return self.grid_get_cell_data(0, index)
        return None
    
    def grid_get_cell_data(self, column, row):
        return self.grid_get_data_model().getCellData(column, row)
    
    def grid_selection_changed(self):
        self.update_buttons_state()
    
    def button_pushed(self, command):
        if command == "add":
            not_defined = self.get_non_defined_locales()
            if not_defined:
                result = LabelDialog(
                    self.ctx, 
                    self.res, 
                    locales=[(locale, self.names_for_iso.get(locale, locale)) 
                        for locale in not_defined], 
                    default=self.labels["en-US"]
                ).execute()
                if result:
                    self.labels_for_locale[result[0]] = result[1]
                    self.grid_get_data_model().insertRow(
                        self.grid_get_row_count(), 
                        result[0], 
                        (self.names_for_iso.get(result[0], result[0]), result[1]))
                    self.grid_redraw()
        
        elif command == "edit":
            row = self.get_selected_row()
            if row:
                result = LabelDialog(
                    self.ctx, 
                    self.res, 
                    locales=((row[0], self.names_for_iso.get(row[0], row[0])),), 
                    default=row[1][1], 
                    disable_locale=True
                ).execute()
                if result:
                    self.labels_for_locale[result[0]] = result[1]
                    index = self.grid_get_single_selection()
                    self.grid_update_cell(1, index, result[1])
                    self.grid_redraw()
        
        elif command == "remove":
            index = self.grid_get_single_selection()
            if 0 <= index:
                locale = self.grid_get_row_heading(index)
                if locale != "en-US":
                    self.labels_for_locale.pop(locale)
                    self.grid_remove_row(index)
                    if 0 < index:
                        index -= 1
                    self.grid_select_row(index)
                    self.grid_redraw()
                    self.update_buttons_state()
    
    def update_buttons_state(self):
        self.set_enable(2, self.ID_BTN_ADD, bool(len(self.get_non_defined_locales())))
        index = self.grid_get_single_selection()
        is_selected = index >= 0
        self.set_enable(2, self.ID_BTN_EDIT, is_selected)
        is_removeable = is_selected
        if is_removeable:
            if index >= 0:
                is_removeable = self.grid_get_cell_data(0, index) != "en-US"
        self.set_enable(2, self.ID_BTN_REMOVE, is_removeable)
    
    
    #  step 3
    class MenuItemListener(ItemListenerBase):
        def itemStateChanged(self, ev):
            self.act.menu_item_changed()
    
    class PositionButtonListener(ActionListenerBase):
        def actionPerformed(self, ev):
            self.act.position_button_pushed()
    
    class PositionContextListener(ItemListenerBase):
        def itemStateChanged(self, ev):
            self.act.position_context_changed()
    
    class PositionMenuListener(unohelper.Base, XMenuListener):
        def __init__(self, act):
            self.act = act
        def disposing(self, ev):
            self.act = None
        def activate(self, ev): pass
        def deactivate(self, ev): pass
        def highlight(self, ev): pass
        def select(self, ev):
            self.itemSelected(ev)
        
        # since AOO 4.0
        def itemActivated(self, ev): pass
        def itemDeactivated(self, ev): pass
        def itemHighlighted(self, ev):
        def itemSelected(self, ev):
            self.act.position_selected(ev.Source.getCommand(ev.MenuId))
    
    def get_merge_point(self):
        return self.selected_position
    
    def get_merge_command(self):
        if 3 in self.pages:
            if self.get_state(3, self.ID_OPTION_BEFORE):
                return "AddBefore"
            return "AddAfter"
        return "AddBefore"
    
    def get_merge_point_label(self):
        if 3 in self.pages:
            list_types = self.get(3, self.ID_LIST_MENU)
            index = list_types.getSelectedItemPos()
            if 0 <= index < list_types.getItemCount():
                base_label = list_types.getSelectedItem()
                btn_position_model = self.get(3, self.ID_BTN_POSITION).getModel()
                label = btn_position_model.Label
                if label != self.position_button_label:
                    return "%s > %s" % (base_label, label)
                else:
                    return base_label
        return "Help"
    
    def get_position(self):
        return self.get_state(3, self.ID_OPTION_BEFORE)
    
    def set_position_label(self, text):
        self.get(3, self.ID_BTN_POSITION).getModel().Label = text
    
    def position_selected(self, command):
        self.selected_position = "%s\%s" % (self.get_selected_menu(), command)
    
    def menu_item_changed(self):
        self.selected_position = self.get_selected_menu()
        self.set_position_label(self.position_button_label)
    
    def position_button_pushed(self):
        if not self.menu:
            self.menu = self.create_service("com.sun.star.awt.PopupMenu")
            self.menu.addMenuListener(self.PositionMenuListener(self))
        self.menu.clear()
        try:
            self.fill_menu(self.menu)
            pos = self.get(3, self.ID_BTN_POSITION).getPosSize()
            if self.use_point:
                pos = Point(pos.X, pos.Y)
            n = self.menu.execute(self.pages[3].getPeer(), pos, 0)
            if 0 < n:
                command = self.menu.getCommand(n)
                self.selected_position = "%s\%s" % (self.get_selected_menu(), command)
                self.set_position_label(self.menu.getItemText(n))
        except Exception as e:
            print(e)
    
    def fill_menu(self, menu):
        menu_defs = self.get_selected_menu()
        container = self.menu_containers.get(menu_defs)
        if menu and container:
            for i in range(container.getCount()):
                item = container.getByIndex(i)
                command, label, type, sub_container = self.read_item(item)
                id = i+1
                if type:
                    menu.insertSeparator(i)
                else:
                    if not label:
                        if self.generic_commands.hasByName(command):
                            label = self.generic_commands.getByName(command).Label
                        elif self.category_commands.hasByName(command):
                            label = self.category_commands.getByName(command).Label
                        elif self.generic_popups.hasByName(command):
                            label = self.generic_popups.getByName(command).Label
                        elif self.category_popups.hasByName(command):
                            label = self.category_popups.getByName(command).Label
                        else:
                            label = command
                    menu.insertItem(id, label, 0, i)
                    menu.setCommand(id, command)
    
    def read_item(self, item):
        label = ""
        command = ""
        container = None
        type = None
        for value in item:
            if value.Name == "CommandURL":
                command = value.Value
            elif value.Name == "ItemDescriptorContainer":
                container = value.Value
            elif value.Name == "Label":
                label = value.Value
            elif value.Name == "Type":
                type = value.Value
            #else:
            #   print(value.Name)
            #print(value.Name)
        return command, label, type, container
    
    def get_submenus(self, items, containers, parent_command, parent_label, container):
        for i in range(container.getCount()):
            command, label, type, sub_container = \
                self.read_item(container.getByIndex(i))
            if sub_container:
                if not label:
                    if self.generic_popups.hasByName(command):
                        label = self.generic_popups.getByName(command).Label
                    elif self.category_popups.hasByName(command):
                        label = self.category_popups.getByName(command).Label
                    elif self.generic_commands.hasByName(command):
                        label = self.generic_commands.getByName(command).Label
                    else:
                        label = command
                
                if parent_command:
                    label = "%s > %s" % (parent_label, label.replace("~", ""))
                    command = "%s\%s" % (parent_command, command)
                else:
                    label = label.replace("~", "")
                items.append((command, label))
                containers[command] = sub_container
                self.get_submenus(items, containers, command, label, sub_container)
    
    def position_context_changed(self):
        try:
            self.menu_containers.clear()
            position_context, ref = self.get_position_context()
            try:
                self.category_popups = get_config(self.ctx, 
                    "/org.openoffice.Office.UI.%s/UserInterface/Popups" % ref)
                self.category_commands = get_config(self.ctx, 
                    "/org.openoffice.Office.UI.%s/UserInterface/Commands" % ref)
            except:
                pass
            manager = self.config_supplier.getUIConfigurationManager(
                position_context)
            self.menu_settings = manager.getSettings(
                    "private:resource/menubar/menubar", False)
            items = []
            self.get_submenus(items, self.menu_containers, "", "", self.menu_settings)
            #print(items)
            list_menu = self.get(3, self.ID_LIST_MENU)
            list_menu_model = list_menu.getModel()
            list_menu_model.StringItemList = uno.Any("[]string", 
                tuple([item[1] for item in items]))
            for i, item in enumerate(items):
                list_menu_model.setItemData(i, item[0])
            list_menu.selectItemPos(list_menu.getItemCount()-1, True)
        except Exception as e:
            print(e)
    
    
    def get_selected_menu(self):
        list_types = self.get(3, self.ID_LIST_MENU)
        index = list_types.getSelectedItemPos()
        if 0 <= index < list_types.getItemCount():
            return list_types.getModel().getItemData(index)
        return
    
    def get_position_context(self):
        list_types = self.get(3, self.ID_LIST_TYPES_POSITION)
        index = list_types.getSelectedItemPos()
        if 0 <= index < list_types.getItemCount():
            return list_types.getModel().getItemData(index).split(";", 1)
        return "", ""
    
    # step 4
    class ContextTypesListener(ItemListenerBase):
        def itemStateChanged(self, ev):
            try:
                self.act.context_changed()
            except Exception as e:
                print(e)
    
    def context_changed(self):
        self.set_enable(self.ID_LIST_CONTEXT, 
            not bool(self.get_state(4, self.ID_OPTION_ALL)))
    
    def get_merge_context(self):
        if 4 in self.pages:
            if self.get_state(4, self.ID_OPTION_ALL):
                return ""
            list_context = self.get(4, self.ID_LIST_CONTEXT)
            list_context_model = list_context.getModel()
            return ",".join(
                [list_context_model.getItemData(position) 
                    for position in list_context.getSelectedItemsPos()]
            )
        return ""
    
    # step 5
    # check older package is installed
    
    def get_include_state(self):
        if self.pages.get(5, None):
            return self.get_state(5, self.ID_CHECK_INCLUDE)
        return False
    
    def get_another_state(self):
        # check named item is exists
        return self.get_state(5, self.ID_CHECK_ANOTHER) and \
            self.get_name() in self.names
    
    # step 6
    
    def confirmFinish(self):
        """ Finish is clicked. """
        try:
            self.package_action("export")
            return True
        except:
            return False
    
    class PackageButtonListener(ButtonListener):
        def actionPerformed(self, ev):
            try:
                self.act.package_action(ev.ActionCommand)
            except Exception as e:
                print(e)
                import traceback
                traceback.print_exc()
    
    class ProgressHandler(unohelper.Base, XProgressHandler):
        def push(self, status): pass
        def update(self, status): pass
        def pop(self): pass
    
    class Interactionhalder(unohelper.Base, XInteractionHandler):
        def __init__(self, act):
            self.act = act
        
        def handle(self, request):
            message = request.getRequest()
            if not isinstance(message, str):
                message = message.Message
            try:
                n = self.act.query(message)
                if n == 1:
                    type_name = "com.sun.star.task.XInteractionApprove"
                else:
                    type_name = "com.sun.star.task.XInteractionAbort"
                for continuation in request.getContinuations():
                    if continuation.queryInterface(uno.getTypeByName(type_name)):
                        continuation.select()
            except Exception as e:
                print(e)
    
    def query(self, message, buttons=2):
        return show_message(self.ctx, self.pages[6].getPeer(), 
            message, "", "querybox", buttons)
    
    
    class CommandEnv(unohelper.Base, XCommandEnvironment):
        def __init__(self, act):
            self.act = act
        
        def getInteractionHandler(self):
            return self.act.__class__.Interactionhalder(self.act)
        
        def getProgressHandler(self):
            return self.act.__class__.ProgressHandler()
    
    def get_command_by_name(self, name):
        config = get_config(self.ctx, CONFIG_NODE_CONTROLLERS)
        for node_name in config.getElementNames():
            node = config.getByName(node_name)
            if node.Name == name:
                return node_name
        return ""
    
    def package_action(self, command):
        from bookmarks import EXT_ID
        from bookmarks.manager import BookmarksManager
        import bookmarks.wizard.package
        if not self.package:
            self.package = bookmarks.wizard.package.Package(self.ctx)
        
        is_include = self.get_include_state()
        data = None
        ext_id = None
        name = self.get_name()
        another = self.get_another_state()
        if name in self.names:
            # already exists
            ext_id = self.names[name]
            #if not another:
            #   # overwrite, with the same extension id
            if is_include:
                _command = self.get_command_by_name(name)
                if _command:
                    data_path = BookmarksManager.command_to_path(self.ctx, _command)
                    try:
                        f = open(data_path, "r")
                        data = f.read()
                        f.close()
                    except:
                        pass
        else:
            ext_id = EXT_ID + "." + name
            data = BookmarksManager.create_simple_base(self.res, True)
        
        merge_command = self.get_merge_command()
        if merge_command == "AddAfter":
            prefix = "After %s"
        else:
            prefix = "Before %s"
        description = self._(prefix) % self.get_merge_point_label()
        
        self.package.generate(
            name, 
            self.get_labels(), 
            self.get_merge_point(), 
            merge_command, 
            self.get_merge_context(), 
            description, 
            data, 
            another, 
            ext_id
        )
        if command == "install":
            result = self.package.install(self.CommandEnv(self))
            
        elif command == "export":
            from bookmarks.dialog import FileSaveDialog
            result = FileSaveDialog(
                self.ctx, self.res, 
                default="BookmarksMenu-%s.oxt" % name
            ).execute()
            if result:
                try:
                    self.package.export(result)
                except Exception as e:
                    pass
            else:
                raise Exception("Canceled")
    
    def update_wizard_state(self):
        lv = 0
        if self.get_name():
            lv = 1
            if self.selected_position:
                lv = 2
        is_finished = False
        next_state = True
        if lv == 0:
            disabled = (2, 3, 4, 5, 6)
            enabled = ()
            next_state = False
        elif lv == 1:
            disabled = (4, 5, 6)
            enabled = (2, 3)
            
        elif lv == 2:
            disabled = ()
            enabled = (2, 3, 4, 5, 6)
            is_finished = True
        
        try:
            if lv > 0:
                next_state = not self.name_exp.match(self.get_name()) is None
        except:
            next_state = False
        
        self.finished = is_finished
        self.enable_button(1, next_state)
        self.enable_button(3, next_state)
        self.set_enable(
            5, self.ID_CHECK_ANOTHER, self.get_name() in self.names)
        try:
            wizard = self.wizard
            # do not try to change state of first page
            for i in enabled:
                wizard.enablePage(i, True)
            for i in disabled:
                wizard.enablePage(i, False)
        except Exception as e:
            print(e)
    
    def _init_names(self):
        self.names = {}
        config = get_config(self.ctx, CONFIG_NODE_CONTROLLERS)
        for id in config.getElementNames():
            self.names[config.getByName(id).Name] = id
    
    def _init_labels(self):
        _ui_locale = get_current_locale(self.ctx)
        if _ui_locale.Country:
            ui_locale = "%s-%s" % (_ui_locale.Language, _ui_locale.Country)
        else:
            ui_locale = _ui_locale.Language
        self.ui_locale = ui_locale
        
        # predefined labels from resource
        res = load_resource(self.ctx, EXT_DIR + "resources", "strings", _ui_locale)
        labels = {}
        for locale in res.getLocales():
            if res.hasEntryForIdAndLocale(self.ID_BOOKMARKS, locale):
                lang = locale.Language
                country = locale.Country
                if country:
                    _locale = "%s-%s" % (lang, country)
                else:
                    _locale = lang
                labels[_locale] = res.resolveStringForLocale(self.ID_BOOKMARKS, locale)
        self.labels = labels
        
        # labels for installed locales
        self.installed_locales = self.get_installed_locales()
        self.names_for_iso = self.create_lang_name_map(self.installed_locales)
        #print(self.names_for_iso)
        
        # shown labels
        labels_for_locale = {}
        for locale in self.installed_locales:
            # load default label from resource, en-US for not found
            try:
                label = labels[locale]
            except:
                if locale == ui_locale:
                    label = labels["en-US"]
                else:
                    # supports fallback. if not the current ui locale, 
                    # ignore it but it can be added later
                    continue
            labels_for_locale[locale] = label
        if not "en-US" in labels_for_locale:
            labels_for_locale["en-US"] = labels["en-US"]
        self.labels_for_locale = labels_for_locale
        
        
    
    def get_installed_locales(self):
        # the same with ui locales
        return get_config(self.ctx, self.NODE_INSTALLED_LOCALES).getElementNames()
    
    def create_lang_name_map(self, locales):
        """ Get readable names for iso locales. """
        iso_names = {}
        for locale in locales:
            iso_names[locale] = locale
        #from bookmarks.wizard.langs import iso_to_lcid
        """
        for locale in locales:
            found = 0
            found = iso_to_lcid.get(tuple(locale.split("-", 1)), 0)
            if not found:
                # search in key
                parts = locale.split("-", 1)
                lang = parts[0]
                country = ""
                if len(parts) == 2:
                    country = parts[1]
                
                for k in iso_to_lcid.iterkeys():
                    if k[0] == lang:
                        found = iso_to_lcid[k]
                        break
            if found:
                iso_names[locale] = found
            else:
                iso_names[locale] = locale
        """
        #resources = get_resource(self.ctx, "svt", "getStringList", 0x40fb)
        #lcid_to_name = dict([(resource.Value, resource.Name) for resource in resources])
        #for k, v in iso_names.iteritems():
        #    if isinstance(v, int):
        #        iso_names[k] = lcid_to_name.get(v, k)
        return iso_names
    
    def _init_config_manager(self):
        self.config_supplier = self.create_service(
            "com.sun.star.ui.ModuleUIConfigurationManagerSupplier")
        self.generic_popups = get_config(self.ctx, 
            "/org.openoffice.Office.UI.GenericCommands/UserInterface/Popups")
        self.generic_commands = get_config(self.ctx, 
            "/org.openoffice.Office.UI.GenericCommands/UserInterface/Commands")
    
    def _init_factory_names(self, list_context, ref=False):
        config = get_config(self.ctx, 
            "/org.openoffice.Setup/Office/Factories")
        modules = []
        for name in config.getElementNames():
            node = config.getByName(name)
            if name == "com.sun.star.text.GlobalDocument":
                label = "Global"
            elif name == "com.sun.star.frame.StartModule":
                label = "StartModule"
            else:
                label = node.ooSetupFactoryUIName
            modules.append((label, name, node.ooSetupFactoryCommandConfigRef))
        modules.sort()
        
        list_context_model = list_context.getModel()
        list_context_model.StringItemList = uno.Any("[]string", tuple([item[0] for item in modules]))
        if ref:
            for i, item in enumerate(modules):
                list_context_model.setItemData(i, "%s;%s" % (item[1], item[2]))
        else:
            for i, item in enumerate(modules):
                list_context_model.setItemData(i, item[1])
        
    
    def _init_ui_1(self, page):
        self.enable_button(3, False)
        pg = page.getControl
        pg(self.ID_COMBO_NAME).addTextListener(self.NameTextListener(self))
        
        self._init_names()
        self.get(1, self.ID_COMBO_NAME).getModel().StringItemList = \
            uno.Any("[]string", tuple([key for key in self.names.keys()]))
        
    
    def _init_ui_2(self, page):
        _ = self._
        dialog_model = page.getModel()
        grid_model = dialog_model.createInstance(
            "com.sun.star.awt.grid.UnoControlGridModel")
        grid_model.setPropertyValues(
            ("Border", "HScroll", "SelectionModel", 
                "ShowColumnHeader", "ShowRowHeader", "VerticalAlign", 
                "VScroll"), 
            (0, False, 1, True, False, 1, True))
        grid_model.setPropertyValues(
            ("Height", "PositionX", "PositionY", "Step", "Width"), 
            (50, 14, 25, 2, 120))
        dialog_model.insertByName(self.ID_GRID, grid_model)
        grid_model.GridDataModel = self.create_service(
            "com.sun.star.awt.grid.DefaultGridDataModel")
        
        columns = grid_model.ColumnModel
        if not columns:
            columns = self.create_service(
                "com.sun.star.awt.grid.DefaultGridColumnModel")
        for title in (_("Locale"), _("Label")):
            column = columns.createColumn()
            column.Title = title
            column.ColumnWidth = 100
            columns.addColumn(column)
        grid_model.ColumnModel = columns
        
        self.grid = page.getControl(self.ID_GRID)
        self.grid.addSelectionListener(self.GridSelectionListener(self))
        
        pg = page.getControl
        
        pg(self.ID_BTN_ADD).setActionCommand("add")
        pg(self.ID_BTN_EDIT).setActionCommand("edit")
        pg(self.ID_BTN_REMOVE).setActionCommand("remove")
        
        listener = self.ButtonListener(self)
        pg(self.ID_BTN_ADD).addActionListener(listener)
        pg(self.ID_BTN_EDIT).addActionListener(listener)
        pg(self.ID_BTN_REMOVE).addActionListener(listener)
        
        self._init_labels()
        
        rows = []
        headings = []
        for key, value in self.labels_for_locale.items():
            headings.append(key)
            rows.append((self.names_for_iso.get(key, key), value))
        
        grid_data_model = self.get(2, self.ID_GRID).getModel().GridDataModel
        grid_data_model.addRows(
            tuple(headings), tuple(rows)
        )
        self.update_buttons_state()
    
    def _init_ui_3(self, page):
        pg = page.getControl
        pg(self.ID_BTN_POSITION).addActionListener(self.PositionButtonListener(self))
        pg(self.ID_LIST_TYPES_POSITION).addItemListener(self.PositionContextListener(self))
        pg(self.ID_LIST_MENU).addItemListener(self.MenuItemListener(self))
        
        self.position_button_label = self.get(3, self.ID_BTN_POSITION).getModel().Label
        self._init_config_manager()
        
        self._init_factory_names(pg(self.ID_LIST_TYPES_POSITION), True)
        self.get(3, self.ID_LIST_TYPES_POSITION).selectItem("Writer", True)
    
    def _init_ui_4(self, page):
        pg = page.getControl
        listener = self.ContextTypesListener(self)
        pg(self.ID_OPTION_ALL).addItemListener(listener)
        pg(self.ID_OPTION_SELECT).addItemListener(listener)
        
        self._init_factory_names(pg(self.ID_LIST_CONTEXT))
        self.set_enable(4, self.ID_LIST_CONTEXT, False)
    
    def _init_ui_5(self, page):
        self.set_enable(5, self.ID_CHECK_INCLUDE, False)
        self.get(5, self.ID_CHECK_ANOTHER).setEnable(False)
    
    def _init_ui_6(self, page):
        pass


def wizard(*args):
    ctx = XSCRIPTCONTEXT.getComponentContext()
    try:
        result = BookmarksMenuWizard(ctx, {}).execute()
        print(result)
    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()
