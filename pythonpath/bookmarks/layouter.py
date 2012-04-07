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

import sys
version = sys.version_info
if version[0] == 2 and version[1] < 4:
    def any(iterable):
        for i in iterable:
            if i:
                return True
        return False
del version
del sys


class PosSize(object):
    from com.sun.star.awt.PosSize import \
        X, Y, WIDTH, HEIGHT, POS, SIZE, POSSIZE

class LayoutBase(object):
    
    ALIGN_START = "start"
    ALIGN_CENTER = "center"
    ALIGN_END = "end"
    ALIGN_FILL = "fill"
    
    def __init__(self, name, attrs={}):
        self.name = name
        self.visible = True
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.width_request = 0
        self.height_request = 0
        self.margin_left = 0
        self.margin_right = 0
        self.margin_top = 0
        self.margin_bottom = 0
        self.halign = "fill"
        self.valign = "fill"
        self.hexpand = False
        self.vexpand = False
        for k, v in attrs.iteritems():
            setattr(self, k, v)
    
    def __str__(self):
        return "<%s.%s %s>" % (
            self.__class__.__module__, 
            self.__class__.__name__, self.name)
    
    def set_visible(self, state):
        self.visible = state
    
    #def __nonzero__(self):
    #   return self.visible
    
    def is_visible(self):
        return self.visible
    
    def get_min_height(self):
        return 0
    
    def get_min_width(self):
        return 0
    
    def get_height(self):
        return 0
    
    def get_width(self):
        return 0
    
    def set_pos(self, x, y):
        self.x = x
        self.y = y
        return self
    
    def set_size(self, width, height):
        self.width = width
        self.height = height
        return self
    
    def set_possize(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        return self
    
    def get_size(self):
        return self.width, self.height
    
    def get_width(self):
        return self.width
    
    def get_height(self):
        return self.height
    
    def get_hori_margin(self):
        return self.margin_left + self.margin_right
    
    def get_vert_margin(self):
        return self.margin_top + self.margin_bottom
    
    def calculate_pos_size(self, width=None, height=None):
        
        x = self.x + self.margin_left
        y = self.y + self.margin_top
        if width is None:
            width = self.get_width()
        if height is None:
            height = self.get_height()
        
        halign = self.halign
        valign = self.valign
        if halign == self.ALIGN_FILL:
            width = self.width - self.get_hori_margin()
        elif halign == self.ALIGN_CENTER:
            x += (self.width - width) / 2
        elif halign == self.ALIGN_END:
            x += self.width - width
        if x < 0:
            x = 0
        
        if valign == self.ALIGN_FILL:
            height = self.height - self.get_vert_margin()
        elif valign == self.ALIGN_CENTER:
            y += (self.height - height) / 2
        elif valign == self.ALIGN_END:
            y += self.height - height
        if y < 0:
            y = 0
        
        return x, y, width, height
    
    def layout(self):
        pass


class Layout(LayoutBase):
    
    def __init__(self, name, attrs, elements):
        LayoutBase.__init__(self, name, attrs)
        self.elements = elements
    
    def get_element(self, name):
        for element in self.elements:
            if element.name == name:
                return element
        return None
    
    def set_visible(self, state):
        LayoutBase.set_visible(self, state)
        for element in self.elements:
            element.set_visible(state)
    
    def set_element_visible(self, name, state):
        item = self.get_element(name)
        if item:
            item.set_visible(state)
    
    def get_min_height(self):
        if self.visible:
            v = max([element.get_min_height() 
                for element in self.elements]) + \
                    self.get_vert_margin()
            return v
        return 0
    
    def get_min_width(self):
        if self.visible:
            return max([element.get_min_width() 
                for element in self.elements]) + \
                    self.get_hori_margin()
        return 0


class GridLayout(Layout):
    
    def __init__(self, name, attrs, elements):
        self.row_spacing = 0
        self.column_spacing = 0
        self.n_rows = 3
        self.n_columns = 3
        Layout.__init__(self, name, attrs, elements)
        if len(elements) != self.n_rows * self.n_columns:
            raise TypeError("Illegal number of elements.")
    
    def set_row_visible(self, index, state):
        if 0 <= index < self.n_rows:
            for element in self.elements[index * self.n_columns:(index + 1) * self.n_columns]:
                element.set_visible(state)
    
    def set_column_visible(self, index, state):
        if 0 <= index < self.n_columns:
            for element in self.elements[index:len(self.elements):self.n_columns]:
                element.set_visible(state)
    
    def get_min_height(self):
        if self.visible:
            return sum([max([element.get_min_height() 
                for element in self.elements[index * self.n_columns:(index +1) * self.n_columns]]) 
                    for index in range(self.n_rows)]) + \
                self.get_vert_margin() + self.n_rows * self.row_spacing - self.row_spacing
        return 0
    
    def get_min_width(self):
        if self.visible:
            content_width = sum([max([element.get_min_width() 
                for element in self.elements[index:self.n_rows * self.n_columns:self.n_columns]]) 
                    for index in range(self.n_columns)]) + \
                self.get_hori_margin() + self.n_columns * self.column_spacing - self.column_spacing
            if content_width < self.width_request:
                content_width = self.width_request
            return content_width
        return 0
    
    def layout(self):
        elements = self.elements
        n_vis_rows = [any([element.is_visible() 
            for element in self.elements[index * self.n_columns:(index +1) * self.n_columns]])
                for index in range(self.n_rows)].count(True)
        
        n_vis_columns = [any([element.is_visible()
            for element in self.elements[index:self.n_rows * self.n_columns:self.n_columns]]) 
                for index in range(self.n_columns)].count(True)
        
        height_in_rows = [[element.get_min_height() 
            for element in self.elements[index * self.n_columns:(index +1) * self.n_columns]] 
                for index in range(self.n_rows)]
        
        width_in_columns = [[element.get_min_width() 
            for element in self.elements[index:self.n_rows * self.n_columns:self.n_columns]] 
                for index in range(self.n_columns)]
        
        rows_height = [max(row_height) for row_height in height_in_rows]
        columns_width = [max(column_width) for column_width in width_in_columns]
        
        total_content_height = sum(rows_height)
        full_content_height = total_content_height
        if self.valign == self.ALIGN_FILL:
            expanded_height = self.height - self.get_hori_margin() - \
                self.row_spacing * (n_vis_rows -1)
            if full_content_height < expanded_height:
                full_content_height = expanded_height
        remained_height = full_content_height - total_content_height
        variable_rows = [any([element.vexpand 
            for element in self.elements[index * self.n_columns:(index +1) * self.n_columns]]) 
                for index in range(self.n_rows)]
        variable_row_add_height = 0
        if variable_rows.count(True):
            variable_row_add_height = remained_height / variable_rows.count(True)
        
        
        variable_rows = [variable_row_add_height * int(row) for row in variable_rows]
        #variable_rows = [variable_row_add_height if row else 0 for row in variable_rows]
        
        total_content_width = sum(columns_width)
        full_content_width = total_content_width
        if self.halign == self.ALIGN_FILL:
            expanded_width = self.width - self.get_vert_margin()# - \
            #    self.column_spacing * (n_vis_columns -1)
            if full_content_width < expanded_width:
                full_content_width = expanded_width
        if full_content_width < self.width_request:
            full_content_width = self.width_request
        
        remained_width = full_content_width - total_content_width - self.column_spacing * (n_vis_columns -1)
        variable_columns = [any([element.hexpand 
            for element in self.elements[index:self.n_rows * self.n_columns:self.n_columns]]) 
                for index in range(self.n_columns)]
        variable_column_add_width = 0
        if variable_columns.count(True):
            variable_column_add_width = remained_width / variable_columns.count(True)
        
        variable_columns = [variable_column_add_width * int(column) 
            for column in variable_columns]
        #variable_columns = [variable_column_add_width if column else 0 
        #    for column in variable_columns]
        
        x = self.x
        y = self.y
        
        if self.halign == self.ALIGN_CENTER:
            x += (full_content_width - total_content_width) / 2
        elif self.halign == self.ALIGN_END:
            x += full_content_width - total_content_width
        
        if self.valign == self.ALIGN_CENTER:
            y += (full_content_height - total_content_height) / 2
        elif self.valign == self.ALIGN_END:
            y += full_content_height - total_content_height
        
        row_spacing = self.row_spacing
        column_spacing = self.column_spacing
        n_columns = self.n_columns
        n_rows = self.n_rows
        _y = y + self.margin_top
        for row in range(n_rows):
            _x = x + self.margin_left
            visible_columns = 0
            for column in range(n_columns):
                element = elements[row * n_columns + column]
                if element.is_visible():
                    visible_columns += 1
                _width = columns_width[column]
                _height = rows_height[row]
                #if element.hexpand:
                _width += variable_columns[column]
                #if element.vexpand:
                _height += variable_rows[row]
                element.set_possize(_x, _y, _width, _height)
                element.layout()
                
                _x += _width + column_spacing
            if visible_columns:
                _y += rows_height[row] + variable_rows[row] + row_spacing
        
        total_width = sum(columns_width) + sum(variable_columns) + \
            (n_vis_columns -1) * self.column_spacing + self.get_hori_margin()
        total_height = sum(rows_height) + sum(variable_rows) + \
            (n_vis_rows -1) * self.row_spacing + self.get_vert_margin()
        width = full_content_width + self.get_hori_margin()
        height = full_content_height + self.get_vert_margin()
        if width < total_width:
            width = total_width
        if height < total_height:
            height = total_height
        
        self.set_size(width, height)


class HBox(Layout):
    
    def __init__(self, name, attrs, elements):
        self.spacing = 0
        Layout.__init__(self, name, attrs, elements)
    
    def get_min_width(self):
        if self.visible:
            min_width = [element.get_min_width() 
                for element in self.elements if element.is_visible()]
            return sum(min_width) + \
                self.spacing * len(min_width) - self.spacing + \
                    self.get_hori_margin()
        return 0
    
    def set_column_visible(self, index, state):
        if 0 <= index < len(self.elements):
            self.elements[index].set_visible(state)
    
    def layout(self):
        elements = self.elements
        spacing = self.spacing
        
        # height
        contents_height = [element.get_min_height() 
            for element in elements if element.is_visible()]
        length = len(contents_height)
        if contents_height:
            total_content_height = max(contents_height)
        else:
            total_content_height = 0
        full_content_height = total_content_height
        if self.valign == self.ALIGN_FILL:
            expanded_height = self.height - self.get_vert_margin()
            if full_content_height < expanded_height:
                full_content_height = expanded_height
        
        # width
        contents_width = [element.get_min_width() 
            for element in elements if element.is_visible()]
        total_content_width = sum(contents_width)
        full_content_width = total_content_width
        if self.halign == self.ALIGN_FILL or self.hexpand:
            expanded_width = self.width - \
                self.get_hori_margin() - spacing * (length -1)
            if full_content_width < expanded_width:
                full_content_width = expanded_width
        variable_elements_width = [element.get_min_width() 
            for element in elements if element.is_visible() and not element.hexpand]
        
        variable_add_width = 0
        if variable_elements_width:
            variable_add_width = (full_content_width - total_content_width) / len(variable_elements_width)
        
        x, y, width, height = self.calculate_pos_size(
            full_content_width + self.get_hori_margin() + spacing * (length -1), 
            full_content_height + self.get_vert_margin())
        
        _x = x
        _y = y
        
        if self.halign == self.ALIGN_CENTER:
            _x += (width - total_content_width) / 2 - spacing * (length -1)
        elif self.halign == self.ALIGN_END:
            _x += width - total_content_width - spacing * (length -1)
        
        _total_width = self.get_hori_margin()
        for element in elements:
            if element.is_visible():
                _width = element.get_min_width()
                if element.hexpand:
                    _width += variable_add_width
            else:
                _width = 0
            
            element.set_possize(_x, _y, _width, full_content_height)
            element.layout()
            if element.is_visible():
                _x += _width + spacing
                _total_width += _width + spacing
        _total_width -= spacing
        
        if width < _total_width:
            width = _total_width
        full_height = full_content_height + self.get_vert_margin()
        if height < full_height:
            height = full_height
        self.set_size(width, height)


class VBox(Layout):
    
    def __init__(self, name, attrs, elements):
        self.spacing = 0
        Layout.__init__(self, name, attrs, elements)
    
    def get_min_height(self):
        if self.visible:
            min_height = [element.get_min_height() 
                for element in self.elements if element.is_visible()]
            return sum(min_height) + \
                self.spacing * len(min_height) - self.spacing + \
                self.get_vert_margin()
        return 0
    
    def set_row_visible(self, index, state):
        if 0 <= index < len(self.elements):
            self.elements[index].set_visible(state)
    
    def layout(self):
        elements = self.elements
        spacing = self.spacing
        # height
        contents_height = [element.get_min_height() 
            for element in elements if element.is_visible()]
        
        length = len(contents_height)
        total_content_height = sum(contents_height)
        full_content_height = total_content_height
        if self.valign == self.ALIGN_FILL:
            expanded_height = self.height - self.get_vert_margin() - \
                spacing * (length -1)
            if full_content_height < expanded_height:
                full_content_height = expanded_height
        variable_elements_height = [element.get_min_height() 
            for element in elements if element.is_visible() and not element.vexpand]
        variable_add_height = 0
        if variable_elements_height:
            variable_add_height = (total_content_height - \
                sum(variable_elements_height)) / len(variable_elements_height)
        
        # width
        contents_width = [element.get_min_width() 
            for element in elements if element.is_visible()]
        total_content_width = 0
        if contents_width:
            total_content_width = max(contents_width)
        
        full_content_width = total_content_width
        if self.halign == self.ALIGN_FILL or self.hexpand:
            expanded_width = self.width - self.get_hori_margin()
            if full_content_width < expanded_width:
                full_content_width = expanded_width
        
        _x = self.x + self.margin_left
        _y = self.y + self.margin_top
        if self.halign == self.ALIGN_CENTER:
            _x += (full_content_width - total_content_width) / 2
        elif self.halign == self.ALIGN_END:
            x += full_content_width - total_content_width
        
        if self.valign == self.ALIGN_CENTER:
            _y += (full_content_height - total_content_height) / 2
        elif self.valign == self.ALIGN_END:
            _y += full_content_height - total_content_height
        
        _total_height = 0
        for element in elements:
            if element.is_visible():
                _height = element.get_min_height()
            else:
                _height = 0
            element.set_possize(_x, _y, full_content_width, _height)
            element.layout()
            if element.is_visible():
                _y += _height + spacing
                _total_height += _height + spacing
        _total_height -= spacing
        
        width = full_content_width + self.get_hori_margin()
        height = _total_height + self.get_vert_margin()
        self.set_size(width, height)


class DialogLayout(Layout):
    
    def __init__(self, name, dialog, attrs, elements):
        Layout.__init__(self, name, attrs, elements)
        self.dialog = dialog
    
    def get_element(self, name):
        if self.elements.name == name:
            return self.elements
        return self.elements.get_element(name)
    
    def layout(self):
        element = self.elements
        
        width = self.width - self.get_hori_margin()
        height = self.height - self.get_vert_margin()
        element.set_possize(
            self.margin_left, self.margin_top, 
            width, height
        )
        element.layout()
        
        width, height = element.get_size()
        width += self.get_hori_margin()
        height += self.get_vert_margin()
        
        if width < self.width:
            width = self.width
        if height < self.height:
            height = self.height
        
        self.dialog.setPosSize(0, 0, width, height, PosSize.SIZE)
    
    def get_pos_size(self):
        ps = self.dialog.getPosSize()
        return ps.Width, ps.Height


class ContainerLayout(Layout):
    """ Container wide layout. """
    
    def __init__(self, name, container, attributes, elements):
        Layout.__init__(self, name, attributes, elements)
        self.container = container
    
    def get_element(self, name):
        return self.elements.get_element(name)
    
    def set_visible(self, state):
        self.elements.set_visible(state)
    
    def set_pos_size(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    def layout(self, x=None, y=None, width=None, height=None):
        ps = self.container.getPosSize()
        width = ps.Width
        height = ps.Height
        
        content_width = width - self.get_hori_margin()
        content_height = height - self.get_vert_margin()
        
        self.elements.set_possize(
            self.margin_left, self.margin_top, content_width, content_height)
        self.elements.layout()
        self.set_pos_size(ps.X, ps.Y, width, height)


class Control(LayoutBase):
    
    def __init__(self, name, element, attrs={}):
        self.width_request = 0
        self.height_request = 0
        LayoutBase.__init__(self, name, attrs)
        if element is None:
            raise TypeError("%s is None element." % name)
        self.element = element
        self._init_element()
    
    def _init_element(self):
        pass
    
    def set_focus(self):
        self.element.setFocus()
    
    def set_visible(self, state):
        LayoutBase.set_visible(self, state)
        self.element.setVisible(state)
    
    def get_min_height(self):
        return self.height_request
    
    def get_min_width(self):
        return self.width_request
    
    def layout(self):
        x, y, width, height = self.calculate_pos_size()
        self.element.setPosSize(x, y, width, height, PosSize.POSSIZE)


class Placeholder(Control):
    """ Empty item for grid layout. """
    def __init__(self, *args):
        Control.__init__(self, "", None, {})
    
    def is_visible(self):
        return False
    
    def set_focus(self):
        pass
    
    def layout(self):
        pass


class Label(Control):
    
    MIN_HEIGHT = 25
    
    def __init__(self, name, element, attrs={}):
        Control.__init__(self, name, element, attrs)
        if not "height_request" in attrs:
            self.height_request = self.MIN_HEIGHT
    
    def _init_element(self):
        ps = self.element.getPreferredSize()
        self.element.setPosSize(0, 0, ps.Width, ps.Height, PosSize.WIDTH)
    
    def get_width(self):
        if self.visible:
            return self.get_min_width()
        return 0
    
    def get_min_width(self):
        if self.visible:
            min_width = self.width_request
            element_width = self.element.getPreferredSize().Width
            if min_width < element_width:
                min_width = element_width
            return min_width + self.get_hori_margin()
        return 0
    
    def get_height(self):
        if self.visible:
            return self.get_min_height()
        return 0
    
    def get_min_height(self):
        if self.visible:
            min_height = self.height_request
            element_height = self.element.getPreferredSize().Height
            if min_height < element_height:
                min_height = element_height
            return min_height + self.get_vert_margin()
        return 0


class Button(Label):
    
    MIN_WIDTH = 5
    MIN_HEIGHT = 25
    
    def __init__(self, name, element, attrs={}):
        self.height_ignore_preferred = False
        Label.__init__(self, name, element, attrs)
        if not "width_request" in attrs:
            self.width_request = self.MIN_WIDTH
        if not "height_request" in attrs:
            self.height_request = self.MIN_HEIGHT
    
    def _init_element(self):
        ps = self.element.getPreferredSize()
        self.element.setPosSize(0, 0, ps.Width, self.MIN_HEIGHT, PosSize.SIZE)
    
    def get_min_height(self):
        if self.visible:
            if self.height_ignore_preferred:
                return self.height_request
            min_height = self.height_request
            element_height = self.element.getPreferredSize().Height
            if element_height < min_height:
                min_height = element_height
            return min_height + self.get_vert_margin()
        return 0
    
    def layout(self):
        x, y, width, height = self.calculate_pos_size()
        if self.height_ignore_preferred:
            height = self.height_request
        self.element.setPosSize(x, y, width, height, PosSize.POSSIZE)


class Edit(Control):
    MIN_HEIGHT = 25
    MIN_WIDTH = 150
    
    def __init__(self, name, element, attrs={}):
        Control.__init__(self, name, element, attrs)
        if not "width_request" in attrs:
            self.width_request = self.MIN_WIDTH
    
    def get_height(self):
        if self.visible:
            return self.get_min_height()
        return 0
    
    def get_min_height(self):
        if self.visible:
            min_height = self.height_request
            if min_height == 0:
                min_height = self.MIN_HEIGHT
            #element_height = self.element.getPreferredSize().Height
            #if element_height < min_height:
            #   min_height = element_height
            return min_height + self.get_vert_margin()
        return 0


class List(Edit):
    pass

class CheckBox(Label):
    pass

class Option(Label):
    pass

class Line(Label):
    
    MIN_WIDTH = 50
    
    def _init_element(self):
        pass
    
    def get_min_width(self):
        if self.visible:
            min_width = self.width_request
            if min_width == 0:
                min_width = self.MIN_WIDTH
            return min_width
        return 0
    
    def get_min_height(self):
        if self.visible:
            min_height = self.height_request
            if min_height == 0:
                if self.element.getModel().Label:
                    min_height = self.MIN_HEIGHT
                else:
                    min_height = 1
            return min_height
        return 0

