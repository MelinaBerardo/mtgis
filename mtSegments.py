from qgis.core import QgsGeometry

from .mtConstants import *
from .mtTree import mtTree, mtNode
from .mtLayer import *
from anytree import PostOrderIter, RenderTree

from typing import Optional

class mtSegment():
    startNodeFk: str
    endNodeFk: str
    cableFk: str
    segmentFK: str
    fid: int
    segLen: float
    startLen: float
    endLen: float
    name: str
    segNum: int
    totalLength: float
    initDistanceAlong: float
    endDistanceAlong: float
    usedFibers: list[tuple[int,int]]
    maxFibers: int
    level: networkLevel
    tasaProject: str       # 

    def __init__(self, thisFeat: mtFeature):
        self.startNodeFk=thisFeat.get(fields.NODO_INICIO) #type:ignore
        self.endNodeFk=thisFeat.get(fields.NODO_FIN) #type:ignore
        self.cableFk=thisFeat.get(fields.PARENT_CABLE) #type:ignore
        self.segmentFK=thisFeat.get(fields.UUID)
        self.fid=thisFeat.id()
        assert self.endNodeFk is not None and self.startNodeFk is not None and self.cableFk is not None, f'{self.fid} - {self.segmentFK} - {self.endNodeFk} - {self.startNodeFk} - {self.cableFk} '
        self.segLen=thisFeat.get(fields.LONG_TOTAL) #type:ignore
        self.startLen=thisFeat.get(fields.DISTANCE_INICIO) #type:ignore
        self.endLen=thisFeat.get(fields.DISTANCE_FIN) #type:ignore
        self.name=thisFeat.get(fields.NOMBRE) #type:ignore
        self.segNum=thisFeat.getNN(fields.ORDEN) #type:ignore
        self.totalLength=thisFeat.getNN(fields.LONG_TOTAL) #type:ignore
        self.initDistanceAlong=thisFeat.getNN(fields.DISTANCE_INICIO) #type:ignore
        self.endDistanceAlong=thisFeat.getNN(fields.DISTANCE_FIN) #type:ignore
        self.tasaProject=thisFeat.getNN(fields.TASA_PROJECT)   # 
        self.usedFibers=[]
        self.maxFibers = thisFeat.getNN(fields.CANT_FIBRAS)
        self.level = thisFeat.getNN(fields.LEVEL)


    def getFeature(self) -> mtFeature:
        return mtFeature(layerSEG.getFeature(self.fid))
    
    def updateFeatureVal(self, fieldTuples: 'list[tuple]'):
        thisFeat=layerSEG.getFeature(self.fid)
        for f,v in fieldTuples:
            thisFeat[f]=v
        layerSEG.updateFeature(thisFeat)
    
    def updateFeature(self,feature: mtFeature):
        layerSEG.updateFeature(feature)
    
    def getCableFeature(self) -> mtFeature:
        return mtFeature(layerCable.getFeaturesBy(fields.UUID,self.cableFk)[0])
    
    def getStartNodeFeature(self) -> mtFeature:
        return mtFeature(layerNode.getFeaturesBy(fields.UUID,self.startNodeFk)[0])
    
    def getEndNodeFeature(self) -> mtFeature:
        return mtFeature(layerNode.getFeaturesBy(fields.UUID,self.endNodeFk)[0])
    
    def getInitDistanceAlong(self) -> float:
        return self.initDistanceAlong
    
    def getEndDistanceAlong(self) -> float:
        return self.endDistanceAlong        
    
    def startKey(self)->str:
        return self.genStartKey(self.cableFk,self.startNodeFk)
    
    def endKey(self)->str:
        return self.genEndKey(self.cableFk,self.endNodeFk)
    
    def segmentKey(self)->str:
        return self.genSegmentKey(self.cableFk, self.startNodeFk, self.endNodeFk)
    
    def segmentOrderKey(self)->str:
        return self.genSegmentOrderKey(self.cableFk, self.segNum)
    
    def getSegmentSuffix(self)->str:
        tempNumm=self.segNum if self.segNum is not None else 'ZZ'
        return f'SEG{tempNumm:0>2}'
    
    def clearUsedFibers(self):
        self.usedFibers=[]
    
    def addUsedFibers(self,localFiber: int, popFiber: int):
        self.usedFibers.append((localFiber, popFiber))

    def getUsedFibersLabel(self, desc: bool=False):
        return self.genUsedFiberLabel(self.usedFibers, self.maxFibers, desc=desc)

    @staticmethod
    def parseUsedFibers(fibersInUseStr: str) -> 'list[tuple[int,int]]':
        #string de FIBRAS_EN_USO a tupla de ints '(1,1),(2,2),(3,3)' a [(1,1),(2,2),(3,3)]
        if not fibersInUseStr:
            return []
        pares = []
        for pairStr in fibersInUseStr.strip('()').split('),('): #saco el primer y ultimo parentesis y separo por '),('
            pairStr = pairStr
            if not pairStr:
                continue
            firstStr, secondStr = (p.strip() for p in pairStr.split(','))
            pares.append((int(firstStr), int(secondStr)))
        return pares
    
    @staticmethod
    def add_range(start, end, asList=False):
        if asList:
            return [start,end]
        else:
            return str(start) if start == end else f"{start}-{end}" 

    @staticmethod
    def format_ranges_local(nums: list[tuple[int,int]], max_value, desc:bool=False):
        tempNum = [k[0] for k in nums]
        return mtSegment.format_ranges_simple(tempNum, max_value=max_value, desc=desc)

    @staticmethod
    def format_ranges_simple(nums: list[int], max_value=None, desc:bool=False, asList:bool=False):
        if not nums:
            return ""

        nums = sorted(set(nums))
        parts = []

        # Add starting gap (from 1 to first element - 1)
        if not asList:
            if nums[0] > 1:
                parts.append(f"+{nums[0] - 1}FM")

        prev_end = None
        i = 0

        while i < len(nums):
            start = nums[i]
            end = start

            # Extend range
            while i + 1 < len(nums) and nums[i + 1] == end + 1:
                i += 1
                end = nums[i]

            # *Gap between ranges*
            if prev_end is not None:
                gap = start - prev_end - 1

                if gap > 0:
                    if not asList:
                        parts.append(f"+{gap}FM")

            parts.append(mtSegment.add_range(start, end, asList=asList))

            prev_end = end
            i += 1


            if desc:
                # *Reverse final output order*
                parts.reverse()


            # *Gap at the end - FM always goes at the end*
            if not asList and max_value:
                if nums[-1] < max_value:
                    gap = max_value - nums[-1]

                    if gap > 0:
                        parts.append(f"+{gap}FM")


            if asList:
                return parts
            else:
                return ",".join(parts)

    @staticmethod
    def format_ranges_both(nums:list[tuple[int,int]], max_value,desc ):
            if not nums:
                return ""

            nums = sorted(set(nums),key=lambda x:x[0])
            parts = []

            if nums[0][0] > 1:
                parts.append(f"+{nums[0][0] - 1}FM")

            prev_end = None
            i = 0

            while i < len(nums):
                start = nums[i][0]
                startPop = nums[i][1]
                end = start
                endPop = startPop


                # Extend range
                while i + 1 < len(nums) and nums[i + 1][0] == end + 1:
                    i += 1
                    end = nums[i][0]
                    endPop = nums[i][1]

                # Gap between ranges
                if prev_end is not None:
                    gap = start - prev_end - 1
                    if gap > 0:
                        parts.append(f"+{gap}FM")

                parts.append(mtSegment.add_range(startPop, endPop))
                prev_end = end
                i += 1

            # Gap at the end
            if nums[-1][0] < max_value:
                gap = max_value - nums[-1][0]
                if gap > 0:
                    parts.append(f"+{gap}FM")

            if desc:
                # Reverse final output order
                parts.reverse()

            return ",".join(parts) 
    
    @staticmethod
    def genUsedFiberLabel(fiberlist: list[tuple[int,int]], max_value: int, desc=False) -> str:
        return mtSegment.format_ranges_both(fiberlist,max_value,desc) + '\t' + mtSegment.format_ranges_local(fiberlist,max_value,desc) 


    @staticmethod
    def genStartKey(cableFK: int, startNodeFK: int) ->str:
        return f"C-{cableFK}-|-SN-{startNodeFK}"
    
    @staticmethod
    def genEndKey(cableFK: int, endNodeFK: int)->str:
        return f"C-{cableFK}-|-EN-{endNodeFK}"
    
    @staticmethod
    def genSegmentKey(cableFK: int, startNodeFK: int, endNodeFK: int)->str:
        return f"C-{cableFK}-|-SN-{startNodeFK}-|-EN-{endNodeFK}"
    
    @staticmethod
    def genSegmentOrderKey(cableFK: int, segNum: int)->str:
        return f"C-{cableFK}-|-S-{segNum}"
    
    
class mtSegments():
    startNodeDict: 'dict[str,mtSegment]'
    endNodeDict: 'dict[str,mtSegment]'
    segmentDict: 'dict[str,mtSegment]'
    segmentFkDict: 'dict[str,mtSegment]'
    segmentsByCableDict: 'dict[str,list[mtSegment]]'
    

    def __init__(self):
        self.clear()
        self.startNodeDict={}
        self.endNodeDict={}
        self.segmentDict={}
        self.segmentFkDict={}

        self.segmentsByCableDict={}

    def addSegment(self, thisSegment: mtSegment):
        self.startNodeDict[thisSegment.startKey()]=thisSegment
        self.endNodeDict[thisSegment.endKey()]=thisSegment
        self.segmentDict[thisSegment.segmentKey()]=thisSegment
        self.segmentFkDict[thisSegment.segmentFK]=thisSegment
        if thisSegment.cableFk not in self.segmentsByCableDict:
            self.segmentsByCableDict[thisSegment.cableFk]=[thisSegment]
        else:
            self.segmentsByCableDict[thisSegment.cableFk].append(thisSegment)
            #self.segmentsByCableDict[thisSegment.cableFk].sort(key=lambda x: x.segNum)

    def addSegmentFromFeature(self, thisSegmentFeature: mtFeature):
        self.addSegment(mtSegment(thisSegmentFeature))

    def clear(self):
        self.startNodeDict={}
        self.endNodeDict={}
        self.segmentDict={}
    
    def getSegment(self, segFK:str) -> 'Optional[mtSegment]':
        return self.segmentFkDict.get(segFK)

    def getSegmentForStartNode(self, cableFK: int, startNodeFK: int) -> 'Optional[mtSegment]':
        return self.startNodeDict.get(mtSegment.genStartKey(cableFK,startNodeFK))
    
    def getSegmentForEndNode(self, cableFK: int, endNodeFK: int) -> 'Optional[mtSegment]':
        return self.endNodeDict.get(mtSegment.genEndKey(cableFK,endNodeFK))
    
    def getSegmentByDistanceAlong(self, cableFK: int, endNodeFK: int) -> 'Optional[mtSegment]':
        return self.endNodeDict.get(mtSegment.genEndKey(cableFK,endNodeFK))
    
    def getSegmentForId(self, cableFK: int, startNodeFK:int, endNodeFK: int) -> 'Optional[mtSegment]':
        return self.segmentDict.get(mtSegment.genSegmentKey(cableFK, startNodeFK, endNodeFK))
    
    def getSegmentsForCable(self, cableFK):
        list=self.segmentsByCableDict.get(cableFK)
        return sorted(list, key=lambda x:x.segNum)
    
    def getUpstreamSegmentList(self, startSegment: mtSegment) -> 'list[mtSegment]':
        # Includes the segment itself in a sorted list
        wholeList=self.segmentsByCableDict[startSegment.cableFk]
        return wholeList[:startSegment.segNum]     

    def getCumulativeDistanceFromEndNode(self, cableFK: int, endNodeFK: int) -> float:
        cumDistance: float=0
        thisSegment=None
        while True:
            thisSegment=self.getSegmentForEndNode(cableFK,endNodeFK)
            if thisSegment is None:
                break
            cumDistance+=thisSegment.totalLength
            if thisSegment.segNum==1:
                break
            endNodeFK=thisSegment.startNodeFk #this way we get the next segment (towards the POP) on the same cable

        return cumDistance
    
    def loadFromTable(self, layer: mtLayer):
        for thisFeat in layer.getFeatures():
            thisFeat=mtFeature(thisFeat)
            self.addSegmentFromFeature(thisFeat)
        # Sort segments in cable dict by segment number
        for segmentList in self.segmentsByCableDict.values():
            segmentList.sort(key=lambda x:x.segNum)
    
    def updateUsedFibersInDB(self,levels: 'list[networkLevel]'=None):
        layerSEG.startEditing()
        for thisSegment in self.segmentDict.values():
            if levels and thisSegment.level not in levels:
                continue
            usedFibersStr = ",".join([f"({a},{b})" for a,b in thisSegment.usedFibers])
            fiberLabel = thisSegment.getUsedFibersLabel()
            thisSegment.updateFeatureVal([(fields.FIBRAS_EN_USO,usedFibersStr),(fields.ETIQUETA_FIBRAS,fiberLabel)])
        layerSEG.commitChanges()



def longCablesParent():
    layerSEG.startEditing()
    
    for seg in layerSEG.getFeatures():

        cableParent= layerCable.getFeaturesBy(fields.UUID,seg[fields.PARENT_CABLE])[0]
        seg[fields.LONG_CABLE]= cableParent[fields.LONG_TOTAL]
        layerSEG.updateFeature(seg)
    layerSEG.commitChanges()
        
def segmentCable(myTree: 'mtTree',layerObj: 'mtLayer', layerSeg: 'mtLayer'):

    camposEnComun =list(set(layerObj.fields().names()).intersection(layerSeg.fields().names()))
    camposEnComun.remove(fields.UUID)
    camposEnComun.remove(fields.FID)


    rootNode=myTree.buildTree()
    layerSeg.startEditing()
    layerSeg.truncate()
    layerSeg.commitChanges()

    layerSeg.startEditing()
    layerObj.startEditing()

    item: 'mtNode'

    expression1 = QgsExpression('uuid(\'Id128\')')
    context = QgsExpressionContext()

    for item in PostOrderIter(rootNode):

        if item.layer != layerObj.LID:
            continue        

        relatedNodes: 'list[mtNode]'
        relatedNodes = [child for child in sorted(item.children, key=lambda child: child.distance)]
        relatedNodes.insert(0,item.parent) #type:ignore 
        pairs = [(relatedNodes[i-1],relatedNodes[i]) for i in range(1,len(relatedNodes))]

        contadorSeg = 0
        longCable = 0
        cable = item.getFeature()

        try:
            if cable.geometry() is None:
                print(f"Cable con geom NULL: {cable}")
            else:
                cablePoints = cable.geometry().asPolyline()
        except Exception as e:
            print(f"Error procesando cable {cable}: {e}")


        for nodes in pairs:
            #aca voy armando cada uno de los segmentos del cable

            startFeat = nodes[0].getFeature()
            endFeat = nodes[1].getFeature()

            startPoint=None
            endPoint=None
            for point in cablePoints:

                if QgsGeometry.fromPointXY(point).equals(startFeat.geometry()):
                    startPoint = cablePoints.index(point)
                
                if QgsGeometry.fromPointXY(point).equals(endFeat.geometry()):
                    endPoint = cablePoints.index(point)
            
            assert startPoint is not None and endPoint is not None, \
                     f"Cable {cable[fields.UUID]} | startNode {startFeat[fields.UUID]} | endNode {endFeat[fields.UUID]}"
            
            contadorSeg += 1
            newSegment = mtFeature(layerSeg.fields())
            for nombreCampo  in camposEnComun:
                newSegment[nombreCampo]=cable[nombreCampo]
            context.setFeature(newSegment)
            newSegment[fields.UUID]=expression1.evaluate(context)
            newSegment[fields.ORDEN]=contadorSeg
            newSegment[fields.SEGMENTO]=f'SEG{contadorSeg:0>2d}'
            segmentName = f'{cable[fields.NOMBRE]}SEG{contadorSeg:0>2d}' if cable[fields.CANT_FIBRAS] != 1 else f'{cable[fields.NOMBRE]}'
            newSegment[fields.NOMBRE]=segmentName
            newSegment[fields.NODO_INICIO]=startFeat[fields.UUID]
            newSegment[fields.NODO_FIN]=endFeat[fields.UUID]            
            newSegment[fields.RECORRIDO]=endFeat[fields.DISTANCE_ALONG]-startFeat[fields.DISTANCE_ALONG]          
            newSegment[fields.PARENT_CABLE]=cable[fields.UUID]
            newSegment[fields.FASE]=cable[fields.FASE]
            newSegment[fields.DISTANCE_INICIO]=startFeat[fields.DISTANCE_ALONG]
            newSegment[fields.DISTANCE_FIN]=endFeat[fields.DISTANCE_ALONG]
            newSegment[fields.TASA_PROJECT]=cable[fields.TASA_PROJECT]
            newSegment[fields.OFFSET]=cable[fields.OFFSET]
            newSegment.setGeometry(QgsGeometry.fromPolylineXY(cablePoints[startPoint : endPoint+1]))
            ganancias = layerNode.getFeaturesByDistanceAlong(fields.PARENT_CABLE,cable[fields.UUID],startFeat[fields.DISTANCE_ALONG],endFeat[fields.DISTANCE_ALONG])
            longGanancias = 0             
            for ganancia in ganancias:
                longGanancias += mtFeature.nullToNone(ganancia[fields.LONG_CABLE],GANANCIA_TECNICA)
                    
            longSegmento = newSegment.calculateSegmentLength(longGanancias)
       
            newSegment[fields.LONG_TOTAL]=longSegmento
            longCable = longCable + longSegmento

            layerSeg.addFeature(newSegment)

        try:
            startFeat = pairs[0][0].getFeature()
            endFeat = pairs[-1][1].getFeature()
        except:
            f'ERROR en cable Con UUID: {print(cable[fields.UUID])}'
        cable[fields.NODO_INICIO] = startFeat[fields.UUID]
        cable[fields.NODO_FIN] = endFeat[fields.UUID]
        cable[fields.LONG_TOTAL] = longCable
        layerObj.updateFeature(cable)
    

    layerSeg.commitChanges()
    layerObj.commitChanges()

    longCablesParent()
    


