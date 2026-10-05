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
    NULL,
)

from qgis import processing

from .mtConstants import *
from .mtOffset import *
from .mtQAQC import *
from .mtHerrajes import *
from .mtSplices import *
from .mtLayer import *
from .mtTree import *


def chunkify(j,n):
    tlist=range(j)
    return [len(tlist[i::n]) for i in range(n)]


def getPuertosIniciales():
   
    layerNode.startEditing()
    areas = layerArea.getFeatures()
    for area in areas:
        
        queryString = f'and \"{fields.FASE}\" = {faseConstruccion.FASE_1}' 
        napsInArea =layerNode.getFeaturesBy(fields.ASSIGNED_AREA,area[fields.UUID],queryString)
        print(len(napsInArea))
        chunks = chunkify(area['demanda'],len(napsInArea))
        i=0
        for nap in napsInArea:
            nap['puertos'] = chunks[i]
            i=i+1
            layerNode.updateFeature(nap)

    layerNode.commitChanges()
    