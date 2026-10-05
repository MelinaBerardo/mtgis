import uuid
import re
import ast

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

from .mtCallTimer import mtCallTimer

from qgis import processing
from .mtCableTraces import mtCableTrace
from .mtGenAtt import mtGenAtt
from .mtConstants import *
from .mtOffset import *
from .mtQAQC import *
from .mtSplices import *
from .mtLayer import *
from .mtTree import *
from .keycomSQL import *
from .mtKeycom import *
from .mtOrder import mtOrder
from .mtAuxFuncs import *
from math import ceil
from anytree import PreOrderIter, RenderTree, PostOrderIter, search
from itertools import groupby, chain
import json
import ast
from collections import defaultdict

import sqlite3
import os
from sqlite3 import OperationalError
from PyQt5 import QtWidgets

def applyDefaultFieldValues(layerObj: mtLayer):

    filteredValues = layerValueMaps.getFeaturesBy(fields.CAPAS,layerObj.friendlyName, f'and {fields.OVERRIDES} is not NULL')
    layerObj.startEditing()
    for value in filteredValues:
        featuresToChange = layerObj.getFeaturesBy(value[fields.CAMPO],value[fields.VALUE])
        for feature in featuresToChange:
            layerObj.overrrideAttribute(feature,value)
            layerObj.updateFeature(feature)

    layerObj.commitChanges()

def linkFeatures():
    # #timer=mtCallTimer('linkFeatures')
    # timerLFA=mtCallTimer('LFA')
    # timerLFI=mtCallTimer('LFI')
    # timerLFB=mtCallTimer('LFB')
    # #timer.print_lap('start')
    layerCable.startEditing()
    layerNode.startEditing()
    #timer.print_lap('startEditing')
    cables = layerCable.getFeatures()
    nodos = layerNode.getFeatures()
    allCables = []
    allNodes = []
    #timer.print_lap('getFeatures')

    for cable in cables:
        mtFeature(cable)
        allCables.append((layerCable,cable,cable[fields.LEVEL],1)) # [(mtLayer,mtFeature,level,OrdenEntreNivel)]
    # timer.print_lap('load cables')

    for nodo in nodos:
        mtFeature(nodo)
     #   timerLFA.start_lap()
        linkFeatureArea(layerNode,nodo)
     #   timerLFA.mark_lap()
     #   timerLFI.start_lap()
        linkFeatureInfra(layerNode,nodo)
     #   timerLFI.mark_lap()
     #   timerLFB.start_lap()
        linkFeatBlock(layerNode,nodo)
     #   timerLFB.mark_lap()
        allNodes.append((layerNode,nodo,nodo[fields.LEVEL],2)) # [(mtLayer,mtFeature,level,OrdenEntreNivel)]
    #timer.print_lap('load and link nodos')
    #timerLFA.print_stats()
    #timerLFI.print_stats()
    #timerLFB.print_stats()


    allFeatures = allCables + allNodes
    SortedFeatures = sorted(allFeatures,key=lambda x: (x[2],x[3]))
    # #se recorren los Cables y los nodos en orden Primero los cables y luego los nodos de ese nivel

    #timer.print_lap('start linkFeatureNetwork loop')

    for feat in SortedFeatures:
        linkFeatureNetwork(feat[0],feat[1]) # le paso el mtLayer y el mtFeature

    #timer.print_lap('end linkFeatureNetwork loop')

    # #linkSlacks()
    linkSuspensionWires()
    #timer.print_lap('end linkSuspensionWires')
    layerCable.commitChanges()
    layerNode.commitChanges()
    #timer.print_lap('commit Finished')

def linkFeatBlock(layerObj: mtLayer, myFeature: mtFeature):
    #Funcion que asocia los nodos a sus manzanas por su vereda
    errors = 0
    parentFeats = []
    assert layerObj.LID == layerIDs.Nodo
    
    #Busco la vereda asociada por interseccion.Todos las CTOs tienen que estar arriba de una vereda
    if myFeature[fields.TIPO] == elementType.CTO and myFeature[fields.FASE]==faseConstruccion.FASE_1:
        parentFeats=layerVeredas.getIntersectingTargetsFromNodeUUID(myFeature)
    elif myFeature[fields.TIPO] == elementType.CTO and myFeature[fields.FASE]==faseConstruccion.FASE_MDU:
        try:
            manzanaMDU_FK = layerManzana.getIntersectingTargetsFromNodeUUID(myFeature)[0][fields.UUID]
            myFeature[fields.MANZANA_FK] = manzanaMDU_FK
        except IndexError:
            errors = statusType.SIN_MANZANA
    else:
        errors = statusType.OK
        featureErrors = mtFeature.nullToNone(myFeature[fields.ERROR_FLAGS],0)
        allErrors = featureErrors | errors
        myFeature[fields.ERROR_FLAGS] = allErrors
        myFeature[fields.STATUS_VINCULO] = allErrors.getStatus()
        layerObj.updateFeature(myFeature)
        return

  
    
    if (len(parentFeats)==1): #hay un solo area de mismo nivel
        #Completo el campo de y vereda manzana_FK
        if myFeature[fields.TIPO] == elementType.CTO and myFeature[fields.FASE]==faseConstruccion.FASE_1:
            myFeature[fields.MANZANA_FK]=parentFeats[0][fields.MANZANA_FK]
            myFeature[fields.VEREDA_FK]=parentFeats[0][fields.UUID]

    elif (len(parentFeats)==0) and myFeature[fields.TIPO] == elementType.CTO and myFeature[fields.FASE]==faseConstruccion.FASE_1:
        errors = statusType.SIN_VEREDA

    elif (len(parentFeats)>1):
        errors = statusType.ERROR_MULTIPLE_VEREDAS

    if (errors == 0):
        errors = statusType.OK
        #statusMsg=f"Se actualizo el feature: {myFeature.id()}"

    # Limpio errores anteriores de vereda/manzana
    featureErrors = mtFeature.nullToNone(myFeature[fields.ERROR_FLAGS], 0)

    featureErrors = featureErrors & ~statusType.SIN_VEREDA
    featureErrors = featureErrors & ~statusType.ERROR_MULTIPLE_VEREDAS

    # Agrego el error actual
    allErrors = featureErrors | errors

    myFeature[fields.ERROR_FLAGS] = allErrors
    myFeature[fields.STATUS_VINCULO] = allErrors.getStatus()
    statusMsg= f"""LINK Capa: {layerObj.LID} - Se actualizo el feature con errores:ID: {myFeature.id()} | {myFeature[fields.STATUS_VINCULO]} """
    layerObj.updateFeature(myFeature)

    if errors != statusType.OK :
        iface.messageBar().pushMessage("Asociar Feature a manzanas", statusMsg, level=Qgis.Warning)
    
def linkSlacks():

    layerHerrajes.startEditing()

    for slack in layerHerrajes.getFeaturesBy(fields.TIPO,herraje.GANANCIA_TECNICA):
        errors = 0
        cablesIntersect = layerCable.getIntersectingFeatures(layerIDs.Cable,slack,f"{fields.LEVEL}={networkLevel.SECUNDARIO} or {fields.LEVEL}={networkLevel.TRONCAL}")
        nodoInfraIntersect = layerInfra.getIntersectingFeatures(layerIDs.InfraNode,slack)
        slack[fields.ASSIGNED_INFRA]=nodoInfraIntersect[0][fields.UUID] if len(nodoInfraIntersect)==1 else None

        if len(cablesIntersect)==1:
            slack[fields.PARENT_CABLE]=cablesIntersect[0][fields.UUID]
        if len(cablesIntersect)>1:
            if slack[fields.PARENT_CABLE] != NULL:
                slack[fields.PARENT_CABLE]=slack[fields.PARENT_CABLE] 
            else:
                errors = errors | statusType.SELECCION_MANUAL_PADRE

        if len(cablesIntersect)==0:
            errors = errors | statusType.NO_COINCIDE_PADRE

        if (errors == 0):
            errors = statusType.OK
        #concatenar todos los errores
        slack[fields.STATUS_VINCULO] = errors.getStatus()

        statusMsg= f"""LINK Capa: {layerHerrajes.LID} -
                Se actualizo el feature con errores:ID: {slack.id()}
                | {slack[fields.STATUS_VINCULO]} """

        if errors != statusType.OK:
            iface.messageBar().pushMessage("Asociar Feature", statusMsg, level=Qgis.Warning)

        layerHerrajes.updateFeature(slack)


    layerHerrajes.commitChanges()
def linkFeatureInfra(layerObj: mtLayer, myFeature: mtFeature) -> QgsFeature:

    errors = 0
    assert layerObj.LID == layerIDs.Nodo
    parentFeats = []

    # Recupero los errores actuales del nodo
    featureErrors = mtFeature.nullToNone( myFeature[fields.ERROR_FLAGS],0)

    # Limpio errores anteriores relacionados con infraestructura
    featureErrors &= ~statusType.SIN_INFRAESTRUCTURA
    featureErrors &= ~statusType.ERROR_MULTIPLE_INFRA

    # El POP y los nodos con colocación libre no necesitan infraestructura
    if (myFeature[fields.LEVEL] == networkLevel.CENTRAL  or myFeature[fields.COLOCACION] == colocacion.LIBRE):    
        myFeature[layerObj.parentInfraField] = None
        allErrors = featureErrors

        if allErrors == 0:
            allErrors = statusType.OK

        myFeature[fields.ERROR_FLAGS] = allErrors
        myFeature[fields.STATUS_VINCULO] = allErrors.getStatus()

        layerObj.updateFeature(myFeature)
        return

    # Busco infraestructura que intersecte con el nodo
    parentFeats = layerInfra.getIntersectingTargetsFromNodeUUID(
        myFeature,
        filter=lambda infra:
        infra[fields.INFRA_TIPO] == myFeature[fields.COLOCACION]
    )

    # Si no intersecta ninguna infraestructura,
    # busco la más cercana dentro de la distancia permitida
    if len(parentFeats) == 0:

        cercanos = layerInfra.getNearestFeatures(
            layerInfra.LID,
            myFeature,
            max_distance=DIST_MAX_INTRAPOSTE,
            limit=1
        )

        for infra in cercanos:
            if infra[fields.INFRA_TIPO] == myFeature[fields.COLOCACION]:
                parentFeats = [
                    {
                        fields.UUID: infra[fields.UUID]
                    }
                ]
                break

    # Analizo la cantidad de infraestructuras encontradas
    if len(parentFeats) == 1:

        myFeature[layerObj.parentInfraField] = (
            parentFeats[0][fields.UUID]
        )

    elif len(parentFeats) == 0:

        errors |= statusType.SIN_INFRAESTRUCTURA
        myFeature[layerObj.parentInfraField] = None

    elif len(parentFeats) > 1:

        errors |= statusType.ERROR_MULTIPLE_INFRA
        myFeature[layerObj.parentInfraField] = None

    # Si no hubo errores de infraestructura, queda OK
    if errors == 0:
        errors = statusType.OK

    # Agrego el resultado actual a los demás errores del nodo
    allErrors = featureErrors | errors

    myFeature[fields.ERROR_FLAGS] = allErrors
    myFeature[fields.STATUS_VINCULO] = allErrors.getStatus()

    statusMsg = (
        f"LINK Capa: {layerObj.LID}\n"
        f"Se actualizó el feature con errores: ID: {myFeature.id()}\n"
        f"| {myFeature[fields.STATUS_VINCULO]}"
    )

    layerObj.updateFeature(myFeature)

    if errors != statusType.OK:
        iface.messageBar().pushMessage(
            "Asociar Feature to Infra",
            statusMsg,
            level=Qgis.Warning
        )
        
def linkFeatureArea(layerObj: mtLayer, myFeature: mtFeature):
    excludeTypes = [elementType.POP,elementType.CE_ACCESO,elementType.CE_ALIMENTACION,elementType.CE_EXT,elementType.GANANCIA_TECNICA_ACCESO,elementType.GANANCIA_TECNICA_ALIMENTACION,elementType.PC] # Estos tipos no se asocian a un area de mismo nivel
    errors = 0
    parentFeats = []
    assert layerObj.LID == layerIDs.Nodo

    #Features que no se asocian a un area de mismo nivel. 
    if myFeature[fields.TIPO] in excludeTypes:
        errors = statusType.OK
        featureErrors = mtFeature.nullToNone(myFeature[fields.ERROR_FLAGS],0)
        allErrors = featureErrors | errors
        myFeature[fields.ERROR_FLAGS] = allErrors
        myFeature[fields.STATUS_VINCULO] = allErrors.getStatus()
        layerObj.updateFeature(myFeature)
        return

    if myFeature[fields.TIPO] in [elementType.CTO,elementType.HUB]:
        if(myFeature[fields.TIPO] == elementType.CTO and myFeature[fields.FASE]==faseConstruccion.FASE_MDU):
            parentFeats=layerArea.getIntersectingTargetsFromNodeUUID(myFeature,filter=lambda a: a[fields.AREA_NIVEL] == myFeature[fields.LEVEL] and a[fields.AREA_TIPO] == areaType.MDU)
        elif myFeature[fields.FASE]==faseConstruccion.FASE_1:
            parentFeats=layerArea.getIntersectingTargetsFromNodeUUID(myFeature,filter=lambda a: a[fields.AREA_NIVEL] == myFeature[fields.LEVEL])
        
        
        if len(parentFeats) == 1:
            myFeature[layerObj.parentAreaField] = parentFeats[0][fields.UUID]
            errors = statusType.OK

        elif len(parentFeats) == 0:
            myFeature[layerObj.parentAreaField] = None
            errors = statusType.SIN_AREA_DE_MISMO_NIVEL

        elif len(parentFeats) > 1:
            myFeature[layerObj.parentAreaField] = None
            errors = statusType.ERROR_MULTIPLES_AREAS


        featureErrors = mtFeature.nullToNone(myFeature[fields.ERROR_FLAGS], 0)

        featureErrors = featureErrors & ~statusType.SIN_AREA_DE_MISMO_NIVEL
        featureErrors = featureErrors & ~statusType.ERROR_MULTIPLES_AREAS

        allErrors = featureErrors | errors

        myFeature[fields.ERROR_FLAGS] = allErrors
        myFeature[fields.STATUS_VINCULO] = allErrors.getStatus()
        statusMsg= f"""LINK Capa: {layerObj.LID} - Se actualizo el feature con errores:ID: {myFeature.id()} | {myFeature[fields.STATUS_VINCULO]} """

    layerObj.updateFeature(myFeature)
    if errors != statusType.OK :
        iface.messageBar().pushMessage("Asociar Feature to Areas", statusMsg, level=Qgis.Warning)

def linkFeatureNetwork(layerObj: mtLayer,myFeature: mtFeature):

    #Toma nodos y cables y los asocia a traves del snap. La asociacion siempre se hace teniendo en
    #cuenta el nivel del elemento de red que estas asociando.

    featureId=myFeature[fields.UUID]
    errors = 0
    parentFeats = []

    if myFeature[fields.LEVEL] == networkLevel.CENTRAL:
        # el nivel 1 (el POP) no se asocia a cables
        errors = statusType.OK
        featureErrors = mtFeature.nullToNone(myFeature[fields.ERROR_FLAGS],0)
        allErrors = featureErrors | errors
        myFeature[fields.ERROR_FLAGS] = allErrors
        myFeature[fields.STATUS_VINCULO] = allErrors.getStatus()
        layerObj.updateFeature(myFeature)
        return

    assert type(layerObj.parentLayer) is mtLayer
    assert layerObj.parentField is not None

    parentLayer = layerObj.parentLayer


    #Relacion para cables
    if layerObj.layerType == geomType.LINE:

        if QgsGeometry.isEmpty(myFeature.geometry()):
        # Los cables puede tener geometrias vacias si el diseñador borra
        #todos los nodos por eso las controlo
            thisLayer = layerObj.L
            thisLayer.startEditing()
            thisLayer.deleteFeature(myFeature[fields.FID])
            thisLayer.commitChanges()
            iface.messageBar().pushMessage(
                        "linkFeature",
                        f"Feature con geometria vacía con ID:{featureId} fue borrada",
                        level=Qgis.Critical
                        )
            return

        #Se pueden realizar derivaciones en todos los cables multifibra.
        
        # Multifibra: se relacionan con un nodo de un nivel superior, a excepcion de las derivaciones que se relacionan a un nodo de su mismo nivel
        # Jumpers:jumpers se pueden vincular con un HUB(un nivel superior) o a una CTO (mismo nivel).
        # la logica del filtro es igual para ambos casos 

        # aca uso la misma capa (cable) para pedir los Noos que la tocan
        parentFeats=layerObj.getIntersectingNodesUUID(myFeature,
                            filter=lambda n: (((n[fields.NODO_NIVEL] == myFeature[fields.LEVEL]-DISTANCELVL) and (n[fields.START_POINT]== 1))
                                                or 
                                                ((n[fields.NODO_NIVEL] == myFeature[fields.LEVEL]) and (n[fields.START_POINT]) == 1)) #Derivaciones
                            )
    #Relaciion para nodos
    elif layerObj.layerType == geomType.NODE:

            #CE,HUB: Se vinculan a un cable de su mismo nivel. Se relacion en cualquier punto del cable excepto en el start point
            if myFeature[fields.TIPO] in [elementType.CE_ACCESO,elementType.CE_ALIMENTACION,elementType.GANANCIA_TECNICA_ACCESO,elementType.GANANCIA_TECNICA_ALIMENTACION,elementType.PC,elementType.HUB,elementType.CE_EXT]:
                parentFeats=parentLayer.getIntersectingTargetsFromNodeUUID(myFeature,
                                                                filter = lambda n: ((n[fields.CABLE_NIVEL] == myFeature[fields.LEVEL])
                                                                                and 
                                                                                (n[fields.START_POINT] == 0 or n[fields.END_POINT] == 1 ))
                                                            )
                
            #CTO: Se vinculan a un cable de su mismo nivel. Se relacion en unicamente en el end point del cable
            elif myFeature[fields.TIPO] in [elementType.CTO]:                
                parentFeats=parentLayer.getIntersectingTargetsFromNodeUUID(myFeature,
                                                                filter = lambda n: (n[fields.CABLE_NIVEL] == myFeature[fields.LEVEL]and n[fields.END_POINT] == 1 ))
            
            

    if (len(parentFeats)==1): #hay un solo nodo de nivel superior
        myFeature[layerObj.parentField]=parentFeats[0][fields.UUID]


    elif (len(parentFeats)==0):
         errors = statusType.NO_COINCIDE_PADRE

    elif (len(parentFeats)>1):
        errors = statusType.SELECCION_MANUAL_PADRE
        for posibleParent in parentFeats:
            if myFeature[layerObj.parentField]==posibleParent[fields.UUID]:
                errors = 0
                break

    if (errors == 0):
        errors = statusType.OK
        #statusMsg=f"Se actualizo el feature: {myFeature.id()}"

    else:
        # Poner en blanco el campo padre
        myFeature[layerObj.parentField] = None

    #concatenar todos los errores
    featureErrors = mtFeature.nullToNone(myFeature[fields.ERROR_FLAGS],0)
    featureErrors = featureErrors & ~statusType.NO_COINCIDE_PADRE
    featureErrors = featureErrors & ~statusType.SELECCION_MANUAL_PADRE
    allErrors = featureErrors | errors
    myFeature[fields.ERROR_FLAGS] = allErrors
    myFeature[fields.STATUS_VINCULO] = allErrors.getStatus()

    statusMsg= f"""LINK Capa: {layerObj.LID} -
                Se actualizo el feature con errores:ID: {myFeature.id()}
                | {myFeature[fields.STATUS_VINCULO]} """

    layerObj.updateFeature(myFeature)

    if errors != statusType.OK:
        iface.messageBar().pushMessage("Asociar Feature", statusMsg, level=Qgis.Warning)

    featureErrors = mtFeature.nullToNone(myFeature[fields.ERROR_FLAGS], 0)

def setEndPoint(myTree: mtTree):
    relationsNode_Cable.updateRelations()
    layerNode.startEditing()
    for thisNode in myTree.getNodesAsList(tipoFilter=geomType.NODE):
        tempFeat=thisNode.getFeature()
        tempFeat[fields.IS_ENDPOINT]=thisNode.isEndPoint
        layerNode.updateFeature(tempFeat)
    layerNode.commitChanges()


def setDistanceAlong (targetLayer: mtLayer):
    targetLayer.startEditing()
    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(targetLayer.L))
    expression = QgsExpression(f'''line_locate_point(geometry(get_feature(
                               \'{targetLayer.parentLayer.LID}\',
                               \'{fields.UUID}\',"{targetLayer.parentField}")),$geometry)''')

    for feature in targetLayer.getFeatures():
        if targetLayer.isValidFieldName(fields.DISTANCE_ALONG):
            context.setFeature(feature)
            feature[fields.DISTANCE_ALONG] = round(mtFeature.nullToNone(expression.evaluate(context),0),2)
            targetLayer.updateFeature(feature)

    targetLayer.commitChanges()


def setCompleteDistanceAlong(myTree): # Agrega los Distance along al POP a todos los nodos

    rootNode=myTree.buildTree()
    layerNode.startEditing()


    for nodo in PreOrderIter(rootNode):
        if nodo.root != nodo and nodo.root != nodo.parent and nodo.tipo == geomType.NODE:

            if nodo.parent.parent.distance == NULL:
                nodo.parent.parent.distance = 0
                nodo.parent.parent.distanceTotal = 0

            nodo.distanceTotal = nodo.distance + nodo.parent.parent.distanceTotal

            mtlayer = nodo.getLayer()
            feat = nodo.getFeature()
            feat[fields.DISTANCE_TOTAL] =  round(mtFeature.nullToNone(nodo.distanceTotal,0),2)
            mtlayer.updateFeature(feat)

    layerNode.commitChanges()

def numberAccAlim(myTree:mtTree, updateNames:bool=False):
    rootNode=myTree.getRootNode()
    layerCable.startEditing() 
    layerNode.startEditing()

    myTree.clearOrder(filter=filterAccAlim, updateFeatures=True)

# Me paro en el POP
#   Numero los cables hijos por centena empezando en 100 en nivel N+1
# Bajo al nivel de cable
#   Itero por los nodos hijos del cable numerados por distance along pero EMEPZANDO el Contador por mismo nivel del cable que estoy
#   En base a la numeracion del padre en el mismo nivel sumandole 1,2,3
# Bajo al nivel del nodo
#   Itero por los cables hijos numerados por centana al en nivel N+1 del nodo
#   EXCEPTO Si el nodo es ENDPOINT, el Contador de cables que normalmente itera de 100-200-300, ahora itera de 0-100-200


    myNodes=PreOrderIterSorted(rootNode,childiter=distAlongAndDescendantsRev,filter_= filterCentralAccAlim)
    
    node:mtNode
    for node in myNodes:
        endpoint=node.isEndPoint
        if node.tipoNodo==elementType.POP:
            node.updateMtOrder(mtOrder(0),True)
            endpoint=False
        
        child:mtNode
        
        if node.tipo==geomType.LINE:
            baseOrder=node.mtOrder.value
            counter=node.mtOrder.getLastOrder()      
            for child in distAlongSort(node.children):
                if child.constructionPhase!=faseConstruccion.DESPLEGADO:
                    counter+=1                 
                    child.updateMtOrder(mtOrder(baseOrder).setLastOrder(counter),True)
                else:
                    # For built cables update the order from the name field
                    child.updateMtOrder(mtOrder(0).setOrderFromDelimString(str(child.featName)),True)
                #print(f"line: {node.name} - Line {child.name} - {child.mtOrder} - {child.orderNumber}")
                if updateNames:
                    child.featName=child.mtOrder.getName()
                    myFeat=child.getFeature()
                    myFeat[fields.NOMBRE]=child.featName
                    child.updateFeature(myFeat)

        elif node.tipo == geomType.NODE:
            baseOrder = node.mtOrder.value

            # Fin del principal: endpoint de nivel 1 (el cable hijo del POP termina acá)
            finPrincipal = endpoint and node.mtOrder.level == 1

            counter = 0 if (endpoint and not finPrincipal) else mtOrder.MAJOR_MULT

            for child in fiberCountAndTotalLengthSortRev(node.children):
                if not filterAccAlim(child):
                    continue

                if child.constructionPhase != faseConstruccion.DESPLEGADO:
                    # Alimentación nunca continúa la numeración del padre
                    if counter == 0 and child.nivelNodo == networkLevel.RED_ALIMENTACION:
                        counter = mtOrder.MAJOR_MULT

                    child.updateMtOrder(mtOrder(baseOrder).appendOrder(counter), True)
                    counter += mtOrder.MAJOR_MULT

                else:
                    child.updateMtOrder(mtOrder(0).setOrderFromDelimString(str(child.featName)), True)

                if updateNames:
                    child.featName = child.mtOrder.getName()
                    myFeat = child.getFeature()
                    myFeat[fields.NOMBRE] = child.featName
                    child.updateFeature(myFeat)
                    
    layerNode.commitChanges()
    layerCable.commitChanges()
 


    
def jumperGroupSort(items, jumperGroupDict) -> list[mtNode]:

    items = list(items)

    if not items:
        return []

    # Armar las parejas según overlap.
    # En caso de empate, desempatar por chirality.
    groupedItems = buildJumperPairs(items,jumperGroupDict)

    orderedItems = []

    for groupItems in groupedItems:
        orderedItems.extend(groupItems)

    return orderedItems



def standardizeOverlaps(
    overlaps: dict,
    absoluteTolerance: float = OVERLAP_ABSOLUTE_TOLERANCE,
    relativeTolerance: float = OVERLAP_RELATIVE_TOLERANCE
) -> dict:

    if not overlaps:
        return {}

    sortedOverlaps = sorted(
        [
            (pair, overlap)
            for pair, overlap in overlaps.items()
            if overlap > 0
        ],
        key=lambda item: item[1],
        reverse=True
    )

    standardizedOverlaps = overlaps.copy()

    if not sortedOverlaps:
        return standardizedOverlaps

    groups = []

    currentGroup = [sortedOverlaps[0]]
    groupMax = sortedOverlaps[0][1]

    for pair, overlap in sortedOverlaps[1:]:

        absoluteDifference = groupMax - overlap

        relativeDifference = (
            absoluteDifference / groupMax
            if groupMax > 0
            else 0
        )

        if (
            absoluteDifference <= absoluteTolerance
            and
            relativeDifference <= relativeTolerance
        ):
            currentGroup.append(
                (pair, overlap)
            )

        else:
            groups.append(currentGroup)

            currentGroup = [
                (pair, overlap)
            ]

            groupMax = overlap

    groups.append(currentGroup)

    # Todos los overlaps similares toman
    # el máximo del grupo.
    for group in groups:

        groupMax = max(
            overlap
            for _, overlap in group
        )

        for pair, _ in group:
            standardizedOverlaps[pair] = groupMax

    return standardizedOverlaps
def generatePairings(indexes):

    indexes = list(indexes)

    if not indexes:
        yield []
        return

    if len(indexes) == 1:
        yield [(indexes[0],)]
        return

    first = indexes[0]

    # Si tenemos una cantidad impar de jumpers,
    # probar la posibilidad de que first quede solo.
    #
    # El jumper solo se agrega SIEMPRE al final.Porque el primer splitter del HUB se tiene que llenar primero
    if len(indexes) % 2 != 0:

        for remainingPairing in generatePairings(indexes[1:]):
            yield [*remainingPairing,(first,)]

    # Probar first emparejado con cada uno de los demás.
    for i in range(1, len(indexes)):

        second = indexes[i]
        remainingIndexes = (indexes[1:i]+indexes[i + 1:])
        for remainingPairing in generatePairings(remainingIndexes):
            yield [(first, second), *remainingPairing]

def getPairScore(indexA, indexB, items, overlaps):

    pairKey = (
        min(indexA, indexB),
        max(indexA, indexB)
    )

    overlap = overlaps.get(pairKey, 0)

    chiralityA = items[indexA].chirality
    chiralityB = items[indexB].chirality

    chiralityDifference = abs(
        chiralityA - chiralityB
    )

    chiralityDistance = min(
        chiralityDifference,
        360 - chiralityDifference
    )

    return (
        overlap,
        -chiralityDistance
    )
def getPairingScore(pairing, items, overlaps):

    pairScores = []

    for group in pairing:

        # Ignorar el jumper que quedó solo.
        if len(group) == 1:
            continue

        indexA, indexB = group

        pairScore = getPairScore(
            indexA,
            indexB,
            items,
            overlaps
        )

        pairScores.append(pairScore)

    # Primero evaluar la mejor pareja,
    # después la segunda mejor, etc.
    pairScores.sort(reverse=True)

    return tuple(pairScores)
               
def buildJumperPairs(items,jumperGroupDict):
        
    items = list(items)
    #el input de este metodo es la salida del model groupJumpers, es la capa de cables con un campo jumperList que tiene la lista de jumpers que se intersectan 
   
    #Si hay 0 o 1 jumper, no hay pares posibles.
    if len(items) <= 1:
        return [items]

    if len(items) == 2:
        return [items]
    # Obtener todos los overlaps entre los jumpers de este HUB.


    pairOverlaps = {}

    #recorre todas las combinaciones posibles de pares de elementos de items, sin comparar un elemento consigo mismo y sin repetir pares.
    for i in range(len(items)):
        for j in range(i + 1, len(items)):

            uuidA = items[i].name
            uuidB = items[j].name

            #está armando una especie de tabla de superposiciones entre todos los jumpers del grupo
            pairOverlaps[(i, j)] = getJumperOverlap(uuidA,uuidB,jumperGroupDict)

    # Si hay más de dos intersecciones reales,
    # considerar equivalentes los overlaps parecidos.

    #Me quedo con los mayores a 0, es decir, los que realmente se intersectan.
    intersectingPairCount = sum(overlap > 0    for overlap in pairOverlaps.values())
    
    # if intersectingPairCount > 2:
    #     pairOverlaps = standardizeOverlaps(pairOverlaps, absoluteTolerance=OVERLAP_ABSOLUTE_TOLERANCE, relativeTolerance=OVERLAP_RELATIVE_TOLERANCE)
    if intersectingPairCount > 2:

      

        pairOverlaps = standardizeOverlaps(
            pairOverlaps,
            absoluteTolerance=OVERLAP_ABSOLUTE_TOLERANCE,
            relativeTolerance=OVERLAP_RELATIVE_TOLERANCE
        )

     
    # Generar todas las combinaciones posibles de pares de índices.
    indexes = range(len(items))

    possibilities = generatePairings(indexes)

    bestPairing = max(possibilities,key=lambda pairing: getPairingScore(pairing,items,pairOverlaps))

    return [
        [
            items[index]
            for index in group
        ]
        for group in bestPairing
    ]


def buildJumperGroupDict(jumpersTable):

    overlapDict = defaultdict(dict)

    
    for feat in jumpersTable.getFeatures():

        jumperUuid = str(feat["UUID"])
        rawList = feat["jumperList"]

        #NO siempre va a haber 
        if rawList is None:
            continue

        try:
            jumperList = json.loads(str(rawList))
        except (json.JSONDecodeError, TypeError):
            continue

        for relation in jumperList:

            otherUuid = relation.get("UUID")
            overlap = relation.get("overlap", 0)

            if not otherUuid:
                continue

            try:
                overlap = float(overlap)
            except (TypeError, ValueError):
                overlap = 0

            otherUuid = str(otherUuid)

            # Guardar la relación en ambos sentidos.
            overlapDict[jumperUuid][otherUuid] = max(
                overlap,
                overlapDict[jumperUuid].get(otherUuid, 0)
            )

            overlapDict[otherUuid][jumperUuid] = max(
                overlap,
                overlapDict[otherUuid].get(jumperUuid, 0)
            )

    return dict(overlapDict)


    
def getJumperOverlap(uuidA, uuidB, jumperGroupDict):
    #Esa función busca en jumperGroupDict cuánto overlap hay entre dos UUID.
    return jumperGroupDict.get(uuidA, {}).get(uuidB,0)
    
    
def distribucionChildSort(items,jumperGroupDict) -> list[mtNode]:

    # Solamente reordena por jumperList los cables que salen
    # directamente de un HUB.

    # Para cualquier otra parte del árbol conserva el orden original:
    # heightSortRev.

    items = list(items)

    if not items:
        return []

    parent = items[0].parent

    # Solamente cambiar el orden de los hijos directos de un HUB.
    if ( parent is not None and parent.tipo == geomType.NODE and parent.tipoNodo == elementType.HUB):
        return jumperGroupSort( items,jumperGroupDict)

    # En el resto del árbol se mantiene el comportamiento original.
    return heightSortRev(items)

def numberDistribucion(myTree: mtTree):

    myTree.buildTree()

    layerCable.startEditing()
    layerNode.startEditing()

    # myTree.clearOrder(filter=filterDistribucion,updateFeatures=True)
    # las CTOs se ordenan desde el HUB con numero de ordern de 2 coordenadas (digito mayo para numero de rama y menor para numero de caja / jumpler)
    
    # Ejecutar el modelo de Processing para tener la tabla de jumpers agrupados. Esto es necesario para poder ordenar los jumpers porque si dos jumpers van para un mismo lado tienen que tener el mismo pelo(pedido de Fernanda).
    result = processing.run(JUMPER_TABLE,{"jumperstable": "memory:"})
    jumpersTable = result["jumperstable"]
    jumperGroupDict = buildJumperGroupDict(jumpersTable)
    myHubs = myTree.getNodesAsList(tipoFilter=geomType.NODE,tipoNodoFilter=elementType.HUB,)

    for hub in myHubs:
        hubFeat = hub.getFeature()
        
        if hubFeat[fields.BLOCK_CHILD_ORDEN]:
            continue
                
        myNodes = PreOrderIterSorted(hub,childiter=lambda items: distribucionChildSort(items,jumperGroupDict),filter_=filterDistribucion,stop=stopStayInHub)
        node:mtNode
        hubChildOrder=mtOrder.MAJOR_MULT
        for node in myNodes:
            if node.parent.tipoNodo==elementType.HUB:
                # Es un cable que sale del HUB
                node.updateMtOrder(mtOrder(0).appendOrder(hubChildOrder),True)
                #print(f"{node.name} - {hubChildOrder} - {node.parent.name}")
                hubChildOrder+=mtOrder.MAJOR_MULT

            if node.tipo==geomType.NODE:
                # children are cables
                baseOrder=node.mtOrder.value
                counter=0 
                for child in node.children:
                    child.updateMtOrder(mtOrder(baseOrder).appendOrder(counter),True)
                    #print(f"{child.name} - {counter} - {child.mtOrder}")
                    counter+=mtOrder.MAJOR_MULT

            elif node.tipo==geomType.LINE:
                #children are nodes
                baseOrder=node.mtOrder.value
                counter=node.mtOrder.getLastOrder()
                for child in node.children:
                    counter+=1
                    child.updateMtOrder(mtOrder(baseOrder).setLastOrder(counter),True)
                    #print(f"{child.name} - {counter} - {child.mtOrder}")
                        
    layerNode.commitChanges()
    layerCable.commitChanges()



def linkNetParents(myTree: mtTree):

    myTree.buildTree()

    layerCable.startEditing()

    myHubs = myTree.getNodesAsList(tipoFilter=geomType.NODE,tipoNodoFilter=elementType.HUB)

    for hub in myHubs:

        myCables = PreOrderIterSorted(hub,childiter=distAlongTotSort,filter_=filterCablesDistribucion)

        for cableNode in myCables:

            feat = cableNode.getFeature()

            # Buscar CTOs aguas arriba de este cable
            parentCTOs = [
                node
                for node in cableNode.ancestors
                if node.tipo == geomType.NODE
                and node.tipoNodo == elementType.CTO
            ]

            if parentCTOs:
                # La PRIMERA CTO desde el HUB define la rama
                netParentNode = parentCTOs[0]
            else:
                # Si todavía no pasó por una CTO, es jumper1
                netParentNode = hub

            feat[fields.NETPARENT_FK] = netParentNode.name

            layerCable.updateFeature(feat)

    layerCable.commitChanges()
    
def demandAggregation(myTree: mtTree):

    #Esta funcion toma las cajas A y agrega las fibras hacia arriba
    rootNode=myTree.getRootNode()
    layerNode.startEditing()
    layerCable.startEditing()

    nodeLvls = [networkLevel.RED_ALIMENTACION]

    for nodo in PostOrderIter(rootNode):

        if nodo.is_root:
            continue

        thisFeat = nodo.getFeature()
        thisLayer = nodo.getLayer()

        childPorts = 0
        childFibers = 0

        for child in nodo.children:

            childPorts += mtFeature.nullToNone(child.demand,0)
            childFibers += mtFeature.nullToNone(child.usedFibers,0)


        areaFibers = 0
        #Las areas HUB ya tienen calculado la cantidad de fibras calculadas,por eso heredamos de las areas las fibras calculadas
        if (nodo.tipo == geomType.NODE and thisFeat[fields.TIPO] == elementType.HUB):
            areasFibers = layerArea.getFeaturesBy(fields.UUID,thisFeat[fields.ASSIGNED_AREA])
            try:
                areaFibers = mtFeature.nullToNone(areasFibers[0][fields.CANT_FIBRAS],0)
            except (IndexError, KeyError) as e:
                print(f"Error occurred while retrieving area fibers for HUB:{thisFeat[fields.UUID]} {e}")
                areaFibers = 0

        localDemand = (mtFeature.nullToNone(thisFeat[fields.PUERTOS],0)
            if nodo.nivelNodo not in nodeLvls
            and nodo.tipo == geomType.NODE
            else 0
        )

        nodo.demand = localDemand + childPorts
        nodo.usedFibers = areaFibers + childFibers


        if (nodo.nivelNodo in nodeLvls and nodo.tipo == geomType.NODE):

            thisFeat[fields.PUERTOS] = nodo.demand

        if thisFeat[fields.TIPO] == elementType.HUB:
            thisFeat[fields.FIB_CALC] = layerArea.getFeaturesBy(fields.UUID,thisFeat[fields.ASSIGNED_AREA])[0][fields.CANT_FIBRAS]
            thisFeat[fields.FIB_ASIG] = mtFeature.nullToNone(thisFeat[fields.FIB_RESERV],0) + max(thisFeat[fields.FIB_CALC],SPLITTERS_HUB)
        
        nodesFibRes = [elementType.PC,elementType.GANANCIA_TECNICA_ACCESO,elementType.GANANCIA_TECNICA_ALIMENTACION,elementType.CE_ACCESO,elementType.CE_ALIMENTACION]
        if thisFeat[fields.TIPO] in nodesFibRes:
            thisFeat[fields.FIB_ASIG] = mtFeature.nullToNone(thisFeat[fields.FIB_RESERV],0) + mtFeature.nullToNone(thisFeat[fields.FIB_CALC],0)
        
        thisLayer.updateFeature(thisFeat)

    layerNode.commitChanges()
    layerCable.commitChanges()


def nameDistribucion(myTree):
    rootNode=myTree.getRootNode()
    layerManzana.updateCacheDict()

    processing.run(ORDEN_CTO_MANZANA,{})
    processing.run(ORIENT_CTO,{})

    layerNode.startEditing()
    layerCable.startEditing()

    nombreHub = mtGenAtt.getValue(mtGenAtt.attName.POP)

    node:mtNode
    
    myNodes=PreOrderIterSorted(rootNode,childiter=heightSortRev,filter_= filterNodesDistribucion)
    for node in myNodes:
        nombre=None
        thisFeat=node.getFeature()
        if node.tipoNodo == elementType.CTO:
            manzana=layerManzana.featureCache.get(thisFeat[fields.MANZANA_FK])
            manzanaID = manzana[fields.ID] if manzana  else None
            #Concatena nombre de la central, el manzana ID, 5 por tipo CTO y el orden dentro de la manzana.
            try:
                if thisFeat[fields.FASE]== faseConstruccion.FASE_1:
                    nombre = f'{nombreHub}{manzanaID}5{int(thisFeat[fields.ORDEN_MANZANA]):02d}'
                elif thisFeat[fields.FASE]== faseConstruccion.FASE_MDU:
                    nombre = f'{nombreHub}{manzanaID}6{int(thisFeat[fields.ORDEN_MANZANA]):02d}'
            except (ValueError, TypeError) as e:
                print(f"Error occurred while formatting nombre for CTO:{thisFeat[fields.UUID]} {e}")
            node.featName=nombre
            thisFeat[fields.NOMBRE]=nombre
            node.updateFeature(thisFeat)

    myNodes=PreOrderIterSorted(rootNode,childiter=heightSortRev,filter_= filterCablesDistribucion)
    for node in myNodes:
        nombre=None
        thisFeat=node.getFeature()
        if node.numFibers == 1:
            #nomenclado jumpers
            try:
                jumperChildren: 'list[mtNode]'
                jumperChildren=list(node.children)
                nombre = jumperChildren[0].featName if len(jumperChildren) == 1 else None
            except (ValueError, TypeError) as e:
                print(f"Error occurred while formatting nombre for jumper:{thisFeat[fields.UUID]} {e}")
            node.featName=nombre
            thisFeat[fields.NOMBRE]=nombre
            node.updateFeature(thisFeat)
    
    layerManzana.clearCacheDict()
    layerNode.commitChanges()
    layerCable.commitChanges()


def linkUFtoArea():

    layerUnidadesFuncionales.startEditing()

    for area in layerArea.getFeaturesBy(fields.LEVEL,networkLevel.DISPERSION,f'and {fields.TIPO} = {areaType.SDU}'):
        ufs=layerArea.getIntersectingFeatures(layerIDs.Vivienda,area)
        for uf in ufs:
            if uf[fields.CLASIFICACION_UF] == clasificacionUF.SDU:
                uf[fields.ASSIGNED_AREA]=area[fields.UUID]
            layerUnidadesFuncionales.updateFeature(uf)

    for area in layerArea.getFeaturesBy(fields.LEVEL,networkLevel.DISPERSION,f'and {fields.TIPO} = {areaType.MDU}'):
        ufs=layerArea.getIntersectingFeatures(layerIDs.Vivienda,area)
        for uf in ufs:
            if uf[fields.CLASIFICACION_UF] == clasificacionUF.MDU:
                uf[fields.ASSIGNED_AREA]=area[fields.UUID]
            layerUnidadesFuncionales.updateFeature(uf)
    layerUnidadesFuncionales.commitChanges()

def calculateFibers(layerObj):

    layerObj.startEditing()

    for cable in layerObj.getFeatures():
        
        #posbiles casos de cables multifibra esto esta determinado por TASA
        #Cable 256 ---> 200 
        # Cable 128 ---> 100
        # cable 32 ---> 16
        if cable[fields.CANT_FIBRAS] ==256:
            if cable[fields.FIB_CALC] > 200: 
                status = statusType.FIBRAS_EXCEDIDAS
            elif cable[fields.FIB_CALC] < 100 : 
                status = statusType.FIBRAS_SOBREDIMENSIONADAS
            else:
                status = statusType.OK
        
        elif cable[fields.CANT_FIBRAS] ==128:
            if cable[fields.FIB_CALC] > 100: 
                status = statusType.FIBRAS_EXCEDIDAS
            elif cable[fields.FIB_CALC] < 48 : 
                status = statusType.FIBRAS_SOBREDIMENSIONADAS
            else:
                status = statusType.OK
        elif cable[fields.CANT_FIBRAS] ==64:
            if cable[fields.FIB_CALC] > 48: 
                status = statusType.FIBRAS_EXCEDIDAS
            elif cable[fields.FIB_CALC] < 16 : 
                status = statusType.FIBRAS_SOBREDIMENSIONADAS
            else:
                status = statusType.OK
        elif cable[fields.CANT_FIBRAS] ==32:
            if cable[fields.FIB_CALC] > 16: 
                status = statusType.FIBRAS_EXCEDIDAS
            elif cable[fields.FIB_CALC] < 1 : 
                status = statusType.FIBRAS_SOBREDIMENSIONADAS
            else:
                status = statusType.OK 
        elif cable[fields.CANT_FIBRAS] ==1:           
            status = statusType.OK
        try:
            cable[fields.STATUS_CAPACIDAD] = status.getStatus()
        except Exception as e:
            print(f"Error al asignar el estado de fibras para el cable con UUID {cable[fields.UUID]}: {e}")                
                
        layerObj.updateFeature(cable)

    layerObj.commitChanges()


def updateJumperCableFields():
    layerCable.startEditing()

    # The length of all primary cables predetermined as jumpers from the calculateFibers function is updated. JMY
    for jumper in layerCable.getFeaturesBy(fields.CANT_FIBRAS,1):
        newLength, exceeded=layerCable.getJumperLength(jumper[fields.LONG_TOTAL])
        jumper[fields.LONG_TOTAL] = newLength
        jumper[fields.FASE] = layerNode.getFeaturesBy(fields.UUID,jumper[fields.NODO_FIN])[0][fields.FASE]
        # if length is exceeded, we need to use MULTIFIBRE cable.
        jumper[fields.TIPO]=cableType.JUMPER
        layerCable.updateFeature(jumper)

    layerCable.commitChanges()

def calculateCE(layerObj):

    layerObj.startEditing()

    for cierre in layerObj.getFeaturesBy(fields.TIPO,elementType.CE_ACCESO,elementType.CE_ALIMENTACION):

        totalFib = cierre[fields.FIB_CALC]
        if totalFib != 0:
            cierre[fields.CAPACIDAD_DERIV], status = layerObj.selectValidSize(totalFib)
        else:
           cablePadre =  layerObj.parentLayer.getFeature(cierre[fields.PARENT_CABLE])
           cierre[fields.CAPACIDAD_DERIV], status = layerObj.selectValidSize(cablePadre[fields.CANT_FIBRAS])
        layerObj.updateFeature(cierre)

    layerObj.commitChanges()


def executeScriptsFromFile(c,filename):
    # Open and read the file as a single buffer
    fd = open(filename, 'r')
    sqlFile = fd.read()
    fd.close()
    # all SQL commands (split on ';')
    sqlCommands = sqlFile.split(';')

    # Execute every command from the input file
    for command in sqlCommands:
        # This will skip and report errors
        # For example, if the tables do not yet exist, this will skip over
        # the DROP TABLE commands
        try:
            c.execute(command)
        except OperationalError as msg:
            print("Command skipped: ", command, "\nError: ", msg )

def closeLayer(saveChanges= True):
    layer= QgsProject.instance().mapLayers().values()
    for lyr in layer:

        if lyr.isEditable():
            print(f"Cerrando capa {lyr.name()} - Guardar cambios: {saveChanges}")
            if saveChanges:
                lyr.commitChanges()
            else:
                lyr.rollBack()

def ajustarCampos():

    dbName = "db-3.gpkg"
    folder = str(os.path.dirname(os.path.abspath(__file__)))
    correctFieldsDir = os.path.join(folder, "correct-fields.sql")

    dir = QgsProject.instance().absolutePath()
    project = QgsProject.instance()
    projectName = QgsProject.instance().fileName()

    print(projectName)

    project.clear()  # Close project
    QtWidgets.QApplication.processEvents()

    outconn = sqlite3.connect(os.path.join(dir, dbName))
    outconn.enable_load_extension(True)
    outconn.execute("select load_extension('mod_spatialite')")

    oc = outconn.cursor()

    # Leer archivo SQL completo-- evita problemas con ;
    with open(correctFieldsDir, "r", encoding="utf-8") as sqlFile:
        sqlScript = sqlFile.read()

    # Ejecutar script completo
    oc.executescript(sqlScript)

    outconn.commit()

    oc.close()
    outconn.close()

    project.read(os.path.join(dir, projectName))

def updateDemandaArea():

    layerArea.startEditing()

    for area in layerArea.getFeaturesBy(fields.LEVEL,networkLevel.DISPERSION):
        total_hpMDU = 0
        total_hpSDU = 0
#          #print(f'PRUEBA:{area[fields.UUID]}') (Me trajo todos los uuid de las areas que le pedi)
        for eje in layerEjes.getFeaturesBy(fields.ASSIGNED_AREA, area[fields.UUID]):
            if eje[fields.ASSIGNED_AREA] == area[fields.UUID]:
                total_hpMDU += eje[fields.DEMANDA_MDU]
                total_hpSDU += eje[fields.DEMANDA_SDU]

        area[fields.DEMANDA_MDU] = total_hpMDU
        area[fields.DEMANDA_SDU] = total_hpSDU
        layerArea.updateFeature(area)
    layerArea.commitChanges()



def nameAreas():

    nombreAlimentador =  layerGeneralAtt.getFeaturesBy(fields.NOMBRE,'Alimentador')[0][fields.VALUE]
    nombreHub = layerGeneralAtt.getFeaturesBy(fields.NOMBRE,'POP')[0][fields.VALUE]

    TRONCAL = int(nombreAlimentador[-2:]) if nombreAlimentador[-2:].isnumeric() else 0

    layerArea.startEditing()
    # filtrar nivel 40 Area Eje
    areaLista = []
    ordenExistente = []
    for feature in layerArea.getFeaturesBy(fields.LEVEL,networkLevel.DISPERSION):

            areaLista.append(feature)

            if feature[fields.ORDEN] != NULL:
                ordenExistente.append(feature[fields.ORDEN])

    ultimoOrden = max(ordenExistente) if ordenExistente else 0

    # editar campos de areaLista
    contador = ultimoOrden + 1
    for feature in areaLista:

        if feature[fields.NOMBRE] == NULL:
            feature[fields.ORDEN] = contador
            feature[fields.NOMBRE] = f'{nombreHub}-SA{str(TRONCAL).zfill(2)}{str(contador).zfill(3)}'

            layerArea.updateFeature(feature)
            contador += 1

    layerArea.commitChanges()

def createUfinetNet():

    processing.run('project:removeRedUfinet', {})
    processing.run('project:crearRedUfinet', {})

    layerNode.startEditing()
    layerCable.startEditing()

    # Actualiza las fases de las cajas de Ufinet
    for area in layerArea.getFeaturesBy(fields.LEVEL, networkLevel.DISPERSION):

        if area[fields.DEMANDA_SDU] > 3:

            cajasAList = []
            cajasBList = []

            nodes = layerNode.getFeaturesBy(
                fields.ASSIGNED_AREA,
                area[fields.UUID]
            )

            for node in nodes:
                if (
                    node[fields.TIPO] == elementType.C_TIPO_A
                    and node[fields.LEVEL] == networkLevel.DISPERSION
                    and node[fields.TELECO] == teleco.UFINET
                    and node[fields.FASE] != faseConstruccion.FASE_MDU
                ):
                    cajasAList.append(node)

                elif (
                    node[fields.TIPO] == elementType.C_TIPO_B
                    and node[fields.LEVEL] == networkLevel.ACCESO
                    and node[fields.TELECO] == teleco.UFINET
                    and node[fields.FASE] != faseConstruccion.FASE_MDU
                ):
                    cajasBList.append(node)

            # Casos donde no hay cajas A
            if len(cajasAList) == 0 and len(cajasBList) > 0:

                # 1. Copiar fase de la caja hermana a TODAS las cajas B
                for cajaB in cajasBList:
                    SisterCTO = layerNode.getIntersectingFeatures(
                        layerIDs.Nodo,
                        cajaB
                    )

                    if not SisterCTO:
                        continue

                    faseSisterCTO = SisterCTO[0][fields.FASE]

                    parentCable = layerCable.getFeaturesBy(
                        fields.UUID,
                        cajaB[fields.PARENT_CABLE]
                    )[0]

                    cajaB[fields.FASE] = faseSisterCTO
                    parentCable[fields.FASE] = faseSisterCTO

                    layerNode.updateFeature(cajaB)
                    layerCable.updateFeature(parentCable)


                # 2. Elegir UNA sola caja B que quede en fase de construcción
                cajaUfinetInicial = next(
                    (
                        cajaB for cajaB in cajasBList
                        if cajaB[fields.FASE] == faseConstruccion.FASE_1
                    ),
                    None
                )

                if cajaUfinetInicial is not None:


                    # 3. Todas las demás cajas B pasan a PROYECCIÓN
                    for cajaB in cajasBList:
                        if cajaB[fields.UUID] == cajaUfinetInicial[fields.UUID]:
                            continue

                        cajaB[fields.FASE] = faseConstruccion.FASE_2

                        parentCable = layerCable.getFeaturesBy(
                            fields.UUID,
                            cajaB[fields.PARENT_CABLE]
                        )[0]

                        parentCable[fields.FASE] = faseConstruccion.FASE_2

                        layerNode.updateFeature(cajaB)
                        layerCable.updateFeature(parentCable)

    layerNode.commitChanges()
    layerCable.commitChanges()



def preprocessing():


    nombreHub = mtGenAtt.getValue(mtGenAtt.attName.POP)
    nombreCableTroncal = mtGenAtt.getValue(mtGenAtt.attName.CABLE_TRONCAL)

    processing.run('project:setEjes',{})
    processing.run('project:setPostes',{})
    nameAreas()

    if nombreHub is None or nombreCableTroncal is None or nombreHub=='' or nombreCableTroncal=='':
        iface.messageBar().pushMessage("Error en atributos generales", "Faltan atributos generales obligatorios (POP y Cable Troncal)", level=Qgis.Critical)
        return False
    else:
        return True

def categorizeCableTraces():
    layerCableTraces.startEditing()
    layerCableTraces.updateCacheDict()
    
    

    for feat in layerCableTraces.getFeatures():
        
        ct = mtCableTrace(mtFeature(feat))

        infraInicio = ct.getStartFeature()
        infraFin = ct.getEndFeature()

        if infraInicio is None or infraFin is None:
            # Caso intra poste, si el cable es fase MDU, se categoriza como aereo
            if  layerCable.getFeaturesBy(fields.UUID, feat[fields.PARENT_CABLE])[0][fields.FASE] == faseConstruccion.FASE_MDU:
                feat[fields.TIPO] = cableTraceType.AEREO
                layerCableTraces.updateFeature(feat)
                continue
            # # print(f"CableTrace {feat[fields.UUID]} sin infra inicio o fin")
            statusMsg = f"Error: cableTrace con infraestructura faltante: {feat[fields.UUID]}"
            iface.messageBar().pushMessage("Cabletrace sin infraestructura", statusMsg, level=Qgis.Warning)
           
            continue

        tipoInicio = infraInicio.get(fields.INFRA_TIPO)
        tipoFin = infraFin.get(fields.INFRA_TIPO)

        if tipoInicio == infraNodeType.POSTE and tipoFin == infraNodeType.POSTE:
            feat[fields.TIPO] = cableTraceType.AEREO
            
        elif tipoInicio == infraNodeType.CAMARA and tipoFin == infraNodeType.CAMARA:
            feat[fields.TIPO] = cableTraceType.CAMARA
            
        elif (tipoInicio == infraNodeType.POSTE and tipoFin == infraNodeType.CAMARA) or (tipoInicio == infraNodeType.CAMARA and tipoFin == infraNodeType.POSTE):
            feat[fields.TIPO] = cableTraceType.TRANSICION
            
        elif (tipoInicio == infraNodeType.POSTE and tipoFin == infraNodeType.SUSPENSOR) or (tipoInicio == infraNodeType.SUSPENSOR and tipoFin == infraNodeType.POSTE):
            feat[fields.TIPO] = cableTraceType.AEREO
        layerCableTraces.updateFeature(feat)

    layerCableTraces.commitChanges()


   

def linkSuspensionWires():

    layerSuspensor.startEditing()

    for suspensor in layerSuspensor.getFeatures():
        errors = 0
        postesIntersect = layerSuspensor.getIntersectingNodesUUID(suspensor)
        
           
        if len(postesIntersect) == 2: #si intersecta 2 postes, el primero es el inicio y el segundo el fin
            suspensor[fields.INFRA_INICIO_FK] = postesIntersect[0][fields.UUID]
            suspensor[fields.INFRA_FIN_FK] = postesIntersect[1][fields.UUID]
        if len(postesIntersect) == 1: #si intersecta 1 poste, ese es el inicio y el fin queda en vacio
            suspensor[fields.INFRA_INICIO_FK] = postesIntersect[0][fields.UUID]
            suspensor[fields.INFRA_FIN_FK] = None

        if len(postesIntersect) > 2 or len(postesIntersect) == 0 :
            errors = errors | statusType.SIN_INFRAESTRUCTURA

        if (errors == 0):
            errors = statusType.OK

        suspensor[fields.STATUS_VINCULO] = errors.getStatus()
        layerSuspensor.updateFeature(suspensor)
    layerSuspensor.commitChanges()




def categorizeSuspensionWires():
    # Crear un diccionario para guardar intersecciones: {UUID: lista de UUIDs intersectados}
    intersections_dict = {}

    # Primero recorremos todos los suspensores para calcular intersecciones
    features = list(layerSuspensor.getFeatures())
    for suspensor in features:
        intersects = [
            f for f in layerSuspensor.getIntersectingFeatures(layerIDs.Suspensor, suspensor)
            if f[fields.UUID] != suspensor[fields.UUID]  # evitar contar a sí mismo
        ]
        intersections_dict[suspensor[fields.UUID]] = intersects

    # Luego actualizamos los features usando la info ya calculada
    layerSuspensor.startEditing()
    for suspensor in features:
        intersects = intersections_dict[suspensor[fields.UUID]]
        if intersects:
            suspensor[fields.TIPO] = suspensionWireCategory.CRUCE_COMPLETO
            suspensor[fields.SUSPENSOR_HERMANO] = intersects[0][fields.UUID]  # marcar el cruce
        else:
            suspensor[fields.TIPO] = suspensionWireCategory.CRUCE_MEDIO

        layerSuspensor.updateFeature(suspensor)

    layerSuspensor.commitChanges()



def removeUfinetFeats():
    
    ufinetFeats = layerNode.getFeaturesBy(fields.TELECO,teleco.UFINET)
    if len(ufinetFeats) == 0:
        return  
    else:
        processing.run('project:removeRedUfinet',{})
    
def changeState():
    layerNode.startEditing()
    layerCable.startEditing()
    for node in layerNode.getFeaturesBy(fields.FASE,faseConstruccion.FASE_1):
        node[fields.FASE] = faseConstruccion.DESPLEGADO
        layerNode.updateFeature(node)
    for cable in layerCable.getFeaturesBy(fields.FASE,faseConstruccion.FASE_1): 
        cable[fields.FASE] = faseConstruccion.DESPLEGADO
        layerCable.updateFeature(cable) 
    layerCable.commitChanges()    
    layerNode.commitChanges()
    
def updateAreasFibers():
    #
    #Recorre los segmentos SEG01 (donde se concentra todas las
    #fibras troncales en uso del cable), y agrupa FIBRAS_EN_USO por proyecto TASA
    
    
    mySegments = mtSegments()
    for feat in layerSEG.getFeaturesBy(fields.SEGMENTO, 'SEG01'):
        mySegments.addSegmentFromFeature(mtFeature(feat))
    fibersByProject = {}

    for thisSegment in mySegments.segmentDict.values():
        if not thisSegment.tasaProject:
            continue

        fibersInUseStr = thisSegment.getFeature().get(fields.FIBRAS_EN_USO)
        pares = mtSegment.parseUsedFibers(fibersInUseStr)
        if not pares:
            continue

        projectId = thisSegment.tasaProject
        trunkFibers =  [par[1] for par in pares]  # me quedo con el segundo elemento de cada (n1, n2)
        fibersByProject.setdefault(projectId, set()).update(trunkFibers)

    #  armo el texto de rangos por proyecto 
    textByProject = {}
    for projectId, fibers in fibersByProject.items():
        textByProject[projectId] = formatNumsAsRanges(fibers)
    #fibrasUtilizadas en cada area segun su proyecto TASA 
    layerAreasProyectoTasa.startEditing()

    updates = {}

    for area in layerAreasProyectoTasa.getFeatures():
        myArea = mtFeature(area)
        projectId = myArea.get(fields.TASA_PROJECT)

        newValue = textByProject.get(projectId)
        oldValue = myArea.get(fields.FIBRAS_UTILIZADAS)
        changed = (oldValue or None) != (newValue or None)
        if changed:
            updates[myArea.id()] = newValue
            myArea[fields.FIBRAS_UTILIZADAS] = newValue
            layerAreasProyectoTasa.updateFeature(myArea)

    layerAreasProyectoTasa.commitChanges()
    print(updates)
    
def netTASAProject(myTree: mtTree):
 
    relationsNode_Cable.updateRelations()
    layerNode.startEditing()
    layerCable.startEditing()
    rootNode = myTree.getRootNode()
    myTree.buildTree()
 
    cablesAlim = myTree.getNodesAsList(filter=lambda x: filterCables(x) and filterAlim(x))
    for cable in cablesAlim:
        cableFeat = cable.getFeature()
        try:
            areaDistribucion= layerAreasProyectoTasa.getFeaturesBy(fields.PARENT_PROJECT, cableFeat[fields.TASA_PROJECT])[0] 
            areaDistribucionProject = areaDistribucion[fields.TASA_PROJECT]     
        except IndexError:
            continue

        for childNode in PreOrderIterSorted(cable, childiter=distAlongTotSort):
            myFeat = childNode.getFeature()
            
            if myFeat[fields.LEVEL] == networkLevel.RED_ACCESO:
                continue
            elif myFeat[fields.LEVEL] == networkLevel.RED_ALIMENTACION:
                myFeat[fields.TASA_PROJECT] = cableFeat[fields.TASA_PROJECT]
            elif myFeat[fields.LEVEL] == networkLevel.RED_DISTRIBUCION and myFeat[fields.FASE] == faseConstruccion.FASE_1:
                myFeat[fields.TASA_PROJECT] = areaDistribucionProject
 
            childNode.updateFeature(myFeat)
 
    layerNode.commitChanges()
    layerCable.commitChanges()
    
    
def infraTASAproject():
    # 1. Crear índice de áreas para saber si el proyecto es nivel 30 o 40
    areasByProject = {}
    for area in layerAreasProyectoTasa.getFeatures():
        areasByProject[area[fields.TASA_PROJECT]] = area
    layerInfra.startEditing()
    infraList = layerInfra.getFeaturesBy(fields.POSTE_EN_USO, True)
    infraDict = {infra[fields.UUID]: infra for infra in infraList}
    # Set para evitar doble asignación de proyectos
    infraAssigned = set()
    # Obtenemos los proyectos válidos de los herrajes
    projectIndex = layerHerrajes.L.fields().indexOf(fields.TASA_PROJECT)
    validProjects = [p for p in layerHerrajes.L.uniqueValues(projectIndex) if p]
    # Ordenamos de MENOR a MAYOR 
    validProjects.sort()
    for tasaProject in validProjects:
        # 2. Por defecto asumimos que el proyecto final es el mismo que tiene el herraje
        finalProject = tasaProject
        # 3. Buscamos el área correspondiente para verificar su nivel
        areaFeature = areasByProject.get(tasaProject)
        if areaFeature:
            areaLevel = areaFeature[fields.LEVEL]
            # Si el área es de nivel 40, sobreescribimos el proyecto final con su parentProject
            if areaLevel == 40: # O usa networkLevel.RED_DISTRIBUCION si prefieres la constante
                finalProject = areaFeature[fields.PARENT_PROJECT]
        # Obtenemos la lista de herrajes para este proyecto
        herrajesList = layerHerrajes.getFeaturesBy(fields.TASA_PROJECT, tasaProject)
        for herraje in herrajesList:
            infraUuid = herraje[fields.ASSIGNED_INFRA]
            # Solo actualizamos si el poste existe y AÚN NO fue procesado
            if infraUuid in infraDict and infraUuid not in infraAssigned:
                infra = infraDict[infraUuid]
                # Asignamos el proyecto validado (el original si era 30, o el del padre si era 40)
                infra[fields.TASA_PROJECT] = finalProject
                layerInfra.updateFeature(infra)
                # Lo agregamos al set
                infraAssigned.add(infraUuid)
 
    layerInfra.commitChanges()
    
    
    
def infraTasaProject():
    layerInfra.startEditing()
    layerAreasProyectoTasa.updateCacheDict()

    for infra in layerInfra.getFeaturesBy(fields.POSTE_EN_USO, True , f"and {fields.INFRA_TIPO}={infraNodeType.POSTE}"):

        herrajesAssigned = layerHerrajes.getFeaturesBy(fields.ASSIGNED_INFRA,infra[fields.UUID])


        herrajesProjectList = [] 

        for herraje in herrajesAssigned:
            areaFeat = layerAreasProyectoTasa.getFeaturesBy(fields.TASA_PROJECT, herraje[fields.TASA_PROJECT],f"and {herraje[fields.TASA_PROJECT]} is not NULL") 
            if len(areaFeat) > 0:
                areaFeat = areaFeat[0]
                # Toda la infraestructura postes/suspensores siempre se asocia
                # a un proyecto de alimentación
                if areaFeat[fields.LEVEL] == networkLevel.RED_DISTRIBUCION:
                    parentAreaFeat = layerAreasProyectoTasa.getFeaturesBy(fields.TASA_PROJECT, areaFeat[fields.PARENT_PROJECT],f"and {areaFeat[fields.PARENT_PROJECT]} is not NULL")[0]
                    herrajeProject = parentAreaFeat[fields.TASA_PROJECT]
                else:
                    herrajeProject = herraje[fields.TASA_PROJECT]

                herrajesProjectList.append(int(herrajeProject))
                #ordeno por proyecto tasa asumiendo que el de menor valor se construye siempre antes
                #ordeno por proyecto tasa de alimnetacion SIEMPRE! 
  
                herrajesProjectList = sorted(herrajesProjectList)
                herrajeProject = herrajesProjectList[0] if herrajesProjectList else None
        try:
            infra[fields.TASA_PROJECT] = herrajeProject
            
        except Exception as e:
            continue
        
        layerInfra.updateFeature(infra)

      
    layerInfra.commitChanges()
     

def RedAccesoTasaProject():
    layerCable.startEditing()
    layerNode.startEditing()
    layerAreasProyectoTasa.updateCacheDict()

    AreaAcceso = layerAreasProyectoTasa.getFeaturesBy(fields.LEVEL, networkLevel.RED_ACCESO)[0]

    for cable in layerCable.getFeaturesBy(fields.LEVEL, networkLevel.RED_ACCESO):
        cable[fields.TASA_PROJECT] = AreaAcceso[fields.TASA_PROJECT]
        layerCable.updateFeature(cable)

    for nodo in layerNode.getFeaturesBy(fields.LEVEL, networkLevel.RED_ACCESO):
       
        nodo[fields.TASA_PROJECT] = AreaAcceso[fields.TASA_PROJECT]
        layerNode.updateFeature(nodo)

    layerCable.commitChanges()
    layerNode.commitChanges()

def createInfraNodes():
    
    deleteInfraNodes()
    trazaInfraVertexNodes()
    createInfraNodesSuspensores()
    
def deleteInfraNodes():
    layerInfra.startEditing()
    featsToDelete = layerInfra.getFeaturesBy(fields.INFRA_TIPO, infraNodeType.SUSPENSOR)
    if featsToDelete:
        layerInfra.deleteFeatures([feat.id() for feat in featsToDelete])
    layerInfra.commitChanges()
 
def trazaInfraVertexNodes():
    layerInfra.startEditing()
    for ducto in layerTrazaInfra.getFeaturesBy(fields.TIPO, trazaInfraType.DUCTOS):
        
        geom = ducto.geometry()
        polyline = geom.asPolyline()
        
        for vertex in polyline:
            pointGeom = QgsGeometry.fromPointXY(vertex)
            
            newInfraNode = QgsFeature(layerInfra.L.fields())
            newInfraNode.setGeometry(pointGeom)
            
            newInfraNode[fields.UUID] = uuid.uuid4().hex
            newInfraNode[fields.INFRA_TIPO] = infraNodeType.VERTICE_DUCTO
            newInfraNode[fields.AUTOGENERADO] = True  
            newInfraNode[fields.POSTE_EN_USO] = True          
            
            layerInfra.addFeature(newInfraNode)
    layerInfra.commitChanges()
        
        
def createInfraNodesSuspensores():
    layerInfra.startEditing()
   
    infraFields = layerInfra.L.fields()
    expression1 = QgsExpression("uuid('Id128')")
    context = QgsExpressionContext()
    
    for suspensor in layerSuspensor.getFeatures():
        geom = suspensor.geometry()      
        polyline = geom.asPolyline()
        
        if len(polyline) >= 3: 
            middleVertices = polyline[1:-1]
            
            for vertex in middleVertices:
                pointGeom = QgsGeometry.fromPointXY(vertex)
                
                newInfraNode = QgsFeature(infraFields)
                newInfraNode.setGeometry(pointGeom)
                
                context.setFeature(newInfraNode)
                newInfraNode[fields.UUID] = expression1.evaluate(context)
                newInfraNode[fields.INFRA_TIPO] = infraNodeType.SUSPENSOR
                newInfraNode[fields.AUTOGENERADO] = True  
                newInfraNode[fields.POSTE_EN_USO] = True          
                suspensorFk = suspensor[fields.UUID]
                
                listCablesIntersecting = layerCable.getIntersectingFeatures(layerIDs.Cable, newInfraNode)
                
                atributosSecundariosDict = {
                    fields.SUSPENSOR_FK: suspensorFk,
                    fields.PARENT_CABLE: []
                }
                
                if len(listCablesIntersecting) > 0:
                    # Ordenamos por nivel de red (LEVEL)
                    listCablesIntersecting = sorted(listCablesIntersecting, key=lambda x: x[fields.LEVEL])
                    
                    # Extraemos los UUIDs de los cables intersectados
                    listaCablesUuids = [cable[fields.UUID] for cable in listCablesIntersecting]               
                    
                    atributosSecundariosDict[fields.PARENT_CABLE] = listaCablesUuids
                else:
                    statusMsg = f"Error: No cables intersecting with suspensor: {suspensorFk}"
                    iface.messageBar().pushMessage("Asociar Feature cable_fk a suspensor", statusMsg, level=Qgis.Warning)       
 
                newInfraNode[fields.ATRIBUTOS_SEC] = json.dumps(atributosSecundariosDict)
                layerInfra.addFeature(newInfraNode)
            
    layerInfra.commitChanges()
    


def assignProjectToSuspensor():
    areasByProject = {}
    
    for area in layerAreasProyectoTasa.getFeatures():
        areasByProject[area[fields.TASA_PROJECT]] = area

    layerInfra.startEditing()
    layerSuspensor.startEditing() 

    suspensorNodesMap = {}
    suspensorCablesMap = {}

    for suspensorPointInfra in layerInfra.getFeaturesBy(fields.INFRA_TIPO, infraNodeType.SUSPENSOR):
        atributosSec = json.loads(suspensorPointInfra[fields.ATRIBUTOS_SEC])
        suspensorUuid = atributosSec[fields.SUSPENSOR_FK]
        listaCablesUuids = atributosSec.get(fields.PARENT_CABLE, [])

        if suspensorUuid not in suspensorNodesMap:
            suspensorNodesMap[suspensorUuid] = []
            suspensorCablesMap[suspensorUuid] = set()

        suspensorNodesMap[suspensorUuid].append(suspensorPointInfra)
        
        for cableUuid in listaCablesUuids:
            suspensorCablesMap[suspensorUuid].add(cableUuid)

    for suspensorUuid, cableUuidsSet in suspensorCablesMap.items():
        # print(f"Suspensor UUID: {suspensorUuid} | Lista de cables unificada: {list(cableUuidsSet)}")
        
        if not cableUuidsSet:
            continue

        suspensorFeature = layerSuspensor.getFeatureByUUID(suspensorUuid)
        if not suspensorFeature:
            continue

        cablesList = []
        for cableUuid in cableUuidsSet:
            cableFeats = layerCable.getFeaturesBy(fields.UUID, cableUuid)
            if cableFeats:
                cablesList.append(cableFeats[0])

        if not cablesList:
            continue

        cablesList = sorted(cablesList, key=lambda x: (x[fields.LEVEL], x[fields.TASA_PROJECT] if x[fields.TASA_PROJECT] is not None else ""))
        assignedCable = cablesList[0]
        proyectoTasaAsignado = None

        if assignedCable[fields.LEVEL] in [networkLevel.RED_ALIMENTACION, networkLevel.RED_ACCESO]:
            proyectoTasaAsignado = assignedCable[fields.TASA_PROJECT]
            
        elif assignedCable[fields.LEVEL] == networkLevel.RED_DISTRIBUCION:
            sigestCable = assignedCable[fields.TASA_PROJECT]
            area40 = areasByProject.get(sigestCable)
            
            if area40:
                proyectoTasaAsignado = area40[fields.PARENT_PROJECT] 

        if proyectoTasaAsignado:
            suspensorFeature[fields.TASA_PROJECT] = proyectoTasaAsignado
            layerSuspensor.updateFeature(suspensorFeature)
            
            for nodeFeature in suspensorNodesMap[suspensorUuid]:
                nodeFeature[fields.TASA_PROJECT] = proyectoTasaAsignado
                layerInfra.updateFeature(nodeFeature)

    layerInfra.commitChanges()
    layerSuspensor.commitChanges()

def camarasEnUso():
    """ Tag las cámaras en uso en el campo "enUso" con true
    """

    infraI = layerCableTraces.uniqueValues(fields.INFRA_INICIO_FK)
    infraF = layerCableTraces.uniqueValues(fields.INFRA_FIN_FK)
    
    infraCableTrace = infraI | infraF

    layerInfraNodeRel.startEditing()
    for camara in layerInfraNodeRel.getFeaturesBy(fields.INFRA_TIPO, colocacion.CAMARA):
        camara[fields.POSTE_EN_USO] = False
        uuidCamara = camara[fields.UUID]

        if uuidCamara in infraCableTrace:
            camara[fields.POSTE_EN_USO] = True

        layerInfraNodeRel.updateFeature(camara)

    layerInfraNodeRel.commitChanges()
    return


def manzanaIntersectTasa():
    """ Completa en el campo pryectoTasaIntersect de la manzana 
        con el numero de proyecto tasa según el area 30 que corresponda"""

    layerManzana.startEditing()

    for manzana in layerManzana.getFeatures():
        areaIntersect = layerManzana.getIntersectingFeatures(layerIDs.AreaProyectoTasa,manzana,f'{fields.LEVEL}={networkLevel.RED_ALIMENTACION}')

        if len(areaIntersect) == 1:
            area = areaIntersect[0]
            manzana[fields.TASA_PROJECT_INTERSECT] = area[fields.TASA_PROJECT]
        elif len(areaIntersect) > 1:
            iface.messageBar().pushMessage(
                        "Areas Proyecto Tasa", 
                        f"Multiples Areas en manzana {manzana[fields.UUID]}", 
                        level=Qgis.Warning
                        )
        else:
            manzana[fields.TASA_PROJECT_INTERSECT] = NULL
            
        layerManzana.updateFeature(manzana)

    layerManzana.commitChanges()
    return

def checkAtributosG():
    """ Revisa que la tabla de atributos generales 
    haya sido modificada para el nuevo proyecto y este en estado True
     - Verificamos el feature de nombre 'check' 
          si value --> 'true' : la tabla fue revisada y actualizada
          si value --> 'false' : revisar tabla """

    # 1. CHEQUEAR QUE HAYA FEATURE CHECK Y SI NO HAY CREARLO
    filaCheck = layerGeneralAtt.getFeaturesBy('nombre','check') #fitro fila
    if not filaCheck: # si no hay fila la crea

        newAtributo = QgsFeature(layerGeneralAtt.L.fields())
        
        layerGeneralAtt.startEditing()
        newAtributo[fields.UUID] = str(uuid.uuid4())
        newAtributo[fields.NOMBRE] = str('check')
        newAtributo[fields.VALUE] = str('false')      
            
        layerGeneralAtt.addFeature(newAtributo)
        layerGeneralAtt.commitChanges()

        filaCheck = layerGeneralAtt.getFeaturesBy('nombre','check')[0]

    else:
        filaCheck = layerGeneralAtt.getFeaturesBy('nombre','check')[0]

    valorCheck = filaCheck[fields.VALUE] #obtengo el valor en la columna value

    # 2. VERIFICAR EL ESTADO DE VALUE 
    if valorCheck == 'true':
        estado = True

    else:
        iface.messageBar().pushMessage(
            "Validación de Proyecto", 
            "Revisar tabla de atributos generales!", 
            level=Qgis.Warning
            )

        estado = False

    return estado


def checkErrorsNetwork() -> bool: 
    # Función debug para encontrar errores previos a runNetwork()
    isNetworkValid = True
    layersToCheck = [layerArea, layerCable, layerNode]
    
    for layerObj in layersToCheck:
        # 1. Chequeo de geometrías nulas o inválidas
        invalidFeats = layerObj.getInvalidGeomFeatures()
        
        if invalidFeats:
            isNetworkValid = False
            # for feat in invalidFeats:
            #     print(f"[ERROR GEOMETRÍA INVÁLIDA] Capa: {layerObj.LID} | UUID: {feat[fields.UUID]} | FID: {feat.id()}")
                
            fidsGeom = ", ".join([str(f.id()) for f in invalidFeats])
            iface.messageBar().pushMessage(
                "Validación de Red", 
                f"Capa {layerObj.LID}: {len(invalidFeats)} geometrías inválidas (FIDs: {fidsGeom}).", 
                level=Qgis.Warning
            )
            
        #  Chequeos capa de cables
        if layerObj == layerCable:
            dupVerticesFeats = []
            dupJumpersFeats = []
            seenJumpers = set() 
            
            # 
            allDupVertices = layerObj.getDuplicatedVerticesFeatures()
            
            # Filtramos (jumpers)
            for feat in allDupVertices:
                if feat[fields.LEVEL] == networkLevel.RED_DISTRIBUCION:
                    dupVerticesFeats.append(feat)
            # ----------------------------------------
            
            # check Jumpers (revisando duplicidad Inicio-Fin)
            for feature in layerObj.getFeatures():
                geom = feature.geometry()
                verticesList = list(geom.vertices())
                
                #  identificar el jumper duplicado
                if feature[fields.LEVEL] == networkLevel.RED_DISTRIBUCION: 
                    if len(verticesList) >= 2:
                        startPt = (verticesList[0].x(), verticesList[0].y())
                        endPt = (verticesList[-1].x(), verticesList[-1].y())
                        jumperGeomPair = (startPt, endPt)
                        
                        if jumperGeomPair in seenJumpers:
                            dupJumpersFeats.append(feature)
                        else:
                            seenJumpers.add(jumperGeomPair)
                            
            # Reporte de Errores Vertices
            if dupVerticesFeats:
                isNetworkValid = False
                for feat in dupVerticesFeats:
                    print(f"[ERROR VÉRTICES DUPLICADOS] Capa: {layerObj.LID} | UUID: {feat[fields.UUID]} | FID: {feat.id()}")  
                    
                fidsVert = ", ".join([str(f.id()) for f in dupVerticesFeats])
                iface.messageBar().pushMessage(
                    "Validación de Red", 
                    f"{len(dupVerticesFeats)} cables de distribución con vértices duplicados (FIDs: {fidsVert}).", 
                    level=Qgis.Warning
                )
                
            # Reporte de Errores Jumpers
            if dupJumpersFeats:
                isNetworkValid = False
                for feat in dupJumpersFeats:
                    print(f"[ERROR JUMPERS DUPLICADOS] Capa: {layerObj.LID} | UUID: {feat[fields.UUID]} | FID: {feat.id()}")  
                    
                fidsJumpers = ", ".join([str(f.id()) for f in dupJumpersFeats])
                iface.messageBar().pushMessage(
                    "Validación de Red", 
                    f"{len(dupJumpersFeats)} jumpers duplicados (FIDs: {fidsJumpers}).", 
                    level=Qgis.Warning
                )
                
    return isNetworkValid


def groupSplices(myTree: mtTree):
    rootNode = myTree.getRootNode()
    layerNode.startEditing()

    groupCount = 1
    for nodeCable in PostOrderIterSorted(rootNode, filter_=filterCables, stop=stopStayCentralAcc,
                                         childiter=centralAccesoLeafAndDistanceFiberSort):
        for node in sorted(nodeCable.children, key=lambda item: item.distance or 0):
            node.groupSplice = groupCount
            nodeFeat = node.getFeature()
            nodeFeat[fields.GROUP_SPLICES] = groupCount
            layerNode.updateFeature(nodeFeat)

            for hub in PreOrderIter(node, filter_=filterHubs, stop=stopNotAlim):
                hub.groupSplice = groupCount
                hubFeat = hub.getFeature()
                hubFeat[fields.GROUP_SPLICES] = groupCount
                layerNode.updateFeature(hubFeat)

            groupCount += 1

    layerNode.commitChanges()