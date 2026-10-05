## El Ofseteado es el mismo que el de Varela, Habria que ver que se puede mejorar si vale la pena


from qgis.core import (
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsProject,
    QgsMessageLog,
    Qgis,
)


from .mtConstants import *
from .mtLayer import *
from queue import Queue
from .mtOrder import mtOrder
import math

class node:
    color = 0
    edges = []
    def __repr__(self):
        return f"Color: {self.color} - edges:{self.edges}"
 
def canPaint(nodes):
 
    # Create a visited array of n
    # nodes, initialized to zero
    visited = {k:0 for k in nodes.keys()}

    # maxColors used till now are 1 as
    # all nodes are painted color 1
    maxColors = 1
 
    # Do a full BFS traversal from
    # all unvisited starting points
    for i in visited.keys():
        if visited[i]:
            #QgsMessageLog.logMessage(f"Ya visitado: {i}", 'updateOffset', level=Qgis.Info)
            continue
 
        # If the starting point is unvisited,
        # mark it visited and push it in queue
        visited[i] = 1
        q = Queue()
        q.put(i)
 
        # BFS Travel starts here
        while not q.empty():
            top = q.get()
 
            # Checking all adjacent nodes
            # to "top" edge in our queue
            for j in nodes[top].edges:
                # IMPORTANT: If the color of the
                # adjacent node is same, increase it by 1
                #QgsMessageLog.logMessage(f"top:{top} color top:{nodes[top].color} Nodo: {j} color: {nodes[j].color}", 'updateOffset', level=Qgis.Info)
                if nodes[top].color == nodes[j].color:
                    nodes[j].color += 1
                    #QgsMessageLog.logMessage(f"top:{top} color top:{nodes[top].color} Nodo: {j} Nuevo color: {nodes[j].color}", 'updateOffset', level=Qgis.Info)
 
                maxColors = max(maxColors, max(
                    nodes[top].color, nodes[j].color))

                # If the adjacent node is not visited,
                # mark it visited and push it in queue
                if not visited[j]:
                    visited[j] = 1
                    q.put(j)

    #QgsMessageLog.logMessage(f"maxColors: {maxColors}", 'updateOffset', level=Qgis.Info)
    return maxColors


def greedyPaint(graph):
    # viene de aca: https://codereview.stackexchange.com/questions/203319/greedy-graph-coloring-in-python
    nodes = [k for k,v in sorted(graph.items(),key=lambda item: len(item[1].edges),reverse=True)]

    color_map = {}
    
    for node in nodes:
        available_colors = [True] * len(nodes)
        for neighbor in graph[node].edges:
            if neighbor in color_map:
                color = color_map[neighbor]
                available_colors[color] = False
        for color, available in enumerate(available_colors):
            if available:
                color_map[node] = color
                break
    
    maxColors=0
    for k,v in color_map.items():
        graph[k].color=v
        maxColors=max(maxColors,v)
    
    #QgsMessageLog.logMessage(f"maxColors: {maxColors}", 'updateOffset', level=Qgis.Info)
    return maxColors


def updateOffset(layerId):
    
    nodes={}

    offsetTranslation=[0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6,7,-7,8,-8,9,-9] #OJO QUE NO TIENE QUE ESTAR EL CARRIL DE JUMPERS

    thisLayer = QgsProject().instance().mapLayer(layerId)
    expression = QgsExpression(f'overlay_intersects( \'{layerId}\',$id)')
    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(thisLayer))

    for feature in thisLayer.getFeatures():
        # iteramos en todos los features del layer
        context.setFeature(feature)
        # pido todas las intersecciones del feature con su layer
        foundFids = expression.evaluate(context)
        # agrego un nodo con todas las intersecciones como "edges" del grafo
        nodes[feature.id()]=node()
        nodes[feature.id()].edges=foundFids
        #QgsMessageLog.logMessage(f"nodo:{feature.id()} edges:{nodes[feature.id()].edges}", 'updateOffset', level=Qgis.Info)

    # coloreo el grafo
    greedyPaint(nodes)

    # ahora copiamos los offsets calculados en el grafo a los features
    offsetFieldId=thisLayer.fields().indexFromName('Offset')
    thisLayer.startEditing()
    for fid in nodes.keys():
        # esto es mas rapido que pedir el feature, actualizarle el valor y grabarlo en el layer de nuevo
        thisLayer.changeAttributeValue(fid, offsetFieldId, offsetTranslation[nodes[fid].color])
    thisLayer.commitChanges()
    
def updateAllOffsets():
    
    nodes={}

    offsetTranslation=[1,-1,2,-2,3,-3,4,-4,5,-5,6,-6,7,-7,8,-8,9,-9] #OJO QUE NO TIENE QUE ESTAR EL CARRIL DE JUMPERS
    offsetTranslation= [x+OFFSET_EVITAR_COLISIONES for x in offsetTranslation]



    expTro = QgsExpression(f'overlay_intersects( \'{layerCable.LID}\',$id,filter:={fields.LEVEL}<{networkLevel.RED_DISTRIBUCION})')

    contextTro = QgsExpressionContext()
    contextTro.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layerCable.L))


    for feature in layerCable.getFeaturesByFilter(f"{fields.LEVEL}<{networkLevel.RED_DISTRIBUCION}"):
        # iteramos en todos los features del layer
        contextTro.setFeature(feature)

        # pido todas las intersecciones del feature con su layer
        fidsTro = expTro.evaluate(contextTro)
        myNodeId=feature.id()

        # agrego un nodo con todas las intersecciones como "edges" del grafo
        
        tempedges=[]
        tempedges+=[k for k in fidsTro]

        nodes[myNodeId]=node()
        nodes[myNodeId].edges=tempedges
            
            #QgsMessageLog.logMessage(f"layer:{myLayerKey} nodo:{myNodeId} edges:{nodes[myNodeId].edges}", 'updateOffset', level=Qgis.Info)
    # coloreo el grafo
    greedyPaint(nodes)


    # ahora copiamos los offsets calculados en el grafo a los features
    offsetFieldId=layerCable.fields().indexFromName('offset')
    layerCable.startEditing()
    for fid in nodes.keys():
        # esto es mas rapido que pedir el feature, actualizarle el valor y grabarlo en el layer de nuevo
        #print("offset asignado", offsetTranslation[nodes[fid].color])
        layerCable.L.changeAttributeValue(fid, offsetFieldId, offsetTranslation[nodes[fid].color])
    
    # Para cables de distribucion (drops) itero por esos features
    for cable in layerCable.getFeaturesBy(field=fields.LEVEL,value=networkLevel.RED_DISTRIBUCION):
        cableOrder=mtOrder(cable[fields.ORDEN])
        cableChirality=cable[fields.CHIRALITY]
        if -CHIRALITY_THRESHOLD < cableChirality < CHIRALITY_THRESHOLD:
            cableChirality=0
        else:
            cableChirality=math.copysign(1,cableChirality)
        
        cable[fields.OFFSET]=((cableOrder.getFirstMajorOrder()*SEPARACION_JUMPERS) + abs(cableChirality)*4*SEPARACION_JUMPERS)*math.copysign(1,cableChirality)*-1
        #cable[fields.OFFSET]=((cableOrder.getFirstMajorOrder()-1)*SEPARACION_JUMPERS)+CARRIL_JUMPERS - cableOrder.getFirstMinorOrder()/10
        layerCable.updateFeature(cable)
    layerCable.commitChanges()  
    