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

from bookmarks.values import PosSize


class BaseDialog(object):
    """ Base class for all dialogs. """
    
    def __init__(self, ctx, reuse=False, **kwds):
        self.ctx = ctx
        self.reuse = reuse
        self.args = kwds
        self.dialog = None
    
    def _result(self):
        """ Returns result of the dialog executed. 
        When canceled, None is returned. """
        return None
    
    def create_dialog(self):
        """ Create instance of dialog for this dialog instance."""
        pass
    
    def _init(self):
        """ Initialize something. """
        pass
    
    def _dispose(self):
        """ Destruct dialog. """
        pass
    
    def execute(self):
        """ Execute dialog and returns result. """
        if self.dialog is None:
            self.create_dialog()
            self._init()
        result = None
        if self.dialog.execute():
            result = self._result()
        if not self.reuse:
            self.dialog.dispose()
            self.dialog = None
            self._dispose()
        return result
    
    def create_service(self, name):
        """ Instantiate servie. """
        return self.ctx.getServiceManager().createInstanceWithContext(
            name, self.ctx)


class DialogBase(BaseDialog):
    """ Base class for dialogs. """
    
    WIDTH_DIALOG = 400
    
    HEIGHT_DIALOG = 400
    
    HEIGHT_LABEL = 25
    HEIGHT_BUTTON = 25
    HEIGHT_EDIT = 25
    
    def __init__(self, ctx, res=None, reuse=False, **kwds):
        BaseDialog.__init__(self, ctx, reuse, **kwds)
        self.res = res
    
    def _(self, name):
        """ Get resource by name. """
        return res.get(name, name)
    
    def create_dialog(self):
        self.dialog = self._create_dialog()
    
    def _init(self):
        pass
    
    def get(self, name):
        """ Get control from dialog. """
        return self.dialog.getControl(name)
    
    def set_focus(self, name):
        self.get(name).setFocus()
    
    def get_text(self, name):
        """ Get text from control. """
        return self.get(name).getModel().Text
    
    def set_text(self, name, text):
        """ Set text to the control having Text property. """
        self.get(name).getModel().Text = text
    
    def get_label(self, name):
        """ Get label text from the control. """
        return self.get(name).getModel().Label
    
    def set_label(self, name, label):
        """ Set label text to the control. """
        self.get(name).getModel().Label = label
    
    def select_text(self, name):
        """ Select all text in the edit field. """
        from com.sun.star.awt import Selection
        self.get(name).setSelection(Selection(0, 1000))
    
    def get_state(self, name):
        """ Get state of check box. """
        return self.get(name).getModel().State
    
    def set_state(self, name, state):
        """ Set state of checkbox. """
        self.get(name).getModel().State = state
    
    def set_enable(self, name, state):
        self.get(name).setEnable(state)


class BuiltinDialog(BaseDialog):
    """ Base class for wrapper dialogs of built-in dialogs. 
        
        _result and _init methods have to be implemented by subclass.
    """
    
    SERVICE_NAME = None
    
    DEFALUT_TITLE = ""
    
    NAME_TITLE = "title"
    
    def _set_title(self):
        """ Set title from args. """
        if self.NAME_TITLE in self.args:
            self.dialog.setTitle(self.args[self.NAME_TITLE], self.DEFALUT_TITLE)
    
    def create_dialog(self):
        """ Initialize dialog by SERVICE_NAME instance variable. """
        self.dialog = self.create_service(self.SERVICE_NAME)


class FolderDialog(BuiltinDialog):
    """ Let user to choose a folder. """
    
    SERVICE_NAME = "com.sun.star.ui.dialogs.FolderPicker"
    
    NAME_FOLDER = "directory"
    NAME_DESCRIPTION = "description"
    
    def _result(self):
        return self.dialog.getDirectory()
    
    def _init(self):
        """ Initialize dialog. These keyword arguments can be 
        used to initialize dialog. 
        
        directory: initial directory.
        description: short description about to choose a folder.
        """
        self._set_title()
        
        dialog = self.dialog
        args = self.args
        if self.NAME_FOLDER in args:
            dialog.setDisplayDirectory(args[self.NAME_FOLDER])
        if self.NAME_DESCRIPTION in args:
            dialog.setDescription(args[self.NAME_DESCRIPTION])


class FileDialogBase(BuiltinDialog):
    """ Base class for file picker dialog. """
    
    SERVICE_NAME = "com.sun.star.ui.dialogs.FilePicker"
    
    INITIALIZE_TEMPLATE = 0
    
    NAME_INITIALIZE = "initialize"
    
    NAME_DIRECTORY = "directory"
    NAME_MULTI = "multi"
    NAME_DEFAULT = "default"
    
    NAME_FILTERS = "filters"
    NAME_CURRENT_FILTER = "current_filter"
    
    NAME_HELP = "help"
    
    NAME_FILTER_MANAGER = "filter_manager"
    
    def get_filter(self):
        """ Returns current filter selected. """
        try:
            return self.selected_filter
        except:
            return self.dialog.getCurrentFilter()
    
    def _result(self):
        """ Returns selected file URLs. 
        
        When a file selected, simply an URL is returned. 
        Otherwise list of file URL is returned, all URL in 
        full length.
        """
        self.selected_filter = self.get_filter()
        files = self.dialog.getFiles()
        if len(files) == 1:
            return files[0]
        else:
            base_url = files[0]
            return [base_url + "/" + name for name in files[1:]]
    
    def _init(self):
        """ Initialize filepicker dialog. Following keyword 
        arguments can be used to initialize. 
        
        """
        self._set_title()
        self._init_type()
        self._init_variables()
    
    def _init_type(self):
        dialog = self.dialog
        args = self.args
        
        if self.NAME_INITIALIZE in args:
            initialize = args[self.NAME_INITIALIZE]
        else:
            initialize = self.INITIALIZE_TEMPLATE
        dialog.initialize((initialize, ))
    
    def _init_variables(self):
        dialog = self.dialog
        args = self.args
        if self.NAME_DIRECTORY in args:
            dialog.setDisplayDirectory(args[self.NAME_DIRECTORY])
        if self.NAME_MULTI in args:
            dialog.setMultiSelectionMode(args[self.NAME_MULTI])
        if self.NAME_DEFAULT in args:
            dialog.setDefaultName(args[self.NAME_DEFAULT])
        if self.NAME_FILTERS in args:
            filters = args[self.NAME_FILTERS]
            for filter in filters:
                dialog.appendFilter(filter[0], filter[1])
        if self.NAME_CURRENT_FILTER in args:
            dialog.setCurrentFilter(args[self.NAME_CURRENT_FILTER])
        if self.NAME_HELP in args:
            dialog.HelpURL = args[self.NAME_HELP]
        if self.NAME_FILTER_MANAGER in args:
            args[self.NAME_FILTER_MANAGER].set_filters(dialog)


from com.sun.star.ui.dialogs.TemplateDescription import \
    FILEOPEN_SIMPLE as TD_FILEOPEN_SIMPLE, \
    FILESAVE_SIMPLE as TD_FILESAVE_SIMPLE, \
    FILESAVE_AUTOEXTENSION_SELECTION as TD_FILESAVE_AUTOEXTENSION_SELECTION


class FileOpenDialog(FileDialogBase):
    """ Let user to choose files to open. """
    
    INITIALIZE_TEMPLATE = TD_FILEOPEN_SIMPLE


class FileSaveDialog(FileDialogBase):
    """ Let user to choose files to store. """
    
    INITIALIZE_TEMPLATE = TD_FILESAVE_SIMPLE

from com.sun.star.ui.dialogs.ExtendedFilePickerElementIds import \
    CHECKBOX_AUTOEXTENSION, CHECKBOX_SELECTION

class FileSaveAutoExtensionAndSelectionDialog(FileSaveDialog):
    
    INITIALIZE_TEMPLATE = TD_FILESAVE_AUTOEXTENSION_SELECTION
    
    def get_filter_extension(self):
        filter = self.get_filter()
        filters = self.args[self.NAME_FILTERS]
        found = None
        for f in filters:
            if f[0] == filter:
                found = f[1]
        if found:
            parts = found.split(";")
            description = parts[0]
            return description.strip("*")
        return ""
    
    def is_auto_extension_selected(self):
        return self.dialog.getValue(CHECKBOX_AUTOEXTENSION, 0)
    
    def is_selection_only_selected(self):
        return self.dialog.getValue(CHECKBOX_SELECTION, 0)
    
    def is_selection_only(self):
        return self.selection_only
    
    def _result(self):
        """ Returns selected file URLs. 
        
        When a file selected, simply an URL is returned. 
        Otherwise list of file URL is returned, all URL in 
        full length.
        """
        files = self.dialog.getFiles()
        if len(files) == 1:
            file_url = files[0]
        else:
            return None
        self.selection_only = self.is_selection_only_selected()
        if self.is_auto_extension_selected():
            ext = self.get_filter_extension()
            if ext and not file_url.endswith(ext):
                file_url += ext
        return file_url

