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

class PosSize(object):
    from com.sun.star.awt.PosSize import \
        X, Y, WIDTH, HEIGHT, POS, SIZE, POSSIZE

class MouseButton(object):
    from com.sun.star.awt.MouseButton import \
        LEFT, RIGHT

class Key(object):
    from com.sun.star.awt.Key import \
        LEFT, RIGHT, UP, DOWN, \
        HOME, END, \
        TAB, RETURN, SPACE

class KeyModifier(object):
    from com.sun.star.awt.KeyModifier import \
        SHIFT, MOD1, MOD2, MOD3


import unohelper

from com.sun.star.awt import XActionListener, \
    XItemListener, XKeyListener, XMouseListener, \
    XTextListener, XFocusListener


class ListenerBase(unohelper.Base):
    """ Base class for listeners. """
    def __init__(self, act):
        self.act = act
    
    def disposing(self, ev):
        self.act = None

class ActionListenerBase(ListenerBase, XActionListener):
    def actionPerformed(self, ev): pass

class ItemListenerBase(ListenerBase, XItemListener):
    def itemStateChanged(self, ev): pass

class KeyListenerBase(ListenerBase, XKeyListener):
    def keyPressed(self, ev): pass
    def keyReleased(self, ev): pass

class MouseListenerBase(ListenerBase, XMouseListener):
    def mousePressed(self, ev): pass
    def mouseReleased(self, ev): pass
    def mouseEntered(self, ev): pass
    def mouseExited(self, ev): pass

class TextListenerBase(ListenerBase, XTextListener):
    def textChanged(self, ev): pass

class FocusListenerBase(ListenerBase, XFocusListener):
    def focusLost(self, ev): pass
    def focusGained(self, ev): pass

