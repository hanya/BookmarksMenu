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
from bookmarks.dialogs import LayoutedDialog
from bookmarks.layouter import DialogLayout, GridLayout, VBox
from bookmarks import EXT_DIR
DIALOG_DIR = EXT_DIR + "dialogs/"

class LabelDialog(LayoutedDialog):
    """ Dialog to input localized label. """
    
    DIALOG_URI = DIALOG_DIR + "Label.xdl"
    
    NAME_LIST_LOCALE = "list_locale"
    NAME_EDIT_LABEL = "edit_label"
    NAME_LABEL_LOCALE = "label_locale"
    NAME_LABEL_LABEL = "label_label"
    
    def _result(self):
        list_locale = self.get(self.NAME_LIST_LOCALE)
        index = list_locale.getSelectedItemPos()
        return (
            list_locale.getModel().getItemData(index), 
            self.get_text(self.NAME_EDIT_LABEL)
        )
    
    def _init(self):
        self._init_ui()
        self.set_text(self.NAME_EDIT_LABEL, self.args.get("default", ""))
        locales = self.args.get("locales", ())
        if locales:
            self.set_items(self.NAME_LIST_LOCALE, locales)
        disable_locale = self.args.get("disable_locale", False)
        if disable_locale:
            self.set_enable(self.NAME_LIST_LOCALE, False)
            self.select_text(self.NAME_EDIT_LABEL)
        self.get(self.NAME_LIST_LOCALE).selectItemPos(0, True)
        self.layouter = self._init_layout()
        self.layouter.layout()
    
    def set_items(self, name, items):
        list_model = self.get(name).getModel()
        list_model.StringItemList = uno.Any("[]string", tuple([item[1] for item in items]))
        for i, item in enumerate(items):
            list_model.setItemData(i, item[0])
    
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
              "label_locale", 
              {"halign": "start"}
            ), 
            self.create_layout(
              self.TYPE_LIST, 
              "list_locale", 
              {}
            ), 
            self.create_layout(
              self.TYPE_LABEL, 
              "label_label", 
              {"halign": "start"}
            ), 
            self.create_layout(
              self.TYPE_EDIT, 
              "edit_label", 
              {"hexpand": True, }
            )
          )
        ), 
        self.get_buttons_layout()
        )
      )
    )
