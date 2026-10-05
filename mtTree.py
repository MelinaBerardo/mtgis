from qgis.core import (
    NULL,
)

from typing import Optional
from .mtConstants import *
from .mtLayer import *
from anytree import NodeMixin
from anytree.iterators.abstractiter import AbstractIter
from .mtAttData import attData
from .mtAuxFuncs import chunks, parsePreOccupiedNums
from .mtLayerRelations import relationsNode_Cable
from .mtOrder import mtOrder
#from .mtTree import mtNode


import copy
import json
import six


def orderSort(items, rev:bool=False) ->'list[mtNode]':
    revOrder=-1 if rev else 1
    return sorted(items, key=lambda item:revOrder*item.orderNumber if item.orderNumber else 0)

def levelOrderSort(items,  levelRev:bool=False, orderRev:bool=False ) ->'list[mtNode]':
    levelMult=-1 if levelRev else 1
    orderMult=-1 if orderRev else 1
    return sorted(items, key=lambda item:
                  ((levelMult*item.nivelNodo if item.nivelNodo else 0),
                   (orderMult*item.orderNumber if item.orderNumber else 0)))
    
    
def groupSplicesOrderSort(items,groupRev: bool = True,orderRev: bool = False) -> 'list[mtNode]':

    groupMult = -1 if groupRev else 1
    orderMult = -1 if orderRev else 1

    return sorted(items,key=lambda item: (
            groupMult * item.groupSplice if item.groupSplice is not None else 0,
            orderMult * item.orderNumber if item.orderNumber is not None else 0
        )
    )
    
    
def levelGroupSpliceOrderSort(items, levelRev: bool = False, groupRev: bool = True, orderRev: bool = False) -> 'list[mtNode]':
    levelMult = -1 if levelRev else 1
    groupMult = -1 if groupRev else 1
    orderMult = -1 if orderRev else 1

    return sorted(items, key=lambda item: (
        (levelMult * item.nivelNodo if item.nivelNodo is not None else 0),
        (groupMult * item.groupSplice if item.groupSplice is not None else 0),
        (orderMult * item.orderNumber if item.orderNumber is not None else 0)
    ))
    
def distAlongTotSort(items) ->'list[mtNode]':
    return sorted(items, key=lambda item:item.distanceTotal if item.distanceTotal else 0)

def distAlongSort(items) ->'list[mtNode]':
    return sorted(items, key=lambda item:item.distance if item.distance else 0)

def parentDistAlongTotSort(items) ->'list[mtNode]':
    return sorted(items, key=lambda item:item.parent.distanceTotal if item.parent else 0)

def totalLengthSort(items) ->'list[mtNode]':
    return sorted(items, key=lambda item:item.length if item.length else 0)

def totalLengthSortRev(items) ->'list[mtNode]':
    return sorted(items, key=lambda item:item.length if item.length else 0, reverse=True)

def distAlongAndTotalLengthRev(items) ->'list[mtNode]':
    return sorted(items, key=lambda item:(item.length if item.length else 0, -item.distance if item.distance else 0))

def distAlongAndDescendantsRev(items) ->'list[mtNode]':
    return sorted(items, key=lambda item:(item.length if item.length else 0, -len(item.descendants) if item.descendants else 0))

def fiberCountAndTotalLengthSortRev(items) ->'list[mtNode]':
    return sorted(items, key=lambda item:(item.numFibers if item.numFibers else 0, item.length if item.length else 0), reverse=True)

def fiberCountAndTotalLengthSort(items) ->'list[mtNode]':
    return sorted(items, key=lambda item:(item.numFibers if item.numFibers else 0, item.length if item.length else 0), reverse=False)

def heightSort(items) ->'list[mtNode]':
    return sorted(items, key=lambda item:item.height)

def heightSortRev(items) ->'list[mtNode]':
    return sorted(items, key=lambda item:item.height, reverse=True)

def levelLeafAndDistanceSort(items, levelFilter):
    return sorted(items,key=lambda item:(-1 if filteredLeaf(item, levelFilter) else 0, item.distance if item.distance else 0))

def levelLeafAndDistancefiberCountSort(items, levelFilter):
    return sorted(
        items,
        key=lambda item: (
            -1 if filteredLeaf(item, levelFilter) else 0,
            item.distance if item.distance else 0,
            item.numFibers if not item.distance else 0,
        ),
    )


def centralAccesoLeafAndDistanceFiberSort(items):
    return levelLeafAndDistancefiberCountSort(items, filterCentralAcc)


def centralAccesoLeafAndDistanceSort(items):
    return levelLeafAndDistanceSort(items, filterCentralAcc)

def filterNodes(item: 'mtNode') -> 'bool':
    return item.tipo==geomType.NODE

def filterCables(item: 'mtNode') -> 'bool':
    return item.tipo==geomType.LINE

def filteredLeaf(item: 'mtNode', levelFilter) -> 'bool':
    return len( [child for child in item.children if levelFilter(child)])==0

def filterCentralAcc(item: 'mtNode') -> 'bool':
    return item.nivelNodo in [networkLevel.CENTRAL, networkLevel.RED_ACCESO ]

def filterHubs(item: 'mtNode') -> 'bool':
    return item.tipoNodo == elementType.HUB

def filterCentralAccAlim(item: 'mtNode') -> 'bool':
    return  item.nivelNodo in [networkLevel.CENTRAL, networkLevel.RED_ACCESO,networkLevel.RED_ALIMENTACION ]

def filterNodesCentralAccAlim(item: 'mtNode') -> 'bool':
    return filterCentralAccAlim(item) and filterNodes(item)

def filterNodesCentralAcc(item: 'mtNode') -> 'bool':
    return filterCentralAcc(item) and filterNodes(item)

def filterCablesCentralAcc(item: 'mtNode') -> 'bool':
    return filterCentralAcc(item) and filterCables(item)

def filterCablesCentralAccAlim(item: 'mtNode') -> 'bool':
    return filterCentralAccAlim(item) and filterCables(item)

def filterAccAlim(item: 'mtNode') -> 'bool':
    return  item.nivelNodo in [networkLevel.RED_ACCESO,networkLevel.RED_ALIMENTACION ]

def filterAlim(item: 'mtNode') -> 'bool':
    return  item.nivelNodo in [networkLevel.RED_ALIMENTACION ]

def filterNodesAccAlim(item: 'mtNode') -> 'bool':
    return  filterAccAlim(item) and filterNodes(item)

def filterCablesAccAlim(item: 'mtNode') -> 'bool':
    return  filterAccAlim(item) and filterCables(item)

def filterDistribucion(item: 'mtNode') -> 'bool':
    return  item.nivelNodo in [networkLevel.RED_DISTRIBUCION] 

def filterNodesDistribucion(item: 'mtNode') -> 'bool':
    return  filterDistribucion(item) and filterNodes(item)

def filterCablesDistribucion(item: 'mtNode') -> 'bool':
    return  filterDistribucion(item) and filterCables(item)

def filterAlimDistribucion(item: 'mtNode') -> bool:
    return filterAlim(item) or filterDistribucion(item)

def stopStayInHub(item: 'mtNode') -> 'bool':
    # Es cable y NO es nivel distribucion - no sigue por derivaciones de Acceso /Alimentacion hijos del HUB
    return filterCables(item) and not filterDistribucion(item)

def stopStayCentralAcc(item: 'mtNode') ->'bool':
    if item.is_root:
        return False
    return not filterCentralAcc(item)

# def stopNotAlim(item: 'mtNode') -> 'bool':
#     return not filterAlim(item)

def stopNotAlim(item: 'mtNode') -> 'bool':
    # el nodo de inicio (PC/CE) cuelga de un cable de central/acceso: no se corta
    if item.parent is not None and filterCables(item.parent) and not stopStayCentralAcc(item.parent):
        return False
    return not filterAlim(item)

class PreOrderIterSorted(six.Iterator):
    def __init__(self, node, filter_=None, stop=None, maxlevel=None, childiter=list):
        self.childiter = childiter
        self.node = node
        self.filter_ = filter_
        self.stop = stop
        self.maxlevel = maxlevel
        self.__iter = None

    def __init(self):
        node = self.node
        maxlevel = self.maxlevel
        filter_ = self.filter_ or self.__default_filter
        stop = self.stop or self.__default_stop
        childiter = self.childiter or list 
        children = [] if self._abort_at_level(1, maxlevel) else self._get_children([node], stop)
        return self._iter(children, filter_, stop, maxlevel, childiter)
    
    @staticmethod
    def __default_filter(node):
        # pylint: disable=W0613
        return True

    @staticmethod
    def __default_stop(node):
        # pylint: disable=W0613
        return False

    def __iter__(self):
        return self

    def __next__(self):
        if self.__iter is None:
            self.__iter = self.__init()
        return next(self.__iter)

    @staticmethod
    def _abort_at_level(level, maxlevel):
        return maxlevel is not None and level > maxlevel

    @staticmethod
    def _get_children(children, stop):
        return [child for child in children if not stop(child)]
    
    @staticmethod
    def _iter(children, filter_, stop, maxlevel, childiter):
        children=childiter(children)
        for child_ in children:
            if stop(child_):
                continue
            if filter_(child_):
                yield child_
            if not PreOrderIterSorted._abort_at_level(2, maxlevel):
                descendantmaxlevel = maxlevel - 1 if maxlevel else None
                for descendant_ in PreOrderIterSorted._iter(child_.children, filter_, stop, descendantmaxlevel, childiter):
                    yield descendant_

class PostOrderIterSorted(six.Iterator):
    def __init__(self, node, filter_=None, stop=None, maxlevel=None, childiter=list):
        self.childiter = childiter
        self.node = node
        self.filter_ = filter_
        self.stop = stop
        self.maxlevel = maxlevel
        self.__iter = None

    def __init(self):
        node = self.node
        maxlevel = self.maxlevel
        filter_ = self.filter_ or self.__default_filter
        stop = self.stop or self.__default_stop
        childiter = self.childiter or list 
        children = [] if self._abort_at_level(1, maxlevel) else self._get_children([node], stop)
        return self._iter(children, filter_, stop, maxlevel, childiter)

    @staticmethod
    def __default_filter(node):
        # pylint: disable=W0613
        return True

    @staticmethod
    def __default_stop(node):
        # pylint: disable=W0613
        return False

    def __iter__(self):
        return self

    def __next__(self):
        if self.__iter is None:
            self.__iter = self.__init()
        return next(self.__iter)

    @staticmethod
    def _abort_at_level(level, maxlevel):
        return maxlevel is not None and level > maxlevel

    @staticmethod
    def _get_children(children, stop):
        return [child for child in children if not stop(child)]

    @staticmethod
    def _iter(children, filter_, stop, maxlevel, childiter):
        return PostOrderIterSorted.__next(children, 1, filter_, stop, maxlevel, childiter)

    @staticmethod
    def __next(children, level, filter_, stop, maxlevel, childiter):
        if not AbstractIter._abort_at_level(level, maxlevel):
            for child in childiter(children):
                grandchildren = AbstractIter._get_children(child.children, stop)
                for grandchild in PostOrderIterSorted.__next(grandchildren, level + 1, filter_, stop, maxlevel, childiter):
                    yield grandchild
                if filter_(child):
                    yield child


class mtNode(NodeMixin):
    layer: 'Optional[str]'
    name: 'str'
    featName: 'str'
    tipo: 'Optional[int]'
    tipoNodo: 'Optional[int]'
    parentId: 'Optional[str]'
    parent: 'Optional[mtNode]'
    distance: 'Optional[float]'
    distanceTotal: 'Optional[float]'
    length: 'Optional[float]'
    nivelNodo: 'Optional[int]'
    spliceCount: 'int'
    localPortCount: 'int'
    orderNumber: 'int'
    mtOrder: 'mtOrder'
    localAttenuation: 'Optional[attData]'
    jumperOutAtt: 'Optional[attData]'
    fid: 'int'
    numFibers: 'Optional[int]'
    assignedFibers: 'Optional[int]'
    usableFiberCount: 'Optional[int]'
    freeFibers: 'Optional[list[int]]'
    isEndPoint: 'Optional[bool]'
    constructionPhase: 'Optional[int]'
    popAllocation: 'dict'
    chirality: 'Optional[float]'
    groupSplice: 'Optional[int]'

    def __init__(self,name, featName, parent: 'Optional[mtNode]' =None, children=None, tipo=None, tipoNodo=None, 
                 orderNumber: 'Optional[int]' = None, distance: 'Optional[float]'=None, distanceTotal : 'Optional[float]'=None,
                 length:'Optional[float]'=None,  numFibers: 'Optional[int]' = None, nivelNodo: 'Optional[int]' = None, 
                 isEndPoint: 'Optional[bool]' = None, constructionPhase: 'Optional[int]' = None, assignedFibers: 'Optional[int]'=None, 
                 fid: 'Optional[int]'=None, chirality: 'Optional[float]'=None, groupSplice: 'Optional[int]'=None, **kwargs):
        self.spliceCount=0
        self.localPortCount=1000
        self.orderNumber=mtFeature.nullToNone(orderNumber,numHarcodes.NO_ORDER) #type:ignore
        self.mtOrder=mtOrder(self.orderNumber)
        self.distance=mtFeature.nullToNone(distance)
        self.distanceTotal=mtFeature.nullToNone(distanceTotal,0)
        self.length=mtFeature.nullToNone(length,0)
        self.nivelNodo = mtFeature.nullToNone(nivelNodo,0)
        self.groupSplice = mtFeature.nullToNone(groupSplice, None)
        self.__dict__.update(kwargs)
        self.name=name
        self.featName=featName
        self.parent=parent
        if children:
            self.children=children
        self.tipo=mtFeature.nullToNone(tipo)
        self.tipoNodo=mtFeature.nullToNone(tipoNodo)
        self.numFibers=numFibers
        self.demand = 0
        self.usedFibers = 0
        self.isEndPoint = isEndPoint
        self.constructionPhase=constructionPhase
        self.assignedFibers = mtFeature.nullToNone(assignedFibers,0)
        self.popAllocation={}
        self.fid=fid
        self.chirality = mtFeature.nullToNone(chirality,0)

    def __repr__(self):
        return f'id: {self.name}, nombre: {self.featName} '

    def getFeature(self) -> mtFeature:
        assert self.fid is not None
        feat = self.getLayer().getFeature(self.fid)
        return mtFeature(feat)
    
    def updateFeature(self, *args, **kwargs):
        assert self.fid is not None
        return self.getLayer().updateFeature(*args, **kwargs)
    
    def getLayer(self) -> mtLayer:
        assert self.layer is not None
        return mtLayers[self.layer]
    
    def getNextSplice(self, localPort: 'bool'=False, numSplices: 'int'=1) -> 'int':
        retVal=1
        if localPort:
            retVal+=self.localPortCount
            self.localPortCount+=numSplices
        else:
            retVal+=self.spliceCount
            self.spliceCount+=numSplices
        return retVal
    
    def getSpliceCount(self):
        return self.spliceCount
    
    def clearSpliceCount(self):
        self.localPortCount = 1000
        self.spliceCount=0
    
    def updateMtOrder(self,newOrder:'Optional[mtOrder]'=None, updateFeatures:bool = False ):
        if mtOrder is not None:
            self.mtOrder=copy.deepcopy(newOrder)
        self.orderNumber=self.mtOrder.value
        if updateFeatures:
            tempFeat=self.getFeature()
            tempFeat[fields.ORDEN]=self.orderNumber
            self.updateFeature(tempFeat)
    

    def updateUsableFibers(self, usableBuffers: 'Optional[int|list[int]]|tuple[int]' =None):
        myFeat=self.getFeature()
        bufSize = myFeat.getNN(fields.BUFFER_SIZE,12) #type:ignore
        maxFibers = myFeat.getNN(fields.CANT_FIBRAS)
        preOccupiedFibers = parsePreOccupiedNums(myFeat.getNN(fields.FIBRAS_PRE_OCUPADAS))
        rawSpliceBuffers = myFeat.getNN(fields.SPLICE_BUFFERS)
        spliceBuffers = None
        usableFibers:list[int] = []
        if rawSpliceBuffers and type(rawSpliceBuffers) is str and len(rawSpliceBuffers)>0:
            try:
                rawList=json.loads(rawSpliceBuffers)
                spliceBuffers=[parsePreOccupiedNums(a) for a in rawList]
            except json.JSONDecodeError as msg:
                QgsMessageLog.logMessage( f"!!Failed to decode spliceBuffer JSON {msg}", 'mtSplices.py', level=Qgis.Critical)
        # creamos la lista usableFibers (antes de considerar las fibras pre-ocupadas) - son todos los pelos del cable o 
        # la INTERSECCION de la lista usableFibers pasada contra todos los pelos
        # de esta manera, usable fibers podria incluir pelos que el cable no tiene y lo truncamos al total de pelos del cable
        usableFibers:list[int]=[]
        # si usable buffers es un entero entonces usamos la lista de listas en spliceBuffers 
        # para cambiar usableBuffers a la sub-lista correcta
        if usableBuffers and type(usableBuffers) is int and spliceBuffers:
            assert 0<usableBuffers<=len(spliceBuffers), f'Usable Buffers out of range: {usableBuffers} but should be between 1 and {len(spliceBuffers)}'
            usableBuffers=spliceBuffers[usableBuffers-1]
        # si usableBuffers es una tupla (N/L), dividimos los buffers posibles en L elementos y usamos el numero N
        if usableBuffers and type(usableBuffers) is tuple and len(usableBuffers) == 2:
            instance=usableBuffers[0]
            divider=usableBuffers[1]
            allBuffers=list(range(1,int(maxFibers/bufSize)+1))
            splitBuffers=list(chunks(allBuffers,divider))
            assert 0<instance<=divider, f'Usable buffer was a wrong tuple: {instance}/{divider}'
            usableBuffers=splitBuffers[instance-1]
        # si es una lista de buffers lo usamos directamente
        if usableBuffers  and type(usableBuffers) is list and len(usableBuffers)>0:
            oneBuf=range(1,bufSize+1)
            for i in usableBuffers:
                usableFibers+=[j+((i-1)*bufSize) for j in oneBuf]
            # me quedo solo con las fibras posibles por si se mandaron mas buffers que los que tiene el cable
            usableFibers=sorted(list(set(usableFibers).intersection(set(range(1,maxFibers+1) ))))
        else:
            usableFibers = range(1,maxFibers+1) 
        self.freeFibers = sorted(list(set(usableFibers)-set(preOccupiedFibers)))
        self.usableFiberCount=len(self.freeFibers)  # Para tener en cuenta la cantidad de fibras realmente disponibles

    def clearAttenuation(self):
        self.localAttenuation=None
        self.jumperOutAtt=None

    def updateFromFeat(self):
        if self.fid is not None:
            feat=self.getFeature()
            self.orderNumber=feat.get(fields.ORDEN)
            self.distance=feat.get(fields.DISTANCE_ALONG)
            self.distanceTotal=feat.get(fields.DISTANCE_TOTAL)
            self.length=feat.get(fields.LONG_TOTAL)
            self.numFibers=feat.getNN(fields.CANT_FIBRAS)
            self.nivelNodo=feat.getNN(fields.LEVEL)
            self.constructionPhase=feat.getNN(fields.FASE)
            self.assignedFibers=feat.getNN(fields.FIB_ASIG,0)


class mtTree():
    nodeDict: 'dict[str,mtNode]'
    def __init__(self):
        self.nodeDict={}
        layers = [layerNode,layerCable]
        rootNode=mtNode(hardcodes.ROOT_NODE,hardcodes.ROOT_NODE, root=True, layer=None, tipo=None, tipoNodo=None, parentId=hardcodes.NO_PARENT)
        self.nodeDict[hardcodes.ROOT_NODE]=rootNode

        for thisLayer in layers: 
            parentFieldName = thisLayer.parentField
            parentLayer = thisLayer.parentLayer
            assert type(parentLayer) is mtLayer  ### Usar UUid en vez de LID_FID
            for feat in thisLayer.getFeatures():
                feat=mtFeature(feat)
                nodeId= feat[fields.UUID]
                isEndPoint=None
                if feat[fields.LEVEL] == networkLevel.CENTRAL:
                    parentId=hardcodes.ROOT_NODE
                else:
                    assert parentLayer is not None and parentFieldName is not None
                    if parentLayer.friendlyName == NULL or feat[parentFieldName] == NULL:
                        parentId=hardcodes.NO_PARENT
                        # Nodos huerfanos (no asociados. Distinto del POP)
                    else:
                        parentId=feat[parentFieldName]
                        if thisLayer is layerNode:
                            foundRelation = relationsNode_Cable.getRelations(fields.TARGET_UUID,parentId, lambda x:(x[fields.NODO_UUID]==nodeId and x[fields.END_POINT] == 1))
                            if len(foundRelation)==1:
                                isEndPoint=True
                                #print(f"feat {feat.get(fields.NOMBRE)} is endopoint to {parentId}")
                tempNode=mtNode(
                                nodeId, 
                                feat.get(fields.NOMBRE),
                                fid=feat.id(),
                                layer = thisLayer.LID, 
                                tipo = thisLayer.layerType,
                                tipoNodo = feat.get(fields.TIPO),
                                root=False,
                                parentId=parentId,
                                orderNumber=feat.get(fields.ORDEN),
                                distance=feat.get(fields.DISTANCE_ALONG),
                                distanceTotal=feat.get(fields.DISTANCE_TOTAL),
                                length=feat.get(fields.LONG_TOTAL),
                                numFibers=feat.getNN(fields.CANT_FIBRAS),
                                nivelNodo=feat.getNN(fields.LEVEL),
                                isEndPoint=isEndPoint,
                                constructionPhase=feat.getNN(fields.FASE),
                                assignedFibers=feat.getNN(fields.FIB_ASIG,0),
                            )
                self.nodeDict[nodeId]=tempNode

    def getNodesAsList(self,tipoFilter=None,tipoNodoFilter=None, filter:'callable[mtNode]' = None) -> 'list[mtNode]':
        def testNode(node: mtNode):
            retval=True
            if tipoFilter is not None:
                retval&=(node.tipo==tipoFilter)
            if tipoNodoFilter is not None:
                retval&=(node.tipoNodo==tipoNodoFilter)
            if filter is not None:
                retval&=filter(node)
            return retval
        return [v for (k,v) in self.nodeDict.items() if testNode(v)]


    def clearTreeRelations(self): 
        for thisNode in self.nodeDict.values():
            if thisNode.parentId not in [hardcodes.ROOT_NODE]:
                thisNode.parent = None
    
    def clearAttenuation(self): 
        for thisNode in self.nodeDict.values():
            thisNode.clearAttenuation()

    def clearOrder(self, filter: 'callable[mtNode]' = None, updateFeatures: bool=False):
        for thisNode in self.nodeDict.values():
            if (filter is None) or filter(thisNode):
                thisNode.mtOrder.clearOrder()
                thisNode.orderNumber=thisNode.mtOrder.value
                if updateFeatures:
                    tempFeat=thisNode.getFeature()
                    tempFeat[fields.ORDEN]=NULL
                    thisNode.updateFeature(tempFeat)
    
    def clearAllSplices(self):
        for thisNode in self.nodeDict.values():
            thisNode.clearSpliceCount()

    def clearCableSplices(self):
        for thisNode in self.nodeDict.values():
            if thisNode.tipo==geomType.LINE:
                thisNode.clearSpliceCount()

    def updateUsableFibers(self, usableBuffers: 'Optional[int|list[int]]|tuple[int]' =None):
        for thisNode in self.nodeDict.values():
            if thisNode.tipo==geomType.LINE:
                thisNode.updateUsableFibers(usableBuffers=usableBuffers)
                
    def clearJointSplices(self):
        for thisNode in self.nodeDict.values():
            if thisNode.tipo==geomType.NODE:
                thisNode.clearSpliceCount()

    def buildTree(self, skipLayers=[]) -> mtNode:
        self.clearTreeRelations() #Limpio las relaciones anteriores si hubiera
        rootNode=self.nodeDict[hardcodes.ROOT_NODE]
        for nodeKey in self.nodeDict:
            if (self.nodeDict[nodeKey].layer not in skipLayers):
                parentId=self.nodeDict[nodeKey].parentId
                if parentId and parentId != hardcodes.NO_PARENT:
                    parentNode=self.nodeDict[parentId]
                    self.nodeDict[nodeKey].parent=parentNode
        return rootNode

    def reloadFeatures(self):
        for thisNode in self.nodeDict.values():
            thisNode.updateFromFeat()
    
    def getNodeDict(self) -> 'dict[str,mtNode]':
        return self.nodeDict

    def getNodeFromUUID(self,uuid: str ) -> mtNode:
        assert uuid in self.nodeDict.keys()
        return self.nodeDict[uuid]
    
    def getRootNode(self) -> mtNode:
        return self.nodeDict[hardcodes.ROOT_NODE]