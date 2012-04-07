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

from com.sun.star.awt.grid import \
    XGridDataModel, XMutableGridDataModel, GridDataEvent
from com.sun.star.lang import XComponent, EventObject, XServiceInfo, \
    IndexOutOfBoundsException, IllegalArgumentException

from com.sun.star.uno import XAdapter, XWeak

from bookmarks.base import ServiceInfo


class WeakBase(XWeak, XAdapter):
    # XWeak
    def queryAdapter(self):
        return self
    
    # XAdapter
    def queryAdapted(self):
        return self
    
    def addReference(self, ref):
        pass
    
    def removeReference(self, ref):
        pass


class CustomGridDataModel(unohelper.Base, WeakBase, ServiceInfo, XMutableGridDataModel):
    
    IMPLE_NAME = "bookmarks.grid.CustomGridDataModel"
    SERVICE_NAMES = ("com.sun.star.awt.grid.DefaultGridDataModel",)
    
    def __init__(self, column_count):
        self._grid_data_listeners = []
        self.rows = []
        self.headings = []
        self.column_count = column_count
    
    # XComponent
    def dispose(self): pass
    def addEventListener(self, listener): pass
    def removeEventListener(self, listener): pass
    
    # XCloneable
    def createClone(self):
        return CustomGridDataModel()
    
    # XGridDataModel
    def get_row_count(self):
        return len(self.rows)
    RowCount = property(get_row_count)
    
    def get_column_count(self):
        return self.column_count
    ColumnCount = property(get_column_count)
    
    def getCellData(self, column, row):
        if 0 <= row < len(self.rows) and \
            0 <= column < len(self.rows[row]):
            #0 <= column < self.column_count:
            return self.rows[row][column]
        raise IndexOutOfBoundsException("", self)
    
    def getCellToolTip(self, column, row):
        return self.getCellData(column, row)
    
    def getRowHeading(self, row):
        if 0 <= row < len(self.rows):
            return self.headings[row]
        raise IndexOutOfBoundsException("", self)
    
    def getRowData(self, row):
        if 0 <= row < len(self.rows):
            #print(self.rows[row])
            return tuple(self.rows[row])
        raise IndexOutOfBoundsException("", self)
    
    # XMutableGridDataModel
    def addRow(self, heading, data):
        self.headings.append(heading)
        self.rows.append(data)
        row_count = len(self.rows)
        self.broadcast_inserted(
            0, self.column_count -1, 
            row_count, row_count +1)
    
    def addRows(self, headings, data):
        if len(headings) != len(data):
            raise IllegalArgumentException()
        row_count = len(self.rows)
        self.headings += list(headings)
        self.rows += list(data)
        self.broadcast_inserted(
            0, self.column_count -1, 
            row_count, len(self.headings))
    
    def insertRow(self, index, heading, data):
        if 0 <= index < len(self.rows):
            self.rows.insert(index, data)
            self.heading.insert(index, heading)
            self.broadcast_inserted(
                0, self.column_count -1, 
                index, index)
            return
        raise IndexOutOfBoundsException("", self)
    
    def insertRows(self, index, headings, data):
        if 0 <= index <= len(self.rows):
            self.rows[index:index] = data
            self.headings[index:index] = headings
            self.broadcast_inserted(
                0, self.column_count -1, 
                index, index + len(data))
            return
        raise IndexOutOfBoundsException("", self)
    
    def removeRow(self, row):
        if 0 <= row < len(self.rows):
            self.rows.pop(row)
            self.headings.pop(row)
            self.broadcast_removed(
                0, self.column_count -1, 
                row, row)
            return
        raise IndexOutOfBoundsException("", self) 
    
    def removeAllRows(self):
        row_count = len(self.rows)
        self.rows[0:] = []
        self.headings[0:] = []
        self.broadcast_removed(
            0, self.column_count -1, 
            0, row_count -1)
    
    def updateCellData(self, column, row, value):
        if 0 <= row < len(self.rows) and \
            0 <= column < self.column_count:
            data = list(self.rows[row])
            data[column] = value
            self.rows[row] = data
            self.broadcast_changed(
                column, column, 
                row, row)
            return
        raise IndexOutOfBoundsException("", self) 
    
    def updateRowData(self, columns, row, values):
        if len(columns) != len(values):
            raise IllegalArgumentException(
                "length of column index and values are different", self, 0)
        if 0 <= row < len(self.rows):
            data = list(self.rows[row])
            column_count = len(data)
            for column, value in zip(columns, values):
                if 0 <= column < column_count:
                    data[column] = value
                else:
                    raise IndexOutOfBoundsException("", self)
            self.rows[row] = data
            self.broadcast_changed(
                min(columns), max(columns), 
                row, row)
    
    def updateRowHeading(self, row, heading):
        pass
    
    def updateCellToolTip(self, column, row, value):
        pass
    
    def updateRowToolTip(self, row, value):
        pass
    
    def addGridDataListener(self, listener):
        self._grid_data_listeners.append(listener)
    
    def removeGridDataListener(self, listener):
        try:
            while True:
                self._grid_data_listeners.remove(listener)
        except:
            pass
    
    def broadcast_inserted(self, first_column, last_column, first_row, last_row):
        self.broadcast("rowsInserted", 
            first_column, last_column, first_row, last_row)
    
    def broadcast_removed(self, first_column, last_column, first_row, last_row):
        self.broadcast("rowsRemoved", 
            first_column, last_column, first_row, last_row)
    
    def broadcast_changed(self, first_column, last_column, first_row, last_row):
        self.broadcast("dataChanged", 
            first_column, last_column, first_row, last_row)
    
    def broadcast_heading(self, first_column, last_column, first_row, last_row):
        self.broadcast("dataChanged", 
            first_column, last_column, first_row, last_row)
    
    def broadcast(self, name, first_column, last_column, first_row, last_row):
        ev = GridDataEvent(self, 
                first_column, last_column, 
                first_row, last_row)
        for listener in self._grid_data_listeners:
            try:
                getattr(listener, name)(ev)
            except:
                pass
