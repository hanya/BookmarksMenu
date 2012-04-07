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

from bookmarks.values import PosSize, Key, KeyModifier, \
    MouseListenerBase, KeyListenerBase


class Chooser(object):
    """ Let user to choose an item in image and text. """
    #HORIZONTAL = 0
    #VERTICAL = 1
    
    IMAGE_SIZE = 32
    LABEL_HEIGHT = 25
    PADDING = 3
    PANEL_HEIGHT = PADDING + IMAGE_SIZE + LABEL_HEIGHT + PADDING
    
    BTN_WIDTH = 15
    
    PANEL_PREFIX = "panel_"
    
    NAME_FRAME = "frame"
    NAME_INNER = "inner"
    NAME_IMAGE = "image"
    NAME_LABEL = "label"
    
    NAME_BTN_PREV = "prev"
    NAME_BTN_NEXT = "next"
    
    SHIFT_PREV = 1
    SHIFT_NEXT = 2
    
    BTN_IMAGE_EXTENSION = ".png"
    LEFT_BTN_NAME = "left"
    RIGHT_BTN_NAME = "right"
    HC_SUFFIX = "_hc"
    
    URI_GRAPHICS = "private:graphicrepository/"
    
    KEY_PREV = Key.LEFT
    KEY_NEXT = Key.RIGHT
    
    
    class MouseListener(MouseListenerBase):
        def mousePressed(self, ev):
            self.act.mouse_pressed(ev.Source.getContext())
    
    class KeyListener(KeyListenerBase):
        def __init__(self, act, key_prev, key_next):
            KeyListenerBase.__init__(self, act)
            self.key_prev = key_prev
            self.key_next = key_next
        
        def keyPressed(self, ev):
            code = ev.KeyCode
            mod = ev.Modifiers
            if mod == 0 and code == self.key_prev or code == self.key_next:
                if code == self.key_next:
                    mode = self.act.SHIFT_NEXT
                else:
                    mode = self.act.SHIFT_PREV
                self.act.select_next(ev.Source.getContext(), mode)
            
            elif code == Key.TAB and \
                (mod == 0 or mod == KeyModifier.SHIFT):
                self.act.tab_pressed(mod == KeyModifier.SHIFT)
    
    def __init__(self, ctx, dialog, images_dir="", x=0, y= 0, width=None, height=None):
        self.ctx = ctx
        self.dialog = dialog
        self.images_dir = images_dir
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.active = -1
        self.count = 0
        self.item_listener = None
        self.tab_listener = None
        self.base = None
        self.inner = None
        self.buttons_shown = False
    
    def dispose(self):
        self.ctx = None
        self.dialog = None
        self.base = None
        self.inner = None
    
    def create_service(self, name):
        return self.ctx.getServiceManager().createInstanceWithContext(
            name, self.ctx)
    
    def create_panel(self):
        control = self.create_service("com.sun.star.awt.UnoControlContainer")
        model = self.create_service("com.sun.star.awt.UnoControlContainerModel")
        control.setModel(model)
        return control
    
    def create_image(self, panel, image_url, tooltip=""):
        image = self.create_service("com.sun.star.awt.UnoControlImageControl")
        #image_model = self.create_service("com.sun.star.awt.UnoControlImageControlModel")
        image_model = self.dialog.getModel().createInstance("com.sun.star.awt.UnoControlImageControlModel")
        image_model.setPropertyValues(
            ("BackgroundColor", "Border", "HelpText", "ImageURL", "ScaleImage", ), 
            (-1, 0, tooltip, image_url, False, )
        )
        #print(dir(panel.getModel()))
        #panel.getModel().insertByName(self.NAME_IMAGE, image_model)
        image.setModel(image_model)
        panel.addControl(self.NAME_IMAGE, image)
        #image = panel.getControl(self.NAME_IMAGE)
        return image
    
    def create_label(self, panel, text, tooltip=""):
        label = self.create_service("com.sun.star.awt.UnoControlFixedText")
        #label_model = self.create_service("com.sun.star.awt.UnoControlFixedTextModel")
        label_model = self.dialog.getModel().createInstance("com.sun.star.awt.UnoControlFixedTextModel")
        label_model.setPropertyValues(
            ("Align", "HelpText", "Label", "Tabstop", "VerticalAlign"), 
            (1, tooltip, text, True, 1)
        )
        label.setModel(label_model)
        #panel.getModel().insertByName(self.NAME_LABEL, label_model)
        panel.addControl(self.NAME_LABEL, label)
        #label = panel.getControl(self.NAME_LABEL)
        return label
    
    def set_item_listener(self, listener):
        self.item_listener = listener
    
    def set_tab_listener(self, listener):
        self.tab_listener = listener
    
    def tab_pressed(self, shift):
        try:
            if self.tab_listener:
                self.tab_listener(shift)
        except:
            pass
    
    def get_count(self):
        return self.count
    
    def set_pos_size(self, x, y, width, height):
        self.width = width
        self.height = height
    
    def get_pos_size(self):
        ps = self.base.getPosSize()
        return ps.X, ps.Y, ps.Width, ps.Height
    
    def set_size(self, width, height):
        self.base.setPosSize(0, 0, width, height, PosSize.SIZE)
        # check button should be shown
    
    def set_width(self, width):
        self.base.setPosSize(0, 0, width, 0, PosSize.WIDTH)
    
    def get_active(self):
        return self.active
    
    def set_active(self, index):
        if 0 <= index < self.count:
            if self.active >= 0:
                current = self.inner.getByIdentifier(self.active)
                current.getModel().BackgroundColor = -1
                current.getControl(self.NAME_LABEL).getModel().TextColor = self.TEXT_DEFAULT_COLOR
                #self.inner.getPeer().invalidate(8)
                self.inner.getPeer().invalidateRect(current.getPosSize(), 8)
            activating = self.inner.getByIdentifier(index)
            activating.getModel().BackgroundColor = self.HIGH_LIGHT_COLOR
            label = activating.getControl(self.NAME_LABEL)
            label.setFocus()
            label.getModel().TextColor = self.TEXT_HIGHT_LIGHT_COLOR
            self.active = index
            try:
                if self.item_listener:
                    self.item_listener(self.active)
            except:
                pass
    
    def get_panel_index(self, panel):
        image = panel.getControl(self.NAME_IMAGE)
        try:
            return int(image.getModel().Tag)
        except:
            pass
        # This does not work on LO 3.5, __eq__ is broken.
        #for i, _panel in enumerate(self.inner.getControls()):
        #    if panel == _panel:
        #        return i
        return -1
    
    def mouse_pressed(self, panel):
        index = self.get_panel_index(panel)
        if 0 <= index and index != self.active:
            self.set_active(index)
    
    def select_next(self, panel, mode):
        index = self.get_panel_index(panel)
        if mode == self.SHIFT_NEXT:
            next_index = index + 1
        else:
            next_index = index - 1
        if 0 <= next_index and next_index != self.active:
            self.set_active(next_index)
            if not self.check_panel_is_shown(self.active):
                self.shift_view(mode)
        else:
            self.shift_view(mode)
    
    def _create_panel(self, text, image_url, tooltip=""):
        panel = self.create_panel()
        image = self.create_image(panel, image_url, tooltip)
        #panel.addControl(self.NAME_IMAGE, image)
        label = self.create_label(panel, text, tooltip)
        #panel.addControl(self.NAME_LABEL, label)
        self.set_panel_pos_size(panel, image, label)
        key_listener = self.KeyListener(self, self.KEY_PREV, self.KEY_NEXT)
        mouse_listener = self.MouseListener(self)
        label.addMouseListener(mouse_listener)
        label.addKeyListener(key_listener)
        image.addMouseListener(mouse_listener)
        image.addKeyListener(key_listener)
        return panel
    
    def set_panel_pos_size(self, panel, image, label):
        image_size = self.IMAGE_SIZE
        padding = self.PADDING
        
        label_width = label.getPreferredSize().Width
        if label_width < image_size:
            label_width = image_size
        label_width += padding * 4
        
        label.setPosSize(0, image_size, label_width, self.LABEL_HEIGHT, PosSize.POSSIZE)
        image.setPosSize(0, padding, label_width, image_size, PosSize.POSSIZE)
        panel.setPosSize(0, 0, label_width, self.PANEL_HEIGHT, PosSize.SIZE | PosSize.Y)
    
    def append_panel(self, text, image_url, tooltip=""):
        panel = self._create_panel(text, image_url, tooltip)
        total_panel_width = self.get_total_width()
        panel.setPosSize(total_panel_width, 0, 0, 0, PosSize.X)
        self.inner.addControl(self.PANEL_PREFIX + str(self.count), panel)
        # workaround
        panel.getControl(self.NAME_IMAGE).getModel().Tag = str(self.count)
        self.count += 1
        return panel
    
    def get_total_width(self, start=None, end=None):
        if start is None:
            return sum([c.getPosSize().Width for c in self.inner.getControls()])
        else:
            if end is None:
                controls = self.inner.getControls()[start:]
            else:
                controls = self.inner.getControls()[start:end]
            return sum([c.getPosSize().Width for c in controls])
    
    def check_content_size(self):
        control_width = self.base.getPosSize().Width
        content_width = self.get_total_width()
        if control_width < content_width:
            # add buttons
            create = self.create_service
            self.buttons_shown = True
            dialog_model = self.dialog.getModel()
            
            def create_image(name, image_url):
                image_model = create("com.sun.star.awt.UnoControlImageControlModel")
                image_model.setPropertyValues(
                    ("Border", "ImageURL", "ScaleImage"), 
                    (0, image_url, False))
                image = create("com.sun.star.awt.UnoControlImageControl")
                image.setModel(image_model)
                self.base.addControl(name, image)
                return image
            
            images_dir = self.images_dir
            is_hc = self.dialog.StyleSettings.FieldColor < 0x888888
            if is_hc:
                left_image_name = "".join((self.LEFT_BTN_NAME, self.HC_SUFFIX, self.BTN_IMAGE_EXTENSION))
                right_image_name = "".join((self.RIGHT_BTN_NAME, self.HC_SUFFIX, self.BTN_IMAGE_EXTENSION))
            else:
                left_image_name = self.LEFT_BTN_NAME + self.BTN_IMAGE_EXTENSION
                right_image_name = self.RIGHT_BTN_NAME + self.BTN_IMAGE_EXTENSION
            left_image = create_image(self.NAME_BTN_PREV, images_dir + left_image_name)
            right_image = create_image(self.NAME_BTN_NEXT, images_dir + right_image_name)
            left_image.setPosSize(0, 0, self.BTN_WIDTH, self.PANEL_HEIGHT, PosSize.POSSIZE)
            right_image.setPosSize(control_width - self.BTN_WIDTH, 0, self.BTN_WIDTH, self.PANEL_HEIGHT, PosSize.POSSIZE)
            
            self.frame.setPosSize(self.BTN_WIDTH, 0, control_width - self.BTN_WIDTH * 2, 0, PosSize.X | PosSize.WIDTH)
            
            class ButtonsMouseListener(MouseListenerBase):
                def __init__(self, act, mode):
                    MouseListenerBase.__init__(self, act)
                    self.mode = mode
                def mousePressed(self, ev):
                    self.act.shift_view(self.mode)
            
            left_image.addMouseListener(ButtonsMouseListener(self, self.SHIFT_PREV))
            right_image.addMouseListener(ButtonsMouseListener(self, self.SHIFT_NEXT))
            left_image.setEnable(False)
            self.inner.setPosSize(0, 0, content_width, 0, PosSize.WIDTH)
    
    def check_panel_is_shown(self, index):
        inner_pos = self.inner.getPosSize()
        frame_width = self.frame.getPosSize().Width
        width_including_panel = self.get_total_width(0, index +1)
        inner_x = abs(inner_pos.X)
        return inner_x < width_including_panel < (inner_x + frame_width)
    
    def shift_view(self, mode):
        inner_pos = self.inner.getPosSize()
        frame_width = self.frame.getPosSize().Width
        content_width = self.get_total_width()
        panel_average_width = content_width / self.get_count()
        
        next_state = True
        prev_state = True
        if mode == self.SHIFT_NEXT:
            shift = - panel_average_width
            min_x = -(content_width - frame_width)
            x = inner_pos.X + shift
            if x < min_x:
                x = min_x
                next_state = False
        else:
            shift = panel_average_width
            x = inner_pos.X + shift
            if x > 0:
                x = 0
                prev_state = False
        self.inner.setPosSize(x, 0, 0, 0, PosSize.X)
        
        self.base.getControl(self.NAME_BTN_NEXT).setEnable(next_state)
        self.base.getControl(self.NAME_BTN_PREV).setEnable(prev_state)
    
    def get_content_size(self):
        width = 0
        height = 0
        # consider item spacing
        for panel in self.inner.getControls():
            ps = panel.getPosSize()
            width += ps.Width
            _height = ps.Height
            if height < _height:
                height = _height
        return width, height
    
    def _create_base(self):
        create_panel = self.create_panel
        width = self.width
        if width is None:
            width = self.dialog.getPosSize().Width
        
        base = create_panel()
        base.setPosSize(self.x, self.y, width, self.PANEL_HEIGHT, PosSize.POSSIZE)
        frame = create_panel()
        frame.setPosSize(0, 0, width, self.PANEL_HEIGHT, PosSize.POSSIZE)
        inner = create_panel()
        inner.setPosSize(0, 0, width, self.PANEL_HEIGHT, PosSize.POSSIZE)
        frame.addControl(self.NAME_INNER, inner)
        base.addControl(self.NAME_FRAME, frame)
        self.base = base
        self.inner = inner
        self.frame = frame
    
    def fit_to_contents(self):
        width = self.get_total_width()
        self.base.setPosSize(0, 0, width, 0, PosSize.WIDTH)
        self.inner.setPosSize(0, 0, width, 0, PosSize.WIDTH)
        self.frame.setPosSize(0, 0, width, 0, PosSize.WIDTH)
    
    def create(self, name, panel_defs):
        style = self.dialog.StyleSettings
        self.HIGH_LIGHT_COLOR = self.dialog.StyleSettings.HighlightColor
        self.TEXT_HIGHT_LIGHT_COLOR = style.HighlightTextColor
        self.TEXT_DEFAULT_COLOR = style.WindowTextColor
        
        self._create_base()
        for panel_def in panel_defs:
            self.append_panel(*panel_def)
        #self.check_content_size()
        
        self.dialog.addControl(name, self.base)
        self.set_active(0)

