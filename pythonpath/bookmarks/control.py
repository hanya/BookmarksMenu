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

class TreeWindow(object):
    """ Provides tree control manipulation. """
    def __init__(self, tree):
        self.tree = tree
    
    def tree_set_focus(self):
        """ Set focus to the tree. """
        self.tree.setFocus()
    
    def tree_get_data_model(self):
        """ Get data model. """
        return self.tree.getModel().getPropertyValue("DataModel")
    
    def tree_is_root_selected(self):
        """ Check is selected node is root. """
        return self.tree_get_root_node() == self.tree_get_selection()
    
    def tree_get_selection(self):
        """ Selection from tree, multiple selection is not allowed. """
        selections = self.tree.getSelection()
        if isinstance(selections, tuple):
            if len(selections) > 0:
                return selections[0]
            return None
        return selections
    
    def tree_set_selection(self, node):
        """ Select node. """
        try:
            self.tree_make_visible(node) # make it visible before to select it
            self.tree.select(node)
        except Exception, e:
            print("Error on tree_set_selection: %s" % node)
            print(e.__class__)
    
    def tree_make_visible(self, node):
        """ Make node visible. """
        self.tree.makeNodeVisible(node)
    
    def tree_is_node_expanded(self, node):
        """ Check node is expanded. """
        return self.tree.isNodeExpanded(node)
    
    def tree_expand_node(self, node):
        """ Expand node. """
        self.tree.expandNode(node)
    
    def tree_create_node(self, name, ondemand=True):
        """ Create new node. """
        return self.tree_get_data_model().create_node(name, ondemand)
    
    def tree_create_root_node(self, name, ondemand=True):
        """ Create root node. """
        return self.tree_get_data_model().create_root(name, ondemand)
    
    def tree_get_root_node(self):
        """ Returns root node. """
        return self.tree_get_data_model().get_root()
    
    def tree_set_root(self, node):
        self.tree_get_data_model().set_root(node)
    
    def tree_insert_node(self, parent, position, node):
        parent.insert_child(position, node)


class ExtendedTreeWindow(TreeWindow):
    
    # index of each node in the child container of the root
    ID_HISTORY = 0
    ID_TAGS = 1
    ID_UNSORTED = 2
    ID_BOOKMRAKS = 3
    
    def tree_show_root(self, state=False):
        self.tree.getModel().RootDisplayed = state
    
    def tree_get_bookmarks_root(self):
        return self.tree_get_root_node().get_child_at(self.ID_BOOKMRAKS)
    
    def tree_create_bookmarks_root(self, name, ondemand=True):
        return self.tree_get_data_model().create_bookmarks_root(name, ondemand)
    
    def tree_get_tags_root(self):
        return self.tree_get_root_node().get_child_at(self.ID_TAGS)
    
    def tree_create_tag_node(self, name, ondemand=False):
        return self.tree_get_data_model().create_tag_node(name, ondemand)
    
    def tree_create_tags_root(self, name, ondemand=True):
        return self.tree_get_data_model().create_tags_root(name, ondemand)
    
    def tree_create_history_root(self, name, ondemand=False):
        return self.tree_get_data_model().create_history_root(name, ondemand)
    
    def tree_create_unsorted_root(self, name, ondemand=False):
        return self.tree_get_data_model().create_unsorted_root(name, ondemand)
    
    def tree_get_unsorted_root(self):
        return self.tree_get_root_node().get_child_at(self.ID_UNSORTED)


class GridWindow(object):
    """ Provides grid control. """
    
    def __init__(self, grid):
        self.grid = grid
    
    def grid_check_interface(self):
        """ Chedk legacy interface is used or not. """
        import uno
        try:
            d = uno.getTypeByName("com.sun.star.awt.grid.XGridRowSelection")
        except:
            self._get_selected_rows = self.foo_get_selected_rows
            self._is_row_selected = self.foo_is_row_selected
            self._has_selected_rows = self.foo_has_selected_rows
    
    def _get_selected_rows(self):
        """ Returns tuple of selected rows. """
        rows = self.grid.getSelectedRows()
        if not isinstance(rows, tuple):
            return ()
        return rows
    
    def _has_selected_rows(self):
        """ Check any row is selected. """
        return self.grid.hasSelectedRows()
    
    def _is_row_selected(self, row):
        """ Check is specific row is selected. """
        return self.grid.isRowSelected(row) 
    
    def foo_get_selected_rows(self):
        """ Returns tuple of selected rows. """
        rows = self.grid.getSelection()
        if not isinstance(rows, tuple):
            return ()
        return rows
    
    def foo_has_selected_rows(self):
        """ Check any row is selected. """
        return not self.grid.isSelectionEmpty()
    
    def foo_is_row_selected(self, row):
        """ Check is specific row is selected. """
        return self.grid.isSelectedIndex(row) 
    
    
    def grid_set_focus(self):
        """ To gain focus. """
        self.grid.setFocus()
    
    def grid_get_data_model(self):
        """ Returns data model of grid. """
        return self.grid.getModel().getPropertyValue("GridDataModel")
    
    def grid_get_column_model(self):
        """ Returns column model of the grid. """
        return self.grid.getModel().getPropertyValue("ColumnModel")
    
    def grid_get_row_count(self):
        """ Returns number of row. """
        return self.grid.getModel().GridDataModel.RowCount
    
    def grid_get_selection_count(self):
        return len(self.grid_get_selection())
    
    def grid_get_selection(self):
        """ Get selection. """
        return self._get_selected_rows()
    
    def grid_get_single_selection(self):
        """ Get selection if only a row is selected. """
        rows = self.grid_get_selection()
        if len(rows) == 1:
            return rows[0]
        return None
    
    def grid_select_row(self, row):
        """ Select row. """
        self.grid.selectRow(row)
    
    def grid_unselect_row(self, row):
        """ Unselect row. """
        self.grid.deselectRow(row)
    
    def grid_unselect_all(self):
        """ Unselect all rows. """
        self.grid.deselectAllRows()
    
    def grid_select_all(self):
        """ Select all rows. """
        self.grid.selectAllRows()
    
    def grid_is_selected(self, row):
        """ Check row is selected. """
        return self._is_row_selected(row)
    
    def grid_has_selection(self):
        """ Check any row is selected. """
        return self._has_selected_rows()
    
    def grid_get_current(self):
        """ Get current row. """
        return self.grid.getCurrentRow()
    
    def grid_to_cell(self, row):
        """ Move cursor to row. """
        try:
            self.grid.goToCell(1, row)
        except:
            pass
    
    def grid_select_current(self):
        """ Select cursor row. """
        self.grid_select_row(self.grid_to_cell())
    
    def grid_unselect_current(self):
        """ Unselect cursor row. """
        self.grid_unselect_row(self.grid_to_cell())
    
    def grid_get_row_at_point(self, x, y):
        """ Find row at point. """
        return self.grid.getRowAtPoint(x, y)
    
    def grid_remove_all(self):
        """ Remove all rows. """
        self.grid_get_data_model().removeAllRows()
    
    def grid_remove_row(self, index):
        """ Remove row. """
        self.grid_get_data_model().removeRow(index)
    
    def grid_remove_rows(self, index=None, count=None, positions=None):
        """ Remove number of rows. """
        data_model = self.grid_get_data_model()
        if positions is None:
            positions = range(index, index + count)
        for position in positions[::-1]:
            data_model.removeRow(position)
    
    def grid_insert_row(self, index, data):
        """ Insert row at index. """
        self.grid_get_data_model().insertRow(index, "", data)
    
    def grid_insert_rows(self, index, data):
        """ Insert multiple rows at index. """
        self.grid_get_data_model().insertRows(index, tuple(["" for i in data]), data)
    
    def grid_set_rows(self, rows):
        """ Replace data with rows. """
        self.grid_unselect_all()
        self.grid_remove_all()
        data_model = self.grid_get_data_model()
        data_model.insertRows(0, tuple(["" for i in range(len(rows))]), rows)
        # to avoid illegal selection remained.
        if self.grid_get_row_count():
            self.grid_to_cell(0)
    
    def grid_redraw(self):
        """ Request to redraw grid. """
        self.grid.getContext().getPeer().invalidate(9)
    
    def grid_reset_size(self):
        height = self.grid.getPosSize().Height
        self.grid.setPosSize(0, 0, 0, height -1, 8)
        self.grid.setPosSize(0, 0, 0, height, 8)
    
    def grid_update_cell(self, column, row, value):
        """ Update data for specific cell. """
        self.grid_get_data_model().updateCellData(column, row, value)
    
    def grid_update_row(self, column_indexes, row, values):
        """ Update row data. """
        self.grid_get_data_model().updateRowData(column_indexes, row, values)
    
    def grid_get_row_at(self, x, y):
        """ Get row position at x, y. """
        return self.grid.getRowAtPoint(x, y)
    
    def grid_get_column_at(self, x, y):
        """ Get column position at x, y. """
        return self.grid.getColumnAtPoint(x, y)

