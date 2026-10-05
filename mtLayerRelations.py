from enum import Enum, IntEnum
import json
from .mtConstants import *
from qgis.core import (

    QgsProject,
    QgsFeatureRequest,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeatureIterator,
    QgsFeature,
    QgsMessageLog,
    QgsGeometry,
    Qgis,
    QgsVectorLayer,
    NULL

)

from qgis import processing

from typing import Optional

class mtRelations():
    tableName: 'str'
    query: 'str'
    rowDict: 'dict'
    relationsList: 'list[dict]'
    
    def __init__(self,tableName: 'str',query: 'str'):

        self.tableName = tableName
        self.query = query
        self.rowDict = {}
        self.relationsList = []

    def updateRelations(self):
        self.rowDict = {}
        self.relationsList = []
        #proyectInstance = QgsProject.instance()
        vlayer = QgsVectorLayer(f"?query={self.query}", self.tableName, "virtual")
        #layer = proyectInstance.addMapLayer(vlayer)
        features = vlayer.getFeatures()
        field_names = [field.name() for field in vlayer.fields()]

        for feature in features:
            for field in field_names:
                self.rowDict[field] = feature[field]
            self.relationsList.append(self.rowDict)
            self.rowDict = {}
        
        #proyectInstance.removeMapLayer(layer)

    def getRelations(self,campoBusqueda : 'str',datoPedido : 'str', filter = None) -> list[dict]:
        
        if filter is None:
            relations = [j for j in self.relationsList if j[campoBusqueda] == datoPedido]
        
        else:
            relations = [j for j in self.relationsList if j[campoBusqueda] == datoPedido and filter(j)]
        return relations

### Query definitions

nodeArea_query = f""" 
select Areas.uuid as {fields.TARGET_UUID},
		Nodos.uuid as {fields.NODO_UUID},
		Nodos.nivel as {fields.NODO_NIVEL},
		Areas.nivel as {fields.AREA_NIVEL},
        Areas.tipo as {fields.AREA_TIPO},
		Nodos.tipo as {fields.NODO_TIPO}
from Areas ,Nodos
where intersects(Areas.geometry,Nodos.geometry) 
"""

nodeCable_query = f"""
select Cables.uuid as {fields.TARGET_UUID},
		Nodos.uuid as {fields.NODO_UUID},
		Nodos.nivel as {fields.NODO_NIVEL},
		Cables.nivel as {fields.CABLE_NIVEL},
		intersects(start_point(Cables.geometry),Nodos.geometry)  as {fields.START_POINT},
		intersects(end_point(Cables.geometry),Nodos.geometry)  as {fields.END_POINT}
from Cables,Nodos
where intersects(Cables.geometry,Nodos.geometry) 
"""

nodeInfra_query=f"""
select nodoInfraestructura.uuid as {fields.TARGET_UUID},
		Nodos.uuid as {fields.NODO_UUID},
		Nodos.colocacion as {fields.NODO_COLOCACION},
		nodoInfraestructura.tipoInfraestructura as {fields.INFRA_TIPO}
from nodoInfraestructura,Nodos
where intersects(nodoInfraestructura.geometry,Nodos.geometry)
"""       

nodeManzana_query=f"""
select Manzana.UUID as {fields.TARGET_UUID},
		Nodos.uuid as {fields.NODO_UUID}
from Manzana,Nodos
where intersects(Manzana.geometry,Nodos.geometry)
"""     

nodeVereda_query=f"""
select Vereda.UUID as {fields.TARGET_UUID},
        Vereda.manzana_FK as {fields.MANZANA_FK},
		Nodos.uuid as {fields.NODO_UUID}
from Vereda,Nodos
where intersects(Vereda.geometry,Nodos.geometry)
"""     

infraSuspensor_query=f"""
select NodoInfraestructura.uuid as {fields.NODO_UUID},
		Suspensor.uuid as {fields.TARGET_UUID}
from NodoInfraestructura,Suspensor
where intersects(NodoInfraestructura.geometry,Suspensor.geometry) AND NodoInfraestructura.tipoInfraestructura = 10;
"""     



cableInfra_query = f"""
select Cables.uuid as {fields.CABLE_UUID},
       Cables.nivel as {fields.CABLE_NIVEL},
       nodoInfraestructura.uuid as {fields.INFRA_UUID}
from Cables, nodoInfraestructura
where intersects(Cables.geometry, nodoInfraestructura.geometry)
"""

##################################

relationsNode_Area = mtRelations(
                        'node_area',
                        nodeArea_query
                    )
relationsNode_Cable = mtRelations(
                        'node_cable',
                        nodeCable_query
                    )
relationsNode_Infra = mtRelations(
                        'node_infra',
                        nodeInfra_query
                    )
relationsNode_Manzana = mtRelations(
                        'node_manzana',
                        nodeManzana_query
                    )
relationsNode_Vereda = mtRelations(
                        'node_vereda',
                        nodeVereda_query
                    )
relationsInfra_Suspensor = mtRelations(
                        'infra_suspensor',
                        infraSuspensor_query
                    )

relationsCable_Infra = mtRelations(
                        'cable_infra',
                        cableInfra_query
                    )