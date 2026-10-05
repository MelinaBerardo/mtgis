from enum import Enum, IntEnum
import json
from urllib import request
from .mtConstants import *
from .mtLayerRelations import *
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
    NULL

)

from qgis import processing

from typing import Optional

class mtLayer():
    LID: 'str'
    layerType: 'int'
    jumpersDisponibles: 'Optional[list[int]]'
    friendlyName: 'Optional[str]'
    featureCache: 'dict[dict]'
    
    def __init__(self,layerId,layerType: 'int',parentLayer: 'Optional[mtLayer|str]'=None,parentField: 'Optional[str]'=None,
                 validSizes:'Optional[list[int]]'=None, parentAreaField: 'Optional[str]'=None,
                 parentInfraField: 'Optional[str]'=None, friendlyName=None,jumpersDisponibles = None,
                 valueMapDict: 'Optional[dict]' = None):

        self.LID=layerId
        self.L=QgsProject().instance().mapLayer(layerId)
        self.parentLayer = parentLayer
        self.parentField = parentField
        self.parentAreaField = parentAreaField
        self.parentInfraField = parentInfraField
        self.validSizes = validSizes
        self.layerType = layerType
        self.friendlyName = friendlyName
        self.jumpersDisponibles = jumpersDisponibles
        self.valueMapDict = valueMapDict
        self.featureCache = None

    def setParentLayer(self, parentLayer: 'mtLayer'):
        self.parentLayer=parentLayer
    
    def setValueMapDict(self, dict: 'dict'):
        self.valueMapDict=dict

    def updateFeature(self, *args, **kwargs):
        return self.L.updateFeature(*args, **kwargs)
    
    def startEditing(self, *args, **kwargs):
        return self.L.startEditing(*args, **kwargs)

    def commitChanges(self, *args, **kwargs):
        return self.L.commitChanges(*args, **kwargs)
    
    def getFeature(self, *args, **kwargs):
        return self.L.getFeature(*args, **kwargs)

    def getFeatures(self, *args, **kwargs):
        return self.L.getFeatures(*args, **kwargs)
    
    def truncate(self, *args, **kwargs):
        return self.L.dataProvider().truncate(*args, **kwargs)
    
    def fields(self, *args, **kwargs):
        return self.L.fields(*args, **kwargs)

    def addFeature(self, *args, **kwargs):
        return self.L.addFeature(*args, **kwargs)

    def deleteFeatures(self, *args, **kwargs):
        return self.L.deleteFeatures(*args, **kwargs)
    
    def uniqueValues(self, fieldName: str):
        return self.L.uniqueValues(self.fields().indexFromName(fieldName))
    
    def getFeatureByUUID(self, uuid: str) -> 'mtFeature':
        query = QgsFeatureRequest(QgsExpression(f"\"{fields.UUID}\" = '{uuid}'"))
        return mtFeature(list(self.getFeatures(query))[0])
    
    def getFeaturesBy(self,field,value,opcional=None) -> 'list[QgsFeature]':
        if type(value) != str:
            queryString=f"\"{field}\" = {value}"
        else:
             queryString=f"\"{field}\" = '{value}'"
        if opcional is not None:
            queryString+=f" {opcional}"
        return self.getFeaturesByFilter(queryString)
    
    def getFeaturesByDistanceAlong(self,field, value, start,end):
        distanceQuery = f' and \"{fields.DISTANCE_ALONG}\" > {start} and \"{fields.DISTANCE_ALONG}\" < {end}'
        return  self.getFeaturesBy(field,value,distanceQuery)
    
    def getFeaturesByFilter(self, filterString):
        return list(self.getFeatures(QgsFeatureRequest().setFilterExpression(filterString)))


    def getIntersectingFeatures(self, layerID: str, feature: 'mtFeature', thisFilter : str = None, excludeIds=None) -> 'list[QgsFeature]':
        context = QgsExpressionContext()
        context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(self.L))
        context.setFeature(feature)

        if thisFilter:
            string = f'overlay_intersects( \'{layerID}\',$id,filter:={thisFilter})'
        else:
            string = f'overlay_intersects( \'{layerID}\',$id)'

        expression = QgsExpression(string)
        foundFids = expression.evaluate(context)
        if excludeIds:
            # removemos los ids de excludeIds
            foundFids=[fid for fid in foundFids if fid not in excludeIds]
        layer = QgsProject().instance().mapLayer(layerID)
        myFeatures = list(layer.getFeatures(QgsFeatureRequest().setFilterFids(foundFids)))
        
        return myFeatures
    
    
    def getNearestFeatures(self, layerID: str, feature: 'QgsFeature', max_distance: float = 0.0, limit:int =None) -> 'list[QgsFeature]':
        context = QgsExpressionContext()
        context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(self.L))
        context.setFeature(feature)
 
        # agregamos el maxdistance como filtro
        paramList=[]
        if max_distance>0:
            paramList.append(f"max_distance:={max_distance}")
        if limit:
            paramList.append(f"limit:={limit}")
        paramString=",".join(paramList)
        string = f"overlay_nearest('{layerID}', fid,{paramString})"
        
        expression = QgsExpression(string)
        foundFids = expression.evaluate(context)
 
        # Si no hay postes encontrados, devolvemos la lista vacia
        if not foundFids:
            return []
 
        layer = QgsProject().instance().mapLayer(layerID)
        myFeatures = list(layer.getFeatures(QgsFeatureRequest().setFilterFids(foundFids)))
 
        return myFeatures
    


    def getContainedFeatures(self, layerID: str, feature: 'mtFeature', thisFilter : str = None, excludeIds=None) -> 'list[QgsFeature]':
        context = QgsExpressionContext()
        context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(self.L))
        context.setFeature(feature)
        thisLayer = QgsProject().instance().mapLayer(layerID)

        if thisFilter:
            string = f'overlay_contains( \'{layerID}\',$id,filter:={thisFilter})'
        else:
            string = f'overlay_contains( \'{layerID}\',$id)'

        expression = QgsExpression(string)
        foundFids = expression.evaluate(context)
        if excludeIds:
            # removemos los ids de excludeIds
            foundFids=[fid for fid in foundFids if fid not in excludeIds]
        myFeatures = list(thisLayer.getFeatures(QgsFeatureRequest().setFilterFids(foundFids)))
        
        return myFeatures

    def selectValidSize(self, fibras: int) -> 'tuple[int,str]':

        possibleValues = self.validSizes
        assert possibleValues is not None
        possibleValues.sort() #Ordeno la lista de menor a mayor

        for fiberCount in possibleValues:
            if(fibras <= fiberCount):
                return fiberCount, 'OK'

        return possibleValues[-1], 'EXCESO FIBRAS'

    def isValidFieldName(self,fieldName):
        return fieldName in [f.name() for f in self.fields()]
    
    def getParentFeature(self,myFeature : 'mtFeature') -> 'mtFeature':
        assert self.parentLayer is not None
        parentLayer = self.parentLayer if type(self.parentLayer) is mtLayer else mtLayers.get(myFeature[self.parentLayer]) #type:ignore
        assert parentLayer is not None
        parentUUID = myFeature.get(self.parentField)
        if parentUUID:
            return mtFeature(parentLayer.getFeaturesBy(fields.UUID,parentUUID)[0])
        else:
            return mtFeature()
    
    def getJumperLength(self,longitud: 'int|float') -> 'tuple[int, bool]':
        # returns the calculated jumper length and an indication whether the length was exceeded or not
        jumpersList = self.jumpersDisponibles
        assert jumpersList is not None
        jumpersList.sort() #Ordeno la lista de menor a mayor

        for largoJumer in jumpersList:
            if(longitud <= largoJumer):
                return largoJumer, False
        
        return JUMPER_EXCEDIDO, True
    
    def clearComputedFields(self):
        self.startEditing()
        fieldsToClear = [fields.ORDEN,fields.NOMBRE,fields.DISTANCE_ALONG,fields.DISTANCE_TOTAL,fields.STATUS_VINCULO,fields.ERROR_FLAGS,fields.ASSEMBLY,fields.ASSEMBLY_FK]
        for thisfeature in self.getFeatures():
            if thisfeature[fields.TIPO]==elementType.HUB:
                continue            
            for field in fieldsToClear:
                if self.isValidFieldName(field):
                    thisfeature[field] = NULL
            self.updateFeature(thisfeature)
        self.commitChanges()
    
    def newFeature(self):
        return mtFeature(self.fields())
    
    def _getIntersectingNodesGeneric(self, feature: 'mtFeature', targetLayer: 'layerIDs', filter = None, onlyUUID=False) -> 'list[QgsFeature]': 
        
        assert self.LID in [layerIDs.Cable, layerIDs.Area, layerIDs.Infra, layerIDs.Manzana, layerIDs.Veredas, layerIDs.Suspensor], f"targetLayer invalido! - {self.LID}"
        additionalFields=None

        # el matchLayer siempre es el MIO,
        match self.LID:
            case layerIDs.Cable:
                relations = relationsNode_Cable
            case layerIDs.Area:
                relations = relationsNode_Area
            case layerIDs.Infra:
                relations = relationsNode_Infra
            case layerIDs.Manzana:
                relations = relationsNode_Manzana
            case layerIDs.Veredas:
                relations = relationsNode_Vereda
                additionalFields=[fields.MANZANA_FK]
            case layerIDs.Suspensor:
                relations = relationsInfra_Suspensor
                

        if targetLayer==layerIDs.Nodo:
            # Si esoy pidiendo devolver nodos, el feature para matchear es un Cables/Area/Infra/Manzana
            # el returnField es un nodo
            matchField=fields.TARGET_UUID
            returnField=fields.NODO_UUID
            returnLayer=layerNode
            additionalFields=None # si devuelvo Nodes, no uso additionalFields
        else:
            # En cambio si estoy pidiendo devolver Targets el matchField y feature es el NODO y el return field es el target
            matchField=fields.NODO_UUID
            returnField=fields.TARGET_UUID 
            returnLayer=self

        foundIntersections = relations.getRelations(matchField, feature[fields.UUID], filter)

        if onlyUUID==False:
            # Si no estoy devolviendo DICTs (onlyUUID) entonces no uso additionalFields
            additionalFields=None

        foundFeats=[]
        # guardamos el valor de returnField en el campo UUID
        for feat in foundIntersections:
            tFeat={fields.UUID:feat[returnField]}
            if additionalFields:
                for addField in additionalFields:
                    tFeat[addField]=feat.get(addField)
            foundFeats.append(tFeat)
        
        if onlyUUID:
            return foundFeats
        else:
            
            myFeatures = []
            for feat in foundFeats:
                aFeature = list(returnLayer.getFeatures(QgsFeatureRequest(QgsExpression(f"\"{fields.UUID}\" = '{feat[fields.UUID]}'"))))
                myFeatures.append(aFeature[0])
            return myFeatures

    def getIntersectingNodes(self, feature: 'mtFeature', filter = None) -> 'list[QgsFeature]':        
        return self._getIntersectingNodesGeneric(feature=feature, targetLayer=layerIDs.Nodo, filter=filter)
        
    def getIntersectingNodesUUID(self, feature: 'mtFeature', filter = None) -> 'list[dict[str]]':        
        return self._getIntersectingNodesGeneric(feature=feature, targetLayer=layerIDs.Nodo, filter=filter, onlyUUID=True)

    def getIntersectingTargetsFromNode(self, feature: 'mtFeature', filter = None) -> 'list[dict[str]]':        
        return self._getIntersectingNodesGeneric(feature=feature, targetLayer=self.LID, filter=filter)
    
    def getIntersectingTargetsFromNodeUUID(self, feature: 'mtFeature', filter = None) -> 'list[dict[str]]':        
        return self._getIntersectingNodesGeneric(feature=feature, targetLayer=self.LID, filter=filter, onlyUUID=True)


    def overrrideAttribute(self, feature: QgsFeature, overrideFeature: QgsFeature):

        overrideString=mtFeature().nullToNone(overrideFeature[fields.OVERRIDES])
        if overrideString is not None and feature is not None:
            try:
                overrideDict=json.loads(overrideString)
                if type(overrideDict) is dict:
                    for k,v in overrideDict.items():
                        if self.isValidFieldName(k) and v is not None:
                            feature[k]=v
                else:
                    QgsMessageLog.logMessage( f"!!!!!! Atributo {overrideFeature[fields.UUID]} con override no DICT!!!", 'mtFuncs.py', level=Qgis.Warning)
            except json.JSONDecodeError as msg:
                QgsMessageLog.logMessage( f"!!!!!! Atributo {overrideFeature[fields.UUID]} con error when decoding DICT!!! {msg}", 'mtFuncs.py', level=Qgis.Critical)

    def updateCacheDict(self, includeMtFeature: bool=False):
        self.featureCache={}
        
        features = self.L.getFeatures()
        field_names = [field.name() for field in self.L.fields()]
        for feature in features:
            rowDict={}
            for field in field_names:
                rowDict[field] = feature[field]
            if includeMtFeature:
                rowDict[fields.MT_FEATURE]=mtFeature(feature)
            self.featureCache[feature[fields.UUID]]=rowDict
    
    def clearCacheDict(self):
        self.featureCache={}

    def batchUpdateField(self, fids: set, fieldName: str, value):
        if fids: 
            idx = self.L.fields().indexOf(fieldName)
            # Si el campo no existe en la tabla mostramos el error y salimos de la función
            if idx == -1:
                QgsMessageLog.logMessage(f"Error: Campo '{fieldName}' no existe en la capa '{self.friendlyName}'.",'mtLayer.py', Qgis.Critical)
                return
            attributeUpdates = {fid: {idx: value} for fid in fids}
            self.startEditing()
            self.L.dataProvider().changeAttributeValues(attributeUpdates)
            self.commitChanges()
    
    def getDuplicatedGeomFetures(self) ->'list[QgsFeature]':
        # returns a list of features in the layer with duplicated geometry.
        tempResult=processing.run("native:deleteduplicategeometries", {'INPUT':self.L,'OUTPUT':'TEMPORARY_OUTPUT'})
        # set of features with duplicates removed (but we dont know which of the two dups are removed)
        tempSet={x[fields.UUID] for x in tempResult['OUTPUT'].getFeatures()}
        self.updateCacheDict()
        # now we do a set difference to find the missing UUIDS between the full set and the removed dups one
        deltaSet=self.featureCache.keys()-tempSet
        # we extract the FIDs of the dup'ed features
        deltaFids=[self.featureCache.get(x).get(fields.FID) for x in deltaSet]
        retList=[]
        # we iterate through the duped features to find the rest
        for thisFeat in self.getFeatures(QgsFeatureRequest().setFilterFids(deltaFids)):
            retList.append(thisFeat)
            # getFeatures returns a list, so we iterate over it.
            retList.extend( self.getIntersectingFeatures(self.LID, thisFeat))
        return retList

    def getDuplicatedVerticesFeatures(self) -> 'list[QgsFeature]':
    # Devuelve una lista de features en la capa que tienen vértices duplicados
        tempResult = processing.run("native:removeduplicatevertices", {
            'INPUT': self.L, # 
            'TOLERANCE': 1e-6,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })
        
        # Creamos un diccionario con {UUID: cantidad_vertices_limpios}
        cleanVertexCount = {
            feat[fields.UUID]: len(list(feat.geometry().vertices())) 
            for feat in tempResult['OUTPUT'].getFeatures()
        }
        retList = []
        for thisFeat in self.getFeatures():
            uuidVal = thisFeat[fields.UUID]
            originalCount = len(list(thisFeat.geometry().vertices()))
            
            # Si el conteo original es mayor al limpio entonces tenia duplicados
            if uuidVal in cleanVertexCount and originalCount > cleanVertexCount[uuidVal]:
                retList.append(thisFeat)
                
        return retList
    
    def getInvalidGeomFeatures(self) -> 'list[QgsFeature]':
        invalidGeomFeats = []
        fidsToDelete = []
        
        for feature in self.getFeatures():
            geom = feature.geometry()
            
            #  Separamos geometrías nulas o vacías para eliminarlas directamente
            if geom.isNull() or geom.isEmpty():
                fidsToDelete.append(feature.id())
                
            #  Separaramos geometrías inválidas para marcarlas como error
            elif not geom.isGeosValid():
                invalidGeomFeats.append(feature)
                
        # Eliminamos directamente los features nulos/vacios de la capa
        if fidsToDelete:
            
            self.L.dataProvider().deleteFeatures(fidsToDelete)
            print(f"[INFO features eliminados] Capa {self.LID}: Se eliminaron {len(fidsToDelete)} features por tener geometría nula o vacía.")
                
        return invalidGeomFeats

class mtFeature(QgsFeature):
    fieldNames: 'list[str]'
    def __init__(self,*args, **kwargs):
        super().__init__( *args, **kwargs)
    
    def get(self, field: 'Optional[str]', errVal=None):
        if field not in self.fields().names():
            return errVal
        else:
            return self[field]
    
    def __str__(self):
        revtal = []
        for fieldName in self.fields().names():
            tVal=self.get(fieldName)
            if tVal:
                revtal.append(f"{fieldName}: {tVal}")
        return "; ".join(revtal)
    
    @staticmethod
    def nullToNone(value, errVal=None):
        return value if value != NULL else errVal
    
    def calculateSegmentLength(self,gananciasTecnicas = 0) -> 'float':
        linearLength = self.geometry().length() * (1+ EFECTO_FLECHA) + gananciasTecnicas
        if self[fields.CANT_FIBRAS]==1:
            totalLength = linearLength + 2 * GANANCIA_JUMPER
        else:
            totalLength = linearLength + 2 * GANANCIA_EN_ELEMENTO
        return round(totalLength,2)
    
    def getNN(self, field: 'Optional[str]', errVal=None):
        tVal=mtFeature.nullToNone(self.get(field))
        return tVal if tVal is not None else errVal
    
    def getPointNthAsFeature(thisFeature: 'mtFeature', nthPoint=0) -> 'mtFeature':
        retFeat=QgsFeature(thisFeature.fields())
        retFeat.setGeometry(QgsGeometry.fromPointXY(thisFeature.geometry().asPolyline()[nthPoint]))
        return mtFeature(retFeat)

layerSuspensor = mtLayer(
                        layerIDs.Suspensor,
                        friendlyName = 'Suspensor',
                        layerType = geomType.LINE
)

layerUnidadesFuncionales = mtLayer(
                        layerIDs.Vivienda,
                        friendlyName = 'unidadesFuncionales',
                        layerType = geomType.NODE
                    )

layerGeneralAtt = mtLayer(
                        layerIDs.atributosGenerlaes,
                        friendlyName = 'atributosGenerlaes',
                        layerType = geomType.TABLE
                    )

layerValueMaps = mtLayer(
                        layerIDs.ValueMapTable,
                        friendlyName = 'value_maps',
                        layerType = geomType.TABLE
                    )

layerNode = mtLayer(
                        layerIDs.Nodo,
                        parentField=fields.PARENT_CABLE,
                        parentAreaField= fields.ASSIGNED_AREA,
                        parentInfraField= fields.ASSIGNED_INFRA,
                        #parentLayer=layerCable,
                        # Esto lo seteamos mas abajo porque el objeto layerCBL_R no lo defini aun
                        layerType = geomType.NODE,
                        friendlyName = 'Nodos',
                        validSizes = [48,144]
                    )

layerCable = mtLayer(
                        layerIDs.Cable,
                        parentLayer=layerNode,
                        parentField=fields.PARENT_NODE,
                        layerType = geomType.LINE,
                        friendlyName = 'Cables',
                        validSizes = [1,32,64,128,256],
                        jumpersDisponibles = [5,75,125,175,250,JUMPER_EXCEDIDO],
                    )

layerArea = mtLayer(
                        layerIDs.Area,
                        parentLayer=layerNode,
                        layerType = geomType.AREA
                    )

layerComentario = mtLayer(
                        layerIDs.Comentario,
                        layerType = geomType.AREA
                    )

layerSEG = mtLayer(
                        layerIDs.Segmento,
                        parentLayer=layerCable,
                        parentField=fields.PARENT_CABLE,
                        friendlyName = 'Segmentos',
                        layerType = geomType.LINE
                    )

layerHerrajes = mtLayer(
                        layerIDs.Herraje,
                        parentField=fields.PARENT_CABLE,
                        parentLayer = layerCable,
                        friendlyName = 'Herrajeria',
                        layerType = geomType.NODE
                    )

layerSplices = mtLayer(
                        layerIDs.Splices,
                        friendlyName = 'Splices',
                        layerType = geomType.TABLE
                    )

layerCableTraces = mtLayer(
                        layerIDs.cableTraces,
                        friendlyName = 'cableTraces',
                        layerType = geomType.LINE
)

layerInfra = mtLayer(
                        layerIDs.Infra,
                        layerType =  geomType.NODE,
                        friendlyName= 'Infraestructura'
)

layerAreaNodeRel = mtLayer(
                        layerIDs.AreaNode,
                        friendlyName = 'Area_Node',
                        layerType = geomType.TABLE
                    )

layerCableNodeRel = mtLayer(
                        layerIDs.CableNode,
                        friendlyName = 'Cable_Node',
                        layerType = geomType.TABLE
                    )

layerInfraNodeRel = mtLayer(
                        layerIDs.InfraNode,
                        friendlyName = 'Infra_Node',
                        layerType = geomType.TABLE
                    )

layerVeredas = mtLayer(
                        layerIDs.Veredas,
                        friendlyName = 'veredas',
                        layerType = geomType.AREA
                    )

layerEjes = mtLayer(
                        layerIDs.eje,
                        friendlyName = 'ejes',
                        layerType = geomType.LINE
                    )

layerTrazaInfra = mtLayer(
                        layerIDs.trazaInfra,
                        friendlyName = 'trazaInfra',
                        layerType = geomType.LINE
                    )

layerManzana = mtLayer(
                        layerIDs.Manzana,
                        friendlyName = 'Manzanas',
                        layerType = geomType.AREA
                    )
layerAssembly = mtLayer(
                        layerIDs.ASY_assembly,
                        friendlyName = 'Assemblies',
                        layerType = geomType.TABLE
                    )

layerAssemblyCondiciones = mtLayer(
                        layerIDs.ASY_condiciones,
                        friendlyName = 'Assembly Conditions',
                        layerType = geomType.TABLE
                    )

layerAssemblyInUse = mtLayer(
                        layerIDs.ASY_inUse,
                        friendlyName = 'Assemblies in Use',
                        layerType = geomType.TABLE
                    )

layerAreasProyectoTasa = mtLayer(
                        layerIDs.AreaProyectoTasa,
                        friendlyName = 'Areas Proyecto Tasa',
                        layerType = geomType.AREA
                    )

layerNode.setParentLayer(layerCable)

mtLayers: 'dict[str,mtLayer]'= {

    layerIDs.Nodo : layerNode,
    layerIDs.Cable : layerCable,
    layerIDs.Area : layerArea,
    layerIDs.Segmento : layerSEG,
    layerIDs.Splices: layerSplices,
    layerIDs.Herraje : layerHerrajes,
    layerIDs.AreaNode: layerAreaNodeRel,
    layerIDs.CableNode : layerCableNodeRel,
}