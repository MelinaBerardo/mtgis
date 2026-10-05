
from .mtConstants import *

import processing
import os
import zipfile

from qgis.utils import (
    iface,
    qgsfunction
)
from qgis.core import (
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsFeatureRequest,
    QgsProject,
    QgsMessageLog,
    QgsGeometry,
    QgsSpatialIndex,
    QgsRectangle,
    Qgis,
    QgsField, # Lo importe para poder agregar campos JMY
    QgsGeometryUtils,
    QgsPoint,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
    QgsVectorFileWriter,
    QgsVectorLayer,
)

import os
import geopandas as gpd


import os
import zipfile

class virtualLayer():
    
    def __init__(self, tableName: 'str', query: 'str'):        

        self.query = query
        self.tableName = tableName        
        self.vlayer = QgsVectorLayer(f"?query={query}", tableName, "virtual")
        self.layer = QgsProject().instance().addMapLayer(self.vlayer)
        
        
    def exportSHP(self):
        

        dir = QgsProject.instance().absolutePath()
      
        export_folder = os.path.join(dir, 'exportKeyCom')
        if not os.path.exists(export_folder):
            os.makedirs(export_folder)

        # QAQC para validar geometrías
        errorGeom = 0
        #errorGeom = self.QAQC()

        # Si hay errores geométricos, no se crea el ZIP
        if errorGeom > 0:
            print('Archivo zip no creado: errorGeom')
        else:
           
            destNodes = os.path.join(export_folder, self.tableName)
            _writerNodes = QgsVectorFileWriter.writeAsVectorFormat(
                self.vlayer, destNodes, 'utf-8', 
                destCRS=QgsCoordinateReferenceSystem("EPSG:3857"), 
                driverName='ESRI Shapefile'
            )
            print(f'SHP guardado en {export_folder}')

            
            createZip(export_folder)

       
        QgsProject.instance().removeMapLayer(self.vlayer)
       

def createZip(export_folder):
    
    zip_path = os.path.join(export_folder, 'exportKeyCom.zip')

    if os.path.exists(zip_path):
        os.remove(zip_path)

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file_name in os.listdir(export_folder):
            file_path = os.path.join(export_folder, file_name)
            
            if not file_name.endswith('.zip'):
                zipf.write(file_path, file_name)

    print(f'Archivo ZIP creado en: {zip_path}')

#**************************************************************************************************************************