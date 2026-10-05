from qgis.core import (
    QgsMapLayer,
)

from .mtConstants import *   #Importamos todas las constantes de mtConstants
from .mtLayer import *
from .mtFuncs import *
from .mtTree import mtTree, mtNode, filterCablesCentralAccAlim 
from .mtSegments import mtSegment
from enum import Enum
import textwrap


class spliceGrpFields(Enum):
    #original splice fields
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
    #added spliceGroupby fields
    CORE_MIN = 'core_min'
    CORE_MAX = 'core_max'
    EDGE_MIN = 'edge_min'
    EDGE_MAX = 'edge_max'
    POP_MIN = 'pop_min'
    POP_MAX = 'pop_max'
    COUNT = 'row_count'
    CORE_SEQLIST = 'core_seqlist'
    #added for passthrough connections
    IS_PASSTHROUGH = 'is_passthrough'
    IS_GANANCIA = 'is_ganancia'
    GANANCIA_HUB = 'ganancia_hub'

    def __get__(self,instance,owner) -> str:
        return self.value

SPLICE_QUERY="""
select 
        CEsplice_nodeFK,
        CEcore_cableFK,
        CEedge_cableFK,
        CEcore_cableSegmentFK,
        CEedge_cableSegmentFK,
        min(CEsplice_nodeName) AS CEsplice_nodeName,
        min(CEcore_cableName) AS CEcore_cableName,
        min(POP_cableSequencial) as pop_min,
        max(POP_cableSequencial) as pop_max,
        CEcore_cableBufferNumber, 
        min(CEcore_cableSequencial) as core_min,
        max(CEcore_cableSequencial) as core_max, 
        min(CEedge_cableName) AS CEedge_cableName,
        min(CEedge_cableSequencial) as edge_min,
        max(CEedge_cableSequencial) as edge_max,
        count(*) as row_count,
        FALSE as is_passthrough,
        FALSE as is_ganancia
from Splices
where splice_report_type=1
group by  
        CEsplice_nodeFK, 
        CEcore_cableFK, 
        CEcore_cableBufferNumber, 
        CEedge_cableFK,
        CEcore_cableSegmentFK,
        CEedge_cableSegmentFK
order by 
        CEsplice_nodeFK, CEcore_cableBufferNumber, pop_min
"""

SPLICE_QUERY_NOHUB="""
with filteredsplices AS (
        select 
                Cables.nivel as edge_level,
                Splices.CEsplice_nodeFK AS CEsplice_nodeFK,
                Splices.CEcore_cableFK AS CEcore_cableFK,
                CASE
                        WHEN Cables.nivel >=30 THEN NULL
                        ELSE Splices.CEedge_cableFK
                END AS CEedge_cableFK,
                Splices.CEcore_cableSegmentFK AS CEcore_cableSegmentFK,
                CASE
                        WHEN Cables.nivel >=30 THEN NULL
                        ELSE Splices.CEedge_cableSegmentFK
                END AS CEedge_cableSegmentFK,
                Splices.CEsplice_nodeName AS CEsplice_nodeName,
                Splices.CEcore_cableName AS CEcore_cableName,
                Splices.POP_cableSequencial AS POP_cableSequencial,
                Splices.CEcore_cableBufferNumber AS CEcore_cableBufferNumber, 
                Splices.CEcore_cableSequencial AS CEcore_cableSequencial,
                CASE
                        WHEN Cables.nivel >=30 THEN NULL
                        ELSE Splices.CEedge_cableName
                END AS CEedge_cableName,
                CASE
                        WHEN Cables.nivel >=30 THEN NULL
                        ELSE Splices.CEedge_cableSequencial
                END AS CEedge_cableSequencial

        from Splices, Cables
        where Splices.CEedge_cableFK = Cables.UUID  and Splices.splice_report_type=1
)
select 
        edge_level,
        CEsplice_nodeFK,
        CEcore_cableFK,
        CEedge_cableFK,
        CEcore_cableSegmentFK,
        CEedge_cableSegmentFK,
        min(CEsplice_nodeName) AS CEsplice_nodeName,
        min(CEcore_cableName) AS CEcore_cableName,
        min(POP_cableSequencial) as pop_min,
        max(POP_cableSequencial) as pop_max,
        CEcore_cableBufferNumber, 
        min(CEcore_cableSequencial) as core_min,
        max(CEcore_cableSequencial) as core_max, 
        min(CEedge_cableName) AS CEedge_cableName,
        min(CEedge_cableSequencial) as edge_min,
        max(CEedge_cableSequencial) as edge_max,
        count(*) as row_count,
        FALSE as is_passthrough,
        FALSE as is_ganancia
from filteredsplices
group by  
        CEsplice_nodeFK, 
        CEcore_cableFK, 
        CEcore_cableBufferNumber, 
        CEedge_cableFK,
        CEcore_cableSegmentFK,
        CEedge_cableSegmentFK
order by 
        CEsplice_nodeFK, CEcore_cableBufferNumber, pop_min
"""

def getSummarySplices(skipHubs:bool=False):

    rowDict = {}
    spliceDict={}

    vlayer = QgsVectorLayer(f"?query={SPLICE_QUERY_NOHUB if skipHubs else SPLICE_QUERY}", "summary_splices", "virtual")
    if not vlayer.isValid():
        raise RuntimeError(f"Capa virtual de Splices inválida: {vlayer.error().summary()}")
    features = vlayer.getFeatures()
    field_names = [field.name() for field in vlayer.fields()]

    for feature in features:
        featName=feature[spliceGrpFields.CESPLICE_NODEFK]
        if featName not in spliceDict:
            spliceDict[featName]=[]
        for field in field_names:
            rowDict[field] = feature[field]
        spliceDict[featName].append(rowDict)
        rowDict = {}
    
    return spliceDict

SPLICE_USAGE_QUERY="""
select 
        CEsplice_nodeFK,
        CEcore_cableFK,
        min(CEsplice_nodeName) AS CEsplice_nodeName,
        GROUP_CONCAT(CEcore_cableSequencial, ',') AS core_seqlist,
        count(*) as row_count
from Splices
where splice_report_type=1
group by  
        CEsplice_nodeFK, 
        CEcore_cableFK 
order by 
        CEsplice_nodeFK
"""

SPLICE_USAGE_QUERY_NOHUB="""
with filteredsplices AS (
        select 
                Cables.nivel as edge_level,
                Splices.CEsplice_nodeFK AS CEsplice_nodeFK,
                Splices.CEcore_cableFK AS CEcore_cableFK,
                CASE
                        WHEN Cables.nivel >=30 THEN NULL
                        ELSE Splices.CEedge_cableFK
                END AS CEedge_cableFK,
                Splices.CEcore_cableSegmentFK AS CEcore_cableSegmentFK,
                CASE
                        WHEN Cables.nivel >=30 THEN NULL
                        ELSE Splices.CEedge_cableSegmentFK
                END AS CEedge_cableSegmentFK,
                Splices.CEsplice_nodeName AS CEsplice_nodeName,
                Splices.CEcore_cableName AS CEcore_cableName,
                Splices.POP_cableSequencial AS POP_cableSequencial,
                Splices.CEcore_cableBufferNumber AS CEcore_cableBufferNumber, 
                Splices.CEcore_cableSequencial AS CEcore_cableSequencial,
                CASE
                        WHEN Cables.nivel >=30 THEN NULL
                        ELSE Splices.CEedge_cableName
                END AS CEedge_cableName,
                CASE
                        WHEN Cables.nivel >=30 THEN NULL
                        ELSE Splices.CEedge_cableSequencial
                END AS CEedge_cableSequencial

        from Splices, Cables
        where Splices.CEedge_cableFK = Cables.UUID  and Splices.splice_report_type=1
)
select 
        CEsplice_nodeFK,
        CEcore_cableFK,
        min(CEsplice_nodeName) AS CEsplice_nodeName,
        GROUP_CONCAT(CEcore_cableSequencial, ',') AS core_seqlist,
        count(*) as row_count
from filteredsplices
group by  
        CEsplice_nodeFK, 
        CEcore_cableFK 
order by 
        CEsplice_nodeFK
"""

def getGroupedSplices(skipHubs:bool=False):
    rowDict = {}
    spliceDict={}

    vlayer = QgsVectorLayer(f"?query={SPLICE_USAGE_QUERY_NOHUB if skipHubs else SPLICE_USAGE_QUERY}", "summary_splices", "virtual")
    if not vlayer.isValid():
        raise RuntimeError(f"Capa virtual de Splices (uso) inválida: {vlayer.error().summary()}")
    features = vlayer.getFeatures()
    field_names = [field.name() for field in vlayer.fields()]

    for feature in features:
        featName=feature[spliceGrpFields.CESPLICE_NODEFK]
        if featName not in spliceDict:
            spliceDict[featName]=[]
        for field in field_names:
            if field==spliceGrpFields.CORE_SEQLIST:
                if feature[field]==NULL:
                    tempSet=set()
                else:
                    # la lista de fibras en uso la convierto a un set 
                    tempSet=set(str(feature[field]).split(','))
                rowDict[field] = {int(item) for item in tempSet}
            else:
                rowDict[field] = feature[field]
        spliceDict[featName].append(rowDict)
        rowDict = {}
    return spliceDict

def buildCompactNodeBody(spliceName, inCableName, outCableName):
    """
    Bloque compacto: solo nombre, assembly y direccion, con un unico
    punto de entrada y uno de salida. Se usa para ganancias tecnicas
    y para nodos con un solo cable de entrada y un solo cable de salida.
    """
    spliceFeat=layerNode.featureCache[spliceName]
    spliceLabel=spliceFeat[fields.NOMBRE]
    spliceSize=spliceFeat[fields.ASSEMBLY]
    spliceAddress="<BR/>".join(textwrap.wrap(f"{spliceFeat[fields.DIRECCION]} - {spliceFeat[fields.NUMERACION]}",width=20))

    inLines=""
    outLines=""
    if inCableName != NULL:
        inLines=f"""
            "{inCableName}_IN" [label="", shape=point]
            "{inCableName}_IN" -> "{spliceName}":"PT":w"""
    if outCableName != NULL:
        outLines=f"""
            "{outCableName}_OUT" [label="", shape=point]
            "{spliceName}":"PT":e -> "{outCableName}_OUT\""""

    return f"""
        subgraph "cluster_{spliceName}"{{
            "{spliceName}"[
            label=<
<TABLE BORDER="1" CELLBORDER="0" CELLPADDING="0" CELLSPACING="0">
    <TR><TD COLSPAN="3" CELLPADDING="10"><B>{spliceLabel}</B><BR/>{spliceSize}</TD></TR>
    <HR/>
    <TR><TD PORT="PT" COLSPAN="3" CELLPADDING="10"></TD></TR>
    <TR><TD COLSPAN="3" CELLPADDING="10">{spliceAddress}</TD></TR>
</TABLE>>];{inLines}{outLines}
        }}
    """

def populateDummyNodeTemplate(myNodeSplices:list[dict]):

    if len(myNodeSplices)!=1:
        print("Mas de 1 renglon para una ganancia u otro nodo passthrough - algo esta mal")
        return "", [], [], [], []
    spliceName=myNodeSplices[0][spliceGrpFields.CESPLICE_NODEFK]
    inCableSegs=[]
    outCableSegs=[]
    inCables=[]
    outCables=[]
    inCableName=NULL
    outCableName=NULL

    for thisRow in myNodeSplices:
        inCableFK=thisRow[spliceGrpFields.CECORE_CABLEFK]
        outCableFK=thisRow[spliceGrpFields.CEEDGE_CABLEFK]
        inCableName=thisRow[spliceGrpFields.CECORE_CABLESEGFK]
        outCableName=thisRow[spliceGrpFields.CEEDGE_CABLESEGFK]
        if inCableName != NULL:
            inCables.append(inCableFK)
            inCableSegs.append(inCableName)
        if outCableName != NULL:
            outCables.append(outCableFK)
            outCableSegs.append(outCableName)

    return  buildCompactNodeBody(spliceName, inCableName, outCableName), inCableSegs, outCableSegs, inCables, outCables

def populateNodeTemplate(myNodeSplices:list[dict],skipHubs:bool=False):
    
    #SPLICE_PASSTHROUGH_ROW=lambda: f"""<TR><TD BORDER="0" PORT="{portName}_L" WIDTH="20"></TD><TD BORDER="1" WIDTH="100"><B>{portLabel}</B></TD><TD BORDER="0" PORT="{portName}_R" WIDTH="20"></TD></TR>\n"""
    SPLICE_PASSTHROUGH_ROW=lambda: f"""<TR><TD BORDER="0" PORT="{portName}_L" WIDTH="20">{portLeftLabel}</TD><TD BORDER="1" WIDTH="100"><B>{portLabel}</B></TD><TD BORDER="0" PORT="{portName}_R" WIDTH="20">{portRightLabel}</TD></TR>\n"""
    SPLICE_PORT_ROW=lambda: f"""<TR><TD BORDER="0" PORT="{portName}_L" WIDTH="20">{portLeftLabel}</TD><TD BORDER="1" WIDTH="100"><B>{portLabel}</B></TD><TD BORDER="0" PORT="{portName}_R" WIDTH="20">{portRightLabel}</TD></TR>\n"""
    SPLICE_IN_CABLE_ROW=lambda: f""" "{inCableName}_IN" [label="", shape=point]\n"""
    SPLICE_OUT_CABLE_ROW=lambda: f""" "{outCableName}_OUT" [label="", shape=point]\n"""

    #SPLICE_IN_PORT_ROW=lambda passthrough: f""" "{inCableName}_IN" -> "{spliceName}":"{portName}_L":{'e' if passthrough else 'w'};\n"""
    #SPLICE_OUT_PORT_ROW=lambda passthrough: f""" "{spliceName}":"{portName}_R":{'w' if passthrough else 'e'} -> "{outCableName}_OUT";\n"""

    SPLICE_IN_PORT_ROW=lambda passthrough: f""" "{inCableName}_IN" -> "{spliceName}":"{portName}_L":w;\n"""
    SPLICE_OUT_PORT_ROW=lambda passthrough: f""" "{spliceName}":"{portName}_R":e -> "{outCableName}_OUT";\n"""

    SUBGRAPH_BODY=lambda: f"""
        subgraph "cluster_{spliceName}"{{
            "{spliceName}" [
                label=<
<TABLE BORDER="1" CELLBORDER="0" CELLPADDING="0" CELLSPACING="0">
    <TR><TD COLSPAN="3" CELLPADDING="10"><B>{spliceLabel}</B><BR/>{spliceSize}</TD></TR>
      <HR/>
    <TR><TD COLSPAN="3" CELLPADDING="10"><B><U>PELOS PASANTES</U></B></TD></TR>
{splicePasstrhoughTable}
    <TR><TD COLSPAN="3" CELLPADDING="10"></TD></TR>
      <HR/>
    <TR><TD COLSPAN="3" CELLPADDING="10"><B><U>BANDEJA EMPALMES</U></B></TD></TR>
{splicePortTable}
    <TR><TD COLSPAN="3" CELLPADDING="10" WIDTH="120" HEIGHT="80" FIXEDSIZE="TRUE">{spliceAddress}</TD></TR>
</TABLE>>
                ];
{spliceInCableTable}
{spliceOutCableTable}
            {{
{spliceInPorts}
{spliceOutPorts}
            }}
    }}
    """

    if len(myNodeSplices)<1:
        return ""
    spliceName=myNodeSplices[0][spliceGrpFields.CESPLICE_NODEFK]
    spliceFeat=layerNode.featureCache[spliceName]
    spliceLabel=spliceFeat[fields.NOMBRE]
    spliceSize=spliceFeat[fields.ASSEMBLY]
    spliceAddress="<BR/>".join(textwrap.wrap(f"{spliceFeat[fields.DIRECCION]} - {spliceFeat[fields.NUMERACION]}",width=20))
    inCableSegs=[]
    outCableSegs=[]
    inCables=[]
    outCables=[]
    splicePortTable=""
    splicePasstrhoughTable=""
    spliceInCableTable=""
    spliceOutCableTable=""
    spliceInPorts=""
    spliceOutPorts=""

    portName=None
    portLeftLabel=None
    portRightLabel=None
    inCableName=None
    outCableName=None

    myNodeSplices=sorted(myNodeSplices,key=lambda x:(-x[spliceGrpFields.IS_PASSTHROUGH],x[spliceGrpFields.POP_MIN]))
    for thisRow in myNodeSplices:
        inCableFK=thisRow[spliceGrpFields.CECORE_CABLEFK]
        outCableFK=thisRow[spliceGrpFields.CEEDGE_CABLEFK]
        inCableName=thisRow[spliceGrpFields.CECORE_CABLESEGFK]
        outCableName=thisRow[spliceGrpFields.CEEDGE_CABLESEGFK]
        passthrough=thisRow[spliceGrpFields.IS_PASSTHROUGH]==True
        if thisRow[spliceGrpFields.POP_MIN]==0 and thisRow[spliceGrpFields.POP_MAX]==0 and passthrough:
            # es passthrough y no hay continuacion
            # salteamos este row
            continue
        portNamePrefix="PT" if passthrough else "P"
        portName=None
        portLeftLabel="  * "
        portRightLabel=" *  "
        outCableFeat=None

        if inCableName != NULL:
            if inCableFK not in inCables:
                inCables.append(inCableFK)
            if inCableName not in inCableSegs:
                inCableSegs.append(inCableName)
            portName=f"{portNamePrefix}{thisRow[spliceGrpFields.POP_MIN]}_{thisRow[spliceGrpFields.POP_MAX]}"
            portLabel=f"{thisRow[spliceGrpFields.POP_MIN]}-{thisRow[spliceGrpFields.POP_MAX]}"
            if thisRow[spliceGrpFields.CORE_MIN]!=NULL:
                portLeftLabel="----"
            if thisRow[spliceGrpFields.EDGE_MIN]!=NULL:
                portRightLabel="----"
            if passthrough:
                splicePasstrhoughTable+=SPLICE_PASSTHROUGH_ROW()
            else:
                splicePortTable+=SPLICE_PORT_ROW()
            spliceInPorts+=SPLICE_IN_PORT_ROW(passthrough)
        if  outCableName != NULL:
            outCableFeat=layerCable.featureCache[outCableFK]
            if skipHubs and outCableFeat[fields.LEVEL]==networkLevel.RED_ALIMENTACION:
                continue
            if outCableFK not in outCables:
                outCables.append(outCableFK)
            if outCableName not in outCableSegs:
                outCableSegs.append(outCableName)
            if portName:
                spliceOutPorts+=SPLICE_OUT_PORT_ROW(passthrough)

    # Nodo con un solo cable de entrada y un solo cable de salida:
    # se dibuja compacto, igual que las ganancias tecnicas
    if len(inCableSegs)==1 and len(outCableSegs)==1:
        return buildCompactNodeBody(spliceName, inCableSegs[0], outCableSegs[0]), inCableSegs, outCableSegs, inCables, outCables
    
    for inCableName in inCableSegs:
        spliceInCableTable+=SPLICE_IN_CABLE_ROW()
    
    for outCableName in outCableSegs:
        spliceOutCableTable+=SPLICE_OUT_CABLE_ROW()

    return  SUBGRAPH_BODY(), inCableSegs, outCableSegs, inCables, outCables



def getFullGraph(myTree:mtTree, mySegments:mtSegments, skipHubs:bool = False): 

    GRAPH_HEADER="""
    digraph G {
    nodesep=1.5;
    ranksep=1;
    rankdir="LR";
    splines=line;
    clusterrank=local;
    margin=0;
    compound=true;
    node[width=0.1, shape=none, fontname="Courier New"];
    edge[style=solid, arrowhead=none, fontname="Courier New"];
    """

    CABLE_TABLE_ROW=lambda: f""" "{cableNameOut}_OUT" -> "{cableNameIn}_IN" [headlabel="{cableLabel}", taillabel="{cableLabel}"]\n"""

    GRAPH_FOOTER=lambda: f"""
    edge[style=solid, penwidth=1, minlen=5];
    {cableTable}
    }}
    """
    layerCable.updateCacheDict()
    layerNode.updateCacheDict()

    spliceNameSrc=None
    spliceNameDst=None
    cableName=None
    cableNameOut=None
    cableNameIn=None
    cableLabel=None

    summarySplices=getSummarySplices(skipHubs=skipHubs)
    groupedSplices=getGroupedSplices(skipHubs=skipHubs)

    if skipHubs:
        filter=filterCablesCentralAcc
    else:
        filter=filterCablesCentralAccAlim

    cables=myTree.getNodesAsList(filter=filter)
    
    for thisCable in cables:
        thisSplice:mtNode
        orderedSplices=sorted(thisCable.children,key=lambda x:x.distance)
        if len(orderedSplices)>1:
            allFibers=set(range(1,thisCable.numFibers+1))
            for thisSplice in orderedSplices:
                coreSegment=mySegments.getSegmentForEndNode(thisCable.name,thisSplice.name)
                edgeSegment=mySegments.getSegmentForStartNode(thisCable.name,thisSplice.name)
                baseDict={
                        spliceGrpFields.CESPLICE_NODEFK:thisSplice.name,
                        spliceGrpFields.IS_PASSTHROUGH:True,
                        spliceGrpFields.IS_GANANCIA:False,
                        spliceGrpFields.GANANCIA_HUB:False,
                        spliceGrpFields.CECORE_CABLEFK:thisCable.name,
                        spliceGrpFields.CECORE_CABLESEGFK:coreSegment.segmentFK,
                        spliceGrpFields.CEEDGE_CABLEFK:NULL if not edgeSegment else thisCable.name,
                        spliceGrpFields.CEEDGE_CABLESEGFK:NULL if not edgeSegment else edgeSegment.segmentFK,
                    }
                if thisSplice.tipoNodo in [elementType.GANANCIA_TECNICA_ACCESO]:
                    # El caso es si son ganancias
                    tempDict=baseDict.copy()
                    tempDict.update({
                        spliceGrpFields.IS_GANANCIA:True,
                        spliceGrpFields.GANANCIA_HUB:not filterCentralAcc(thisCable)
                    })
                    summarySplices[thisSplice.name]=[tempDict]
                else:
                                   
                    nodeGroups = groupedSplices.get(thisSplice.name)
                    if nodeGroups:
                        assert nodeGroups[0][spliceGrpFields.CECORE_CABLEFK]==thisCable.name, f"Cable no coincide en nodo {thisSplice.name}"
                        localFibers = nodeGroups[0][spliceGrpFields.CORE_SEQLIST]
                    else:
                        # nodo sin empalmes: todas las fibras son pasantes
                        localFibers = set()
                    deltaFibers=allFibers-localFibers
                    deltaFiberRanges=mtSegment.format_ranges_simple(list(deltaFibers), asList=True)
                    for thisRange in deltaFiberRanges:
                        lastSplice=thisSplice.isEndPoint
                        tempDict=baseDict.copy()
                        tempDict.update({
                            spliceGrpFields.CORE_MIN:thisRange[0],
                            spliceGrpFields.EDGE_MIN:0 if not edgeSegment else thisRange[0],
                            spliceGrpFields.POP_MIN:0 if not edgeSegment else thisRange[0],
                            spliceGrpFields.CORE_MAX:thisRange[1],
                            spliceGrpFields.EDGE_MAX:0 if not edgeSegment else thisRange[1],
                            spliceGrpFields.POP_MAX:0 if not edgeSegment else thisRange[1],
                            spliceGrpFields.COUNT:thisRange[1]-thisRange[0]+1,
                        })
                        summarySplices.setdefault(thisSplice.name, []).append(tempDict)

    #print(summarySplices)


    cableDict={}
    cableSegDict={}

    graphString=GRAPH_HEADER

    if skipHubs:
        filter=filterNodesCentralAcc
    else:
        filter=filterNodesCentralAccAlim

    nodes=sorted(myTree.getNodesAsList(filter=filter), key=lambda x:x.orderNumber)

    for treeNode in nodes:
        thisNode=treeNode.name
        if thisNode in summarySplices:
            thisSplices=summarySplices[thisNode]
            if skipHubs:
                if layerNode.featureCache[thisNode][fields.TIPO]==elementType.HUB:
                    continue
            if thisSplices[0].get(spliceGrpFields.IS_GANANCIA, False):
                if skipHubs and thisSplices[0].get(spliceGrpFields.GANANCIA_HUB, False):
                    continue
                tempString, inCablesSegs, outCablesSegs, inCables, outCables = populateDummyNodeTemplate(thisSplices)
            else:
                tempString, inCablesSegs, outCablesSegs, inCables, outCables = populateNodeTemplate(thisSplices,skipHubs=skipHubs)
            graphString+=tempString
            
            for inCableSeg in inCablesSegs:
                if inCableSeg not in cableSegDict:
                    cableSegDict[inCableSeg]={'tailSet':set(), 'headSet':set()}
                cableSegDict[inCableSeg]['tailSet'].add(thisNode)
            
            for inCable in inCables:
                if inCable not in cableDict:
                    cableDict[inCable]={'tailSet':set(), 'headSet':set()}
                cableDict[inCable]['tailSet'].add(thisNode)
            
            for outCableSeg in outCablesSegs:
                if outCableSeg not in cableSegDict:
                    cableSegDict[outCableSeg]={'tailSet':set(), 'headSet':set()}
                cableSegDict[outCableSeg]['headSet'].add(thisNode)
            
            for outCable in outCables:
                if outCable not in cableDict:
                    cableDict[outCable]={'tailSet':set(), 'headSet':set()}
                cableDict[outCable]['headSet'].add(thisNode)
        # else:
        #     #nodo no en la lista de empalmes
        #     print(f"Nodo no en splices - {treeNode.name}")

    cableTable=""    
    for k,v in cableSegDict.items():
        cableNameOut=k
        cableNameIn=k
        segmentFeat=mySegments.getSegment(k).getFeature()
        cableLabel=f"{str(segmentFeat[fields.ROTULADO]).replace('&','\\n').strip()} "
        for head in v['headSet']:
            spliceNameSrc=head
            for tail in v['tailSet']:
                spliceNameDst=tail
                cableTable+=CABLE_TABLE_ROW()

    graphString+=GRAPH_FOOTER()
    return graphString