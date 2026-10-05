from qgis.core import (
    QgsMapLayer,
)

from .mtConstants import *   #Importamos todas las constantes de mtConstants
#from .mtFuncs import *
from anytree import PreOrderIter
from .mtTree import mtTree, mtNode
from .mtSegments import mtSegments
from .mtAttData import attData
from .mtLayer import *

HELIX_FACTOR = (3/100) #Efecto helice para cable 144 - 3.45%
JUMPERMAX = 250
ATT_FIBER=attData((0.34 / 1000) , (0.21 / 1000)) # US @1310 [dB/m] /  DS @1490 [dB/m]
ATT_POP=attData.sameAtt( 0.4 ) # Atenuacion a la salida del nodo
ATT_SPLITTER_1X8=attData.sameAtt( 10.6 )
ATT_SPLITTER_1X4=attData.sameAtt( 7 )
ATT_SPLICE=attData.sameAtt( 0.1 )
ATT_CONNECTOR=attData.sameAtt( 0.3 ) 


def atenuacionAll(myTree: 'mtTree', mySegments: 'mtSegments'):

    rootNode = myTree.buildTree()
    myTree.clearAttenuation()

    layerNode.startEditing()

    nodo: mtNode
    for nodo in PreOrderIter(rootNode):
        #print(nodo)
        #print(type(nodo), type(nodo) is mtNode, nodo is mtNode)
        assert (type(nodo) is mtNode)
        if nodo.is_root or nodo.tipo != geomType.NODE:
            continue
        if nodo.tipoNodo == elementType.HUB:
            nodo.localAttenuation = ATT_POP
            continue
        if nodo.tipoNodo not in [elementType.PC, elementType.HUB,elementType.CE_ACCESO,elementType.CE_ALIMENTACION,elementType.CE_CONTINUIDAD]:   # We shouldnt hit this  but just in case
            print('tipo de elemento no tipificado')
            continue
        thisFeature = nodo.getFeature()

        assert nodo.parent is not None
        assert nodo.parent.parent is not None

        if nodo.tipoNodo in  [elementType.CE_ACCESO,elementType.CE_ALIMENTACION, elementType.HUB,elementType.PC]:
            parentAtt=nodo.parent.parent.localAttenuation
            assert parentAtt is not None
            thisFiberLength = mySegments.getCumulativeDistanceFromEndNode(nodo.parent.fid,nodo.fid) * (1+ HELIX_FACTOR)
            fiberAtt = thisFiberLength * ATT_FIBER
            nodo.localAttenuation = parentAtt + fiberAtt + ATT_SPLICE
            savedAttenuation=nodo.localAttenuation
            
            if nodo.tipoNodo==elementType.HUB:
                nodo.jumperOutAtt = nodo.localAttenuation + ATT_SPLITTER_1X4 + ATT_CONNECTOR
                savedAttenuation = nodo.jumperOutAtt # we save the local attenuation, there are no client ports

            thisFeature[fields.ATENUACION_DS] = round(savedAttenuation.DS, 2)
            thisFeature[fields.ATENUACION_US] = round(savedAttenuation.US, 2)

        if nodo.tipoNodo in[ elementType.C_TIPO_A, elementType.C_TIPO_B]:
            parentAtt=nodo.parent.parent.jumperOutAtt
            assert parentAtt is not None
            jumper = nodo.parent.getFeature()
            thisFiberLength = jumper[fields.LONG_TOTAL] if jumper[fields.LONG_TOTAL] != JUMPER_EXCEDIDO else JUMPERMAX
            fiberAtt = thisFiberLength * ATT_FIBER

            if nodo.tipoNodo == elementType.C_TIPO_A: 
                nodo.jumperOutAtt = parentAtt + fiberAtt + ATT_SPLITTER_1X4 + 2*ATT_CONNECTOR 
                nodo.localAttenuation = nodo.jumperOutAtt + ATT_SPLITTER_1X8 + ATT_SPLICE
            elif nodo.tipoNodo == elementType.C_TIPO_B:
                nodo.localAttenuation = parentAtt + fiberAtt + ATT_SPLITTER_1X8 + 2*ATT_CONNECTOR
            
            
            thisFeature[fields.ATENUACION_DS] = round(nodo.localAttenuation.DS,2)
            thisFeature[fields.ATENUACION_US] = round(nodo.localAttenuation.US,2)

        nodo.getLayer().updateFeature(thisFeature)

    layerNode.commitChanges() 

        
        
        
        


        


