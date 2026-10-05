from qgis.core import (
    QgsMapLayer,
)

from .mtConstants import *   #Importamos todas las constantes de mtConstants
from .mtLayer import *
from .mtFuncs import *
from .mtTree import mtTree, mtNode, PreOrderIterSorted, orderSort, filterDistribucion, stopStayInHub, levelOrderSort,groupSplicesOrderSort,levelGroupSpliceOrderSort
from .mtSegments import mtSegments, mtSegment
from .mtAuxFuncs import chunks, parsePreOccupiedNums
import math
import json


localSegments: mtSegments
MAX_PORTS=512
REVERSE_ALLOCATION=True

class spliceFields(Enum):
    SPLICE_CIRCUIT = 'splice_circuit'
    SPLICE_TOTALDEPTH = 'splice_totalDepth'
    SPLICE_ORDER = 'splice_order'
    SPLICE_ISROWPOP  = 'splice_isRowPOP'
    SPLICE_ISROWCTOA = 'splice_isRowCTOA'
    SPLICE_REPORT_TYPE = 'splice_report_type'
    POP_NODEFK = 'POP_nodeFK'
    POP_PORT = 'POP_port'
    POP_CABLEFIB = 'POP_cableFiberInBuffer'
    POP_CABLEBBN = 'POP_cableBufferNumber'
    POP_CABLESEQ = 'POP_cableSequencial'
    CECORE_CABLEFK = 'CEcore_cableFK'
    CECORE_CABLENAME = 'CEcore_cableName'
    CECORE_CABLETYPE = 'CEcore_cableType'
    CECORE_CABLESEGFK = 'CEcore_cableSegmentFK'
    CECORE_CABLESEGNAME = 'CEcore_cableSegmentName'
    CECORE_CABLESEGLEN = 'CEcore_cableSegmentLength'
    CECORE_CABLESEQ = 'CEcore_cableSequencial'
    CECORE_CABLEBN = 'CEcore_cableBufferNumber'
    CECORE_CABLEFIB = 'CEcore_cableFiberInBuffer'
    CESPLICE_NODEFK = 'CEsplice_nodeFK'
    CESPLICE_NODENAME = 'CEsplice_nodeName'
    CESPLICE_TYPE = 'CEsplice_type'
    CESPLICE_PORT = 'CEsplice_port'
    CEEDGE_CABLEFIB = 'CEedge_cableFiberInBuffer'
    CEEDGE_CABLEBN = 'CEedge_cableBufferNumber'
    CEEDGE_CABLESEQ = 'CEedge_cableSequencial'
    CEEDGE_CABLEFK = 'CEedge_cableFK'
    CEEDGE_CABLENAME = 'CEedge_cableName'
    CEEDGE_CABLETYPE = 'CEedge_cableType'
    CEEDGE_CABLESEGFK = 'CEedge_cableSegmentFK'
    CEEDGE_CABLESEGNAME = 'CEedge_cableSegmentName'
    CEEDGE_CABLESEGLEN = 'CEedge_cableSegmentLength'
    CTOA_CABLESEQ = 'CTOA_cableSequencial'
    CTOA_CABLEBN = 'CTOA_cableBufferNumber'
    CTOA_CABLEFIB = 'CTOA_cableFiberInBuffer'
    CTOA_NODEFK = 'CTOA_nodeFK'
    CTOA_NODENAME = 'CTOA_nodeName'
    CTOA_NODETYPE = 'CTOA_nodeType'
    CTOA_PORT = 'CTOA_port'
    SORT_ORDER = 'sortOrder'

    def __get__(self,instance,owner) -> str:
        return self.value
    
class spliceCable():
    mtNode: 'mtNode'
    bufSize: int
    seq: 'int'
    spliceCount: 'int'
    mtSegment: 'Optional[mtSegment]'
    maxFibers: 'int'
    freeFibers: 'list[int]'
    preOccupiedFibers: 'list[int]'
    reverseAllocation: bool
    popAllocation: 'list[int]'
    
    def __init__(self, mtNode: 'mtNode', seq:int, spliceCount:int =1):
        self.mtNode=mtNode
        self.bufSize=self.mtNode.getFeature().getNN(fields.BUFFER_SIZE,12) #type:ignore
        self.maxFibers = self.mtNode.getFeature().getNN(fields.CANT_FIBRAS)
        self.preOccupiedFibers = parsePreOccupiedNums(self.mtNode.getFeature().getNN(fields.FIBRAS_PRE_OCUPADAS))
        self.freeFibers=self.mtNode.freeFibers
        self.spliceCount=spliceCount
        self.seq=seq
        self.reverseAllocation=REVERSE_ALLOCATION
        self.popAllocation=[None for i in range(spliceCount)]

    def getSeq(self,spliceOffset:int=0) -> int:
        assert 0<=spliceOffset<self.spliceCount
        assert (self.seq+spliceOffset-1)<len(self.freeFibers), f'cable {self.mtNode.featName} - freeF {len(self.freeFibers)} - seq {self.seq} off: {spliceOffset} - freeflist {self.freeFibers}'
        index = (len(self.freeFibers)-(self.seq+spliceOffset)) if self.reverseAllocation else (self.seq+spliceOffset-1)
        return self.freeFibers[index]
    
    def getFIB(self, spliceOffset:int=0) -> int:
        tSeq=self.getSeq(spliceOffset)
        return (tSeq-1)%self.bufSize + 1
    
    def getBN(self,spliceOffset:int=0) -> int:
        tSeq=self.getSeq(spliceOffset)
        return math.floor((tSeq-1)/self.bufSize)+1
    
    def setSpliceCount(self, spliceCount:int=1):
        self.spliceCount=spliceCount
        self.popAllocation=[None for i in range(spliceCount)]
    
    def getMtNode(self) -> 'mtNode':
        return self.mtNode
    
    def setPopAllocation(self, spliceOffset:int=0, value:int=None,):
        assert 0<=spliceOffset<self.spliceCount, f"Offset: {spliceOffset}, count: {self.spliceCount}"
        #print(f"spliceCount:{self.spliceCount} popAlloc:{self.popAllocation}")
        self.popAllocation[spliceOffset]=value

    def getPopAllocation(self, spliceOffset:int=0):
        assert 0<=spliceOffset<self.spliceCount, f"Offset: {spliceOffset}, count: {self.spliceCount}"
        return self.popAllocation[spliceOffset]

class spliceNode():
    mtNode: 'mtNode'
    firstPort: int
    portCount: int
    popAllocation: 'list[int]'

    def __init__(self, mtNode: 'mtNode', firstPort: int, spliceCount: int = 1):
        self.mtNode = mtNode
        self.firstPort=firstPort
        self.portCount=spliceCount
        self.preOccupiedPorts = parsePreOccupiedNums(self.mtNode.getFeature().getNN(fields.PUERTOS_PRE_OCUPADOS))
        self.freePorts = sorted(list(set(range(1,MAX_PORTS+1))-set(self.preOccupiedPorts)))
        self.popAllocation=[None for i in range(spliceCount)]

    def getPort(self, portOffset:int=0) -> int:
        assert 0<=portOffset<self.portCount
        assert portOffset<MAX_PORTS
        #assert (self.firstPort+portOffset)<len(self.freePorts), f'name: {self.mtNode.name} fp {self.firstPort} of:{portOffset} len{len(self.freePorts)}'
        if self.firstPort>1000:
            return self.firstPort+portOffset
            # if firstPort is >1000 its a local port for splitters,etc// dont consider pre-occupied
        else:
            return self.freePorts[self.firstPort+portOffset-1]
    
    def setSpliceCount(self, spliceCount:int=1):
        self.portCount=spliceCount
        self.popAllocation=[None for i in range(spliceCount)]

    def getMtNode(self) -> 'mtNode':
        return self.mtNode
    
    def setPopAllocation(self, spliceOffset:int=0, value:int=None,):
        assert 0<=spliceOffset<self.portCount, f"Offset: {spliceOffset}, count: {self.portCount}"
        self.popAllocation[spliceOffset]=value

    def getPopAllocation(self, spliceOffset:int=0):
        assert 0<=spliceOffset<self.portCount, f"Offset: {spliceOffset}, count: {self.portCount}"
        return self.popAllocation[spliceOffset]

class splice():
    coreCable: 'Optional[spliceCable]'
    coreSegment: 'Optional[mtSegment]'
    spliceNode: 'spliceNode'
    edgeCable: 'Optional[spliceCable]'
    edgeSegment: 'Optional[mtSegment]'
    hop: int
    isCore: bool
    isEdge: bool
    numSplices: int
    
    def __init__(self, 
                 spliceNode: 'spliceNode', 
                 hop: int, 
                 coreCable: 'Optional[spliceCable]'=None, 
                 edgeCable: 'Optional[spliceCable]'=None,
                 isCore:bool=False,
                 numSplices:int=1 ):
        self.spliceNode=spliceNode
        self.coreCable=coreCable
        self.edgeCable=edgeCable
        self.hop = hop
        self.isCore = isCore
        self.isEdge = (hop==1)
        self.numSplices=numSplices
        if self.coreCable:
            self.coreCable.setSpliceCount(numSplices)
            self.coreSegment=localSegments.getSegmentForEndNode(self.coreCable.getMtNode().getFeature().getNN(fields.UUID), self.spliceNode.getMtNode().getFeature().getNN(fields.UUID))
        else:
            self.coreCable=None
            self.coreSegment=None
        if self.edgeCable:
            self.edgeCable.setSpliceCount(numSplices)
            self.edgeSegment=localSegments.getSegmentForStartNode(self.edgeCable.getMtNode().getFeature().getNN(fields.UUID), self.spliceNode.getMtNode().getFeature().getNN(fields.UUID))
        else:
            self.edgeCable=None
            self.edgeSegment=None
        self.spliceNode.setSpliceCount(numSplices)
    
    def getNode(self) -> 'spliceNode':
        return self.spliceNode

    def getCore(self) -> 'tuple[Optional[spliceCable],Optional[mtSegment]]':
        return self.coreCable, self.coreSegment

    def getEdge(self) -> 'tuple[Optional[spliceCable],Optional[mtSegment]]':
        return self.edgeCable, self.edgeSegment


def recursiveSplice(spliceList: 'list', currentNode: 'mtNode', edgeCable: 'Optional[spliceCable]'=None, numSplices: 'int'=1, hop: int=1,disableLocalPort: 'bool'= False):
    #print(currentNode.name, currentNode.__dict__)
    #Si no estamos en un nivel tipo NODO estamos mal
    assert currentNode.tipo==geomType.NODE
    #El primer nivel (hop==1) usa LocalPort, el resto no. Seria solo para los HUBs cuando son "leaf y no transit"
    localPort = (not disableLocalPort) and hop == 1 and (currentNode.tipoNodo in [elementType.HUB])
    thisPort=currentNode.getNextSplice(localPort=localPort, numSplices=numSplices)
    thisSpliceNode=spliceNode(currentNode,thisPort)
    coreCable=None
    lastHop=(currentNode.is_root or currentNode.tipoNodo==elementType.POP)
    #print(f"lastHop: {lastHop} - is_root:{currentNode.is_root} - {currentNode.tipoNodo} - {elementType.POP}")
    if not lastHop:
        #si no es POP o root, busco el cable core y sigo
        coreCableNode=currentNode.parent
        assert coreCableNode is not None
        coreCableStrand=coreCableNode.getNextSplice(numSplices=numSplices)
        coreCable=spliceCable(coreCableNode, coreCableStrand)
        # the parent of coreCableNode should be the next node in the hierarchy
        assert coreCableNode.parent is not None
        # the current coreCable becomes the higher level's edgeCable
        spliceList=recursiveSplice(spliceList,currentNode=coreCableNode.parent, edgeCable=coreCable, numSplices=numSplices,hop=hop+1)
        #print(spliceList)

    thisSplice=splice(thisSpliceNode, hop, coreCable, edgeCable, isCore=lastHop, numSplices=numSplices)
    spliceList.append(thisSplice)
    return spliceList


def generatePartialSplices(myTree: 'mtTree', allSplices: 'list[splice]'):
    #hubs =  PreOrderIterSorted(myTree.getRootNode(),childiter=distAlongTotSort, filter_=lambda n: (n.tipo == geomType.NODE and n.tipoNodo == elementType.HUB))
    #hubs= orderSort(myTree.getNodesAsList(tipoFilter=geomType.NODE, tipoNodoFilter=elementType.HUB),rev=True)
    hubs = levelGroupSpliceOrderSort(myTree.getNodesAsList(
                tipoFilter=geomType.NODE,
                filter=lambda x:
                    x.nivelNodo not in [networkLevel.CENTRAL]
                    and x.assignedFibers > 0
            ),
            levelRev = True,                         
            groupRev=False,
            orderRev=False
        )
            
    layerNode.startEditing()
    layerSEG.startEditing()
    layerCable.startEditing()

    for thisHub in hubs:
        aSplice=[]
        numSplices=thisHub.assignedFibers
        if numSplices>0:
            thisSplice=recursiveSplice(aSplice,thisHub,numSplices=numSplices)
            allSplices.append(thisSplice)
            hubFeat=thisHub.getFeature()
            retAllocation=populatePopAllocation(thisSplice)
            thisHub.popAllocation=retAllocation
            hubFeat[fields.ASIGNACION]=";".join(f"{k}:{v}" for k,v in retAllocation.items())
            thisHub.updateFeature(hubFeat)
            ctoJumperPopAssignment(thisHub=thisHub)

    layerNode.commitChanges()
    layerSEG.commitChanges()
    layerCable.commitChanges()

def generateSplices(myTree: 'mtTree', mySegments: 'mtSegments',fillPop: 'Optional[bool]'=True):
    global localSegments
    localSegments=mySegments

    myTree.reloadFeatures()
    myTree.buildTree()
    myTree.updateUsableFibers()
    allSplices=[]

    generatePartialSplices(myTree=myTree, allSplices=allSplices)

    occupySegmentFibersAndNodes(allSplices)

    localSegments.updateUsedFibersInDB(levels=[networkLevel.CENTRAL, networkLevel.RED_ACCESO,networkLevel.RED_ALIMENTACION ])

    layerSplices.startEditing()
    layerSplices.truncate()
    layerSplices.commitChanges()

    layerSplices.startEditing()
    thisSplices: 'list[splice]'
    for thisSplices in allSplices:
        numSplices=thisSplices[0].numSplices
        for spliceNum in range(numSplices):
            #printSplice(thisSplices, spliceNum)
            spliceFeatsByCircuit(layerSplices.L, thisSplices, spliceNum)
            spliceFeatsByCircuitAgus(layerSplices.L, thisSplices, spliceNum)
            spliceFeaturesByElement(layerSplices.L, thisSplices, spliceNum)

    layerSplices.commitChanges()


def populatePopAllocation(oneSplice: 'list[splice]') -> 'dict':
    #print(f"popAlloc {oneSplice} - {oneSplice[0].__dict__} - {oneSplice[-1].__dict__}")
    numSplices=oneSplice[-1].numSplices
    popEdgeCable, popEdgeSegment=oneSplice[0].getEdge()
    aSplice:splice
    retAllocation={}
    for spliceNum in range(numSplices):
        fiberAlloc=popEdgeCable.getSeq(spliceNum)
        #print(f"spliceNum:{spliceNum} - numSplices:{numSplices} - alloc:{fiberAlloc}")
        for aSplice in oneSplice:    
            retAllocation[spliceNum+1]=fiberAlloc #spliuceNum is 0-based. We store the allocation in 1-base
            if aSplice.coreCable:
                aSplice.coreCable.setPopAllocation(spliceNum,fiberAlloc)
            if aSplice.edgeCable:
                aSplice.edgeCable.setPopAllocation(spliceNum,fiberAlloc)
            aSplice.spliceNode.setPopAllocation(spliceNum,fiberAlloc)
    return retAllocation

def ctoJumperPopAssignment(thisHub: mtNode):
    orderToSplitterPort={1:(1,1), 2:(1,2), 3:(2,1), 4:(2,2)}
    global localSegments

    myNodes=PreOrderIterSorted(thisHub,childiter=orderSort, filter_= filterDistribucion, stop=stopStayInHub)
    thisNode: mtNode
    for thisNode in myNodes:
        fullOrder=thisNode.mtOrder.getGroupAtLevel(1)
        majorOrder=mtOrder.getMajorOrder(fullOrder)
        minorOrder=mtOrder.getMinorOrder(fullOrder)
        splitter,port=orderToSplitterPort[majorOrder]
        assert splitter in thisHub.popAllocation.keys(), f"Node {thisNode.name} with order {fullOrder} failed to access sp {splitter} in popAllocation {thisHub.popAllocation.keys()}"
        popAssignment=thisHub.popAllocation[splitter]
        
        if thisNode.tipo==geomType.LINE:
            #para drops grabamos en la capa de segmentos, campo etiquetaFibras y en el feature mismo tambien
            assignmentText= f"{popAssignment},{port}"
            thisFeat=thisNode.getFeature()
            assignmentText = f"{popAssignment},{port}"
            thisFeat[fields.ASIGNACION]=assignmentText
            thisNode.updateFeature(thisFeat)
            segments=localSegments.getSegmentsForCable(thisNode.name)
            assert len(segments)==1, f"more than 1 - ({len(segments)}) segment returned for DROP {thisNode.name}"
            segments[0].updateFeatureVal([(fields.ETIQUETA_FIBRAS, assignmentText)])
        
        elif thisNode.tipo==geomType.NODE:
            # para CTOs en el mismo elemento
            thisFeat=thisNode.getFeature()
            thisFeat[fields.ASIGNACION]=f"{popAssignment},{port}{minorOrder}"
            thisNode.updateFeature(thisFeat)
    
        

def occupySegmentFibersAndNodes(allSplices: list[list[splice]]):
    global localSegments

    nodeCounter: 'dict[str,list[int,mtFeature]]'={}
    thisSplices: 'list[splice]'
    for thisSplices in allSplices:
        numSplices=thisSplices[0].numSplices
        for spliceNum in range(numSplices):
            # get the POP cable to find the fiber allocation - at the POP level this is the EDGE CABLE
            edgeCable, edgeSegment=thisSplices[0].getEdge()
            fiberAlloc=edgeCable.getSeq(spliceNum)
            # we start after the 1st splice (after the POP)
            for thisSplice in thisSplices[1:]:
                spliceMtNode=thisSplice.getNode().getMtNode()
                nodeFk=spliceMtNode.name
                if nodeFk not in nodeCounter:
                    nodeCounter[nodeFk]=[1,spliceMtNode.getFeature()]
                else:
                    nodeCounter[nodeFk][0]+=1
                coreCable, coreSegment=thisSplice.getCore()
                upstreamSegments:list[mtSegment]
                upstreamSegments=localSegments.getUpstreamSegmentList(coreSegment)
                for thisSegment in upstreamSegments:
                    #we mark the upstream segments as occupied by this fiber
                    thisSegment.addUsedFibers(coreCable.getSeq(spliceNum),fiberAlloc)
    
    layerNode.startEditing()
    for thisNodeCount in nodeCounter.values():
        thisFeat=thisNodeCount[1]
        if thisFeat[fields.TIPO]==elementType.HUB:
            thisFeat[fields.FUSIONES]=min(thisNodeCount[0],2)
        else:
            thisFeat[fields.FUSIONES]=thisNodeCount[0]
        layerNode.updateFeature(thisFeat)
    layerNode.commitChanges()


def spliceFeatsByCircuit(layer: 'QgsMapLayer', thisSplices: 'list[splice]', spliceNum: 'int'):
    expression1 = QgsExpression('uuid(\'Id128\')')
    context = QgsExpressionContext()
    tempFeat = mtFeature(layer.fields())
    circuit=f"{thisSplices[0].getNode().getMtNode().featName}||{thisSplices[-1].getNode().getMtNode().featName}||{thisSplices[-1].getNode().getPort(spliceNum)}"
    sortMajor=thisSplices[0].getNode().getMtNode().fid*10000 +thisSplices[0].getNode().getPort()   #FID del primer nodo
    totalNodes=len(thisSplices)
    i=0
    row=0
    writeLine=False
    while i <totalNodes:
        thisNode=None
        edgeCable=None
        coreCable=None
        edgeSegment=None
        coreSegment=None

        tempFeat[spliceFields.SPLICE_CIRCUIT]=circuit
        tempFeat[spliceFields.SPLICE_TOTALDEPTH]=totalNodes
        tempFeat[spliceFields.SPLICE_ORDER]=row
        tempFeat[spliceFields.SPLICE_REPORT_TYPE]=spliceReportType.BY_CIRCUIT
        tempFeat[spliceFields.SORT_ORDER]=(sortMajor*100 + spliceNum)*100 + i

        if (i==0):
            # PARA las columnas POP
            thisNode=thisSplices[i].getNode()
            edgeCable, edgeSegment=thisSplices[i].getEdge()
            assert edgeCable is not None and thisNode is not None,f"edgeCable{edgeCable},node{thisNode}"
            tempFeat[spliceFields.SPLICE_ISROWPOP]=True
            tempFeat[spliceFields.POP_NODEFK]=thisNode.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.POP_PORT]=thisNode.getPort(spliceNum)
            tempFeat[spliceFields.POP_CABLEBBN]=edgeCable.getBN(spliceNum)
            tempFeat[spliceFields.POP_CABLEFIB]=edgeCable.getFIB(spliceNum)
            tempFeat[spliceFields.POP_CABLESEQ]=edgeCable.getSeq(spliceNum)
            # ACA Sigue la parte del cable
            # SI SI SI  - aca uso el objeto edgeCable para los campos CECORE
            # en el core no aplicamos el segmento
            # if edgeSegment is not None:
            #     tempFeat[spliceFields.CECORE_CABLESEGFK]=edgeSegment.fid
            #     tempFeat[spliceFields.CECORE_CABLESEGNAME]=edgeSegment.getSegmentSuffix()
            #     tempFeat[spliceFields.CECORE_CABLESEGLEN]=edgeSegment.segLen
            tempFeat[spliceFields.CECORE_CABLEFK]=edgeCable.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CECORE_CABLENAME]=edgeCable.getMtNode().featName
            tempFeat[spliceFields.CECORE_CABLETYPE]=edgeCable.getMtNode().getFeature().get(fields.ASSEMBLY)
            if totalNodes==1:
                # This isi a special case for POP-only splices (that the splices list has only 1 entry)
                writeLine=True
        
        elif i==(totalNodes-1):
            writeLine=True
            # PARA las columnas CTOA
            thisNode=thisSplices[i].getNode()
            coreCable, coreSegment=thisSplices[i].getCore()
            assert coreCable is not None and thisNode is not None
            tempFeat[spliceFields.SPLICE_ISROWCTOA]=True
            tempFeat[spliceFields.CTOA_NODEFK]=thisNode.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CTOA_NODENAME]=thisNode.getMtNode().featName
            tempFeat[spliceFields.CTOA_NODETYPE]=thisNode.getMtNode().getFeature().get(fields.ASSEMBLY)
            tempFeat[spliceFields.CTOA_PORT]=thisNode.getPort(spliceNum)
            tempFeat[spliceFields.CTOA_CABLEBN]=coreCable.getBN(spliceNum)
            tempFeat[spliceFields.CTOA_CABLEFIB]=coreCable.getFIB(spliceNum)
            tempFeat[spliceFields.CTOA_CABLESEQ]=coreCable.getSeq(spliceNum)
            # ACA Sigue la parte del cable
            # SI SI SI  - aca uso el objeto coreCable para los campos CEEDGE
            if coreSegment is not None:
                tempFeat[spliceFields.CEEDGE_CABLESEGFK]=coreSegment.getFeature().getNN(fields.UUID)
                tempFeat[spliceFields.CEEDGE_CABLESEGNAME]=coreSegment.getSegmentSuffix()
                tempFeat[spliceFields.CEEDGE_CABLESEGLEN]=coreSegment.segLen
            tempFeat[spliceFields.CEEDGE_CABLEFK]=coreCable.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CEEDGE_CABLENAME]=coreCable.getMtNode().featName
            tempFeat[spliceFields.CEEDGE_CABLETYPE]=coreCable.getMtNode().getFeature().get(fields.ASSEMBLY)
            
        else:
            # Para todos los cierres intermedios
            if i!=(totalNodes-2):
                # en el anteultimo salto, no hago el writeLine y no incremento la fila
                row+=1
                writeLine=True
            thisNode=thisSplices[i].getNode()
            coreCable, coreSegment=thisSplices[i].getCore()
            edgeCable, edgeSegment=thisSplices[i].getEdge()
            assert coreCable is not None and thisNode is not None and edgeCable is not None
            tempFeat[spliceFields.CECORE_CABLEFK]=coreCable.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CECORE_CABLENAME]=coreCable.getMtNode().featName
            tempFeat[spliceFields.CECORE_CABLETYPE]=coreCable.getMtNode().getFeature().get(fields.ASSEMBLY)
            tempFeat[spliceFields.CECORE_CABLESEQ]=coreCable.getSeq(spliceNum)
            tempFeat[spliceFields.CECORE_CABLEBN]=coreCable.getBN(spliceNum)
            tempFeat[spliceFields.CECORE_CABLEFIB]=coreCable.getFIB(spliceNum)
            if coreSegment is not None:
                tempFeat[spliceFields.CECORE_CABLESEGFK]=coreSegment.getFeature().getNN(fields.UUID)
                tempFeat[spliceFields.CECORE_CABLESEGNAME]=coreSegment.getSegmentSuffix()
                tempFeat[spliceFields.CECORE_CABLESEGLEN]=coreSegment.segLen

            tempFeat[spliceFields.CESPLICE_NODEFK]=thisNode.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CESPLICE_NODENAME]=thisNode.getMtNode().featName
            tempFeat[spliceFields.CESPLICE_TYPE]=thisNode.getMtNode().getFeature().get(fields.ASSEMBLY)
            tempFeat[spliceFields.CESPLICE_PORT]=thisNode.getPort(spliceNum)
            
            tempFeat[spliceFields.CEEDGE_CABLEFK]=edgeCable.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CEEDGE_CABLENAME]=edgeCable.getMtNode().featName
            tempFeat[spliceFields.CEEDGE_CABLETYPE]=edgeCable.getMtNode().getFeature().get(fields.ASSEMBLY)
            tempFeat[spliceFields.CEEDGE_CABLESEQ]=edgeCable.getSeq(spliceNum)
            tempFeat[spliceFields.CEEDGE_CABLEBN]=edgeCable.getBN(spliceNum)
            tempFeat[spliceFields.CEEDGE_CABLEFIB]=edgeCable.getFIB(spliceNum)
            if edgeSegment is not None:
                tempFeat[spliceFields.CEEDGE_CABLESEGFK]=edgeSegment.getFeature().getNN(fields.UUID)
                tempFeat[spliceFields.CEEDGE_CABLESEGNAME]=edgeSegment.getSegmentSuffix()
                tempFeat[spliceFields.CEEDGE_CABLESEGLEN]=edgeSegment.segLen

        #print(f"{circuit}-({i}/{totalNodes}) - WL:{writeLine} - Row: {tempFeat[spliceFields.SPLICE_ORDER]} ---> TF: {tempFeat}")
        if writeLine:
            context.setFeature(tempFeat)
            tempFeat[fields.UUID]=expression1.evaluate(context)
            layer.addFeature(tempFeat)
            tempFeat = mtFeature(layer.fields())
            writeLine=False
        i+=1


def spliceFeatsByCircuitAgus(layer: 'QgsMapLayer', thisSplices: 'list[splice]', spliceNum: 'int'):
    expression1 = QgsExpression('uuid(\'Id128\')')
    context = QgsExpressionContext()
    tempFeat = mtFeature(layer.fields())
    circuit=f"{thisSplices[0].getNode().getMtNode().featName}||{thisSplices[-1].getNode().getMtNode().featName}||{thisSplices[-1].getNode().getPort(spliceNum)}"
    sortMajor=thisSplices[0].getNode().getMtNode().fid*10000 +thisSplices[0].getNode().getPort()   #FID del primer nodo
    totalNodes=len(thisSplices)
    i=0
    row=1
    writeLine=False
    while i <totalNodes:
        thisNode=None
        edgeCable=None
        coreCable=None
        edgeSegment=None
        coreSegment=None

        tempFeat[spliceFields.SPLICE_CIRCUIT]=circuit
        tempFeat[spliceFields.SPLICE_TOTALDEPTH]=totalNodes
        tempFeat[spliceFields.SPLICE_ORDER]=row
        tempFeat[spliceFields.SPLICE_REPORT_TYPE]=spliceReportType.BY_CIRCUIT_V2
        tempFeat[spliceFields.SORT_ORDER]=(sortMajor*100 + spliceNum)*100 + i

        if (i==0):
            # PARA las columnas POP
            thisNode=thisSplices[i].getNode()
            edgeCable, edgeSegment=thisSplices[i].getEdge()
            assert edgeCable is not None and thisNode is not None
            tempFeat[spliceFields.SPLICE_ISROWPOP]=True
            tempFeat[spliceFields.POP_NODEFK]=thisNode.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.POP_PORT]=thisNode.getPort(spliceNum)
            tempFeat[spliceFields.POP_CABLEBBN]=edgeCable.getBN(spliceNum)
            tempFeat[spliceFields.POP_CABLEFIB]=edgeCable.getFIB(spliceNum)
            tempFeat[spliceFields.POP_CABLESEQ]=edgeCable.getSeq(spliceNum)
            # en el core no aplicamos el segmento porque no coincidiria con el resto
            # # SI SI SI  - aca uso el objeto edgeCable para los campos CECORE
            # if edgeSegment is not None:
            #     tempFeat[spliceFields.CECORE_CABLESEGFK]=edgeSegment.fid
            #     tempFeat[spliceFields.CECORE_CABLESEGNAME]=edgeSegment.getSegmentSuffix()
            #     tempFeat[spliceFields.CECORE_CABLESEGLEN]=edgeSegment.segLen
            tempFeat[spliceFields.CECORE_CABLEFK]=edgeCable.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CECORE_CABLENAME]=edgeCable.getMtNode().featName
            tempFeat[spliceFields.CECORE_CABLETYPE]=edgeCable.getMtNode().getFeature().get(fields.ASSEMBLY)
            if totalNodes==1:
                # This isi a special case for POP-only splices (that the splices list has only 1 entry)
                writeLine=True

        else:
            # Para todos los cierres intermedios incluido el final - ahora la CTOA queda en el ultimo renglon sola
            row+=1
            writeLine=True
            thisNode=thisSplices[i].getNode()
            coreCable, coreSegment=thisSplices[i].getCore()
            edgeCable, edgeSegment=thisSplices[i].getEdge()

            assert coreCable is not None and thisNode is not None 
            tempFeat[spliceFields.CECORE_CABLEFK]=coreCable.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CECORE_CABLENAME]=coreCable.getMtNode().featName
            tempFeat[spliceFields.CECORE_CABLETYPE]=coreCable.getMtNode().getFeature().get(fields.ASSEMBLY)
            tempFeat[spliceFields.CECORE_CABLESEQ]=coreCable.getSeq(spliceNum)
            tempFeat[spliceFields.CECORE_CABLEBN]=coreCable.getBN(spliceNum)
            tempFeat[spliceFields.CECORE_CABLEFIB]=coreCable.getFIB(spliceNum)
            if coreSegment is not None:
                tempFeat[spliceFields.CECORE_CABLESEGFK]=coreSegment.getFeature().getNN(fields.UUID)
                tempFeat[spliceFields.CECORE_CABLESEGNAME]=coreSegment.getSegmentSuffix()
                tempFeat[spliceFields.CECORE_CABLESEGLEN]=coreSegment.segLen

            tempFeat[spliceFields.CESPLICE_NODEFK]=thisNode.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CESPLICE_NODENAME]=thisNode.getMtNode().featName
            tempFeat[spliceFields.CESPLICE_TYPE]=thisNode.getMtNode().getFeature().get(fields.ASSEMBLY)
            tempFeat[spliceFields.CESPLICE_PORT]=thisNode.getPort(spliceNum)
            
            if edgeCable is not None:   # Para el caso de CTOA en ultimo renglon, no tiene edgeCable/segment
                tempFeat[spliceFields.CEEDGE_CABLEFK]=edgeCable.getMtNode().getFeature().getNN(fields.UUID)
                tempFeat[spliceFields.CEEDGE_CABLENAME]=edgeCable.getMtNode().featName
                tempFeat[spliceFields.CEEDGE_CABLETYPE]=edgeCable.getMtNode().getFeature().get(fields.ASSEMBLY)
                tempFeat[spliceFields.CEEDGE_CABLESEQ]=edgeCable.getSeq(spliceNum)
                tempFeat[spliceFields.CEEDGE_CABLEBN]=edgeCable.getBN(spliceNum)
                tempFeat[spliceFields.CEEDGE_CABLEFIB]=edgeCable.getFIB(spliceNum)
            if edgeSegment is not None:
                tempFeat[spliceFields.CEEDGE_CABLESEGFK]=edgeSegment.getFeature().getNN(fields.UUID)
                tempFeat[spliceFields.CEEDGE_CABLESEGNAME]=edgeSegment.getSegmentSuffix()
                tempFeat[spliceFields.CEEDGE_CABLESEGLEN]=edgeSegment.segLen
            if i==(totalNodes-1):
                # this is for the last node - CTOA
                tempFeat[spliceFields.SPLICE_ISROWCTOA]=True
                tempFeat[spliceFields.CTOA_NODEFK]=thisNode.getMtNode().getFeature().getNN(fields.UUID)
                tempFeat[spliceFields.CTOA_NODENAME]=thisNode.getMtNode().featName
                tempFeat[spliceFields.CTOA_NODETYPE]=thisNode.getMtNode().getFeature().get(fields.ASSEMBLY)
                tempFeat[spliceFields.CTOA_PORT]=thisNode.getPort(spliceNum)

        #print(f"{circuit}-({i}/{totalNodes}) - WL:{writeLine} - Row: {tempFeat[spliceFields.SPLICE_ORDER]} ---> TF: {tempFeat}")
        if writeLine:
            context.setFeature(tempFeat)
            tempFeat[fields.UUID]=expression1.evaluate(context)
            layer.addFeature(tempFeat)
            tempFeat = mtFeature(layer.fields())
            writeLine=False
        i+=1

def spliceFeaturesByElement(layer: 'QgsMapLayer', thisSplices: 'list[splice]', spliceNum: 'int'):
    expression1 = QgsExpression('uuid(\'Id128\')')
    context = QgsExpressionContext()
    circuit=f"{thisSplices[0].getNode().getMtNode().featName}||{thisSplices[-1].getNode().getMtNode().featName}||{thisSplices[-1].getNode().getPort(spliceNum)}"
    totalNodes=len(thisSplices)
    for i in range(totalNodes):
        thisNode=None
        edgeCable=None
        coreCable=None
        edgeSegment=None
        coreSegment=None
        thisNode=thisSplices[i].getNode()
        sortMajor=(thisNode.getMtNode().fid*1000 + thisNode.getPort(spliceNum))*100+spliceNum
        tempFeat = mtFeature(layer.fields())
        
        # These fields are static on the splice chain
        tempFeat[spliceFields.SPLICE_REPORT_TYPE]=spliceReportType.BY_ELEMENT
        tempFeat[spliceFields.SPLICE_CIRCUIT]=circuit
        tempFeat[spliceFields.SPLICE_TOTALDEPTH]=totalNodes
        
        # Here onwards the fields start changing in the splice chain
        tempFeat[spliceFields.SPLICE_ORDER]=i+1
        tempFeat[spliceFields.SORT_ORDER]=sortMajor

        # Populate pop Allocation (Asignacion) from the node
        tempFeat[spliceFields.POP_CABLESEQ]=thisNode.getPopAllocation(spliceNum)

        tempFeat[spliceFields.CESPLICE_NODEFK]=thisNode.getMtNode().getFeature().getNN(fields.UUID)
        tempFeat[spliceFields.CESPLICE_NODENAME]=thisNode.getMtNode().featName
        tempFeat[spliceFields.CESPLICE_TYPE]=thisNode.getMtNode().getFeature().get(fields.ASSEMBLY)
        tempFeat[spliceFields.CESPLICE_PORT]=thisNode.getPort(spliceNum)

        coreCable, coreSegment=thisSplices[i].getCore()
        if coreCable is not None:
            tempFeat[spliceFields.CECORE_CABLEFK]=coreCable.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CECORE_CABLENAME]=coreCable.getMtNode().featName
            tempFeat[spliceFields.CECORE_CABLETYPE]=coreCable.getMtNode().getFeature().get(fields.ASSEMBLY)
            tempFeat[spliceFields.CECORE_CABLESEQ]=coreCable.getSeq(spliceNum)
            tempFeat[spliceFields.CECORE_CABLEBN]=coreCable.getBN(spliceNum)
            tempFeat[spliceFields.CECORE_CABLEFIB]=coreCable.getFIB(spliceNum)
        if coreSegment is not None:
            tempFeat[spliceFields.CECORE_CABLESEGFK]=coreSegment.getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CECORE_CABLESEGNAME]=coreSegment.getSegmentSuffix()
            tempFeat[spliceFields.CECORE_CABLESEGLEN]=coreSegment.segLen

        edgeCable, edgeSegment=thisSplices[i].getEdge()
        if edgeCable is not None:
            tempFeat[spliceFields.CEEDGE_CABLEFK]=edgeCable.getMtNode().getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CEEDGE_CABLENAME]=edgeCable.getMtNode().featName
            tempFeat[spliceFields.CEEDGE_CABLETYPE]=edgeCable.getMtNode().getFeature().get(fields.ASSEMBLY)
            tempFeat[spliceFields.CEEDGE_CABLESEQ]=edgeCable.getSeq(spliceNum)
            tempFeat[spliceFields.CEEDGE_CABLEBN]=edgeCable.getBN(spliceNum)
            tempFeat[spliceFields.CEEDGE_CABLEFIB]=edgeCable.getFIB(spliceNum)
        if edgeSegment is not None:
            tempFeat[spliceFields.CEEDGE_CABLESEGFK]=edgeSegment.getFeature().getNN(fields.UUID)
            tempFeat[spliceFields.CEEDGE_CABLESEGNAME]=edgeSegment.getSegmentSuffix()
            tempFeat[spliceFields.CEEDGE_CABLESEGLEN]=edgeSegment.segLen
        
        context.setFeature(tempFeat)
        tempFeat[fields.UUID]=expression1.evaluate(context)
        layer.addFeature(tempFeat)

def printSplice(thisSplices: 'list[splice]', spliceNum: 'int'):
    circuit=f"{thisSplices[0].getNode().getMtNode().featName}||{thisSplices[-1].getNode().getMtNode().featName}||{thisSplices[-1].getNode().getPort(spliceNum)}"
    totalNodes=len(thisSplices)
    print(f"----({circuit})----")
    for i in range(totalNodes):
        thisNode=None
        edgeCable=None
        coreCable=None
        thisNode=thisSplices[i].getNode()
        print(f"({i}/{totalNodes})-->")
        coreCable=thisSplices[i].getCore()[0] #Solo quiero el coreCable
        if coreCable:
            print(f"\t\t\tCoCa ({coreCable.getMtNode().featName} fid:{coreCable.getMtNode().fid}) - Seq:{coreCable.getSeq(spliceNum)}")
        print(f"\t\tNODE ({thisNode.getMtNode().featName} fid:{thisNode.getMtNode().fid}) - Port:{thisNode.getPort(spliceNum)}")
        edgeCable=thisSplices[i].getEdge()[0]
        if edgeCable:
            print(f"\t\t\tEdCa ({edgeCable.getMtNode().featName} fid:{edgeCable.getMtNode().fid}) - Seq:{edgeCable.getSeq(spliceNum)}")
