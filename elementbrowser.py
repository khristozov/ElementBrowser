#!/usr/bin/env python

#   name : element browser
# author : konstantin hristozov
#   date : march 26, 2013

import os
import sys
import re
import sqlite3
from PyQt4 import QtGui
from PyQt4 import QtCore



FilepathRole = QtCore.Qt.UserRole
SequencePathRole = QtCore.Qt.UserRole + 1
FrameRole = QtCore.Qt.UserRole + 2

class DataSource(object):
    _images = []
    
    def __init__(self, root="/"):
        self.root = root
    
    def setRoot(self, root):
        self.root = root
    
    def root(self):
        return self.root
    
    def images(self):
        return self._images
    
    def clear(self):
        self._images = []
# end DataSource
 
class Entity(object):
    _thumb = None
    _filepath = None
    
    def __init__(self, filepath, thumb=None):
        self._filepath = filepath
        self._thumb = thumb
    
    def setFilepath(self, path):
        self._filepath = path
    
    def setThumb(self, thumb):
        self._thumb = thumb
        
    def filepath(self):
        return self._filepath
    
    def thumb(self):
        return self._thumb
        
        
class Database(DataSource):
    def setRoot(self, root):
        self.root = root
    
    def images(self):
        self.clear()
        return self._images
      
      
class Disk(DataSource):
    def images(self):
        self.clear()
        for i in os.listdir(self.root):
            thumb_path = os.path.join(self.root, i)
            if thumb_path.endswith(".jpg"):
                filepath = ""
                entity = Entity(filepath, thumb_path)                        
                self._images.append(entity) 
        return self._images        
# end Disk

class BasicItem(object):
    _image_width = 128
    
    def __init__(self, parent=None):
        self._parent = None
        self._view = parent
        self._values = {}
        self.setFrame(-1)
        
        if self._view:
            self._model = self._view.model()

    def imageWidth(self):
        return self._image_width
    
    def setImageWidth(self, width):
        self._image_width = width
        
    def view(self):
        return self._view
    
    def data(self, role, column=0):
        return self._values.get(role, None)
    
    def setData(self, role, value, column=0):
        self._values[role] = value
    
    def pixmap(self):
        full = QtGui.QPixmap()
        if not QtGui.QPixmapCache.find(self.filepath(), full):
            l = Loader.loader()
            l.load( self.filepath(), self.view() )
            
            full = QtGui.QPixmap(self._image_width,self._image_width)
            full.fill(QtGui.QColor(50,50,50))
        return full
        
    
    def setFrame(self, frame):
        self.setData(FrameRole, frame)
        
    def frame(self):
        return self.data(FrameRole)
        
    def totalFrames(self):
        return self.pixmap().width()/self._image_width
    
    def setFilepath(self, path):
        self.setData(FilepathRole, path)
        
    def filepath(self):
        return self.data(FilepathRole)
    
    def setSeqPath(self, path):
        self.setData(SequencePathRole, path)
    
    def seqpath(self):
        return self.data(SequencePathRole)

    def setText(self, text):
        self.setData(QtCore.Qt.DisplayRole, text)
    
    def text(self):
        return self.data(QtCore.Qt.DisplayRole)
# end BasicItem

class BasicItemModel(QtCore.QAbstractListModel):
    def __init__(self, parent=None):
        super(BasicItemModel, self).__init__(parent)
        self._items = []
        self._parent = parent
    
    def clear(self):
        self._items = []
    
    def index(self, row, column=0, parent=QtCore.QModelIndex()):
        return self.createIndex(row, column)
    
    def parent(self):
        return self._parent
    
    def hasChildren(self, parent):
        return not parent.isValid()
    
    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._items)
    
    def addItem(self, item):
        self.beginInsertRows(QtCore.QModelIndex(), len(self._items), len(self._items))
        self._items.append( item )
        self.endInsertRows()
    
    def at(self, index):
        return self._items[index.row()]
    
    def setData(self, index, role, value):
        if not index.isValid():
            return
        item = self.at(index)
        item.setData(role, value)
        
    def data(self, index, role):
        if not index.isValid():
            return None
      
        item = self.at(index)
        if role == QtCore.Qt.DecorationRole:
            full = item.pixmap()
            iwidth = item.imageWidth()
            
            total = full.width()/iwidth
            frame = item.data(FrameRole)
            # if initial frame was not set, set it to .5 (middle of the clip)
            if frame == -1:
                frame = .5
            
            i = int(total * frame)
            pix = full.copy(min(iwidth * i, full.width()-iwidth),0,iwidth,iwidth)
            
            return pix
            
        return item.data(role)

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction
    
    def flags(self, index):
        defaultFlags = QtCore.QAbstractListModel.flags(self, index)
        if index.isValid():
            return QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled | defaultFlags
        else:
            return QtCore.Qt.ItemIsDropEnabled | defaultFlags
    
    def mimeTypes(self):
        '''
        types = QtCore.QStringList()
        types << "text/plain"
        return types
        '''
        return ["text/plain"]
    
    def mimeData(self, indexes):
        mimeData = QtCore.QMimeData()
        stream = []
        for index in indexes:
            if index.isValid():
                text = self.data(index, SequencePathRole)
                stream.append(text)
    
        mimeData.setText('\n'.join(stream))
        return mimeData
# end BasicItemModel

    
class ThumbTable(QtGui.QListView):
    def __init__(self, parent=None):
        QtGui.QListView.__init__(self, parent)
        self.setFlow(QtGui.QListView.LeftToRight)
        self.setViewMode(QtGui.QListView.IconMode)
        self.setResizeMode(QtGui.QListView.Adjust)
        self.setUniformItemSizes(True)
        self.setMouseTracking(True)
        self.setDragDropMode(QtGui.QAbstractItemView.DragOnly)
        self.setDragEnabled(True)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        
        self._model = BasicItemModel(self)
        self.setModel( self._model )
    
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000/24.0) # 24 fps
        
        self.connect(self.timer, QtCore.SIGNAL("timeout()"), self.animate)
        self.doubleClicked.connect(self.itemDoubleClicked)
        
        self.current_index = QtCore.QModelIndex()
        self.frame = 0
    
    def itemDoubleClicked(self, index):
        item = self.model().at(index)
        path = item.seqpath()
        # launch favorite player here
          
        
    def animate(self):
        index = self.current_index
            
        if not index.isValid():
            return
        
        item = self.model().at(index)
        width = self.rectForIndex(index).width()
        inc = width / item.totalFrames()

        item.setFrame((self.frame + 1)/float(width))
        self.update(index)

        self.frame = (self.frame + inc) % width + 1
        
    def customEvent(self, event):
        if isinstance(event, ThumbEvent):
            pix = QtGui.QPixmap(event.qimage)
            QtGui.QPixmapCache.insert(event.path, pix)
            self.viewport().update()
        else:
            QtCore.QEvent.customEvent(self, event)
        
    def clear(self):
        self.timer.stop()
        self.current_index = QtCore.QModelIndex()
        self.model().clear()
        self.model().reset()
        
        
    def addItem(self, text, thumbpath, seqpath=''):
        if not self.timer.isActive():
            self.timer.start()
        item = BasicItem(self)
        item.setText(text)
        item.setFilepath(thumbpath)
        item.setSeqPath(seqpath)
        self._model.addItem(item)        
        return item
    
    def mouseMoveEvent(self, event):
        index = self.indexAt(event.pos())
        rect = self.visualRect(index)
        # mouse is over upper half of item: moving = scrubbing
        if (event.pos().y() - rect.y()) > rect.height()/2:
            if not self.timer.isActive():
                self.timer.start()
            if index != self.current_index:
                self.frame = 0
                self.current_index = index
        # mouse is over lower half of item: animated thumbnail at 24 fps
        else:
            # stop timer if active 
            if self.timer.isActive():
                self.timer.stop()
            
            if index.isValid():
                frame = (event.pos().x() - rect.x())
                item = self.model().at(index)
                item.setFrame(frame/float(rect.width()))
                self.update(index)
        
        QtGui.QListView.mouseMoveEvent(self, event)
# end ThumbTable
        
class ThumbEvent(QtCore.QEvent):
    def __init__(self, path='', qimage=QtGui.QImage()):
        QtCore.QEvent.__init__(self, QtCore.QEvent.User)
        self.qimage = qimage
        self.path = path
# end ThumbEvent


class Loader(QtCore.QThread):
    _loader = None
    notify_map = {}
    queue = []
    
    thumbIsReadySignal = QtCore.pyqtSignal()
    
    @classmethod
    def loader(cls):
        if not cls._loader:
            cls._loader = Loader()
        return cls._loader
        
    def load(self, path, notify, index=QtCore.QModelIndex()):
        if path not in self.notify_map.keys():
            self.notify_map[path] = []
            if path in self.queue:
                self.queue.pop( self.queue.index(path) )
            
            self.queue.append(path)
            
        if notify and notify not in self.notify_map[path]:
            self.notify_map[path].append( notify )
        
        if not self.isRunning():
            self.start()
            
    def run(self):
        while self.queue:
            path = self.queue.pop()
            full = QtGui.QImage( path )
            for obj in self.notify_map.pop( path ):  
                QtGui.QApplication.postEvent(obj, ThumbEvent(path, full))
# end Loader
        
class ElementBrowser(QtGui.QMainWindow):
    def __init__(self, root):
        QtGui.QMainWindow.__init__(self)        
        QtGui.QPixmapCache.setCacheLimit(1000000)

        self.root = root

        # data source
        self.source = Disk()

        # thumb widget
        self.table = ThumbTable(self)
        
        # categories widget
        self.categories = QtGui.QListWidget(self)


        
        # layout
        central_widget = QtGui.QSplitter(self)
        central_widget.addWidget(self.categories)
        central_widget.addWidget(self.table)
        central_widget.setSizes([110,820])
        self.setCentralWidget(central_widget)
        self.resize(930,600)
        self.center()

        # init
        for cat in sorted(os.listdir(root)):
            if cat.startswith('.'):
                continue
            item = QtGui.QListWidgetItem(cat)
            self.categories.addItem(item)

        # connections
        self.connect(self.categories, QtCore.SIGNAL("itemClicked(QListWidgetItem*)"), self.updateList)

        self.updateList()

    def updateList(self):
        # add elements
        if not self.categories.currentItem():
            return
        
        self.table.setUpdatesEnabled(False)
        path = os.path.join( self.root, str(self.categories.currentItem().text()))
        self.source.setRoot(path)
        
        self.table.clear()
        
        for i,entity in enumerate( sorted(self.source.images()) ):
            thumbpath = entity.thumb()
            seqpath = entity.filepath()           
            item = self.table.addItem( os.path.basename(thumbpath), thumbpath, seqpath )

        self.table.setUpdatesEnabled(True)
    
    def center(self):
        screen = QtGui.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width()-size.width())/2, 
                  (screen.height()-size.height())/2)    
# end ElementBrowser


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    cwd = os.path.dirname(__file__)+"/images"
    dlg = ElementBrowser(cwd)
    dlg.show()
    
    app.exec_()
