from __future__ import annotations

from qgis.core import (
    QgsMessageLog,
    Qgis
)

import processing
from .mtConstants import *
import json
#from typing import *
from typing import Optional
#from typing import get_type_hints
from .mtLayer import *

CABLETRACE_MODEL_PROCESS='project:updateCableTraces'

class ctFields(Enum):
    
    FID = 'fid'
    UUID = 'uuid'
    CABLE_FK = 'cable_FK'
    CROSS_STREETS = 'crossStreets'
    CROSS_STREETS_FK = 'crossStreets_FK'
    AZI = 'azi'
    INFRA_INICIO = 'infraInicio_FK'
    INFRA_FIN = 'infraFin_FK'
    TRACE_ORDER = 'orden'
    JSON_GAN = 'ganancias'
    START_GAN_FK = 'startGanFk'
    END_GAN_FK = 'endGanFk'
    JSON_CAJ = 'nodos'
    START_CAJ_FK = 'startCajFk'
    END_CAJ_FK = 'endCajFk'
    
    def __get__(self,instance,owner) -> str:
        return self.value

KEYS_TO_LOAD=[ctFields.START_GAN_FK, ctFields.END_GAN_FK, ctFields.START_CAJ_FK, ctFields.END_CAJ_FK ]

class mtCableTrace():
    keysToLoad: 'list[str]'
    fid: int
    uuid: str
    startNodeFk: 'Optional[str]'
    endNodeFk: 'Optional[str]'
    startGanFk: list[str]
    endGanFk: list[str]
    startCajFk: list[str]
    endCajFk: list[str]
    azi: float
    crossStreets: int
    crossStreetsFK:list[str]

    cableFk: str
    traceOrder: int
    def __init__(self, thisFeat: mtFeature):
        self.initKeysToLoad()
        self.fid=thisFeat.id()
        self.startNodeFk=thisFeat.getNN(ctFields.INFRA_INICIO) #type:ignore
        self.endNodeFk=thisFeat.getNN(ctFields.INFRA_FIN) #type:ignore
        self.crossStreetsFK = thisFeat.getNN(ctFields.CROSS_STREETS_FK).split(',') if thisFeat.getNN(ctFields.CROSS_STREETS_FK) else [] #type:ignore
        self.crossStreets= len(thisFeat.getNN(ctFields.CROSS_STREETS_FK).split(',')) if thisFeat.getNN(ctFields.CROSS_STREETS_FK) else 0 #type:ignore
        self.azi=thisFeat.get(ctFields.AZI) #type:ignore
        self.lyrFriendlyName = layerCable.friendlyName
        self.cableFk =  thisFeat.getNN(ctFields.CABLE_FK)
        self.traceOrder=thisFeat.get(ctFields.TRACE_ORDER) #type:ignore
        self.setAttrFromJson(thisFeat.getNN(ctFields.JSON_GAN))
        self.setAttrFromJson(thisFeat.getNN(ctFields.JSON_CAJ))
       
    def getCableFeature(self) -> mtFeature:
        return  mtFeature(layerCable.getFeaturesBy(fields.UUID,self.cableFk)[0])
    
    def getStartFeature(self) -> 'Optional[mtFeature]':
        if self.startNodeFk is not None:
            return mtFeature(layerInfra.getFeaturesBy(fields.UUID,self.startNodeFk)[0])
        else:
            return None

    def getEndFeature(self) -> 'Optional[mtFeature]':
        if self.endNodeFk is not None:
            return mtFeature(layerInfra.getFeaturesBy(fields.UUID,self.endNodeFk)[0])
        else:
            return None
    
    def getLayrFriendlyNameFid(self) -> 'tuple[str,int]':
        return self.lyrFriendlyName, self.cableFk
    
    def getStartFid(self) -> 'Optional[int]':
        return self.startNodeFk
    
    def getEndFid(self) -> 'Optional[int]':
        return self.endNodeFk

    def getFeature(self) -> mtFeature:
        return mtFeature(layerCableTraces.getFeature(self.fid))
    
    def startKey(self)-> 'Optional[str]':
        return self.genStartKey(self.cableFk,self.startNodeFk)
    
    def endKey(self)-> 'Optional[str]':
        return self.genEndKey(self.cableFk,self.endNodeFk)
    
    def cableKey(self)->str:
        return self.genCableKey(self.cableFk)
    
    @staticmethod
    def genStartKey( cableFk: str, startNodeFk: 'Optional[str]') ->'Optional[str]':
        if startNodeFk is None:
            return None
        return f"C-{cableFk}-|-SN-{startNodeFk}"
    
    @staticmethod
    def genEndKey( cableFk: str, endNodeFk: 'Optional[str]')->'Optional[str]':
        if endNodeFk is None:
            return None
        return f"C-{cableFk}-|-EN-{endNodeFk}"

    @staticmethod
    def genCableKey(cableFk: str)->str:
        return f"C-{cableFk}"
    
    def setAttrFromJson(self, inJson: 'Optional[str]'):  
        if inJson is None or len(inJson)==0:
            return
        try:
            ganJson=json.loads(inJson)
            thisDict:dict
            for thisDict in ganJson:
                for thisKey in thisDict.keys():
                    if thisKey in KEYS_TO_LOAD:
                        if type(self.__dict__[thisKey]) is list:
                            self.__dict__[thisKey].append(thisDict[thisKey])
                        else:
                            self.__dict__[thisKey]=thisDict[thisKey]
                    else:
                        QgsMessageLog.logMessage( f"!!!!!! CableTrace {self.fid} with unused key:{thisKey} - JSON:{inJson}", 'mtCableTraces.py', level=Qgis.Warning)
        except json.JSONDecodeError as msg:
            QgsMessageLog.logMessage( f"!!!!!! CableTrace {self.fid} con error when decoding GANJSON!!! {msg} - JSON:{inJson}", 'mtCableTraces.py', level=Qgis.Critical)
        return
    
    def initKeysToLoad(self):
        # This function initializes the variables named in KEYS_TO_LOAD to the types defined in the annotation
        declaredTypes=self.__annotations__
        for thisKey in KEYS_TO_LOAD:
            if thisKey in declaredTypes.keys():
                #print(thisKey,declaredTypes[thisKey], type(declaredTypes[thisKey]), eval(declaredTypes[thisKey]))
                self.__dict__[thisKey]=eval(declaredTypes[thisKey])() # This will create a new object of the declared type. We need the "eval" and "()" to init the object based on the type string
            else:
                self.__dict__[thisKey]=None

    def getAngleBetween(self, otherTrace: 'mtCableTrace'):
        alfa=abs(self.azi - otherTrace.azi-180)
        return alfa if alfa<=180 else 360-alfa


class mtCableTraces():
    ctStartDict: 'dict[str,mtCableTrace]'
    ctEndDict: 'dict[str,mtCableTrace]'
    ctCableDict: 'dict[str,list[mtCableTrace]]'

    def __init__(self):
        self.clear()

    def addCableTrace(self, thisTrace: mtCableTrace):
        startKey=thisTrace.startKey
        if startKey is not None:
            self.ctStartDict[startKey]=thisTrace #type:ignore

        endKey=thisTrace.endKey
        if endKey is not None:
            self.ctEndDict[endKey]=thisTrace #type:ignore

        cableKey=thisTrace.cableKey()
        if cableKey not in self.ctCableDict:
            self.ctCableDict[cableKey]=list()
        self.ctCableDict[cableKey].append(thisTrace)

    def addCableTraceFromFeature(self, thisTraceFeature: mtFeature):
        tempFeat=mtCableTrace(thisTraceFeature)
        self.addCableTrace(tempFeat)

    def updateTable(self):
        processing.run(CABLETRACE_MODEL_PROCESS,{'cabletraces':layerCableTraces.LID})

    def loadAllFromTable(self):
        self.clear()
        thisFeat: mtFeature
        for thisFeat in layerCableTraces.getFeatures():
            self.addCableTraceFromFeature(mtFeature(thisFeat))
        self.sortAllLists()

    def sortAllLists(self):
        for thisList in self.ctCableDict.values():
            thisList.sort(key=lambda cableTrace: cableTrace.traceOrder)

    def clear(self):
        self.ctStartDict={}
        self.ctEndDict={}
        self.ctCableDict={}

    def getTracesListForCable(self,  cableFk: str) -> 'list[mtCableTrace]':
        return self.ctCableDict.get(mtCableTrace.genCableKey(cableFk), [])

    def getCableTraceForStartNode(self,  cableFk: str, startNodeFk: str) -> 'Optional[mtCableTrace]':
        thisKey=mtCableTrace.genStartKey(cableFk, startNodeFk)
        return None if thisKey is None else self.ctStartDict.get(thisKey)

    def getCableTraceForEndNode(self,  cableFk: str, endNodeFk: str) -> 'Optional[mtCableTrace]':
        thisKey=mtCableTrace.genEndKey(cableFk, endNodeFk)
        return None if thisKey is None else self.ctEndDict.get(thisKey)

    
