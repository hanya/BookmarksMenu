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

CMD_CUT = "Cut"
CMD_COPY = "Copy"
CMD_PASTE = "Paste"
CMD_DELETE = "Delete"
CMD_SELECTALL = "SelectAll"
CMD_UNDO = "Undo"
CMD_REDO = "Redo"
CMD_INSERTDOC = "InsertDoc"
CMD_EXPORTTO = "ExportTo"
CMD_SAVE = "Save"

ID_CUT = 10
ID_COPY = 11
ID_PASTE = 12
ID_DELETE = 13
ID_SELECTALL = 15
ID_UNDO = 20
ID_REDO = 21
ID_INSERTDOC = 40
ID_EXPORTTO = 50
ID_SAVE = 5

UNO_COMMANDS = {
	CMD_CUT: ID_CUT, 
	CMD_COPY: ID_COPY, 
	CMD_PASTE: ID_PASTE, 
	CMD_DELETE: ID_DELETE, 
	CMD_SELECTALL: ID_SELECTALL, 
	CMD_UNDO: ID_UNDO, 
	CMD_REDO: ID_REDO, 
	CMD_INSERTDOC: ID_INSERTDOC, 
	CMD_EXPORTTO: ID_EXPORTTO, 
    CMD_SAVE: ID_SAVE, 
}

CMD_INSERT_BOOKMRAK = "InsertBookmark"
CMD_INSERT_SEPARATOR = "InsertSeparator"
CMD_INSERT_FOLDER = "InsertFolder"
CMD_BACK = "Back"
CMD_FORWARD = "Forward"
CMD_MOVE = "Move"
CMD_OPEN = "Open"
CMD_MIGRATION = "Migration"
CMD_NEW_MENU = "NewMenu"
CMD_ABOUT = "About"
"""
CMD_GO_UP = "GoUp"
CMD_GO_DOWN = "GoDown"
CMD_GO_TO_START = "GoToStart"
CMD_GO_TO_END = "GoToEnd"
CMD_GO_UP_SEL = "GoUpSel"
CMD_GO_DOWN_SEL = "GoDownSel"
CMD_GO_TO_START_SEL = "GoToStartSel"
CMD_GO_TO_END_SEL = "GoToEndSel"
"""

ID_INSERT_BOOKMRAK = 100
ID_INSERT_SEPARATOR = 101
ID_INSERT_FOLDER = 102
ID_BACK = 110
ID_FORWARD = 120
ID_MOVE = 130
ID_OPEN = 134
ID_MIGRATION = 138
ID_NEW_MENU = 139
ID_ABOUT = 140

CUSTOM_COMMANDS = {
	CMD_INSERT_BOOKMRAK: ID_INSERT_BOOKMRAK, 
	CMD_INSERT_SEPARATOR: ID_INSERT_SEPARATOR, 
	CMD_INSERT_FOLDER: ID_INSERT_FOLDER, 
	CMD_BACK: ID_BACK, 
	CMD_FORWARD: ID_FORWARD,
	CMD_MOVE: ID_MOVE, 
	CMD_OPEN: ID_OPEN, 
	CMD_MIGRATION: ID_MIGRATION, 
    CMD_NEW_MENU: ID_NEW_MENU, 
	CMD_ABOUT: ID_ABOUT, 
}

DISPATCH_COMMANDS = {}
DISPATCH_COMMANDS.update(UNO_COMMANDS)
DISPATCH_COMMANDS.update(CUSTOM_COMMANDS)
