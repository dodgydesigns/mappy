'''
Created on 11 Jan. 2019

@author: mullsy
'''
from math import trunc, floor, log
import os
import urllib.request

from PySide2.QtCore import (QPointF, QRect, Qt, QRectF, QEvent)
from PySide2.QtGui import (QImage, QPainter, QPixmap, QBrush)
from PySide2.QtWidgets import QApplication, QMainWindow, QWidget, QGraphicsView, \
    QGraphicsScene


# tile size in pixels
TILE_DIMENSION = 256
ENABLE_CACHE = True
class TileKey():
    '''
    This is used for identifying the required tile and help with caching.
    '''
    def __init__(self, tileZoomIndex, x, y):
    
        self.tileZoomIndex = tileZoomIndex
        self.x = x
        self.y = y
    
    def key(self):
        return '{}_{}_{}'.format(self.tileZoomIndex, self.x, self.y)

    def __hash__(self):
        return hash((self.tileZoomIndex, self.x, self.y))

    def __eq__(self, other):
        return (self.tileZoomIndex, self.x, self.y) == (other.tileZoomIndex, other.x, other.y)

    def __ne__(self, other):
        return not(self == other)

    
class TMSLayer(QWidget):

    def __init__(self, layerName, canvasSize, centreCoordinate, zoom):
        super(TMSLayer, self).__init__()
        
        self.setStyleSheet("background: transparent")
        self.setMouseTracking(True) 
        
        self.layerName = layerName
        self.canvasSize = canvasSize
        self.centreCoordinate = centreCoordinate

        # Make sure map fills canvas window
        while (2**(zoom + 1)*TILE_DIMENSION) < canvasSize.width():
            zoom += 1
        self.calculateTileZoomIndex(zoom)

        self.tilePixmaps = {}
        self.setGeometry(canvasSize.x(), canvasSize.y(), canvasSize.width(), canvasSize.height())
        self.painter = QPainter()
        self.download()

    def mouseMoveEvent(self, event):

        tcX = self.requiredTiles['left']
        tcY = self.requiredTiles['top']
        offsetX = self.canvasSize.width()/2 - (self.centrePoint.x() - tcX) * TILE_DIMENSION
        offsetY = self.canvasSize.height()/2 + (self.centrePoint.y() - (tcY+1)) * TILE_DIMENSION
                
        xTile = tcX + ((event.pos().x()-offsetX)/256)
        yTile = (tcY+1) - ((event.pos().y()-offsetY)/256)
        self.centreCoordinate = self.tileToGeographic(xTile, yTile, self.tileZoomIndex)
#         print('{}, {}'.format(self.centreCoordinate.x(), self.centreCoordinate.y()))
                
    def paintEvent(self, event):

        self.painter.begin(self)
        self.render(self.painter)
        self.painter.setPen(Qt.black)
        self.painter.end()   
        
    def calculateTileZoomIndex(self, zoom):
        
#         if floor(zoom) > 2:
#             self.tileZoomIndex = floor(zoom) -1
#         else:
        self.tileZoomIndex = floor(zoom)

    def updateRasterImage(self, lat, lon, zoom):
        
#         print('{}, {}  {}:{}'.format(lat, lon, self.tileZoomIndex, zoom))
        self.calculateTileZoomIndex(zoom)

#         self.updateCanvasSize(canvasSize)
        newCentre = self.tileToGeographic(lat, lon, self.tileZoomIndex)
#         self.updateCentre(newCentre)
#         self.updateCentre(QPointF(-32.2138204, 115.0387413))
        self.updateZoom(zoom)
   
        
#         tcX = self.requiredTiles['left']
#         tcY = self.requiredTiles['top']
#         offsetX = self.canvasSize.width()/2 - (self.centrePoint.x() - tcX) * TILE_DIMENSION
#         offsetY = self.canvasSize.height()/2 + (self.centrePoint.y() - (tcY+1)) * TILE_DIMENSION
#                 
#         xTile = tcX + ((event.pos().x()-offsetX)/256)
#         yTile = (tcY+1) - ((event.pos().y()-offsetY)/256)
#         self.centreCoordinate = self.tileToGeographic(xTile, yTile, self.zoom)
        
        
#         print('{} {} {}'.format(lat, lon, zoom))
#         oldAnchorPoint = self.geographicToTile(lat, lon, self.zoom)
#         newAnchorPoint = self.geographicToTile(lat, lon, zoom)
#         
#         offset = newAnchorPoint - oldAnchorPoint
#         if offset.x() > 0:
#             print('{}'.format(offset))
#             print('OLD:{} NEW:{}'.format(self.tileToGeographic(oldAnchorPoint.x(), oldAnchorPoint.y(), self.zoom),
#                                          self.tileToGeographic(newAnchorPoint.x(), newAnchorPoint.y(), zoom)))
#             
#         cp = QPointF(len(self.xTiles)/2, len(self.yTiles)/2)
#         tmp = QPointF(cp.x() + offset.x(), cp.y() + offset.y())
# #         print('CP:{} off:{} tmp:{}'.format(self.centrePoint, offset, tmp))
#         self.centreCoordinate = self.tileToGeographic(tmp.x()/256, tmp.y()/256, zoom)
# #         print('tmpX:{} tmpY:{} centreCoord:{}'.format(tmp.x(), tmp.y(), self.centreCoordinate))
#         self.zoom = zoom
#         
#         self.updateTiles(self.canvasSize, self.centreCoordinate, self.zoom)

    def updateZoom(self, zoom):
#         print('updateZoom --- CANVAS:{} CENTRE:{} ZOOM:{}'.format(self.canvasSize, self.centreCoordinate, zoom))
        self.calculateTileZoomIndex(zoom)
        self.download()
        self.update()
        
    def updateCentre(self, centre):
#         print('updateCentre --- CANVAS:{} CENTRE:{} ZOOM:{}'.format(self.canvasSize, self.centreCoordinate, self.tileZoomIndex))
        self.centreCoordinate = centre
#         self.download()
#         self.update()
        
    def updateCanvasSize(self, canvasSize):  
#         print('updateCanvasSize --- CANVAS:{} CENTRE:{} ZOOM:{}'.format(canvasSize, self.centreCoordinate, self.tileZoomIndex))
        self.canvasSize = canvasSize
        self.download()
        self.update()        
        
    def download(self):
        
        self.requiredTiles = self.getTiles()
        
        for xTile in range(self.requiredTiles['left'], self.requiredTiles['right']+1):
            for yTile in range(self.requiredTiles['bottom'], self.requiredTiles['top']+1):
                grab = TileKey(self.tileZoomIndex, xTile, yTile)
                if grab not in self.tilePixmaps:
                    cacheLayerName = self.layerName.split(':')[1]
                    hardDrive = os.path.abspath(os.sep)
                    tilePath = hardDrive + 'cache/{}/{}/{}/{}.png'.format(cacheLayerName, grab.tileZoomIndex, grab.x, grab.y)    
                    if ENABLE_CACHE and os.path.exists(tilePath):
                        self.tilePixmaps[grab] = QPixmap(tilePath)
                    else:
                        path = 'http://localhost:8080/geoserver/' + \
                               'gwc/' + \
                               'service/' + \
                               'tms/' + \
                               '1.0.0/' + \
                               self.layerName + \
                               '@EPSG:4326' + \
                               '@png' + \
                               '/{}/{}/{}.png'.format(grab.tileZoomIndex, grab.x, grab.y)
                        try:
                            contents = urllib.request.urlopen(path).read()
                            img = QImage()
                            img = QImage.fromData(contents, "PNG")
                            pic = QPixmap.fromImage(img)
                            self.tilePixmaps[grab] = pic  
                            if ENABLE_CACHE:
                                if not os.path.exists(hardDrive + 'cache/{}/{}/{}/'.format(cacheLayerName, grab.tileZoomIndex, grab.x)):
                                    os.makedirs(hardDrive + 'cache/{}/{}/{}/'.format(cacheLayerName, grab.tileZoomIndex, grab.x))
                                pic.save(tilePath, 'png')
                        except:
                            pass
#                             print(e)
               
    def render(self, painter):
        '''
        This takes whatever tiles are in the range of tiles for GPS coordinates and fills them IF
        the tile lies within the the canvas size.
        '''       
        tcX = self.requiredTiles['left']
        tcY = self.requiredTiles['top']
        offsetX = self.canvasSize.width()/2 - (self.centrePoint.x() - tcX) * TILE_DIMENSION
        offsetY = self.canvasSize.height()/2 + (self.centrePoint.y() - (tcY+1)) * TILE_DIMENSION
            
        for tileKey, pic in self.tilePixmaps.items():
 
            xPos = (tileKey.x - self.requiredTiles['left']) * TILE_DIMENSION
            yPos = (self.requiredTiles['top'] - tileKey.y) * TILE_DIMENSION
            box = QRect(xPos + offsetX, yPos + offsetY, TILE_DIMENSION, TILE_DIMENSION)
            painter.drawPixmap(box, pic)
            
            # draw grid lines and label tiles
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            painter.setBrush(QBrush(Qt.transparent))
             
            tile = self.tileToGeographic(tileKey.x, tileKey.y, self.tileZoomIndex)
            painter.drawText(QRect(xPos, yPos, 200, 100), 
                              "{},{}\n{:.1f},{:.1f}\n{:.1f},{:.1f}".format(tileKey.x, 
                                                                           tileKey.y, 
                                                                           box.x(),
                                                                           box.y(),
                                                                           tile.x(), 
                                                                           tile.y()))
            painter.drawRect(xPos + offsetX, yPos + offsetY, TILE_DIMENSION, TILE_DIMENSION)
            
        # draw a square at Perth
        pt = self.geographicToTile(-32.2138204, 115.0387413, self.tileZoomIndex)
        painter.drawRect(((pt.x() - self.requiredTiles['left']) * TILE_DIMENSION) + offsetX, 
                         (((self.requiredTiles['top'] - pt.y() + 1)) * TILE_DIMENSION) + offsetY, 10, 10)
        
    def getTiles(self):
        '''
        
        '''
        self.xTiles = range(0, 2**(self.tileZoomIndex + 1))
        self.yTiles = range(0, 2**(self.tileZoomIndex + 0))
                
        self.centrePoint = self.geographicToTile(self.centreCoordinate.x(),
                                                 self.centreCoordinate.y(), 
                                                 self.tileZoomIndex)

        left = trunc(self.centrePoint.x() - self.canvasSize.width() / (TILE_DIMENSION*2))
        right = trunc(self.centrePoint.x() + self.canvasSize.width() / (TILE_DIMENSION*2))
        bottom = trunc(self.centrePoint.y() - self.canvasSize.height() / (TILE_DIMENSION*2))
        top = trunc(self.centrePoint.y() + self.canvasSize.height() / (TILE_DIMENSION*2))
        
        requiredTiles = {'left': left,
                         'right': right,
                         'top': top,
                         'bottom': bottom}  
        
        return requiredTiles

    def getCanvasLocation(self, lat, lng):

        tcX = self.requiredTiles['left']
        tcY = self.requiredTiles['top']
        offsetX = self.canvasSize.width()/2 - (self.centrePoint.x() - tcX) * TILE_DIMENSION
        offsetY = self.canvasSize.height()/2 + (self.centrePoint.y() - (tcY+1)) * TILE_DIMENSION
                
        pt = self.geographicToTile(lat, lng, self.tileZoomIndex)

        x = ((pt.x() - self.requiredTiles['left']) * TILE_DIMENSION) + offsetX
        y = ((self.requiredTiles['top'] - pt.y() + 1) * TILE_DIMENSION) + offsetY
        
        return QPointF(x, y)
    
    def tileToGeographic(self, tx, ty, zoom):
        ''' 
        :param self: 
        :param x: floating point  x coordinate, integer part is the tile number, decimal part is the proportion across that tile
        :param y: floating point  y coordinate, integer part is the tile number, decimal part is the proportion across that tile
        :param zoom: 
        :return: Latitude and longitude in degrees 
        :Note: x,y origin is bottom left, (lat, long) origin is map centre i.e. map is TL (85.05112877, -180) BR (-85.05112877, 180)
                Uses self.zoom as the current zoom level. There are 2^(zoom+1) x tiles and 2^(zoom) y tiles 
        '''
        znx = float(1 << (zoom+1))
        lon = tx / znx * 360.0 - 180.0
        
        zny = float(1 << zoom)
        lat = ty / zny * 180.0 - 90.0
        
        return QPointF(lat, lon)

    def geographicToTile(self, latitude, longitude, zoom):
        '''
        :param self: 
        :param latitude: world coordinates latitude (degrees)
        :param longitude: world coordinates longitude (degrees)
        :param zoom:
        :return: QPointF(x,y) tile coordinates. Integer part is the tile number, decimal part is the proportion across that tile
        :Note: x,y origin is bottom left, (lat, long) origin is map centre i.e. map is TL (85.05112877, -180) BR (-85.05112877, 180)
            Uses self.zoom as the current zoom level. There are 2^(zoom+1) x tiles and 2^(zoom) y tiles 
        '''
        zn = float(1 << zoom)
        tx = float(longitude + 180.0) / 360.0
        ty = float(latitude + 90.0) / 180.0

        return QPointF(tx * zn * 2, ty * zn)

''' ######################### TEST HARNESS ######################### '''
class TMSTester(QMainWindow):
    def __init__(self, width, height):
        super(TMSTester, self).__init__(None)
        
        self.setStyleSheet("background: transparent")
        
        self.canvasSize = QRectF(QPointF(0, 0), QPointF(width, height))
        
        self.view = QGraphicsView()
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.scene = QGraphicsScene(0, 0, width, height, self.view)
        self.view.setScene(self.scene)
        
        self.centreCoordinate = QPointF(-32.2138204, 115.0387413)
        self.zoom = 3
        self.mapLayer = TMSLayer('CRUSE:World_Bathymetric_Heightmap', 
                                 self.canvasSize,
                                 self.centreCoordinate, 
                                 3)
        self.mapLayerHandle = self.scene.addWidget(self.mapLayer)
        self.setCentralWidget(self.view)
        self.mapLayer.setFocus()
                
    def mouseMoveEvent(self, event):

        tcX = self.mapLayer.requiredTiles['left']
        tcY = self.mapLayer.requiredTiles['top']
        offsetX = self.mapLayer.canvasSize.width()/2 - (self.mapLayer.centrePoint.x() - tcX) * TILE_DIMENSION
        offsetY = self.mapLayer.canvasSize.height()/2 + (self.mapLayer.centrePoint.y() - (tcY+1)) * TILE_DIMENSION
                
        xTile = tcX + ((event.pos().x()-offsetX)/256)
        yTile = (tcY+1) - ((event.pos().y()-offsetY)/256)
        self.mapLayer.centreCoordinate = self.mapLayer.tileToGeographic(xTile, yTile, self.mapLayer.tileZoomIndex)
        print('{}'.format(self.mapLayer.centreCoordinate))
        
    def mousePressEvent(self, event):

        tcX = self.mapLayer.requiredTiles['left']
        tcY = self.mapLayer.requiredTiles['top']
        offsetX = self.mapLayer.canvasSize.width()/2 - (self.mapLayer.centrePoint.x() - tcX) * TILE_DIMENSION
        offsetY = self.mapLayer.canvasSize.height()/2 + (self.mapLayer.centrePoint.y() - (tcY+1)) * TILE_DIMENSION
                
        xTile = tcX + ((event.pos().x()-offsetX)/256)
        yTile = (tcY+1) - ((event.pos().y()-offsetY)/256)
        centreCoordinate = self.mapLayer.tileToGeographic(xTile, yTile, self.mapLayer.tileZoomIndex)
        
        self.mapLayer.updateCentre(centreCoordinate)
            
    def wheelEvent(self, event):
        '''
        Only used for zooming.
        '''
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.viewport().installEventFilter(self)

        if event.delta() > 0:
            self.zoom *= 1 + (event.delta()/120) * 0.1
            scale = 1 + (self.zoom % self.mapLayer.tileZoomIndex)
        else:
            self.zoom *= (1 + (event.delta()/120) * 0.1)
            scale = 1 / (1 + (self.zoom % self.mapLayer.tileZoomIndex))

        rasterZoom = self.mapLayer.tileZoomIndex + 2**(floor(log(self.zoom, 2)) + 0) - 1

            
        if scale <= 2:
            self.view.scale(scale, scale)
        else:
            self.view.scale(1/scale, 1/scale)
            self.mapLayer.updateZoom(rasterZoom)
            
            
        print('zoom:{} scale:{} raster:{}'.format(self.zoom, scale, rasterZoom))
   
    def eventFilter(self, qobject, event):
        if (event.type() == QEvent.Wheel):
            return True
        else:
            return False
        
    def keyPressEvent(self, event):
 
        if event.key() == Qt.Key_Left:
            self.centreCoordinate = QPointF(self.mapLayer.centreCoordinate.x(), self.mapLayer.centreCoordinate.y()-self.mapLayer.tileZoomIndex)
            self.mapLayer.updateCentre(self.centreCoordinate)
        if event.key() == Qt.Key_Right:
            self.centreCoordinate = QPointF(self.mapLayer.centreCoordinate.x(), self.mapLayer.centreCoordinate.y()+self.mapLayer.tileZoomIndex)
            self.mapLayer.updateCentre(self.centreCoordinate)
        if event.key() == Qt.Key_Up:
            self.centreCoordinate = QPointF(self.mapLayer.centreCoordinate.x()+self.mapLayer.tileZoomIndex, self.mapLayer.centreCoordinate.y())
            self.mapLayer.updateCentre(self.centreCoordinate)
        if event.key() == Qt.Key_Down:
            self.centreCoordinate = QPointF(self.mapLayer.centreCoordinate.x()-self.mapLayer.tileZoomIndex, self.mapLayer.centreCoordinate.y())
            self.mapLayer.updateCentre(self.centreCoordinate)
        if event.key() == Qt.Key_Z:
            self.zoom *= 1.3
            self.mapLayer.updateZoom(self.zoom)
        if event.key() == Qt.Key_X:
            self.zoom /= 1.3
            self.mapLayer.updateZoom(self.zoom)
        if event.key() == Qt.Key_P:
            self.centreCoordinate = QPointF(-32.2138204, 115.0387413)   
            self.mapLayer.updateCentre(self.centreCoordinate)
        if event.key() == Qt.Key_A:
            self.centreCoordinate = QPointF(-35.09138204, 138.07387413)  
            self.mapLayer.updateCentre(self.centreCoordinate)           
        if event.key() == Qt.Key_M:
            self.centreCoordinate = QPointF(0, 0) 
            self.mapLayer.updateCentre(self.centreCoordinate)
            
        self.mapLayer.updateCanvasSize(self.canvasSize)
        


if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    w = TMSTester(3840, 2160)
    w.resize(3840, 2160)
    w.show()
    sys.exit(app.exec_())