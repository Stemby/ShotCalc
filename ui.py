#!/usr/bin/env python3

#    ShotCalc Qt Ui
#    Copyright (C) 2013, Spediacci Fabio
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
TODO:
- add support for translations
- add\remove of columns
- insert\remove of rows
- enchance ui
- error handling from shotcalc
- window title
- add icons
"""

from PyQt4.QtGui  import *
from PyQt4.QtCore import *
from PyQt4.QtSql  import *
import sys, json
import shotcalc

class ShotcalcModel(QAbstractTableModel):
  
  def __init__(self, rows):
    QAbstractTableModel.__init__(self)
    self.loadData(rows)
    
  def loadData(self, rows):
    self.movs = list(set(mov for frame, movs in rows for mov, value in movs.items())) 
    self.movs.sort()
    self.rows = list(rows)
      
  def setFramerate(self, framerate):
    self.framerate = int(framerate)
    
  def columnCount(self, index=QModelIndex()):
    if index == QModelIndex():
      return len(self.movs) + 1
    
  def rowCount(self, index=QModelIndex()):
    if index == QModelIndex():
      return len(self.rows)
    
  def headerData(self, section, orientation, role):                                                                                          
    if role == Qt.DisplayRole or orientation == Qt.Vertical:                                                                                 
      if section == 0:                                                                                                                       
        return "Frame"                                                                                                                       
      if section - 1 < len(self.movs):                                                                                                       
        return self.movs[section - 1]                                                                                                        
                                                                                                                                             
  def data(self, index, role):                                                                                                               
    if role in (Qt.DisplayRole, Qt.EditRole):
      frame, movs = self.rows[index.row()]
      if index.column() == 0:
        return frame
      else:
        try:
          return float(movs[self.movs[index.column() - 1]])
        except KeyError:
          pass
          
  def setData(self, index, value, role):
    if role in (Qt.DisplayRole, Qt.EditRole):
      frame, movs = self.rows[index.row()]
      if index.column() == 0:
        self.rows[index.row()] = (value, movs)
      else:
        movs[self.movs[index.column() - 1]] = value
      self.dataChanged.emit(index, index)
      if index.row() == self.rowCount() - 1 and value != None:
        self.insertRow(self.rowCount())
      return True
      
  def insertRows(self, row, count, parent):
    self.beginInsertRows(parent, row, row + count - 1)
    for r in range(row, row + count):
      self.rows.insert(r, (None, dict()))
    self.endInsertRows()
    return True
    
  def insertColumns(self, column, count, parent):
    self.beginInsertColumns(parent, column, column + count - 1)
    for c in range(column, column + count):
      self.movs.insert(c, None)
    self.endInsertColumns()
    return True
  
  def removeRows(self, row, count, parent):
    self.beginRemoveRows(parent, row, row + count - 1)
    for r in range(row, row + count):
      self.rows.remove(r)
    self.endRemoveRows()
    return True
  
  def removeColumns(self, column, count, parent):
    self.beginRemoveColumns(parent, column, column + count - 1)
    for c in range(column, column + count):
      self.movs.remove(c)
    self.endRemoveColumns()
    return True
      
class ProjectModel(ShotcalcModel):
  
  def __init__(self, name, path, framerate, rows):
    ShotcalcModel.__init__(self, rows)
    self.name = name
    self.path = path
    self.framerate = framerate
    self.insertRow(self.rowCount())
  
  def flags(self, index):
    return QAbstractTableModel.flags(self, index) | Qt.ItemIsEditable
  
  def validRows(self):
    for frame, movs in self.rows:
      if frame != None and len(movs) > 0:
        yield frame, movs
  
  def toCamera(self):
    c = shotcalc.Camera(self.framerate, self.movs)
    for frame, movs in self.validRows():
      c.add_step(frame, movs)
    return c
  
  def saveToFile(self):
    if not self.path:
      self.path = QFileDialog.getSaveFileName(mw, "Save project", QDir.currentPath())
    if self.path:
      with open(self.path, "w") as file:
        data = {"name": self.name, "framerate": self.framerate, "data": list(self.validRows())}
        json.dump(data, file)
  
class ProjectModelOut(ShotcalcModel):
  
  def __init__(self, sourceModel):
    ShotcalcModel.__init__(self, [])
    self.sourceModel = sourceModel
    self.reload()
    
  def reload(self):
    c = self.sourceModel.toCamera()
    if len(c.steps) > 0:
      self.loadData(list(c.find_positions()))
    else:
      self.clearAll()
    self.reset()
    
  def changeTab(self, index):
    if index == 1:
      self.reload()
      
  def clearAll(self):
    self.rows, self.movs = [], []
    
class MainWindow(QMainWindow):

  def __init__(self):
    QMainWindow.__init__(self)
    
    self.toolbar = QToolBar()
    new = QAction("New", self.toolbar)
    new.triggered.connect(self.newProject)
    open = QAction("Open", self.toolbar)
    open.triggered.connect(self.openProject)
    save = QAction("Save", self.toolbar)
    save.triggered.connect(self.saveProject)
    saveAll = QAction("Save all", self.toolbar)
    saveAll.triggered.connect(self.saveAllProjects)
    
    for n in (new, open, save, saveAll):
      self.toolbar.addAction(n)
    self.addToolBar(self.toolbar)
    
    self.projTab = QTabWidget()
      
    frame = QFrame()
    frame.setLayout(QVBoxLayout())
    frame.layout().addWidget(self.projTab)
    self.setCentralWidget(frame)
    
  def loadProjectUi(self, model):
    FRAMERATES = [24, 32, 48]
    combo = QComboBox()
    combo.setModel(QStringListModel(list(map(str, FRAMERATES))))
    combo.currentIndexChanged[str].connect(model.setFramerate)
    combo.setCurrentIndex(FRAMERATES.index(model.framerate))
    
    formLay = QFormLayout()
    formLay.addRow("framerate:", combo)
    frame = QFrame()
    frame.setLayout(formLay)
    
    view = QTableView()
    view.verticalHeader().hide()
    view.setModel(model)
    
    frame2 = QFrame()
    frame2.setLayout(QVBoxLayout())
    frame2.layout().addWidget(frame)
    frame2.layout().addWidget(view)
    
    modelOut = ProjectModelOut(model)
    outView = QTableView()
    outView.verticalHeader().hide()
    outView.setModel(modelOut)
    
    ioTab = QTabWidget()
    ioTab.addTab(frame2, "Input")
    ioTab.addTab(outView, "Output")
    ioTab.currentChanged.connect(modelOut.changeTab)
    
    self.projTab.addTab(ioTab, model.name)
    
  def newProject(self):
    name, ok = QInputDialog.getText(self, "New project", "Name:", QLineEdit.Normal)
    if ok and name:
      model = ProjectModel(name, None, 24, [])
      self.addProject(model)
      
  def addProject(self, model):
    projects.append(model)
    self.loadProjectUi(model)
    self.projTab.setCurrentIndex(self.projTab.count() - 1)    
    
  def delProject(self):
    ok = QMessageBox.critical(self, "Delete project", 'Delete project "%s" are you sure?' % self.selProject.currentText(), QMessageBox.Ok | QMessageBox.Cancel)
    if ok == QMessageBox.Ok:
      self.selProject.removeItem(self.selProject.currentIndex())
  
  def saveProject(self):
    p = projects[self.projTab.currentIndex()]
    p.saveToFile()
    
  def saveAllProjects(self):
    for p in projects:
      p.saveToFile()
    
  def openProject(self):
    fileName = QFileDialog.getOpenFileName(self, "Open file", QDir.currentPath())
    if fileName:
      with open(fileName) as file:
        data = json.load(file)
        model = ProjectModel(data["name"], fileName, data["framerate"], data["data"])
        self.addProject(model)
  
if __name__ == "__main__":
  data = [(32, {'dolly': 35, 'pan': 60, 'tilt': 15}),
          (34, {'dolly': 375}),
          (36, {'dolly': 400, 'pan': 90, 'tilt': 0})]
  projects = [ProjectModel("proj1", None, 24, data), ProjectModel("proj2", None, 32, data)]
  
  app = QApplication(sys.argv)
  
  mw = MainWindow()
  
  for p in projects:
    mw.loadProjectUi(p)
  
  mw.resize(600, 300)
  mw.show()
  
  exit(app.exec_())
