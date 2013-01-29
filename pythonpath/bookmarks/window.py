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
import unohelper
import time

from com.sun.star.awt import Rectangle, Point, \
    XMouseListener, XMouseMotionListener, XWindowListener
from com.sun.star.awt.grid import XGridSelectionListener
from com.sun.star.view import XSelectionChangeListener

from bookmarks.values import PosSize, MouseButton, Key, KeyModifier, \
    ListenerBase, ActionListenerBase, KeyListenerBase, \
    MouseListenerBase, TextListenerBase, FocusListenerBase


class WindowListenerBase(XWindowListener):
    def __init__(self, act):
        self.act = act
    
    def disposing(self, ev):
        self.act = None
    
    def windowResized(self, ev): pass
    def windowMoved(self, ev): pass
    def windowShown(self, ev): pass
    def windowHidden(self, ev): pass


class VerticalSeparator(MouseListenerBase, XMouseMotionListener):
    """ Vertical separator. """
    
    VERT_SEP_IMAGE = "vertsep"
    
    def __init__(self, ctx, act, vertsep):
        MouseListenerBase.__init__(self, act)
        self.enabled = True
        
        ps = vertsep.getPosSize()
        self.origin_x = ps.X
        self.original_width = ps.Width
        self.not_started = True
        self.started_x = 0
        self.moving = False
        
        from bookmarks import ICONS_DIR
        from bookmarks.tools import create_graphic
        is_high_contrast = vertsep.StyleSettings.HighContrastMode
        suffix = ".png"
        if is_high_contrast:
            suffix = "_h" + suffix
        self.graphic = create_graphic(
            ctx, ICONS_DIR + self.VERT_SEP_IMAGE + suffix)
        vertsep.getModel().Graphic = self.graphic
    
    def set_enable(self, state):
        """ Supress dragging on self. """
        self.enabled = state
    
    def mouseMoved(self, ev): pass
    
    def reset_size(self, ev):
        distance = ev.X - self.started_x
        ev.Source.setPosSize(
            self.origin_x + distance, 0, 
            self.original_width, 0, 
            PosSize.X | PosSize.WIDTH)
        self.origin_x = self.origin_x + distance
    
    def mousePressed(self, ev):
        if ev.Buttons == 1 and ev.ClickCount == 1:
            self.started_x = self.origin_x + ev.X
    
    def mouseReleased(self, ev):
        self.moving = False
        try:
            if not self.not_started:
                self.reset_size(ev)
                ev.Source.getModel().Graphic = self.graphic
                self.act.tree.setVisible(True)
                self.act.restore_column_width()
            self.not_started = True
        except:
            pass
    
    def mouseDragged(self, ev):
        if not self.enabled:
            return
        if not ev.Buttons:
            return
        if self.moving:
            return
        self.moving = True
        x = ev.X
        if self.not_started:
            self.not_started = False
            self.act.tree.setVisible(False)
            vertsep = ev.Source
            vertsep.getModel().Graphic = None
            vertsep.setPosSize(
                0, 0, 
                self.act.cont.getPosSize().Width, 0, 
                PosSize.X | PosSize.WIDTH)
            x = vertsep.getPosSize().X + ev.X
        self.act.vert_sep_moved(self.origin_x + x - self.started_x)
        self.moving = False


class MouseDraggingManager(unohelper.Base, XMouseListener, XMouseMotionListener):
    """ Manages dragging items. """
    
    def __init__(self, act, tree, grid, pointer):
        self.act = act
        self.tree = tree
        self.grid = grid
        self.pointer = pointer
        self.clear()
        if self.act.tree.StyleSettings.FieldColor > 0x888888:
            self.color = 0
        else:
            self.color = 0xffffff
        self.row_height = None
        self.MODE_TREE = act.MODE_TREE
        self.MODE_GRID = act.MODE_GRID
        self.POSITION_NONE = act.POSITION_NONE
        self.POSITION_ITEM = act.POSITION_ITEM
        self.POSITION_ABOVE = act.POSITION_ABOVE
        self.POSITION_BELOW = act.POSITION_BELOW
        
    def clear(self):
        self.propose_dragging = 0
        self.dragging = 0
        self.data_node = None
        self.node = None
        self.pos = 0
        self.row_index = -1
        self.origin = 0
        self.mode = 0
        self.dragging_time = 0
        self.scrolled_time = 0
    
    def drag_started(self):
        self.act.vertsep.set_enable(False)
    
    def drag_ended(self):
        self.act.vertsep.set_enable(True)
    
    def disposing(self, ev):
        self.act = None
    
    def redraw_grid(self):
        self.grid.getPeer().invalidate(8)
    
    def redraw_tree(self):
        self.tree.getPeer().invalidate(8)
    
    def redraw_by_mode(self, mode):
        if mode == self.MODE_TREE:
            self.redraw_tree()
        else:
            self.redraw_grid()
    
    def set_pointer(self, pointer_type):
        pointer = self.pointer
        pointer.setType(pointer_type)
        self.tree.getPeer().setPointer(pointer)
        self.grid.getPeer().setPointer(pointer)
    
    def mouseMoved(self, ev): pass
    def mouseEntered(self, ev): pass
    def mouseExited(self, ev): pass
    
    def mouseReleased(self, ev):
        # dragging is finished
        self.drag_ended()
        if not self.dragging:
            self.clear()
            return
        try:
            self.redraw_tree()
            self.redraw_grid()
            self.set_pointer(0)
            
            is_copy = (ev.Modifiers & KeyModifier.MOD1 == KeyModifier.MOD1)
            mode = self.get_mode(ev)
            
            tree = self.tree
            grid = self.grid
            
            y = ev.Y
            x = ev.X
            # ToDo ignore released on out of the control
            if mode == self.MODE_TREE and ev.Source == self.grid:
                x += tree.getPosSize().Width
            
            if mode == self.MODE_TREE:
                near = tree.getClosestNodeForLocation(x, y)
                if not near:
                    near = self.node
                if near:
                    rect = tree.getNodeRect(near)
                    pos = self.get_tree_pos(y, rect)
                    pos = self.act.controller.can_move_to(
                            near, 
                            pos, 
                            (ev.Modifiers & KeyModifier.MOD1) == KeyModifier.MOD1)
        
                else:
                    return
            else:
                row_index = grid.getRowAtPoint(0, y)
                row_height = self.get_grid_row_height(grid)
                first_row = grid.getRowAtPoint(0, row_height)
                row_in_view = row_index
                if first_row >= 0:
                    row_in_view = row_index - first_row
                pos, row_index = self.get_grid_pos(y, row_index, row_height, row_in_view)
            
            if self.origin == self.MODE_TREE:
                if pos == self.POSITION_ITEM:
                    data_node = self.data_node
                else:
                    data_node = self.act.tree_get_selection()
                if mode == self.MODE_TREE:
                    self.act.controller.move_from_tree(
                        data_node, pos, dest_node=near, is_copy=is_copy)
            else:
                data_positions = self.act.grid_get_selection()
                if mode == self.MODE_TREE:
                    self.act.controller.move_from_grid(
                        data_positions, pos, dest_node=near, is_copy=is_copy)
                    self.tree.setFocus()
                    self.grid.setFocus()
                else:
                    self.act.controller.move_from_grid(
                        data_positions, pos, dest_index=row_index, is_copy=is_copy)
        except Exception as e:
            print(e)
            traceback.print_exc()
        self.clear()
        
    
    def mousePressed(self, ev):
        # maybe dragging is started
        self.dragging_time = time.time()
        control = ev.Source
        # ToDo get vertical scrollbar width
        if ev.X > control.getPosSize().Width - 20:
            return # ignore near the scroll bar
        if ev.Y < self.get_grid_row_height(self.grid):
            return # ignore on the column header
        if not self.act.controller.can_move():
            return
        try:
            if control == self.tree:
                if self.tree.getClosestNodeForLocation(ev.X, ev.Y) is None:
                    return
                self.origin = self.MODE_TREE
                self.data_node = self.act.tree_get_selection()
            else:
                if not self.act.grid_get_selection_count() or \
                    self.act.grid_get_row_count() == 0:
                    return
                self.origin = self.MODE_GRID
            self.propose_dragging = 1
            self.drag_started()
        except Exception as e:
            print(e)
        self.act.regulator.click_on_grid()
    
    def get_mode(self, ev):
        if ev.Source == self.tree:
            mode = self.MODE_TREE
        else:
            if ev.X < 0:
                mode = self.MODE_TREE
            else:
                mode = self.MODE_GRID
        return mode
    
    def get_tree_pos(self, y, rect):
        height = rect.Height
        quoter = height / 4
        rect_y = rect.Y
        if y < (rect_y + quoter * 3):
            if (rect_y + quoter) < y:
                pos = self.POSITION_ITEM
            else:
                pos = self.POSITION_ABOVE
        else:
            pos = self.POSITION_BELOW
        return pos
    
    def get_grid_pos(self, y, row_index, row_height, row_in_view):
        quoter = row_height / 4
        if row_index < 0:
            if 0 <= self.row_index:
                row_index = self.row_index
                pos = self.pos
            else:
                row_index = 0
                pos = self.POSITION_ABOVE
            # check is in the header or empty part
            if y > row_height:
                row_index = self.grid.getModel().GridDataModel.RowCount
                pos = self.POSITION_ABOVE
            else:
                pos = self.POSITION_BELOW
        else:
            #row_y = (row_index +1) * row_height
            row_y = (row_in_view +1) * row_height
            if self.act.controller.check_item_is_container(row_index):
                if y < (row_y + quoter * 3):
                    if (row_y + quoter) < y:
                        # check item is container
                        pos = self.POSITION_ITEM
                    else:
                        pos = self.POSITION_ABOVE
                else:
                    pos = self.POSITION_BELOW
            else:
                half = row_height / 2
                if y < row_y + half:
                    pos = self.POSITION_ABOVE
                else:
                    pos = self.POSITION_BELOW
        return pos, row_index
    
    def find_sibling(self, node):
        parent = node.getParent()
        if parent:
            index = parent.getIndex(node)
            if parent.getChildCount() > index + 1:
                return parent.getChildAt(index + 1)
            else:
                return self.find_sibling(parent)
    
    def get_nearest_node(self, tree, node, below=True):
        _node = None
        if below:
            if tree.isNodeExpanded(node) and node.getChildCount():
                _node = node.getChildAt(0)
            else:
                _node = self.find_sibling(node)
        else:
            parent = node.getParent()
            if parent:
                index = parent.getIndex(node)
                if index == 0:
                    _node = parent
                else:
                    _node = parent.getChildAt(index -1)
        return _node
    
    def get_hori_scrollbar(self, tree):
        acc = tree.getAccessibleContext()
        for i in range(acc.getAccessibleChildCount()):
            child = acc.getAccessibleChild(i)
            try:
                child.getOrientation() == 0
            except:
                return child
        return None
    
    def mouseDragged(self, ev):
        if self.propose_dragging and not self.dragging:
            if self.dragging_time + 0.15 < time.time():
                self.dragging = 1
            else:
                self.propose_dragging = 0
        if not self.dragging:
            return
        
        pointer_type = 0
        if ev.Modifiers & KeyModifier.MOD1:
            pointer_type = 1
        self.set_pointer(40 + pointer_type)
        
        mode = self.get_mode(ev)
        if mode != self.mode:
            self.redraw_by_mode(self.mode)
        self.mode = mode
        try:
            if mode == self.MODE_TREE:
                self.drag_on_tree(ev)
            else:
                self.drag_on_grid(ev)
        except Exception as e:
            print(e)
            traceback.print_exc()
    
    def drag_on_tree(self, ev):
        tree = self.tree
        x = ev.X
        if ev.Source == self.grid:
            x += tree.getPosSize().Width
        y = ev.Y
        near = tree.getClosestNodeForLocation(x, y)
        if not near:
            near = self.node
            if near is None:
                return
        rect = tree.getNodeRect(near)
        pos = self.get_tree_pos(y, rect)
        pos = self.act.controller.can_move_to(
            near, 
            pos, 
            (ev.Modifiers & KeyModifier.MOD1) == KeyModifier.MOD1)
        
        if pos != self.POSITION_NONE and self.pos != pos or near != self.node:
            if self.node:
                self.erase_tree_older_drawing(tree, tree.getNodeRect(self.node))
                hori_scroll = self.get_hori_scrollbar(tree)
                # ToDo repeat scrolling
                if near and y < 20 or \
                    y > tree.getOutputSize().Height - 25 or \
                    (hori_scroll and \
                        y > tree.getOutputSize().Height - hori_scroll.getPosSize().Height):
                    if (y < 20 and self.scrolled_time + 0.03 < time.time()) or \
                        self.scrolled_time + 0.2 < time.time():
                        _node = self.get_nearest_node(tree, near, not y < 20)
                        if _node:
                            try:
                                tree.makeNodeVisible(_node)
                                self.scrolled_time = time.time()
                            except:
                                pass
            if pos != self.POSITION_NONE:
                self.draw_tree_dest(
                    tree, pos, rect.X, rect.Y, rect.Width, rect.Height)
        self.node = near
        self.pos = pos
    
    def get_nearest_row(self, grid, row_index, below=True):
        if 0 < row_index < grid.getModel().GridDataModel.RowCount -1:
            if below:
                row_index += 1
            else:
                row_index -= 1
        return row_index
    
    def drag_on_grid(self, ev):
        if self.origin == self.MODE_TREE:
            return # do not move items from tree to grid.
        grid = self.grid
        y = ev.Y
        _row_index = grid.getRowAtPoint(0, y)
        
        row_height = self.get_grid_row_height(grid)
        first_row = grid.getRowAtPoint(0, row_height)
        row_in_view = _row_index
        if first_row >= 0:
            row_in_view = _row_index - first_row
        pos, row_index = self.get_grid_pos(y, _row_index, row_height, row_in_view)
        if self.pos != pos or self.row_index != row_index:
            if first_row > 0:
                row_index -= first_row
            self.erase_grid_older_drawing(
                grid, self.pos, self.row_index, row_height)
            
            if _row_index >= 0 and y < row_height *2 or \
                (y > grid.getOutputSize().Height - row_height):
                _row = self.get_nearest_row(grid, _row_index, not y < row_height *2)
                if _row >= 0 and self.scrolled_time + 0.05 < time.time():
                    self.act.grid_to_cell(_row)
                    self.scrolled_time = time.time()
            
            self.draw_grid_dest(grid, pos, row_index, row_height)
            self.row_index = row_index
            self.pos = pos
    
    def get_grid_row_height(self, grid):
        if self.row_height is None:
            def go_to_next_row(start_y):
                ny = start_y
                _row = grid.getRowAtPoint(0, ny)
                
                for i in range(30):
                    row = grid.getRowAtPoint(0, ny)
                    if row != _row:
                        return ny
                    ny += 1
                return None
            
            y = go_to_next_row(0)
            if y is None:
                return 0
            y2 = go_to_next_row(y)
            if y2 is None:
                return 0
            self.row_height = y2 - y
            
        return self.row_height
    
    def erase_grid_older_drawing(self, grid, pos, row, row_height):
        grid.getPeer().invalidateRect(
            Rectangle(0, row_height * (row + 1) -1, 60, row_height + 2), 8)
    
    def draw_grid_dest(self, grid, pos, row, row_height):
        g = grid.getGraphics()
        if not g:
            g = grid.getPeer().createGraphics()
            grid.setGraphics(g)
        
        y = row_height * (row + 1)
        g.push()
        g.setLineColor(self.color)
        if pos == self.POSITION_ITEM:
            g.setFillColor(-1)
            g.drawRect(1, y, 21, row_height)
        else:
            if pos == self.POSITION_BELOW:
                y += row_height -1
            else:
                y -= 1
            g.drawLine(10, y, 50, y)
        g.pop()
    
    
    def erase_tree_older_drawing(self, tree, rect):
        tree.getPeer().invalidateRect(
            Rectangle(rect.X-2, rect.Y-1, rect.Width + 4, rect.Height+2), 8)
    
    def draw_tree_dest(self, tree, pos, x, y, width, height):
        g = tree.getGraphics()
        if not g:
            g = tree.getPeer().createGraphics()
            tree.setGraphics(g)
        
        g.push()
        g.setLineColor(self.color)
        if pos == self.POSITION_ITEM:
            g.setFillColor(-1)
            g.drawRect(x -2, y -1, width + 4, height +2)
        else:
            if pos == self.POSITION_BELOW:
                y = y + height
            elif pos == self.POSITION_ABOVE:
                y = y - 1
            g.drawLine(x, y, x + 50, y)
        g.pop()


class Regulator(object):
    """ Regulate funny focus and selection changes. """
    
    def __init__(self, window):
        self.window = window
        self.tree_change_enabled = True
        self.ids = (
            window.ID_DATA_EDIT_NAME, 
            window.ID_DATA_EDIT_VALUE1, 
            window.ID_DATA_EDIT_VALUE2, 
            window.ID_DATA_EDIT_TAGS, 
            window.ID_DATA_EDIT_DESCRIPTION
        )
        self.reset()
    
    def enable_tree_change(self, state):
        self.tree_change_enabled = state
    
    def dispose(self):
        self.window = None
    
    def reset(self):
        self.regulated = False
        self._old_mode = 0
        self._current_mode = 0
        self._grid_selection_changed = False
        self.old_tree_selection = None
        self.current_tree_selection = None
        self.old_grid_selection = None
        self.current_grid_selection = None
        self._edit_focus_lost = False
        self._old_data = {}
        self._last_focus_lost_edit_control = None
        self._field_modified = False
        self._inhibit_grid_selection_change = False
    
    def get_mode(self):
        return self._current_mode
    
    def text_modified(self):
        self._field_modified = True
    
    def get_grid_selection(self):
        if self.regulated:
            return self.old_grid_selection
        else:
            return self.current_grid_selection
    
    def get_data_type(self, control):
        """ Get data type from edit control. """
        window = self.window
        dcc = window.data_cont.getControl
        for id in self.ids:
            if control == dcc(id):
                return id
        return ""
    
    def collect_data(self):
        """ Keep data before changes of grid selection. """
        self._old_data.update(
            [(id, self.window.get_data_value(id)) for id in self.ids])
    
    def get_data_value(self, data_type):
        window = self.window
        if self.regulated:
            return self._old_data[data_type]
        else:
            return window.get_data_value(data_type)
    
    def update_mode(self, mode):
        try:
            self._old_mode = self._current_mode
            self._current_mode = mode
            if self._edit_focus_lost and self._field_modified:
                # edit > grid or somewhere
                if self._old_mode == 1 and self._current_mode == 1:
                    # focus: tree 1 > edit > tree 1
                    # update container data selected on tree, 
                    # selection of tree is not yet changed
                    self.update_data(self._current_mode)
                elif self._old_mode == 1 and self._current_mode == 2:
                    # focus: tree 1 > edit > grid 2
                    # update have to be with old_mode
                    if self._grid_selection_changed:
                        self.regulated = True
                    self.update_data(self._old_mode)
                    self.regulated = False
                elif self._old_mode == 2 and self._current_mode == 1:
                    # focus: tree 1 > grid 2 > edit > tree 1
                    # update data selected on grid, 
                    # selection will be changed by change of tree selection 
                    # after this update
                    self.regulated = False
                    self.update_data(self._old_mode)
                elif self._old_mode == 2 and self._current_mode == 2:
                    if self._grid_selection_changed:
                        # focus: grid 2 > edit > grid 2 (selection changed)
                        # update data for older selection
                        self.regulated = True
                        self.update_data(self._current_mode)
                        self.regulated = False
                    else:
                        # focus: grid 2 > edit > grid 2 (selection is the same)
                        # update data for current selection
                        self.regulated = False
                        self.update_data(self._current_mode)
                self._edit_focus_lost = False
            elif mode == self.window.MODE_TREE:
                self.window.controller.change_display_item(self.window.MODE_TREE)
            elif self._old_mode == 1 and self._current_mode == 2:
                # tree to grid
                if not self._grid_selection_changed:
                    self.window.controller.change_display_item(self.window.MODE_GRID)
        except Exception as e:
            print(e)
            traceback.print_exc()
        self._grid_selection_changed = False
        self._field_modified = False
    
    def update_data(self, mode):
        self.window.controller.data_update_request(
            mode, self.get_data_type(self._last_focus_lost_edit_control))
    
    def update_tree_selection(self):
        self.old_tree_selection = self.current_tree_selection
        self.current_tree_selection = self.window.tree_get_selection()
    
    def tree_selection_changed(self):
        if self.tree_change_enabled and self.window.tree_get_selection():
            self.window.controller.change_display_container()
    
    def inhibit_grid_selection_change(self, state=True):
        self._inhibit_grid_selection_change = state
    
    def grid_selection_changed(self):
        self._grid_selection_changed = True
        self.old_grid_selection = self.current_grid_selection
        self.current_grid_selection = self.window.grid_get_selection()
        try:
            self.collect_data()
            if not self._inhibit_grid_selection_change:
                self.window.controller.change_display_item(self.window.MODE_GRID)
            self._inhibit_grid_selection_change = False
        except Exception as e:
            print(e)
            traceback.print_exc()
    
    def edit_focus_lost(self, control):
        self._edit_focus_lost = True
        self._last_focus_lost_edit_control = control
    
    def edit_focus_gained(self):
        if self._edit_focus_lost and self._last_focus_lost_edit_control:
            # focus moved to other edit control
            # update data on current grid selection
            try:
                self.update_data(self.window.get_mode())
            except Exception as e:
                print(e)
            self._edit_focus_lost = False
        self._last_focus_lost_edit_control = None
    
    def click_on_grid(self):
        """ When mouse click on the grid. """
        # To trigger selection change event on MULTI selection mode
        # See GridSelectionListener class.
        # When single row is clicked and selection is changed, 
        # current_grid_selection has been updated and length is 1.
        if self.current_grid_selection and \
            len(self.current_grid_selection) > 1:
            new_selection = self.window.grid_get_selection()
            if new_selection and len(new_selection) == 1:
                self.grid_selection_changed()


from bookmarks.control import ExtendedTreeWindow, GridWindow
from bookmarks.tree import BookmarksMenuTreeDataModel


class BookmarksWindow(ExtendedTreeWindow, GridWindow):
    """ Edit window for bookmarks menu. """
    
    WINDOWS = {}
    
    def get(command):
        return BookmarksWindow.WINDOWS.get(command, None)
    
    def create(ctx, frame, command, controller, res, settings):
        klass = BookmarksWindow
        window = klass(ctx, frame, command, controller, res, settings)
        klass.WINDOWS[command] = window
        return window
    
    def remove(command):
        try:
            BookmarksWindow.WINDOWS.pop(command)
        except:
            pass
    
    get = staticmethod(get)
    create = staticmethod(create)
    remove = staticmethod(remove)
    
    URI_EDIT = "Edit.xdl"
    URI_EDIT_DATA = "EditData.xdl"
    URI_EDIT_GRID = "EditGrid.xdl"
    
    NAME_GRID_CONT = "grid_cont"
    NAME_DATA_CONT = "data_cont"
    
    NAME_GRID = "grid"
    NAME_TREE = "tree"
    
    ID_VERT_SEP = "vertsep"
    VERT_SEP_WIDTH = 6
    
    ID_DATA_LABEL_NAME = "label_name"
    ID_DATA_LABEL_VALUE1 = "label_value1"
    ID_DATA_LABEL_VALUE2 = "label_value2"
    ID_DATA_LABEL_TAGS = "label_tags"
    ID_DATA_LABEL_DESCRIPTION = "label_description"
    
    ID_DATA_EDIT_NAME = "edit_name"
    ID_DATA_EDIT_VALUE1 = "edit_value1"
    ID_DATA_EDIT_VALUE2 = "edit_value2"
    ID_DATA_EDIT_TAGS = "edit_tags"
    ID_DATA_EDIT_DESCRIPTION = "edit_description"
    
    ID_DATA_BTN_VALUE1 = "btn_value1"
    ID_DATA_BTN_VALUE2 = "btn_value2"
    #ID_DATA_BTN_TAGS = "btn_tags"
    
    EDIT_HEIGHT = 26
    ROW_SPACING = 4
    COLUMN_SPACING = 5
    DATA_MARGIN = 5
    
    DATA_HEIGHT = EDIT_HEIGHT * 6 + ROW_SPACING * 3
    
    MODE_NONE = 0
    MODE_TREE = 1
    MODE_GRID = 2
    
    POSITION_NONE = 0
    POSITION_ITEM = 1 # move item into it
    POSITION_ABOVE = 2
    POSITION_BELOW = 3
    
    DATA_NAME = 1
    DATA_VALUE1 = 2
    DATA_VALUE2 = 4
    DATA_DESCRIPTION = 8
    DATA_TAG = 16
    
    TYPE_NONE = 0
    TYPE_ITEM = 1
    TYPE_FOLDER = 2
    TYPE_ROOT = 3
    TYPE_TAGS = 4
    
    LABEL_TYPE_VALUE_1 = 1
    LABEL_TYPE_VALUE_2 = 2
    
    class WindowListener(unohelper.Base, WindowListenerBase):
        """ Manages resizing event of the window. """
        
        def __init__(self, act):
            WindowListenerBase.__init__(self, act)
            self.SIZE = PosSize.SIZE
            self.POS_WIDTH = PosSize.POS | PosSize.WIDTH
            self.X_SIZE = PosSize.X | PosSize.SIZE
            self.HEIGHT = PosSize.HEIGHT
        
        def windowResized(self, ev):
            klass = self.act.__class__
            cont = ev.Source
            cg = cont.getControl
            ps = cont.getOutputSize()
            
            tree = self.act.tree
            tree_width = tree.getPosSize().Width
            right_portion_x = tree_width + klass.VERT_SEP_WIDTH
            
            content_height = ps.Height
            content_width = ps.Width - tree_width - klass.VERT_SEP_WIDTH
            
            tree.setPosSize(0, 0, 0, content_height, self.HEIGHT)
            cg(klass.ID_VERT_SEP).setPosSize(
                0, 0, 0, content_height, self.HEIGHT)
            
            grid_cont = cg(klass.NAME_GRID_CONT)
            grid_height = content_height - klass.DATA_HEIGHT
            grid_cont.setPosSize(
                right_portion_x, 0, content_width, grid_height, self.X_SIZE)
            grid_cont.getByIdentifier(0).setPosSize(
                0, 0, content_width, grid_height, self.SIZE)
            
            self.act.data_cont.setPosSize(
                right_portion_x, grid_height, 
                content_width, 0, self.POS_WIDTH)
            
            self.act.data_layout.layout()
    
    def vert_sep_moved(self, width_left):
        self.tree.setPosSize(0, 0, width_left, 0, PosSize.WIDTH)
        right_x = width_left + self.VERT_SEP_WIDTH
        right_width = self.cont.getPosSize().Width - right_x
        self.grid_cont.setPosSize(
            right_x, 0, right_width, 0, PosSize.X | PosSize.WIDTH)
        self.grid.setPosSize(0, 0, right_width, 0, PosSize.WIDTH)
        self.data_cont.setPosSize(
            right_x, 0, right_width, 0, PosSize.X | PosSize.WIDTH)
        self.data_layout.layout()
    
    class ButtonListener(ActionListenerBase):
        def actionPerformed(self, ev):
            cmd = ev.ActionCommand
            if cmd == "value1":
                self.act.controller.get_value1()
            elif cmd == "value2":
                self.act.controller.get_value2()
            #elif cmd == "tags":
            #    self.act.switch_tag_list()
    
    class FocusModeListener(FocusListenerBase):
        def __init__(self, act, mode):
            FocusListenerBase.__init__(self, act)
            self.mode = mode
        def focusGained(self, ev):
            self.act.mode_changed(self.mode)
    
    class TextListener(TextListenerBase):
        def textChanged(self, ev):
            self.act.regulator.text_modified()
    
    class GridMouseListener(MouseListenerBase):
        """ Mouse listener for grid. """
        def mousePressed(self, ev):
            if ev.X > (ev.Source.getPosSize().Width - 20) or \
                ev.Y < 20:
                return
            buttons = ev.Buttons
            mod = ev.Modifiers
            if mod == 0 and buttons == MouseButton.RIGHT:
                self.act.select_row_at_point(ev.X, ev.Y)
                self.act.grid_set_focus()
                self.act.show_popup_menu(
                    self.act.__class__.MODE_GRID, ev.X, ev.Y)
            elif mod == 0 and buttons == MouseButton.LEFT and \
                ev.ClickCount == 2:
                self.act.action_executed("Open")
    
    class TreeMouseListener(MouseListenerBase):
        """ Mouse listener for tree. """
        def mousePressed(self, ev):
            if ev.Modifiers == 0 and ev.Buttons == MouseButton.RIGHT:
                self.act.show_popup_menu(
                    self.act.__class__.MODE_TREE, ev.X, ev.Y)
    
    class GridSelectionListener(ListenerBase, XGridSelectionListener):
        def selectionChanged(self, ev):
            # This method is not triggered when the multiple selection is 
            # reduced to the one of the selection.
            self.act.regulator.grid_selection_changed()
    
    class TreeSelectionListener(ListenerBase, XSelectionChangeListener):
        def selectionChanged(self, ev):
            self.act.regulator.tree_selection_changed()
    
    class GridKeyListener(KeyListenerBase):
        def __init__(self, act):
            KeyListenerBase.__init__(self, act)
            self.keys = (Key.UP, Key.DOWN, Key.HOME, Key.END, Key.SPACE)
        
        def keyPressed(self, ev):
            code = ev.KeyCode
            mod = ev.Modifiers
            if code in self.keys:
                self.act.grid_key_pressed(
                    code, 
                    mod & KeyModifier.MOD1, 
                    mod & KeyModifier.SHIFT
                )
            elif code == Key.TAB:
                if mod & KeyModifier.SHIFT:
                    self.act.tree.setFocus()
                else:
                    self.act.data_cont.\
                        getControl(self.act.ID_DATA_EDIT_NAME).setFocus()
            else:
                self.act.key_pressed(ev)
    
    def grid_key_pressed(self, code, ctrl, shift):
        """ Grid arrow key control. """
        def unselect_all_without_broadcasting():
            self.regulator.inhibit_grid_selection_change()
            self.grid_unselect_all()
            self.regulator.inhibit_grid_selection_change(False)
        
        if code == Key.UP:
            index = self.grid_get_current()
            if shift:
                pass
            elif ctrl:
                # cursor not moved yet
                if 0 <= index -1 < self.grid_get_row_count():
                    self.grid_to_cell(index -1)
            else:
                selected = self.grid_get_selection()
                if len(selected) == 1 and index in selected:
                    return
                # cursor is already moved
                unselect_all_without_broadcasting()
                self.grid_select_row(index)
            
        elif code == Key.DOWN:
            index = self.grid_get_current()
            if shift:
                pass
            elif ctrl:
                if 0 <= index +1 < self.grid_get_row_count():
                    self.grid_to_cell(index +1)
            else:
                selected = self.grid_get_selection()
                if len(selected) == 1 and index in selected:
                    return
                unselect_all_without_broadcasting()
                self.grid_select_row(index)
        
        elif code == Key.HOME:
            if shift:
                pass
            elif ctrl:
                self.grid_to_cell(0)
            else:
                selected = self.grid_get_selection()
                if len(selected) == 1 and 0 in selected:
                    return
                unselect_all_without_broadcasting()
                if self.grid_get_row_count() > 0:
                    self.grid_to_cell(0)
                    self.grid_select_row(0)
        
        elif code == Key.END:
            index = self.grid_get_row_count() -1
            if shift:
                pass
            elif ctrl:
                self.grid_to_cell(index)
            else:
                selected = self.grid_get_selection()
                if len(selected) == 1 and index in selected:
                    return
                unselect_all_without_broadcasting()
                if index >= 0:
                    self.grid_to_cell(index)
                    self.grid_select_row(index)
        
        elif code == Key.SPACE:
            if not ctrl:
                index = self.grid_get_current()
                if index >= 0:
                    selected = self.grid_get_selection()
                    if index in selected:
                        self.grid_unselect_row(index)
                    else:
                        self.grid_select_row(index)
    
    def select_row_at_point(self, x, y):
        """ Select row specified by x, y. """
        index = self.grid_get_row_at_point(x, y)
        if 0 <= index:
            if not self.grid_is_selected(index):
                self.grid_unselect_all()
                self.grid_select_row(index)
                self.grid_to_cell(index)
    
    class TreeKeyListener(KeyListenerBase):
        def __init__(self, act):
            KeyListenerBase.__init__(self, act)
        
        def keyPressed(self, ev):
            if ev.KeyCode == Key.TAB:
                if ev.Modifiers & KeyModifier.SHIFT:
                    try:
                        description = self.act.data_layout.get_element(
                            self.act.ID_DATA_EDIT_DESCRIPTION)
                        if description.is_visible():
                            description.set_focus()
                    except Exception as e:
                        print(e)
                else:
                    self.act.grid.setFocus()
            else:
                self.act.key_pressed(ev)
    
    class EditFocusListener(FocusListenerBase):
        def focusLost(self, ev):
            self.act.regulator.edit_focus_lost(ev.Source)
        
        def focusGained(self, ev):
            self.act.regulator.edit_focus_gained()
    
    class EditKeyListener(KeyListenerBase):
        def keyPressed(self, ev):
            if ev.KeyCode == Key.TAB:
                if ev.Modifiers & KeyModifier.SHIFT:
                    pass
                else:
                    self.act.tree.setFocus()
                
    
    def key_pressed(self, ev):
        """ Get command bound to key and execute it. """
        command = None
        try:
            command = self.local_keys.getCommandByKeyEvent(ev)
        except:
            pass
        if command is None:
            try:
                command = self.global_keys.getCommandByKeyEvent(ev)
            except:
                pass
        if command:
            self.controller.do_action_by_name(command)
    
    def __init__(self, ctx, frame, command, controller, res, settings={}):
        self.ctx = ctx
        self.command = command
        self.regulator = Regulator(self)
        self.controller = controller
        self.res = res
        
        self.mode = 0
        self.popup_menu = None
        self.context_menu = None
        
        self.frame = frame
        self.window = None
        self.cont = None
        self.tree = None
        self.grid = None
        self.grid_cont = None
        self.data_cont = None
        self.data_layout = None
        self.menu_bar = None
        self.data_state = 0
        
        from bookmarks import DOCUMENT_IMPLE_NAME
        from com.sun.star.beans import PropertyValue
        self.global_keys = self.create_service(
            "com.sun.star.ui.GlobalAcceleratorConfiguration")
        self.local_keys = self.create_service(
            "com.sun.star.ui.ModuleAcceleratorConfiguration", 
            (PropertyValue("ModuleIdentifier", -1, DOCUMENT_IMPLE_NAME, 0),))
        
        self._create_window(controller, settings)
        self.grid_check_interface()
        
        import bookmarks.tools
        self.use_point = bookmarks.tools.check_method_parameter(
            ctx, "com.sun.star.awt.XPopupMenu", "execute", 1, "com.sun.star.awt.Point")
    
    def _(self, name):
        return self.res.get(name, name)
    
    def lock(self):
        pass
    
    def unlock(self):
        pass
    
    def create_service(self, name, args=None):
        if args is None:
            return self.ctx.getServiceManager().createInstanceWithContext(
                    name, self.ctx)
        else:
            return self.ctx.getServiceManager().createInstanceWithArgumentsAndContext(
                    name, args, self.ctx)
    
    def get_data_text(self, name):
        return self.data_cont.getControl(name).getModel().Text
    
    def get_data_value(self, data_type):
        return self.get_data_text(data_type)
    
    def set_data_label(self, name, text):
        label = self.data_cont.getControl(name).getModel()
        state = label.Label != text
        if state:
            label.Label = text
        return state
    
    def update_data_state(self, type, label_value1="", label_value2="", state_btn_value2=False):
        """ Change visibility of the data fields. """
        if type == self.TYPE_NONE:
            self.data_layout.set_visible(False)
            self.data_state = 0
        elif type == self.TYPE_TAGS:
            state = self.DATA_TAG
            self.data_cont.getControl(
                self.ID_DATA_EDIT_NAME).getModel().ReadOnly = False
            if self.data_state != state:
                self.data_state = state
                vis = self.data_layout.elements.set_row_visible
                vis(0, False)
                vis(1, False)
                vis(2, False)
                vis(3, True)
                vis(4, False)
                self.data_layout.layout()
        else:
            state_value1 = type == self.TYPE_ITEM and label_value1 != ""
            state_description = type != self.TYPE_ROOT
            state_value2 = label_value2 != ""
            state_tags = type == self.TYPE_ITEM
            
            state = self.DATA_NAME
            if state_value1:
                state |= self.DATA_VALUE1
            if state_value2:
                state |= self.DATA_VALUE2
            if state_tags:
                state |= self.DATA_TAG
            if state_description:
                state |= self.DATA_DESCRIPTION
            update = (self.data_state != state)
            self.data_cont.getControl(
                self.ID_DATA_EDIT_NAME).getModel().ReadOnly = not state_description
            update = self.set_data_label(self.ID_DATA_LABEL_VALUE1, label_value1) or update
            update = self.set_data_label(self.ID_DATA_LABEL_VALUE2, label_value2) or update
            state_description = type != self.TYPE_ROOT
            self.data_cont.getControl(
                self.ID_DATA_BTN_VALUE2).setEnable(state_btn_value2)
            if update:
                self.data_state = state
                self.data_layout.set_visible(True)
                layout = self.data_layout.elements
                layout.set_row_visible(0, True)
                layout.set_row_visible(1, state_value1)
                layout.set_row_visible(2, state_value2)
                layout.set_row_visible(3, state_tags)
                layout.set_row_visible(4, state_description)
                self.data_layout.layout()
    
    def update_data(self, name="", description="", value1="", value2="", tag=""):
        """ Set data. """
        dc = self.data_cont.getControl
        dc(self.ID_DATA_EDIT_NAME).getModel().Text = name
        dc(self.ID_DATA_EDIT_DESCRIPTION).getModel().Text = description
        dc(self.ID_DATA_EDIT_VALUE1).getModel().Text = value1
        dc(self.ID_DATA_EDIT_VALUE2).getModel().Text = value2
        dc(self.ID_DATA_EDIT_TAGS).getModel().Text = tag
    
    def closed(self):
        try:
            self.__class__.remove(self.command)
            self.ctx = None
            self.menubar = None
            self.window.setMenuBar(None)
            self.window = None
            self.controller = None
            self.tree = None
            self.grid = None
            self.regulator.dispose()
            self.regulator = None
        except Exception as e:
            print(e)
            print("#closed error.")
    
    def move_to_front(self):
        self.window.setFocus()
    
    def mode_changed(self, mode):
        """ Mode is changed by focusing to tree or grid. """
        self.regulator.update_mode(mode)
        self.mode = mode
        if mode == self.MODE_GRID:
            if self.grid_get_current() < 0 and self.grid_get_row_count():
                self.grid_to_cell(0)
        self.controller.mode_changed()
    
    def get_mode(self):
        """ Get current mode. """
        return self.mode
    
    def action_executed(self, command):
        """ Request to action by command. """
        try:
            self.controller.do_action_by_name(command)
        except Exception as e:
            print(e)
            traceback.print_exc()
    
    def message(self, message, title, error=False):
        """ Shows message. """
        from bookmarks.tools import show_message
        box_type = "messbox"
        if error:
            box_type = "warningbox"
        show_message(
                self.ctx, 
                self.frame, 
                self.res.get(message, message), 
                self.res.get(title, title), 
                box_type)
    
    def query(self, message, title, buttons=4 | 0x40000, labels=None):
        from bookmarks.tools import show_message
        return show_message(
                self.ctx, 
                self.frame, 
                self.res.get(message, message), 
                self.res.get(title, title), 
                "querybox", 
                buttons, 
                labels)
    
    def show_popup_menu(self, type, x=0, y=0):
        """ Request to show popup menu. """
        menu = self.context_menu
        if not menu:
            menu = self.create_service("com.sun.star.awt.PopupMenu")
            menu.hideDisabledEntries(True)
            self.controller.fill_menu(type, menu)
            self.context_menu = menu
        
        if self.use_point:
            pos = Point(x, y)
        else:
            pos = Rectangle(x, y, 0, 0)
        if type == self.MODE_GRID:
            parent = self.grid.getPeer()
        elif type == self.MODE_TREE:
            parent = self.tree.getPeer()
        self.controller.update_menu(menu, type)
        n = menu.execute(parent, pos, 0)
        if 0 < n:
            try:
                self.action_executed(menu.getCommand(n))
            except Exception as e:
                print(e)
    
    def show_popup_controller_menu(self, command, imple_name, _controller=None):
        """ Instantiate popup menu controller and show its menu. """
        from com.sun.star.beans import PropertyValue
        args = (
                PropertyValue("ModuleName", -1, "", 1), 
                PropertyValue("Frame", -1, self.frame, 1), 
                PropertyValue("CommandURL", -1, command, 1), 
        )
        menu = self.create_service("com.sun.star.awt.PopupMenu")
        try:
            controller = self.create_service(imple_name, args)
            if _controller:
                controller.set_controller(_controller)
            controller.setPopupMenu(menu)
            # ToDo where to show
            if self.use_point:
                pos = Point()
            else:
                pos = Rectangle()
            menu.execute(self.grid.getPeer(), pos, 0)
        except Exception as e:
            print(e)
    
    def get_column_width(self):
        """ Returns each column width. """
        cm = self.grid_get_column_model()
        d = {}
        for i in range(1, cm.getColumnCount()):
            c = cm.getColumn(i)
            d[c.Identifier] = c.ColumnWidth
        return d
    
    def restore_column_width(self):
        """ Resize columns equally. """
        column_model = self.grid.getModel().ColumnModel
        num_columns = column_model.getColumnCount()
        width = sum([column_model.getColumn(i).ColumnWidth 
                        for i in range(1, num_columns)]) / (num_columns -1)
        for i in range(1, num_columns):
            column_model.getColumn(i).ColumnWidth = width
    
    def visible_column(self, show_value, show_description, show_tag):
        """ Make columns visible. """
        column_model = self.grid.getModel().ColumnModel
        num_columns = column_model.getColumnCount()
        required = 2
        if show_value:
            required += 1
        if show_description:
            required += 1
        if show_tag:
            required += 1
        
        n = required - num_columns
        if n > 0:
            for i in range(n):
                column = column_model.createColumn()
                column_model.addColumn(column)
            width = sum([column_model.getColumn(i).ColumnWidth 
                        for i in range(1, required)]) / (required -1)
            for i in range(1, required)[::-1]:
                column_model.getColumn(i).ColumnWidth = width
        elif n < 0:
            for i in range(-n):
                column_model.removeColumn(column_model.getColumnCount()-1)
        n = 2
        if show_tag:
            c = column_model.getColumn(n)
            c.Title = self._("Tags")
            c.Identifier = "Tags"
            n += 1
        if show_value:
            c = column_model.getColumn(n)
            c.Title = self._("Value")
            c.Identifier = "Value"
            n += 1
        if show_description:
            c = column_model.getColumn(n)
            c.Title = self._("Description")
            c.Identifier = "Description"
    
    def prepare_ui_config(self):
        from bookmarks import EXT_DIR
        from bookmarks.tools import get_user_config
        sfa = self.create_service("com.sun.star.ucb.SimpleFileAccess")
        dest_dir = get_user_config(self.ctx) + "/soffice.cfg/modules/bookmarks"
        if not sfa.exists(dest_dir):
            source_dir = EXT_DIR + "bookmarks"
            sfa.copy(source_dir, dest_dir)
    
    def show_window_contents(self):
        """ Make the window visible. """
        self.grid_cont.setVisible(True)
        self.data_cont.setVisible(True)
        self.cont.setVisible(True)
        self.window.setVisible(True)
    
    def _create_window(self, controller, settings):
        _ = self._
        def create(name):
            return self.ctx.getServiceManager().\
                createInstanceWithContext(name, self.ctx)
        
        from bookmarks import EXT_DIR
        DIALOG_DIR = EXT_DIR + "dialogs/"
        
        frame = self.frame
        container_window = frame.getContainerWindow()
        
        ccwp = create("com.sun.star.awt.ContainerWindowProvider").createContainerWindow
        cont = ccwp(DIALOG_DIR + self.URI_EDIT, "", container_window, None)
        grid_cont = ccwp(DIALOG_DIR + self.URI_EDIT_GRID, "", cont.getPeer(), None)
        data_cont = ccwp(DIALOG_DIR + self.URI_EDIT_DATA, "", cont.getPeer(), None)
        cont.addControl(self.NAME_GRID_CONT, grid_cont)
        cont.addControl(self.NAME_DATA_CONT, data_cont)
        
        data_cont.setPosSize(0, 0, 0, self.DATA_HEIGHT, PosSize.HEIGHT)
        tree = cont.getControl(self.NAME_TREE)
        tree.setPosSize(0, 0, 0, 0, PosSize.POS)
        grid_cont.setPosSize(0, 0, 0, 0, PosSize.Y)
        
        grid_cont_model = grid_cont.getModel()
        grid_model = grid_cont_model.createInstance(
                            "com.sun.star.awt.grid.UnoControlGridModel")
        grid_model.setPropertyValues(
            ("Border", "HScroll", "SelectionModel", 
                "ShowColumnHeader", "ShowRowHeader", "VerticalAlign", "VScroll"), 
            (0, False, 2, True, False, 1, True))
        grid_cont_model.insertByName(self.NAME_GRID, grid_model)
        grid = grid_cont.getControl(self.NAME_GRID)
        
        import bookmarks.tools
        if bookmarks.tools.check_interface(
            self.ctx, 
            "com.sun.star.awt.grid.XMutableGridDataModel", 
            ("insertRow",)):
            grid_data_model = create("com.sun.star.awt.grid.DefaultGridDataModel")
        else:
            import bookmarks.grid
            grid_data_model = bookmarks.grid.CustomGridDataModel(4)
        
        grid_model.GridDataModel = grid_data_model
        column_model = grid_model.ColumnModel
        if not column_model:
            column_model = create("com.sun.star.awt.grid.DefaultGridColumnModel")
        columns_labels = ("Name", "Tags", "Value", "Description")
        columns = settings.get("columns")
        columns.insert(0, ("", True))
        for label, state in columns:
            if state:
                column = column_model.createColumn()
                column.Title = _(label)
                column.Identifier = label
                column_model.addColumn(column)
        column = column_model.getColumn(0)
        column.ColumnWidth = 10
        column.Resizeable = False
        column.HorizontalAlign = 1
        column.Identifier = "Icon"
        grid_model.ColumnModel = column_model
        
        column_width = settings.get("column_width", None)
        if column_width:
            try:
                for i, width in enumerate(column_width):
                    if width > 0:
                        column_model.getColumn(i+1).ColumnWidth = width
            except:
                pass
        
        self.tree = tree
        tree_data_model = BookmarksMenuTreeDataModel()
        tree.getModel().DataModel = tree_data_model
        tree_model = tree.getModel()
        tree_root_node = self.tree_create_root_node("ROOT", True)
        self.tree_set_root(tree_root_node)
        tree_width = settings.get("tree_width", 185)
        tree.setPosSize(0, 0, tree_width, 0, PosSize.WIDTH)
        
        vertsep = cont.getControl(self.ID_VERT_SEP)
        vertsep.setPosSize(tree_width, 0, self.VERT_SEP_WIDTH, 0, PosSize.X | PosSize.WIDTH)
        listener = VerticalSeparator(self.ctx, self, vertsep)
        self.vertsep = listener
        vertsep.addMouseListener(listener)
        vertsep.addMouseMotionListener(listener)
        pointer = create("com.sun.star.awt.Pointer")
        pointer.setType(25) # HSIZEBAR
        vertsep.getPeer().setPointer(pointer)
        
        self.window = container_window
        self.grid_cont = grid_cont
        self.grid = grid
        self.data_cont = data_cont
        self.cont = cont
        cont.addWindowListener(self.WindowListener(self))
        self.data_layout = self._init_layout(data_cont)
        
        self.prepare_ui_config()
        RES_MENUBAR = "private:resource/menubar/menubar"
        menubar = create("com.sun.star.awt.MenuBar")
        container_window.setMenuBar(menubar)
        frame.setComponent(cont, self.controller)
        self.controller.attachFrame(frame)
        layout_manager = frame.LayoutManager
        layout_manager.createElement(RES_MENUBAR)
        self.menubar = menubar
        
        grid.addMouseListener(self.GridMouseListener(self))
        grid.addFocusListener(self.FocusModeListener(self, self.MODE_GRID))
        grid.addKeyListener(self.GridKeyListener(self))
        grid.addSelectionListener(self.GridSelectionListener(self))
        tree.addMouseListener(self.TreeMouseListener(self))
        tree.addFocusListener(self.FocusModeListener(self, self.MODE_TREE))
        tree.addKeyListener(self.TreeKeyListener(self))
        tree.addSelectionChangeListener(self.TreeSelectionListener(self))
        
        pointer = create("com.sun.star.awt.Pointer")
        pointer.setType(40)
        dd = MouseDraggingManager(self, tree, grid, pointer)
        grid.addMouseListener(dd)
        grid.addMouseMotionListener(dd)
        tree.addMouseListener(dd)
        tree.addMouseMotionListener(dd)
        data_cont.getControl(self.ID_DATA_EDIT_DESCRIPTION).\
            addKeyListener(self.EditKeyListener(self))
        listener = self.ButtonListener(self)
        btn_value1 = data_cont.getControl(self.ID_DATA_BTN_VALUE1)
        btn_value1.addActionListener(listener)
        btn_value1.setActionCommand("value1")
        btn_value2 = data_cont.getControl(self.ID_DATA_BTN_VALUE2)
        btn_value2.addActionListener(listener)
        btn_value2.setActionCommand("value2")
        #btn_tags = data_cont.getControl(self.ID_DATA_BTN_TAGS)
        #btn_tags.addActionListener(listener)
        #btn_tags.setActionCommand("tags")
        
        listener = self.EditFocusListener(self)
        text_listener = self.TextListener(self)
        for name in data_cont.getModel().getElementNames():
            if name.startswith("edit_"):
                edit = data_cont.getControl(name)
                edit.addFocusListener(listener)
                edit.addTextListener(text_listener)
        
        for control in data_cont.getControls():
            model = control.getModel()
            if hasattr(model, "Label"):
                model.Label = _(model.Label)
            if hasattr(model, "HelpText"):
                model.HelpText = _(model.HelpText)
    
    def _init_layout(self, container):
        from bookmarks.layouter import \
            GridLayout, HBox, \
            ContainerLayout, Label, Edit, Button
        dg = container.getControl
        data_layout = GridLayout(
            "data vert layout", 
            {
                "n_columns": 2, "n_rows": 5, 
                "column_spacing": self.COLUMN_SPACING, 
                "row_spacing": self.ROW_SPACING, 
                "halign": "fill", "hexpand": True, 
                "valign": "fill", "vexpand": True, 
            }, 
            (
                Label(
                    self.ID_DATA_LABEL_NAME, dg(self.ID_DATA_LABEL_NAME)
                ), 
                Edit(
                    self.ID_DATA_EDIT_NAME, dg(self.ID_DATA_EDIT_NAME), 
                    { "halign": "fill", "hexpand": True, }
                ), 
                Label(
                    self.ID_DATA_LABEL_VALUE1, dg(self.ID_DATA_LABEL_VALUE1)
                ), 
                HBox(
                    "value1 hori", 
                    {
                        "spacing": self.COLUMN_SPACING, 
                        "halign": "fill", "hexpand": True
                    }, 
                    (
                        Edit(
                            self.ID_DATA_EDIT_VALUE1, dg(self.ID_DATA_EDIT_VALUE1), 
                            { "halign": "fill", "hexpand": True, }
                        ), 
                        Button(
                            self.ID_DATA_BTN_VALUE1, dg(self.ID_DATA_BTN_VALUE1), 
                            { "halign": "end", "height_ignore_preferred": True, }
                        )
                    )
                ), 
                Label(
                    self.ID_DATA_LABEL_VALUE2, dg(self.ID_DATA_LABEL_VALUE2)
                ), 
                HBox(
                    "value2 hori", 
                    {
                        "spacing": self.COLUMN_SPACING, 
                        "halign": "fill", "hexpand": True
                    }, 
                    (
                        Edit(
                            self.ID_DATA_EDIT_VALUE2, dg(self.ID_DATA_EDIT_VALUE2), 
                            { "halign": "fill", "hexpand": True, }
                        ), 
                        Button(
                            self.ID_DATA_BTN_VALUE2, dg(self.ID_DATA_BTN_VALUE2), 
                            { "halign": "end", "height_ignore_preferred": True, }
                        )
                    )
                ), 
                Label(
                    self.ID_DATA_LABEL_TAGS, dg(self.ID_DATA_LABEL_TAGS)
                ), 
                Edit(
                    self.ID_DATA_EDIT_TAGS, dg(self.ID_DATA_EDIT_TAGS), 
                    { "halign": "fill", "hexpand": True, }
                ), 
                Label(
                    self.ID_DATA_LABEL_DESCRIPTION, dg(self.ID_DATA_LABEL_DESCRIPTION)
                ), 
                Edit(
                    self.ID_DATA_EDIT_DESCRIPTION, dg(self.ID_DATA_EDIT_DESCRIPTION), 
                    {
                        "halign": "fill", "hexpand": True, 
                        "valign": "fill", "vexpand": True, 
                        
                    }
                )
            )
        )
        margin = self.DATA_MARGIN
        return ContainerLayout(
            "data container layout", 
            container, 
            {
                "margin_left": margin, "margin_right": margin, 
                "margin_top": margin, "margin_bottom": margin, 
            }, 
            data_layout
        )

