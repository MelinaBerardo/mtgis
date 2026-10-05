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
    QgsWkbTypes,
    QgsRectangle,
    Qgis,
    QgsField, # Lo importe para poder agregar campos JMY
    QgsGeometryUtils,
    QgsPoint,
    QgsPointXY,
    QgsVectorLayer,
    NULL,
)

from .mtConstants import *   #Importamos todas las constantes de mtConstants
from .mtFuncs import *
from PyQt5.QtCore import QVariant
from .mtTree import *
from .mtGenAtt import *

## Ceacion de la tabla de QAQC

def QAQC_Table(checkDict,deleteOld):
    resultLayer = QgsProject.instance().mapLayer(layerIDs.QAQC)
    resultLayer.startEditing()
    resultLayer.dataProvider().truncate()
    resultLayer.commitChanges()

    for thisCheck in checkDict.keys():
        runQAQCTest(checkDict,thisCheck,deleteOld)


def runQAQCTest(checkDict,thisCheck,deleteOld=True):
    resultLayer = QgsProject.instance().mapLayer(layerIDs.QAQC)
    resultLayer.startEditing()

    if deleteOld:
        featsToDelete=resultLayer.getFeatures(QgsFeatureRequest().setFilterExpression(
                                                f'\"chequeo\" = \'{thisCheck}\''))
        resultLayer.deleteFeatures([feat[fields.UUID] for feat in featsToDelete])

    orden=checkDict[thisCheck]['orden']
    resultCounter=0

    # Ejecuto el test
    thisResults=checkDict[thisCheck]['test']()

    # Inserto un renglon con la descripcion del test
    tempFeat = QgsFeature(resultLayer.fields())
    tempFeat['orden']=orden
    tempFeat['chequeo']=thisCheck
    tempFeat['resultado']=checkDict[thisCheck]['desc']
    resultLayer.addFeature(tempFeat)

    # Insertamos los resultados del test
    for aResult in thisResults:
        resultCounter+=1
        tempFeat = QgsFeature(resultLayer.fields())
        tempFeat['orden']=orden+resultCounter
        tempFeat['chequeo']=thisCheck
        tempFeat['resultado']=aResult['msg']
        tempFeat['feature_LID']=aResult['lid']
        tempFeat['feature_FK']=aResult['feature_FK']
        tempFeat['Descripcion']=checkDict[thisCheck]['desc']
        resultLayer.addFeature(tempFeat)
    resultLayer.commitChanges()

      
##Chequeos
def CheckStatusVinculo():
    """
    Revisa que nodos y cables tengan status vinculo OK
    """
    layers = [layerCable,layerNode]

    errorMsgs = []

    for layer in layers:
        for feature in layer.getFeatures():
            if feature[fields.STATUS_VINCULO] != 'OK' and feature[fields.STATUS_VINCULO] != NULL:

                errorMsgs.append({
                    'msg':f"""Error en status vinculo: {feature[fields.NOMBRE]} de la capa {layer.friendlyName}
                              tiene Status_Vinculo = {feature[fields.STATUS_VINCULO]}""",
                    'lid':layer.LID,
                    'UUID':feature[fields.UUID],
                    'feature_FK':feature[fields.FID]
                })

    return errorMsgs

def CheckStatusCapacidad():
    """
    Revisa que los cables no tengan mas fibras calculadas que la cantidad de fibras del cable
    """
    layers = [layerCable]
    errorMsgs = []


    for layer in layers:
        for feature in layer.getFeatures():
            if feature[fields.CANT_FIBRAS]>1:

                if feature[fields.FIB_CALC] > feature[fields.CANT_FIBRAS]:

                    errorMsgs.append({
                        'msg':f"""Error en status capacidad: {feature[fields.NOMBRE]} """,
                        'lid':layer.LID,
                        'UUID':feature[fields.UUID],
                        'feature_FK':feature[fields.FID]
                    })



    return errorMsgs


def CheckUFContenidas():
    errorMsgs=[]

    layerUF = QgsProject().instance().mapLayer(layerIDs.Vivienda)
    for uf in layerUF.getFeatures():

        if uf[fields.ASSIGNED_AREA] == NULL:
            errorMsgs.append({
                'msg':f"Error de UF: {uf[fields.UUID]} no esta contenido en un area SDU ni MDU",
                'lid':layerIDs.Vivienda,
                'UUID':uf[fields.UUID],
                'feature_FK':uf[fields.FID]
            })

    return errorMsgs


def checkInfraestructuraEnCables():
    
    errorMsgs = []
    cablesReportados = set()

    # Traces que quedaron con tipo null 
    tracesSinTipo = [
        ct for ct in layerCableTraces.getFeatures()
        if ct[fields.TIPO] is None or ct[fields.TIPO] == NULL
    ]

    for trace in tracesSinTipo:
        traceUuid = trace[fields.UUID]
        cableUuid = trace[fields.PARENT_CABLE]  
        if cableUuid in cablesReportados:
            continue
        cablesReportados.add(cableUuid)

        cableFeat = layerCable.getFeaturesBy(fields.UUID, cableUuid)

        errorMsgs.append({
            'msg': (f"Error cable: {cableFeat[0][fields.NOMBRE] } (UUID: {cableUuid}) "
                    f"Tiene un cable trace sin infraestructura en inicio y/o fin), Revisar cable trace {traceUuid}"),
            'lid': layerCableTraces.LID,      
            'UUID': traceUuid,                
            'feature_FK': trace[fields.FID]   # FID del cabletrace
        })

    return errorMsgs




def CheckNAPsDesplegadas():
    errorMsgs=[]

    for areaTroncal in layerArea.getFeaturesBy("esMDU",False):
        naps = layerNode.getFeaturesBy("areaPrimFK",areaTroncal[fields.UUID],f"AND \"desplegado\" = True")
        if len(list(naps)) !=2:
            errorMsgs.append({
                'msg':f"Error de Naps: {areaTroncal[fields.UUID]} no tiene 2 Naps para despliegue inicial",
                'lid':layerArea.L,
                'UUID':areaTroncal[fields.UUID],
                'feature_FK':areaTroncal[fields.FID]
            })

    return errorMsgs

def CheckJumpersExcedidos():
    errorMsgs=[]
    
    for jumper in layerCable.getFeatures():
        if jumper[fields.LONG_TOTAL] == JUMPER_EXCEDIDO:
            errorMsgs.append({
                'msg':f"Error Jumpers: {jumper[fields.UUID]} excede longitud máxima para el diseño",
                'lid':layerCable.L,
                'UUID':jumper[fields.UUID],
                'feature_FK':jumper[fields.FID]
            })
                

    return errorMsgs


def checkCablesSecundarios():
    errorMsgs=[]
    myTree = mtTree()
    rootNode=myTree.buildTree()

    for parentFeature in layerNode.getFeaturesBy(fields.TIPO,elementType.PC):

        parentNode = myTree.getNodeFromUUID(parentFeature[fields.UUID])

        countCablesSecundarios = 0 #la cantidad de cables secundarios por CT

        countCajaDistribucionTotales = 0

        for node in PreOrderIterSorted(parentNode,childiter=distAlongTotSort,
                                            filter_=lambda n: (n.layer == layerCable.LID and n.nivelNodo == networkLevel.SECUNDARIO and n.getFeature()[fields.NODO_INICIO] == parentFeature[fields.UUID])
                                            ):
            countCablesSecundarios+=1

            cableFeat = node.getFeature()
            cableTree = myTree.getNodeFromUUID(cableFeat[fields.UUID])

            countCajaDistribucionPorCable =0
            for node in PreOrderIterSorted(cableTree,childiter=distAlongTotSort,
                                    filter_= lambda n: (n.layer == layerNode.LID and n.nivelNodo == networkLevel.SECUNDARIO)):
                countCajaDistribucionPorCable+=1
            countCajaDistribucionTotales = countCajaDistribucionTotales+countCajaDistribucionPorCable
            if countCajaDistribucionPorCable>8:
                errorMsgs.append({
                        'msg':f"Error cantidad cables secundarios: {parentFeature[fields.UUID]} mas de 8 CD por cable",
                        'lid':layerCable.LID,
                        'UUID':parentFeature[fields.UUID],
                        'feature_FK':parentFeature[fields.FID],
                        'tipo': f"Error"
                    })      

        if countCablesSecundarios>2:
            errorMsgs.append({
                    'msg':f"Error cantidad cables secundarios: {parentFeature[fields.UUID]} tiene mas de dos cables secundarios",
                    'lid':layerCable.LID,
                    'UUID':parentFeature[fields.UUID],
                    'feature_FK':parentFeature[fields.FID],
                    'tipo': f"Error"
                })


        if countCajaDistribucionTotales>12:
            errorMsgs.append({
                    'msg':f"Error cantidad cables secundarios: {parentFeature[fields.UUID]} mas de 12 CD",
                    'lid':layerCable.LID,
                    'UUID':parentFeature[fields.UUID],
                    'feature_FK':parentFeature[fields.FID],
                    'tipo': f"Error"
                })

    return errorMsgs


def checkCantidadCD():
    #Chequea que no haya mas de 60 CD

    counCD =  len(layerNode.getFeaturesBy(fields.TIPO,elementType.HUB))
    errorMsgs=[]

    if counCD>MAX_CD:
            errorMsgs.append({
                    'msg':f"Error cantidad de cajas CD, exceden {MAX_CD}",
                    'lid':layerNode.LID,
                    'UUID':'',
                    'feature_FK':1
                })
    return errorMsgs



def CheckCajasPostes():
    # Chequea cajas en poste
    errorMsgs=[]

    #cuando la caja sea colocación libre :  chequear que ese nodo no intersecte ningun poste  
    for caja in layerNode.getFeaturesBy(fields.COLOCACION, 999): # Caja Libre = 99
            # print("caja tiene 999 es libre", caja[fields.UUID])
            for poste in layerInfra.getFeatures():
                if caja.geometry().intersects(poste.geometry()):
                    errorMsgs.append({
                        'msg':f"Error Caja: {caja[fields.UUID]} con colocacion libre pero intersecta un poste {poste[fields.UUID]}",
                        'lid':layerIDs.Nodo,
                        'UUID':caja[fields.UUID],
                        'feature_FK':caja[fields.FID],
                        'tipo': f"Error"
                    })    

    return errorMsgs


def CheckCajasMismoPoste():
    # Chequea si dos cajas de la misma teleco intersects en mismo poste
    errorMsgs=[]

    for caja in layerNode.getFeatures():
        if caja[fields.COLOCACION] == 10: # Poste = 10
            for poste in layerInfra.getFeatures():
                if caja.geometry().intersects(poste.geometry()):
                    # busca otra caja que intersecte
                    for otraCaja in layerNode.getFeatures():
                        if otraCaja[fields.UUID] != caja[fields.UUID] and otraCaja[fields.COLOCACION] == 10:
                            if otraCaja.geometry().intersects(poste.geometry()):
                                errorMsgs.append({
                                'msg':f"Error: Caja {caja[fields.UUID]} y {otraCaja[fields.UUID]} de la misma teleco intersectan el mismo poste",
                                'lid':layerIDs.Nodo,
                                'UUID':caja[fields.UUID],
                                'feature_FK':caja[fields.FID]
                            })

    return errorMsgs


def CheckCajasInicialesYfuturas():
   
    errorMsgs = []
   
    # Recorrer areas y contar intersecciones de nodos CLARO.
    for area in layerArea.getFeaturesBy(fields.LEVEL, networkLevel.DISPERSION ):
        listaTipoNodos=[elementType.C_TIPO_A,elementType.C_TIPO_B]
        listaNivelesNodos=[networkLevel.DISPERSION, networkLevel.ACCESO]

        cajasInicialesIntersect=0
        cajasFuturasIntersect=0
        cajasMDUintersect=0

        nodes=layerArea.getIntersectingFeatures(layerIDs.Nodo,area)
        for nodo in nodes:
            if (nodo[fields.LEVEL] in listaNivelesNodos and nodo[fields.TIPO] in listaTipoNodos and nodo[fields.TELECO] == teleco.CLARO):
                if nodo[fields.FASE] == faseConstruccion.FASE_1:
                    cajasInicialesIntersect+=1
                elif nodo[fields.FASE] == faseConstruccion.FASE_2:
                    cajasFuturasIntersect+=1
                elif nodo[fields.FASE] == faseConstruccion.FASE_MDU:
                    cajasMDUintersect+=1
        
        if(area[fields.TIPO]== areaType.SDU):
            if cajasInicialesIntersect != area[fields.CAJAS_INICIALES]:
                errorMsgs.append({
                    'msg': f"Error Area: {area[fields.UUID]} tiene Cajas iniciales: {area[fields.CAJAS_INICIALES]}, pero intersecta con ({cajasInicialesIntersect}) cajas inciales",
                    'lid': layerIDs.Area,
                    'UUID': area[fields.UUID],
                    'feature_FK': area[fields.FID],
                    'tipo': f"Error"
                })
            if cajasFuturasIntersect != area[fields.CAJAS_FUTURAS]:
                errorMsgs.append({
                    'msg': f"Error Area: {area[fields.UUID]} tiene CajasFuturas: {area[fields.CAJAS_FUTURAS]}, pero intersecta con ({cajasFuturasIntersect}) cajas futuras",
                    'lid': layerIDs.Area,
                    'UUID': area[fields.UUID],
                    'feature_FK': area[fields.FID],
                    'tipo': f"Error"
                })
        
        if(area[fields.TIPO]== areaType.MDU): #AREAS MDU
            if cajasMDUintersect != area[fields.CAJAS_FUTURAS] or cajasInicialesIntersect> 0 or cajasFuturasIntersect>0 :
                errorMsgs.append({
                    'msg': f"Error Area: {area[fields.UUID]} tiene CajasFuturas: {area[fields.CAJAS_FUTURAS]}, pero intersecta con ({cajasMDUintersect}) cajas MDU",
                    'lid': layerIDs.Area,
                    'UUID': area[fields.UUID],
                    'feature_FK': area[fields.FID],
                    'tipo': f"Error"
                })
    
    return errorMsgs


def checkGanancias():
    errorMsgs = []
    for segmento in layerSEG.getFeatures():
        
        # Filtramos por niveles multifibra (20 y 30)
        if segmento[fields.LEVEL] == networkLevel.RED_ACCESO or segmento[fields.LEVEL] == networkLevel.RED_ALIMENTACION:
            
            # Verificamos 
            if segmento[fields.LONG_TOTAL] > DIST_ENTRE_GANANCIAS: #Ver margen
                
                tipoFibra = "Acceso (20)" if segmento[fields.LEVEL] == networkLevel.RED_ACCESO else "Alimentacion (30)"
                
                errorMsgs.append({
                    'msg': (f"Segmento Multifibra ({tipoFibra}) '{segmento[fields.NOMBRE]}' "
                            f"supera los {DIST_ENTRE_GANANCIAS}m | "
                            f"Longitud actual: {round(segmento[fields.LONG_TOTAL], 2)} m"),
                    'lid': layerSEG.LID,
                    'UUID': segmento[fields.UUID],
                    'feature_FK': segmento[fields.FID],
                    'tipo': "Error"
                })

    return errorMsgs


def checkComFactInfraFk(): 
    errorMsgs = []
    
    for poste in layerInfra.getFeatures():
        if poste[fields.COMENTARIO_FACT] != NULL and poste[fields.COMENTARIO_FACT] in (feasibilityComment.CAMBIO, feasibilityComment.SOLICITAR_INST, feasibilityComment.NO_RELEVADO_CAMBIO):
            #verifico que el poste este en uso
            posteEnUso = False

            for suspensor in layerSuspensor.getFeatures():
                if suspensor[fields.INFRA_INICIO_FK] == poste[fields.UUID] or suspensor[fields.INFRA_FIN_FK] == poste[fields.UUID]:
                    posteEnUso = True
                    break   
            
            if posteEnUso == False: 
                for herraje in layerHerrajes.getFeatures():
                    if herraje[fields.ASSIGNED_INFRA] == poste[fields.UUID]:
                        posteEnUso = True
                        break
           
            if posteEnUso == False:
                errorMsgs.append({
                    'msg':f"Error: Poste {poste[fields.UUID]} tiene comentario Factibilidad pero no esta en uso",
                    'lid':layerInfra.LID,
                    'UUID':poste[fields.UUID],
                    'feature_FK':poste[fields.FID],
                    'tipo': f"Error"
                })
  
    return errorMsgs

def checkPostesAInstalarEnUso(): 
    errorMsgs = []
    for poste in layerInfra.getFeatures():
        # ComFact 2 == Solicitar Instalacion
        if poste[fields.COMENTARIO_FACT] == feasibilityComment.SOLICITAR_INST:
            
            posteEnUso = False
            
            #  Primero vemos si tiene herrajes asociados
            herrajesAsociados = layerHerrajes.getFeaturesBy(fields.ASSIGNED_INFRA, poste[fields.UUID])
            
            if herrajesAsociados:
                posteEnUso = True
            else:
                #  Si no tiene herrajes, vemos en suspensores (Nodo de Inicio Y fin)
                suspInicio = layerSuspensor.getFeaturesBy(fields.INFRA_INICIO_FK, poste[fields.UUID])
                if suspInicio:
                    posteEnUso = True
                else:
                    
                    suspFin = layerSuspensor.getFeaturesBy(fields.INFRA_FIN_FK, poste[fields.UUID])
                    if suspFin:
                        posteEnUso = True

            #  Si después de revisar ambas capas sigue en False, hay error
            if not posteEnUso:
                errorMsgs.append({
                    'msg': f"Error: Poste {poste[fields.UUID]} tiene ComFact= Solicitar Instalacion pero no está en uso (sin herrajes ni suspensores)",
                    'lid': layerInfra.LID,
                    'UUID': poste[fields.UUID],
                    'feature_FK': poste[fields.FID],
                    'tipo': "Error"
                })
    return errorMsgs


def checkJumpersDuplicados():
    errorMsgs = []
    jumperDict = {}
    
    tree = mtTree()
    for seg in layerSEG.getFeatures():
        nivel = seg[fields.LEVEL]
        
        if nivel not in (elementType.C_TIPO_A, elementType.C_TIPO_B):
            continue
        inicio = seg[fields.NODO_INICIO]
        fin = seg[fields.NODO_FIN] 
        key = (nivel, inicio, fin)
        if inicio not in tree.nodeDict or fin not in tree.nodeDict:
            errorMsgs.append({
                'msg':f"Advertencia: Nodo inicio o fin no encontrado en el árbol para el segmento {seg[fields.UUID]}",
                'lid':layerSEG.LID,
                'UUID':seg[fields.UUID],
                'feature_FK':seg[fields.FID],
                'tipo': f"Warning"
            })
            continue
        
        if key not in jumperDict:
            jumperDict[key] = []
        jumperDict[key].append(seg)
    for key, segList in jumperDict.items():
        if len(segList) > 1:
            nivel, inicio, fin = key
            jumperIDs = [seg[fields.UUID] for seg in segList]
            errorMsgs.append({
                'msg':f"Error: Jumpers duplicados detectados UUIDs: {', '.join(jumperIDs)}",
                'lid':layerSEG.LID,
                'UUID':', '.join(jumperIDs),
                'feature_FK':', '.join(str(seg[fields.FID]) for seg in segList),
                'tipo': f"Error"
            })
    
    return errorMsgs

def checkCantidadCajasB():
    #Chequea que no haya mas de 3 cajas B por Cada CAJA A, revisar si tiene que ser por distinta teleco
    errorMsgs=[]
    for cajaA in layerNode.getFeaturesBy(fields.TIPO,elementType.C_TIPO_A):
       
        countCajasB=0
        for cajaB in layerNode.getFeaturesBy(fields.TIPO,elementType.C_TIPO_B):
            
            if cajaB[fields.NETPARENT_FK] == cajaA[fields.UUID] and cajaB[fields.TELECO] == teleco.CLARO: #filtro por teleco CLARO 10
                countCajasB+=1

        if countCajasB>3:
            
            #print(f'Cantidad encontrada: {countCajasB}')
            errorMsgs.append({
                    'msg':f"Error la Caja A: {cajaA[fields.UUID]} tiene mas de 3 cajas B asociadas, ( {countCajasB} cajas B )",
                    'lid':layerNode.LID,
                    'UUID':cajaA[fields.UUID],
                    'feature_FK':cajaA[fields.FID],
                    'tipo': f"Error"
                })
            
        
    print('listo el Pollo')
    return errorMsgs

def checkCajasAporCajasCD():
     # check que muestre si existen mas de 4 cajas A conectadas a una CAJA de Distribucion (CD) 
    errorMsgs=[]
    
    for cajaCD in layerNode.getFeaturesBy(fields.TIPO,elementType.HUB):
        countCajasA_UFINET=0
        countCajasA_CLARO=0

        for cajaA in layerNode.getFeaturesBy(fields.TIPO,elementType.C_TIPO_A):
            if cajaA[fields.NETPARENT_FK] == cajaCD[fields.UUID]:
                if cajaA[fields.TELECO] == teleco.UFINET: 
                    countCajasA_UFINET=countCajasA_UFINET+1
                 
                elif cajaA[fields.TELECO] ==teleco.CLARO: 
                    countCajasA_CLARO=countCajasA_CLARO+1
                   

        if countCajasA_UFINET>4:
            errorMsgs.append({
                    'msg':f"Error Caja CD: {cajaCD[fields.UUID]} tiene mas de 4 Cajas A, ( {countCajasA_UFINET} ) Cajas tipo A de UFINET asociadas",
                    'lid':layerNode.LID,
                    'UUID':cajaCD[fields.UUID],
                    'feature_FK':cajaCD[fields.FID],
                    'tipo': f"Error"
                })
          
        if countCajasA_CLARO>4:
            errorMsgs.append({
                    'msg':f"Error Caja CD: {cajaCD[fields.UUID]} tiene mas de 4 Cajas A, ( {countCajasA_CLARO} ) Cajas tipo A de CLARO asociadas",
                    'lid':layerNode.LID,
                    'UUID':cajaCD[fields.UUID],
                    'feature_FK':cajaCD[fields.FID],
                    'tipo': f"Error"
                })
           
    return errorMsgs


def checkConsistencyAreasCDyCajas(): 
    errorMsgs=[]   
    
    for areaDist in layerArea.getFeaturesBy(fields.LEVEL,areaType.DISTRIBUCION):  

        listaCajasCD=layerNode.getFeaturesBy(fields.ASSIGNED_AREA,areaDist[fields.UUID],f"AND \"tipo\" = {elementType.HUB}")

        if len(listaCajasCD) != 1: 
            errorMsgs.append({
                'msg':f"Error Area Distribucion: {areaDist[fields.UUID]} tiene asignada {len(listaCajasCD)} cajas CD, pero deberia tener exactamente 1 caja CD asignada",
                'lid':layerArea.LID,
                'UUID':areaDist[fields.UUID],
                'feature_FK':areaDist[fields.FID],
                'tipo':f"Error"
            })
        else:
            cajaCD=listaCajasCD[0]
            #recorre las cajas A que tengan como padre a esta caja CD y que intersecten con el area de distribucion
            listaCajasAClaro=layerNode.getFeaturesBy(fields.NETPARENT_FK,cajaCD[fields.UUID],f"AND \"tipo\" = {elementType.C_TIPO_A} AND \"{fields.TELECO}\" = {teleco.CLARO}")
            listaCajasAUfinet=layerNode.getFeaturesBy(fields.NETPARENT_FK,cajaCD[fields.UUID],f"AND \"tipo\" = {elementType.C_TIPO_A} AND \"{fields.TELECO}\" = {teleco.UFINET}")

            if len(listaCajasAClaro)>4 or len(listaCajasAUfinet)>4:
                errorMsgs.append({
                    'msg':f"Error Caja CD: {cajaCD[fields.UUID]} tiene mas de 4 Cajas A de cada red. Existen ( {len(listaCajasAClaro)} ) Cajas tipo A CLARO y ( {len(listaCajasAUfinet)} ) Cajas tipo A UFINET asociadas",
                    'lid':layerNode.LID,
                    'UUID':cajaCD[fields.UUID],
                    'feature_FK':cajaCD[fields.FID],
                    'tipo':f"Error"
                })
       
            
            for cajaA in (listaCajasAClaro+listaCajasAUfinet):
                if not cajaA.geometry().intersects(areaDist.geometry()):
                    errorMsgs.append({
                        'msg':f"Error Caja A: {cajaA[fields.UUID]} asignada al area de distribucion {areaDist[fields.UUID]} no intersecta con su area de distribucion",
                        'lid':layerNode.LID,
                        'UUID':cajaA[fields.UUID],
                        'feature_FK':cajaA[fields.FID],
                        'tipo':f"Error"
                    })
                #recorro las cajas B que tengan como padre a esta caja A y que intersecten con el area de distribucion
                listaCajasBClaro=layerNode.getFeaturesBy(fields.NETPARENT_FK,cajaA[fields.UUID],f"AND \"tipo\" = {elementType.C_TIPO_B} AND \"{fields.TELECO}\" = {teleco.CLARO}")
                listaCajasBUfinet=layerNode.getFeaturesBy(fields.NETPARENT_FK,cajaA[fields.UUID],f"AND \"tipo\" = {elementType.C_TIPO_B} AND \"{fields.TELECO}\" = {teleco.UFINET}")
                
                if len(listaCajasBClaro)>3 or len(listaCajasBUfinet)>3: #si hay mas de 3 cajas B asociadas a esta caja A es un error
            
                    errorMsgs.append({
                    'msg':f"Error la Caja A: {cajaA[fields.UUID]} tiene mas de 3 cajas B asociadas de cada red. Existen ( {len(listaCajasBClaro)} cajas B CLARO y {len(listaCajasBUfinet)} cajas B UFINET)",
                    'lid':layerNode.LID,
                    'UUID':cajaA[fields.UUID],
                    'feature_FK':cajaA[fields.FID],
                    'tipo':f"Error"
                })
       
                for cajaB in (listaCajasBClaro+listaCajasBUfinet):
                    if not cajaB.geometry().intersects(areaDist.geometry()):
                        errorMsgs.append({
                            'msg':f"Error Caja B: {cajaB[fields.UUID]} asignada al area de distribucion {areaDist[fields.UUID]} no intersecta con su area de distribucion",
                            'lid':layerNode.LID,
                            'UUID':cajaB[fields.UUID],
                            'feature_FK':cajaB[fields.FID],
                            'tipo':f"Error"
                        })
    

    return errorMsgs


def CheckJumpersDuplicadosYConexiones():
    errorMsgs = []
    nombresVistos = set()
    conteoJumpersAporNodoClaro = {}
    conteoJumperBporNodoClaro = {}
    conteoJumpersAporNodoUfinet = {}
    conteoJumperBporNodoUfinet = {}
    
    nodoCache = {}
    for nodo in layerNode.getFeatures():
        nodoCache[nodo[fields.UUID]] = nodo
    
    for jumper in layerCable.getFeatures():

        if jumper[fields.LEVEL] not in (networkLevel.JUMPER_A, networkLevel.JUMPER_B):
            continue
        if jumper[fields.NODO_INICIO] == NULL or jumper[fields.NODO_FIN] == NULL:
            errorMsgs.append({
                'msg':f"Error: Jumper {jumper[fields.NOMBRE]} tiene nodo inicio o fin nulo",
                'lid':layerCable.LID,
                'UUID':jumper[fields.UUID],
                'feature_FK':jumper[fields.FID],
                'tipo': f"Error"
            })
            continue

        #validar duplicados
        if jumper[fields.NOMBRE] in nombresVistos:
            errorMsgs.append({
                'msg':f"Error: Nombre de Jumper duplicado detectado: {jumper[fields.NOMBRE]}",
                'lid':layerCable.LID,
                'UUID':jumper[fields.UUID],
                'feature_FK':jumper[fields.FID],
                'tipo': f"Error"
            })
            continue
        nombresVistos.add(jumper[fields.NOMBRE])
        
        #validar que los nodos de inicio y fin existan en la capa nodos
        nodoInicio = nodoCache.get(jumper[fields.NODO_INICIO])
        nodoFin = nodoCache.get(jumper[fields.NODO_FIN])
        if nodoInicio is None or nodoFin is None:
            errorMsgs.append({
                'msg':f"Warning: Jumper {jumper[fields.NOMBRE]} tiene nodo inicio o fin no encontrado en la capa de nodos",
                'lid':layerCable.LID,
                'UUID':jumper[fields.UUID],
                'feature_FK':jumper[fields.FID],
                'tipo': f"Warning"
            })
            continue
        
        #consistencia parent node
        if jumper[fields.PARENT_NODE] != nodoInicio[fields.UUID] and jumper[fields.PARENT_NODE] != nodoFin[fields.UUID]:
            errorMsgs.append({
                'msg':f"Error: Jumper {jumper[fields.NOMBRE]} tiene un parent node que no coincide con su nodo inicio o fin",
                'lid':layerCable.LID,
                'UUID':jumper[fields.UUID],
                'feature_FK':jumper[fields.FID],
                'tipo': f"Error"
            })
            continue
            
        #valirdar conexiones Jumper A: conecta CD con A
        if jumper[fields.LEVEL] == networkLevel.JUMPER_A: 
            if (nodoInicio[fields.TIPO] == elementType.HUB and nodoFin[fields.TIPO] == elementType.C_TIPO_A):
                pass 
            else:
                errorMsgs.append({
                    'msg':f"Error: Jumper A {jumper[fields.NOMBRE]} no conecta una caja A y una caja de distribucion CD: {nodoInicio[fields.UUID]} y {nodoFin[fields.UUID]}",
                    'lid':layerCable.LID,
                    'UUID':jumper[fields.UUID],
                    'feature_FK':jumper[fields.FID],
                    'tipo': f"Error"
                })
        #validar conexiones Jumper B: conecta caja A con caja B
        elif jumper[fields.LEVEL] == networkLevel.JUMPER_B:
            if (nodoInicio[fields.TIPO] == elementType.C_TIPO_A and nodoFin[fields.TIPO] == elementType.C_TIPO_B):
                pass
            else:
                errorMsgs.append({
                    'msg':f"Error: Jumper B {jumper[fields.NOMBRE]} no conecta una caja A y una caja B: {nodoInicio[fields.UUID]} y {nodoFin[fields.UUID]}",
                    'lid':layerCable.LID,
                    'UUID':jumper[fields.UUID],
                    'feature_FK':jumper[fields.FID],
                    'tipo': f"Error"
                })
        #validar teleco del nodo inicio vs jumper
        if nodoFin[fields.TELECO] != jumper[fields.TELECO]:
            errorMsgs.append({
                'msg':f"Error: Jumper {jumper[fields.NOMBRE]} tiene teleco {jumper[fields.TELECO]} pero su nodo fin no coincide",
                'lid':layerCable.LID,
                'UUID':jumper[fields.UUID],
                'feature_FK':jumper[fields.FID],
                'tipo': f"Error"
            })
        
        #validar cantidad de jumpers A y B por nodo y por teleco
        if jumper[fields.LEVEL] == networkLevel.JUMPER_A:
            if nodoFin[fields.TELECO] == teleco.CLARO: #comparo con nodoFin porque el Jumper A conecta con CD (donde su teleco es Compartido).
                conteoJumpersAporNodoClaro[jumper[fields.PARENT_NODE]] = conteoJumpersAporNodoClaro.get(jumper[fields.PARENT_NODE], 0) + 1
                if conteoJumpersAporNodoClaro[jumper[fields.PARENT_NODE]] > 4:
                    errorMsgs.append({
                        'msg':f"Error: Nodo {jumper[fields.PARENT_NODE]} tiene mas de 4 jumpers A de CLARO conectados",
                        'lid':layerNode.LID,
                        'UUID':jumper[fields.PARENT_NODE],
                        'feature_FK':'',
                        'tipo': f"Error"
                    })
            elif nodoFin[fields.TELECO] == teleco.UFINET:
                conteoJumpersAporNodoUfinet[jumper[fields.PARENT_NODE]] = conteoJumpersAporNodoUfinet.get(jumper[fields.PARENT_NODE], 0) + 1
                if conteoJumpersAporNodoUfinet[jumper[fields.PARENT_NODE]] > 4:
                    errorMsgs.append({
                        'msg':f"Error: Nodo {jumper[fields.PARENT_NODE]} tiene mas de 4 jumpers A de UFINET conectados",
                        'lid':layerNode.LID,
                        'UUID':jumper[fields.PARENT_NODE],
                        'feature_FK':'',
                        'tipo': f"Error"
                    })
        elif jumper[fields.LEVEL] == networkLevel.JUMPER_B:
            if nodoFin[fields.TELECO] == teleco.CLARO:
                conteoJumperBporNodoClaro[jumper[fields.PARENT_NODE]] = conteoJumperBporNodoClaro.get(jumper[fields.PARENT_NODE], 0) + 1
                if conteoJumperBporNodoClaro[jumper[fields.PARENT_NODE]] > 3:
                    errorMsgs.append({
                        'msg':f"Error: Nodo {jumper[fields.PARENT_NODE]} tiene mas de 3 jumpers B de CLARO conectados",
                        'lid':layerNode.LID,
                        'UUID':jumper[fields.PARENT_NODE],
                        'feature_FK':'',
                        'tipo': f"Error"
                    })
            elif nodoFin[fields.TELECO] == teleco.UFINET:
                conteoJumperBporNodoUfinet[jumper[fields.PARENT_NODE]] = conteoJumperBporNodoUfinet.get(jumper[fields.PARENT_NODE], 0) + 1
                if conteoJumperBporNodoUfinet[jumper[fields.PARENT_NODE]] > 3:
                    errorMsgs.append({
                        'msg':f"Error: Nodo {jumper[fields.PARENT_NODE]} tiene mas de 3 jumpers B de UFINET conectados",
                        'lid':layerNode.LID,
                        'UUID':jumper[fields.PARENT_NODE],
                        'feature_FK':'',
                        'tipo': f"Error"
                    })
        
    return errorMsgs


def checkJumpersNodosCDyCajaA():
    errorMsgs = []
    tree = mtTree()
    rootNode = tree.buildTree()
    
    # recorro todos los CD, cuento los jumpers A conectados y filtro por teleco
    for parentFeature in layerNode.getFeaturesBy(fields.TIPO,elementType.HUB):
        
        nodoTree = tree.getNodeFromUUID(parentFeature[fields.UUID])
        if nodoTree is None:
            continue

        countJumpersAClaro = 0
        countJumpersAUfinet = 0
        for node in PreOrderIterSorted(nodoTree,childiter=distAlongTotSort,
                                            filter_=lambda n: (n.layer == layerCable.LID and n.nivelNodo == networkLevel.JUMPER_A and n.getFeature()[fields.NODO_INICIO] == parentFeature[fields.UUID])
                                            ):
            telecoJumper = node.getFeature()[fields.TELECO]
            if telecoJumper == teleco.CLARO:
                countJumpersAClaro+=1
            elif telecoJumper == teleco.UFINET:
                countJumpersAUfinet+=1

        if countJumpersAClaro>4:
            errorMsgs.append({
                'msg':f"Error: Nodo CD {parentFeature[fields.NOMBRE]} tiene mas de 4 jumpers A conectados, ( {countJumpersAClaro} jumpers A de CLARO )",
                'lid':layerNode.LID,
                'UUID':parentFeature[fields.UUID],
                'feature_FK':parentFeature[fields.FID],
                'tipo': f"Error"
            })
        if countJumpersAUfinet>4:
            errorMsgs.append({
                'msg':f"Error: Nodo CD {parentFeature[fields.NOMBRE]} tiene mas de 4 jumpers A conectados, ( {countJumpersAUfinet} jumpers A de UFINET )",
                'lid':layerNode.LID,
                'UUID':parentFeature[fields.UUID],
                'feature_FK':parentFeature[fields.FID],
                'tipo': f"Error"
            })
        if countJumpersAClaro==0 and countJumpersAUfinet==0:
            errorMsgs.append({
                'msg':f"Warning: Nodo CD {parentFeature[fields.NOMBRE]} no tiene jumpers A conectados",
                'lid':layerNode.LID,
                'UUID':parentFeature[fields.UUID],
                'feature_FK':parentFeature[fields.FID],
                'tipo': f"Warning"
            })

    # recorro todos los nodos A, cuento los jumpers B conectados y filtro por teleco
    for parentFeature in layerNode.getFeaturesBy(fields.TIPO,elementType.C_TIPO_A):
        nodoTree = tree.getNodeFromUUID(parentFeature[fields.UUID])
        if nodoTree is None:
            continue
    
        nodoTeleco = parentFeature[fields.TELECO]
        if nodoTeleco not in (teleco.CLARO, teleco.UFINET):
            continue
        
        countJumpersB = 0
        for node in PreOrderIterSorted(nodoTree,childiter=distAlongTotSort,
                                            filter_=lambda n: (n.layer == layerCable.LID and n.nivelNodo == networkLevel.JUMPER_B and n.getFeature()[fields.TELECO] == nodoTeleco)
                                            ):
            countJumpersB+=1

        if countJumpersB>3:
            errorMsgs.append({
                'msg':f"Error: Nodo A {parentFeature[fields.NOMBRE]} tiene mas de 3 jumpers B conectados, ( {countJumpersB} jumpers B de {nodoTeleco} )",
                'lid':layerNode.LID,
                'UUID':parentFeature[fields.UUID],
                'feature_FK':parentFeature[fields.FID],
                'tipo': f"Error"
            })
        if countJumpersB==0:
            errorMsgs.append({
                'msg':f"Warning: Nodo A {parentFeature[fields.NOMBRE]} no tiene jumpers B conectados",
                'lid':layerNode.LID,
                'UUID':parentFeature[fields.UUID],
                'feature_FK':parentFeature[fields.FID],
                'tipo': f"Warning"
            })
    
    return errorMsgs


def checkCableConectDelNodosMismoNivel():
    #recorro la capa de cables y veo si hay cables que conecten a Nodos del mismo nivel, ej si un Jumper A conecta a una Caja A y otra Caja A, es un error 
    errorMsgs = []
   
    for cable in layerCable.getFeaturesBy(fields.LEVEL,networkLevel.JUMPER_A):
        NodoInicioUUID=cable[fields.NODO_INICIO]
        NodoFinUUID=cable[fields.NODO_FIN]

        #ahora con estos UUID recorro la capa de Nodos y veo si son del mismo nivel
        nodoInicio= layerNode.getFeaturesBy(fields.UUID,NodoInicioUUID)
        nodoFin= layerNode.getFeaturesBy(fields.UUID,NodoFinUUID)
        if len(nodoInicio)==0 or len(nodoFin)==0:
            continue
        else:
            if nodoInicio[0][fields.TIPO]==nodoFin[0][fields.TIPO]:
                errorMsgs.append({
                'msg':f"Error: Cable {cable[fields.UUID]} conecta a nodos del mismo nivel",
                'lid':layerCable.LID,
                'UUID':cable[fields.UUID],
                'feature_FK':cable[fields.FID],
                'tipo': f"Error"
            })

    
    for cable in layerCable.getFeaturesBy(fields.LEVEL,networkLevel.JUMPER_B):
        NodoInicioUUID=cable[fields.NODO_INICIO]
        NodoFinUUID=cable[fields.NODO_FIN]
        #ahora con estos UUID recorro la capa de Nodos y veo si son del mismo nivel
        nodoInicio= layerNode.getFeaturesBy(fields.UUID,NodoInicioUUID)
        nodoFin= layerNode.getFeaturesBy(fields.UUID,NodoFinUUID)
        
        #fields.TIPO,elementType.C_TIPO_A
        if len(nodoInicio)==0 or len(nodoFin)==0:
           
            continue
        else:
            if nodoInicio[0][fields.TIPO]==nodoFin[0][fields.TIPO]:
                errorMsgs.append({
                    'msg':f"Error: Cable {cable[fields.UUID]} conecta a nodos del mismo nivel",
                    'lid':layerCable.LID,
                    'UUID':cable[fields.UUID],
                    'feature_FK':cable[fields.FID],
                    'tipo': f"Error"
                })
    return errorMsgs


def checkManzanas():
    """
       Realiza el control de IDs de las manzanas

       1. Revisa IDs Nulos, vacíos o con 'X' (invalido): 
       - Si la manzana tiene un nodo asociado (lo hace con .uniqueValues()), verifica que 
         tenga un comentario (con .getIntersectingFeatures()) y si no tiene, es Error.
       - Si tiene nodo y comentario, tira una alerta de revisión ("Ver").
       - Si no tiene ni ID pero tampoco nodo, no hace nada

       2. Revisa IDs repetidos: Si el ID es válido, verifica que no se repita en otra manzana.
    """

    idRevisados = []
    idRepetidos = []
    errorMsgs = []

    nodoManzana = layerNode.uniqueValues(fields.MANZANA_FK)

    for manzana in layerManzana.getFeatures(): 
            idActual = manzana[fields.ID]
            uuidActual = manzana[fields.UUID]

            if idActual is None or str(idActual).strip().upper() in ['NULL', ''] or "X" in str(idActual).upper(): # Si no tiene id

                if uuidActual in nodoManzana: # me fijo si el uuid esta en manzanas_fk osea si tiene caja
                    comentarioIntersect = layerComentario.getIntersectingFeatures(layerIDs.Comentario, manzana)
    
                    if len(comentarioIntersect) > 0: # tiene comentario
                         errorMsgs.append({
                               'msg': f"Ver: Manzana {uuidActual} SIN ID CON caja pero CON comentario",
                                'lid': layerManzana.LID,
                                'UUID': uuidActual,
                                'feature_FK': manzana[fields.FID],
                                'tipo': "Error"
                                        }) 
                    else:
                        errorMsgs.append({
                                'msg': f"Error: Manzana {uuidActual} SIN ID CON caja y SIN comentario",
                                'lid': layerManzana.LID,
                                'UUID': uuidActual,
                                'feature_FK': manzana[fields.FID],
                                'tipo': "Error"
                                        }) 
    
            elif idActual in idRevisados:
                if idActual not in idRepetidos:
                    idRepetidos.append(idActual)
    
                errorMsgs.append({
                    'msg': f"Error: Manzana {manzana[fields.UUID]} con ID repetido {manzana[fields.ID]}",
                    'lid': layerManzana.LID,
                    'UUID': uuidActual,
                    'feature_FK': manzana[fields.FID],
                    'tipo': "Error"
                         }) 
                        
            else:
                idRevisados.append(idActual)
      
    return errorMsgs

def checkCamaras():
    """Chequea que las cámaras que estan en uso y se completaron con true en el campo enUso, tengan un nodo
    """
    errorMsgs = []

    infraFk = layerNode.uniqueValues(fields.ASSIGNED_INFRA) # obtengo los uuid de infra fk de la capa nodos
    for camara in layerInfraNodeRel.getFeaturesBy(fields.INFRA_TIPO, colocacion.CAMARA):
        
        if camara[fields.POSTE_EN_USO]:
            uuidCamara = camara[fields.UUID]

            if uuidCamara not in infraFk:
                errorMsgs.append({
                            'msg': f"Error: Cámara {camara[fields.UUID]} en uso pero sin nodo",
                            'lid': layerInfraNodeRel.LID,
                            'UUID': uuidCamara,
                            'feature_FK': camara[fields.FID],
                            'tipo': "Error"
                                }) 

    return errorMsgs

def CheckAtenuacion():

    errorMsgs = []
    # Chequea que en la capa de Nodos, en los campos: atenuacionUS y atenuacionDS no pase de estos valores maximos: Upstream: 32.4 y Downstream: 30.9
    for nodo in layerNode.getFeatures():
        if nodo[fields.ATENUACION_US] != NULL:
            if nodo[fields.ATENUACION_US] > MAX_ATENUACION_UPSTREAM:
                errorMsgs.append({
                    'msg':f"Error Atenuacion Upstream: Nodo {nodo[fields.UUID]} tiene atenuacionUS = {nodo[fields.ATENUACION_US]} que excede el maximo de {MAX_ATENUACION_UPSTREAM}",
                    'lid':layerNode.LID,
                    'UUID':nodo[fields.UUID],
                    'feature_FK':nodo[fields.FID],
                    'tipo': f"Error"
                })
        if nodo[fields.ATENUACION_DS] != NULL:
            if nodo[fields.ATENUACION_DS] > MAX_ATENUACION_DOWNSTREAM:
                errorMsgs.append({
                    'msg':f"Error Atenuacion Downstream: Nodo {nodo[fields.UUID]} tiene atenuacionDS = {nodo[fields.ATENUACION_DS]} que excede el maximo de {MAX_ATENUACION_DOWNSTREAM}",
                    'lid':layerNode.LID,
                    'UUID':nodo[fields.UUID],
                    'feature_FK':nodo[fields.FID],
                    'tipo': f"Error"
                })
    return errorMsgs

def checkAreasCDdemanda128():
    """
    Chequea si existe alguna Área de nivel 30 y demanda <= 128.
    """
    errorMsgs = []

    # Filtramos primero por nivel 60
    for area in layerArea.getFeaturesBy(fields.LEVEL,areaType.DISTRIBUCION):
        demanda_num = area[fields.DEMANDAAREA]

        if demanda_num is not None and demanda_num >= 128 :
            errorMsgs.append({
                'msg': (
                    f"Existe Área nivel=60 con demanda mayor a 128HH. "
                    f"(Área UUID: {area[fields.UUID]}, demanda={demanda_num})"
                ),
                'lid': layerArea.LID,
                'UUID': area[fields.UUID],
                'feature_FK': area[fields.FID],
                'tipo': f"Error"
            })

    return errorMsgs

def checkCierresEmpalme():
    errorMsgs = []
   
    for cable in layerCable.getFeaturesBy( fields.LEVEL, networkLevel.RED_ACCESO, f'or {fields.LEVEL} = {networkLevel.RED_ALIMENTACION}'):
             
            tieneCE = True
                  
            # Calcular longitud del cable 
            longitudCable = cable[fields.LONG_TOTAL] 
            
            if longitudCable > DIST_ENTRE_CE_CONTINUIDAD:
                    tieneCE = False
                   
                    # Buscar CE asociados al cable
                    cantidadCE =len(layerNode.getFeaturesBy(fields.PARENT_CABLE, cable[fields.UUID], 'and ' + fields.TIPO + f' = { elementType.CE_EXT }'))
                    
                    # Calculo la cantidad de CE
                    minCE = int(longitudCable / DIST_ENTRE_CE_CONTINUIDAD)
                    if cantidadCE >= minCE:
                        tieneCE = True
                    if cable[fields.CANT_FIBRAS]==144 and longitudCable <= (DIST_ENTRE_CE_CONTINUIDAD + MARGEN_CE_CONTINUIDAD):
                        tieneCE = True # excepcion                 
        
            if not tieneCE:
                errorMsgs.append({
                    'msg': f"Faltan cierres de empalme en el cable {cable[fields.NOMBRE]} (longitud: {round(longitudCable,2)} m)",
                    'lid': layerCable.LID,
                    'UUID': cable[fields.UUID],
                    'feature_FK': cable[fields.FID],
                    'tipo': f"Error"
                })
    
    return errorMsgs

def CheckCEsinDerivacion():
    errorMsgs = []

    for nodo in layerNode.getFeaturesBy(fields.TIPO, elementType.CE_ACCESO):
        uuidCE = nodo[fields.UUID]
        tieneDerivacion = False
        # Buscar en la capa de segmentos si existe algun segmento que tenga este CE como nodo_inicio
        # armo lista de los cables que cumplen con esta condicion con este UUID, si la lista es vacia es porque no tiene derivacion
        CablesAsociados = layerCable.getFeaturesBy(fields.NODO_INICIO, uuidCE)
        # print(f"Cables asociados al CE {uuidCE}: {len(CablesAsociados)}")
        if len(CablesAsociados) > 0:
            tieneDerivacion = True

        if not tieneDerivacion:
            errorMsgs.append({
                'msg': f"Error: Cierre de Empalme (CE) {uuidCE} no tiene una derivacion asociada.",
                'lid': layerNode.LID,
                'UUID': nodo[fields.UUID],
                'feature_FK': nodo[fields.FID],
                'tipo': f"Error"
            })
    
    return errorMsgs

def checkAreasConPoste():
    # Chequea que las areas SDU tengan al menos un poste dentro de su geometria
    errorMsgs = []
    for area in layerArea.getFeaturesBy(fields.TIPO, areaType.SDU):
        tienePoste = False
        for poste in layerInfra.getFeatures():
            if area.geometry().intersects(poste.geometry()):
                tienePoste = True
                break
        if not tienePoste and (area[fields.CAJAS_INICIALES] + area[fields.CAJAS_FUTURAS]) > 0:
            errorMsgs.append({
                'msg': f"Error: Area SDU {area[fields.UUID]} no tiene ningun poste dentro de su geometria.",
                'lid': layerArea.LID,
                'UUID': area[fields.UUID],
                'feature_FK': area[fields.FID],
                'tipo': f"Error"
            })
    
    return errorMsgs

def checkSumHHEjesAreas():
    # Chequea que la suma de HH de UFs, ejes y areas SDU/MDU coincidan
    errorMsgs = []    
 
    # --- areas SDU
    for area in layerArea.getFeaturesBy(fields.LEVEL, networkLevel.DISPERSION, f'and {fields.TIPO} = {areaType.SDU}'):
        sumHH=0
        sumHHEje=0
        ejes = layerEjes.getFeaturesBy(fields.ASSIGNED_AREA, area[fields.UUID])        
        sumHHEje = sum(eje[fields.DEMANDA_SDU] for eje in ejes)
 
        ufs = layerUnidadesFuncionales.getFeaturesBy(fields.ASSIGNED_AREA, area[fields.UUID])
        sumHH = sum(uf[fields.HH_UF] for uf in ufs)
        if not (sumHH == sumHHEje == area[fields.DEMANDA_SDU]):
            errorMsgs.append({
                'msg': f"Error: La suma de HH no coincide. Suma UFs: {sumHH}, Suma Ejes: {sumHHEje}, Suma Areas SDU/MDU: {area[fields.DEMANDA_SDU]}",
                'lid': layerArea.LID,
                'UUID': area[fields.UUID],
                'feature_FK': area[fields.FID],
                'tipo': f"Error"
            })
 
    # --- areas MDU 
    ejes_procesados = set()
 
    for area in layerArea.getFeaturesBy(fields.LEVEL, networkLevel.DISPERSION, f'and {fields.TIPO} = {areaType.MDU}'):
        eje_fk = area[fields.ASSIGNED_EJE]
        # Si no tiene eje asignado, o ya lo procesamos, saltamos
        if not eje_fk or eje_fk in ejes_procesados:
            continue
        ejes_procesados.add(eje_fk)
        # demanda del EJE
        ejes = list(layerEjes.getFeaturesBy(fields.UUID, eje_fk))
        if not ejes:
            continue
        eje_padre = ejes[0]
        demanda_eje_mdu = eje_padre[fields.DEMANDA_MDU]
        # TODAS las áreas MDU que pertenecen a este mismo Eje
        areas_mdu_grupo = list(layerArea.getFeaturesBy(fields.ASSIGNED_EJE, eje_fk))
        areas_mdu_grupo = [a for a in areas_mdu_grupo if a[fields.TIPO] == areaType.MDU]
        sum_areas_mdu = sum(a[fields.DEMANDA_MDU] for a in areas_mdu_grupo)
        # Sumamos TODAS las UFs que están adentro de esas áreas MDU
        sum_ufs_mdu = 0
        for area_asociada in areas_mdu_grupo:
            ufs = layerUnidadesFuncionales.getFeaturesBy(fields.ASSIGNED_AREA, area_asociada[fields.UUID])
            sum_ufs_mdu += sum(uf[fields.HH_UF] for uf in ufs)
        # Comparamos las 3
        if not (sum_ufs_mdu == demanda_eje_mdu == sum_areas_mdu):
            # Si hay error, se levantan las areas MDU 
            for area_asociada in areas_mdu_grupo:
                errorMsgs.append({
                    'msg': f"Error: La suma de HH no coincide. Suma UFs: {sum_ufs_mdu}, Suma Ejes: {demanda_eje_mdu}, Suma Areas SDU/MDU: {sum_areas_mdu}",
                    'lid': layerArea.LID,
                    'UUID': area_asociada[fields.UUID],
                    'feature_FK': area_asociada[fields.FID],
                    'tipo': f"Error"
                })
 
    return errorMsgs

def checkMaxCajasAreasDistribucion():
    # Chequea que las areas de distribucion tengan como maximo 16 cajasIniciales + cajasFuturas
    errorMsgs = []
    maxCajasPermitidas = 16
    for areaDist in layerArea.getFeaturesBy(fields.LEVEL, areaType.DISTRIBUCION):        
        totalCajas=0

        for area in layerArea.getIntersectingFeatures(layerArea.LID, areaDist):
            if area[fields.TIPO] == areaType.SDU or area[fields.TIPO] == areaType.MDU:
                if areaDist.geometry().contains(area.geometry().centroid()):
                    totalCajas += area[fields.CAJAS_INICIALES] + area[fields.CAJAS_FUTURAS]
        
        if totalCajas > maxCajasPermitidas:
            errorMsgs.append({
                'msg': f"Error: Area de Distribucion {areaDist[fields.UUID]} tiene {totalCajas} cajas (maximo permitido es 16).",
                'lid': layerArea.LID,
                'UUID': areaDist[fields.UUID],
                'feature_FK': areaDist[fields.FID]
            })
    
    return errorMsgs

def checkCableEnPostesCriticosYDuctos():
    errorMsgs = []
    DuctosList = list(layerTrazaInfra.getFeaturesBy(fields.TIPO, 20))
    # print(len(DuctosList))  
    CablesTroncales = list(layerTrazaInfra.getFeaturesBy(fields.TIPO, 30))
    # print("hay esta cantidad de cables en traza infra")
    print(len(CablesTroncales))
    PostesCriticos = [p for p in layerInfra.getFeatures() if p[fields.CLASIF_USO] == 30]
    def get_startpoint(geom):
        return geom.asMultiPolyline()[0][0] if geom.isMultipart() else geom.asPolyline()[0]
 
    def get_endpoint(geom):
        return geom.asMultiPolyline()[-1][-1] if geom.isMultipart() else geom.asPolyline()[-1]
 
    # --- NUEVA FUNCIÓN: Extractor de datos y deductor de Fibras ---
    def obtener_datos_cable(feature):
        try:
            texto_json = feature['atributosSecundarios']
            if texto_json and str(texto_json).strip() != "":
                datos = json.loads(texto_json)
                nombre = datos.get('nombre', 'Sin Nombre')
                fibras = 0
                if nombre != 'Sin Nombre':
                    # Separamos el nombre por los guiones (ej: BZC01 - A01A02 - 1)
                    partes = nombre.split('-')
                    if len(partes) >= 2:
                        # Si la parte del medio tiene más de 3 caracteres (ej: A01A02), es 288
                        if len(partes[1]) > 3:
                            fibras = 288
                        else:
                            # Si es corto (ej: A02), es 144
                            fibras = 144
                    else:
                        # Plan B por si alguien no le puso guiones: miramos el largo total
                        fibras = 288 if len(nombre) > 12 else 144
                return fibras, nombre
        except Exception as e:
            pass 
        return 0, 'Sin Nombre'
 
    cables_con_error = {}
    for i, cable1 in enumerate(CablesTroncales):
        geom1 = cable1.geometry()
        f1, nombre1 = obtener_datos_cable(cable1)
        if f1 not in [144, 288]:
            continue
        for j, cable2 in enumerate(CablesTroncales):
            if i >= j: continue
            geom2 = cable2.geometry()
            if not geom1.intersects(geom2): continue
            inter_geom = geom1.intersection(geom2)
            cruce_en_ducto = any(inter_geom.distance(d.geometry()) <= 0.05 for d in DuctosList)
            if cruce_en_ducto: continue
            cruce_en_poste = any(inter_geom.distance(p.geometry()) <= 0.05 for p in PostesCriticos)
            if cruce_en_poste: continue
            es_empalme_valido = False
            if inter_geom.type() == QgsWkbTypes.PointGeometry:
                pts = inter_geom.asMultiPoint() if inter_geom.isMultipart() else [inter_geom.asPoint()]
                f2, nombre2 = obtener_datos_cable(cable2)
                puntos_ok = True
                for pt in pts:
                    pt_valido = False
                    if f1 == 288 and f2 == 144:
                        if pt.distance(get_endpoint(geom1)) <= 0.01 and pt.distance(get_startpoint(geom2)) <= 0.01: pt_valido = True
                    elif f1 == 144 and f2 == 288:
                        if pt.distance(get_startpoint(geom1)) <= 0.01 and pt.distance(get_endpoint(geom2)) <= 0.01: pt_valido = True
                    elif f1 == 144 and f2 == 144:
                        if pt.distance(get_startpoint(geom1)) <= 0.01 and pt.distance(get_startpoint(geom2)) <= 0.01: pt_valido = True
 
                    if not pt_valido:
                        puntos_ok = False
                        break
                if puntos_ok:
                    es_empalme_valido = True
            if not es_empalme_valido:
                cables_con_error[cable1[fields.FID]] = cable1
                cables_con_error[cable2[fields.FID]] = cable2
 
    for fid, cable in cables_con_error.items():
        fibras_actual, nombre_cable = obtener_datos_cable(cable)
        if fibras_actual == 288:
            tiene_ducto = any(cable.geometry().intersects(d.geometry()) for d in DuctosList)
            tiene_poste = any(cable.geometry().intersects(p.geometry()) for p in PostesCriticos)
            if tiene_ducto or tiene_poste:
                continue
 
        errorMsgs.append({
            'msg': f"Error: Cable {cable[fields.UUID]} de nombre: {nombre_cable} ({fibras_actual}F) intersecta irregularmente en el aire sin empalme válido.",
            'lid': layerInfra.LID,
            'UUID': cable[fields.UUID],
            'feature_FK': cable[fields.FID]
        })
 
    return errorMsgs


def checkAreasTroncales():
    # Chequea que las areas troncales tengan excatamente 60 areas de distribucion
    errorMsgs = []
    numAreasDistribucion = 60
    nivelTroncal = 10
    for areaTroncal in layerArea.getFeaturesBy(fields.LEVEL, nivelTroncal):
        totalAreasDistribucion = 0
        for area in layerArea.getIntersectingFeatures(layerArea.LID, areaTroncal):
            if area[fields.LEVEL] == areaType.DISTRIBUCION:
                if areaTroncal.geometry().contains(area.geometry().centroid()):
                    totalAreasDistribucion += 1
        
        if totalAreasDistribucion != numAreasDistribucion:
            errorMsgs.append({
                'msg': f"Error: Area Troncal {areaTroncal[fields.UUID]} tiene {totalAreasDistribucion} areas de distribucion (deberia tener {numAreasDistribucion}).",
                'lid': layerArea.LID,
                'UUID': areaTroncal[fields.UUID],
                'feature_FK': areaTroncal[fields.FID],
                'tipo': f"Error"
            })
    
    return errorMsgs


def checkSumHHEjesAreasPrediseno():
    # Chequea que la suma de HH de UFs, ejes y areas SDU/MDU coincidan
    #   suma_demanda_total_ejes == suma_HH_UFs == demanda_SDU_area + suma_MDU_areas
 
    errorMsgs = []
 
    # Iteramos por áreas SDU
    for area_sdu in layerArea.getFeaturesBy(fields.LEVEL, networkLevel.DISPERSION,
                                             f'and {fields.TIPO} = {areaType.SDU}'):
 
        area_uuid = area_sdu[fields.UUID]
 
        # el area SDU debe tener eje_FK 
        eje_uuid = area_sdu[fields.ASSIGNED_EJE]
        if not eje_uuid:
            errorMsgs.append({
                'msg': f"[Area SDU: {area_uuid}] Error: El área SDU no tiene eje asignado (eje_FK vacío).",
                'lid': layerArea.LID,
                'UUID': area_uuid,
                'feature_FK': area_sdu[fields.FID],
                'tipo': "Error"
            })
            continue
 
        # Datos del eje principal
        ejes = list(layerEjes.getFeaturesBy(fields.UUID, eje_uuid))
        if not ejes:
            errorMsgs.append({
                'msg': f"[Area SDU: {area_uuid}] Error: El área SDU tiene un eje_FK que no existe en la capa de ejes.",
                'lid': layerArea.LID,
                'UUID': area_uuid,
                'feature_FK': area_sdu[fields.FID],
                'tipo': "Error"
            })
            continue
 
        # Buscamos si hay un segundo eje que tenga el mismo ASSIGNED_AREA 
        ejes_hermanos = list(layerEjes.getFeaturesBy(fields.ASSIGNED_AREA, area_uuid))
        for eje_hermano in ejes_hermanos:
            if eje_hermano[fields.UUID] != eje_uuid:  # evitamos duplicar el principal
                ejes.append(eje_hermano)
 
        # Sumamos demandas de todos los ejes asociados (1 o 2)
        ejes_uuids        = [eje[fields.UUID] for eje in ejes]
        demanda_sdu_eje   = sum(eje[fields.DEMANDA_SDU] or 0 for eje in ejes)
        demanda_mdu_eje   = sum(eje[fields.DEMANDA_MDU] or 0 for eje in ejes)
        demanda_total_eje = demanda_sdu_eje + demanda_mdu_eje
 
        #  Demanda del area SDU
        demanda_sdu_area = area_sdu[fields.DEMANDA_SDU] or 0
 
        # Areas MDU y UFs
        areas_mdu = []
        suma_hh_ufs = 0
 
        for eje_uuid in ejes_uuids:
 
            # Areas MDU asociadas a este eje
            areas_mdu += list(layerArea.getFeaturesBy(
                fields.ASSIGNED_EJE, eje_uuid,
                f'and {fields.TIPO} = {areaType.MDU}'
            ))
 
            # UFs asociadas a este eje
            ufs = list(layerUnidadesFuncionales.getFeaturesBy(fields.ASSIGNED_EJE, eje_uuid))
            suma_hh_ufs += sum(uf[fields.HH_UF] or 0 for uf in ufs)
 
        suma_demanda_mdu_areas = sum(a[fields.DEMANDA_MDU] or 0 for a in areas_mdu)
 
        # Demanda total desde las areas (SDU + suma MDUs)
        demanda_total_areas = demanda_sdu_area + suma_demanda_mdu_areas
 
        #  CHEQUEO FINAL 
        if not (demanda_total_eje == suma_hh_ufs == demanda_total_areas):
 
            ejes_str = " + ".join(ejes_uuids)
            msg = (
                f"[Ejes: {ejes_str}] "
                f"Error HH: "
                f"Eje=({demanda_sdu_eje} SDU + {demanda_mdu_eje} MDU = {demanda_total_eje}) | "
                f"Areas=({demanda_sdu_area} SDU + {suma_demanda_mdu_areas} MDU = {demanda_total_areas}) | "
                f"UFs={suma_hh_ufs}"
            )
 
            # Marcamos el area SDU
            errorMsgs.append({
                'msg': msg,
                'lid': layerArea.LID,
                'UUID': area_uuid,
                'feature_FK': area_sdu[fields.FID],
                'tipo': "Error"
            })
 
            # Marcamos cada area MDU involucrada
            for area_mdu in areas_mdu:
                errorMsgs.append({
                    'msg': msg,
                    'lid': layerArea.LID,
                    'UUID': area_mdu[fields.UUID],
                    'feature_FK': area_mdu[fields.FID],
                    'tipo': "Error"
                })
 
    return errorMsgs

def CheckAreasSduMduIntersectadasPorCD():
    # Chequea que las areas de nivel 40 (SDU y MDU) tengan su centroide dentro de una sola area CD
    errorMsgs = []
    for area in layerArea.getFeaturesBy(fields.LEVEL, 40):
        # veo si q el area sea SDU o MDU
        if area[fields.TIPO] == areaType.SDU or area[fields.TIPO] == areaType.MDU:
            areasCD = []
            centroide = area.geometry().centroid()
            # Buscar áreas CD que contengan el centroide del area actual
            for areaCD in layerArea.getFeaturesBy(fields.LEVEL, 30):
                if areaCD.geometry().contains(centroide):

                    areasCD.append(areaCD)
            # Verificar que exista solo 1 área CD
            cantidadCD = len(areasCD)
            # print(f"Area {area[fields.UUID]} tiene {cantidadCD} areas CD")
            if cantidadCD != 1:
                if cantidadCD == 0:
                    errorMsgs.append({
                        'msg': f"Error: Area de UUID: {area[fields.UUID]} no tiene su centroide contenido en ninguna area CD.",
                        'lid': layerArea.LID,
                        'UUID': area[fields.UUID],
                        'feature_FK': area[fields.FID]
                    })
                else:
                    errorMsgs.append({
                        'msg': f"Error: Area de UUID: {area[fields.UUID]} tiene su centroide contenido en {cantidadCD} areas CD (Solamente tiene que ser 1).",
                        'lid': layerArea.LID,
                        'UUID': area[fields.UUID],
                        'feature_FK': area[fields.FID]
                    })
    return errorMsgs

def checkMaxCTOHUBporAreaCP():
    # Chequea que ninguna area de CP tenga mas de 20 CTO_HUB asociados
    errorMsgs=[]
    count={}
    relations = relationsNode_Area.getRelations(fields.AREA_NIVEL, areaType.CP, filter=lambda r: r[fields.NODO_TIPO] == elementType.HUB)

    for rel in relations:
        areaCPUUID = rel[fields.TARGET_UUID]
        if areaCPUUID not in count:
            count[areaCPUUID] = 0
        count[areaCPUUID] += 1

    for areaCPUUID, ctoCount in count.items():
        if ctoCount > MAX_CTOHUB_IN_AREA_CP:    
            errorMsgs.append({
                    'msg':f"Error cantidad HUB por Area CP: {areaCPUUID} tiene {ctoCount} HUB asociados, excede el maximo de {MAX_CTOHUB_IN_AREA_CP}",
                    'lid':layerArea.LID,
                    'UUID':areaCPUUID,
                    'feature_FK':None,
                    'tipo': f"Error"
                })

    return errorMsgs            
    



def checkRamasDistintasEnVereda():
    errorMsgs = []
    veredaDict = {} 
    
    #
    relationsNode_Vereda.updateRelations()
    relations = relationsNode_Vereda.relationsList
    

    for rel in relations:
        veredaUuid = rel.get(fields.TARGET_UUID)
        nodoUuid = rel.get(fields.NODO_UUID)
        
        nodosEncontrados = layerNode.getFeaturesBy(fields.UUID, nodoUuid)
        if not nodosEncontrados:
            continue
            
        nodoFeat = nodosEncontrados[0]
        
        # Filtro: Solo tipo 50 (CTO)
        if nodoFeat[fields.TIPO] != elementType.CTO:
            continue
            
        ordenVal = nodoFeat[fields.ORDEN]
        nombreVal = nodoFeat[fields.NOMBRE] if fields.NOMBRE in nodoFeat.fields().names() else 'Sin_Nombre'
            
        rama = obtenerRama(ordenVal)
        if rama is None or not veredaUuid:
            continue
            
        veredaDict.setdefault(veredaUuid, []).append({
            'rama': rama,
            'nombre': nombreVal,
            'orden': ordenVal
        })


    
    for veredaUuid, cajas in veredaDict.items():
        # Creo un (set) de ramas para ver las distintas
        ramasEncontradas = {c['rama'] for c in cajas}
        
        if len(ramasEncontradas) > 1:
            detalle = ', '.join(f"{c['nombre']} (rama {c['rama']})" for c in cajas)
            
            errorMsgs.append({
                'msg': f"Error: la vereda {veredaUuid} tiene CTOs de distinta rama asociados: {detalle}",
                'lid': layerVeredas.LID,
                'UUID': veredaUuid,
                'feature_FK': layerVeredas.getFeaturesBy(fields.UUID, veredaUuid)[0][fields.FID] if layerVeredas.getFeaturesBy(fields.UUID, veredaUuid) else None,
                'tipo': "Error"
            })
            
            
    #         print(f"Error en Vereda {veredaUuid}:")
    #         print(f"  Ramas presentes: {ramasEncontradas}")
    #         print(f"  Nodos: {detalle}")
            
    # print(f"Se detectaron {len(errorMsgs)} veredas con errores de mezcla de ramas.")
    
    return errorMsgs


def obtenerRama(orden) -> 'Optional[int]':
    if orden is None or orden == NULL or orden == numHarcodes.NO_ORDER:
        return None
        
    try:
        ordenStr = str(int(orden))
        if len(ordenStr) == 0:
            return None
        return int(ordenStr[0])
    except (ValueError, TypeError):
        return None

def checkMaxCTOHUBporCP():
    # Chequea que ninguna CP tenga mas de 8 CTO HUB asociados
    errorMsgs=[]
    conteo={}
    
    for cto in layerNode.getFeaturesBy(fields.TIPO,elementType.HUB):
        padreUUID=cto[fields.NETPARENT_FK]
        
        if padreUUID == NULL:
            continue
        
        if padreUUID not in conteo:
            conteo[padreUUID]=0
        conteo[padreUUID]+=1
    
    for cp in layerNode.getFeaturesBy(fields.TIPO,elementType.PC):
        cantidad = conteo.get(cp[fields.UUID],0)
        if cp[fields.UUID] in conteo and conteo[cp[fields.UUID]]>MAX_CTOHUB_POR_CP:
            errorMsgs.append({
                    'msg':f"Error cantidad CTO HUB por CP: {cp[fields.UUID]} tiene {cantidad} HUB asociados, excede el maximo de {MAX_CTOHUB_POR_CP}",
                    'lid':layerNode.LID,
                    'UUID':cp[fields.UUID],
                    'feature_FK':cp[fields.FID],
                    'tipo': f"Error"
                })
    return errorMsgs

def checkDemandaAreas():
    # Chequea la demanda de las areas CTO y MDU
    errorMsgs=[]
    demandaSDU={}
    demandaMDU={}
    
    for uf in layerUnidadesFuncionales.getFeatures():
        
        if not uf[fields.ASSIGNED_AREA]:
            continue
        hh =uf[fields.HH_UF] or 0

        if uf[fields.CLASIFICACION_UF] == clasificacionUF.SDU:
            demandaSDU[uf[fields.ASSIGNED_AREA]]=demandaSDU.get(uf[fields.ASSIGNED_AREA],0)+hh
        
        elif uf[fields.CLASIFICACION_UF] == clasificacionUF.MDU:
            demandaMDU[uf[fields.ASSIGNED_AREA]]=demandaMDU.get(uf[fields.ASSIGNED_AREA],0)+hh
    
    for area in layerArea.getFeatures():
        if area[fields.TIPO] == areaType.SDU:
            demandaCalculada=demandaSDU.get(area[fields.UUID],0)
            
            if area[fields.DEMANDA_SDU] != demandaCalculada:
                errorMsgs.append({
                        'msg':f"Error Demanda SDU: {area[fields.UUID]} tiene demanda {area[fields.DEMANDA_SDU]}, pero la demanda calculada por vivienda asociada es {demandaCalculada}",
                        'lid':layerArea.LID,
                        'UUID':area[fields.UUID],
                        'feature_FK':area[fields.FID],
                        'tipo': f"Error"
                    })
        elif area[fields.TIPO] == areaType.MDU:
            demandaCalculada=demandaMDU.get(area[fields.UUID],0)
            
            if area[fields.DEMANDA_MDU] != demandaCalculada:
                errorMsgs.append({
                        'msg':f"Error Demanda MDU: {area[fields.UUID]} tiene demanda {area[fields.DEMANDA_MDU]}, pero la demanda calculada por vivienda asociada es {demandaCalculada}",
                        'lid':layerArea.LID,
                        'UUID':area[fields.UUID],
                        'feature_FK':area[fields.FID],
                        'tipo': f"Error"
                    })

    return errorMsgs

def checkDerivaciones():
    # Es un error si un nodo endpoint tiene derivaciones del mismo fibercount
    errorMsgs=[]
    tree = mtTree()
    tree.buildTree()

    # Pido lista de nodos endpoint en la capa Acceso y Alimentacion
    endPointNodes = tree.getNodesAsList(filter=lambda x: x.isEndPoint==True and filterNodesAccAlim(x))

    for node in endPointNodes:
        parentCable = node.parent
        
        for childCable in node.children:
            if filterCablesAccAlim(childCable): #No nos importan los jumpers, solo cables Acceso o alimentacion
                if childCable.numFibers == parentCable.numFibers:
                    errorMsgs.append({
                        'msg':f"Error Derivacion: En el nodo {node.name} inicia y finaliza un cable con la misma capacidad, tendria que ser el mismo cable",
                        'lid':layerNode.LID,
                        'UUID':node.name,
                        'feature_FK':node.fid,
                        'tipo': f"Error",
                    })

    return errorMsgs


def checkMaxCables32PorPC():
    # Chequea que ningún nodo PC (tipo 30) esté asociado a más de 4 cables de 32 fibras
    errorMsgs = []
    tree = mtTree()
    tree.buildTree()
    MAX_CABLES_32F = 4
    pcNodesData = {}
    
    # 1. Identificamos los nodos PC (tipo 30) en la capa y guardamos el fid
    for pc in layerNode.getFeaturesBy(fields.TIPO, elementType.PC):
        pcNodesData[pc[fields.UUID]] = pc[fields.FID]
    allNodes = tree.getNodesAsList()

    for node in allNodes:
        # Solo procesamos si el es nodo PC de la lista
        if node.name in pcNodesData:
            conteoCables32 = 0
            # Revisar el cable entrante al nodo (parent)
            if node.parent is not None and node.parent.numFibers == 32:
                conteoCables32 += 1
            # Revisar todos los cables salientes del nodo (children)
            for childCable in node.children:
                if childCable.numFibers == 32:
                    conteoCables32 += 1
            if conteoCables32 > MAX_CABLES_32F:
                errorMsgs.append({
                    'msg': f"Error cables por PC: El nodo PC {node.name} tiene {conteoCables32} cables de 32 fibras asociados, excede el máximo de {MAX_CABLES_32F}",
                    'lid': layerNode.LID,
                    'UUID': node.name,
                    'feature_FK': pcNodesData[node.name],
                    'tipo': f"Error"
                })
    return errorMsgs


QAQC_DICT=({
    'Chequeo_1' :{
        'desc':'Chequea que todos los elementos de red tengas Status Vinculo OK',
        'test': CheckStatusVinculo,
        'orden':10000,
    },
    'Chequeo_2':{
        'desc':'Chequea que todos los cables tengan Status Capacidad OK',
        'test':CheckStatusCapacidad,
        'orden':20000,
    },
    # 'Chequeo_3' :{
    # 'desc':'chequea que todas las UF esten contenidas',
    # 'test': CheckUFContenidas,
    # 'orden':30000,
    # },    
    'Chequeo_4' :{
    'desc':'Chequea las longitudes de Jumpers',
    'test': CheckJumpersExcedidos,
    'orden':40000,
     },
    # 'Chequeo_5' :{
    # 'desc':'Chequea los cables secundarios en CP',
    # 'test': checkCablesSecundarios,
    # 'orden':50000,
    # },
    # 'Chequeo_6' :{
    # 'desc':'Chequea que no haya mas de 60CD',
    # 'test': checkCantidadCD,
    # 'orden':60000,
    # },
    'Chequeo_7' :{
    'desc':'Chequea cajas con colocacion en poste y si son colocacion libre que no intersecten con postes',
    'test': CheckCajasPostes,
    'orden':70000,
    },
    # 'Chequeo_8' :{
    # 'desc':'Chequea si dos cajas de la misma teleco intersectan en mismo poste',
    # 'test': CheckCajasMismoPoste,
    # 'orden':80000,
    #  },
    # 'Chequeo_9' :{
    # 'desc':'Chequea cuantas cajas iniciales y futuras intersectan un area ',
    # 'test': CheckCajasInicialesYfuturas,
    # 'orden':90000,
    # },
    'Chequeo_10' :{
    'desc':'Chequea que todos los postes que tengan un comentario de factibilidad este en uso ',
    'test': checkPostesAInstalarEnUso,
    'orden':100000,
     },
    # 'Chequeo_11' :{
    # 'desc':'Chequea las ganancias estrategicas',
    # 'test': checkGanancias,
    # 'orden':100000,
    # }
    # ,
    # 'Chequeo_12' :{
    # 'desc':'Chequea que no haya mas de 3 cajas B por cada caja A',
    # 'test': checkCantidadCajasB,
    # 'orden':110000,
    # },
    # 'Chequeo_13' :{
    # 'desc':'Chequea jumpers duplicados',
    # 'test': checkJumpersDuplicados,
    # 'orden':120000,
    # },
    # 'Chequeo_14' :{
    # 'desc':'Chequea que no exista mas de 4 cajas A por cada caja de distribucion (CD)',
    # 'test': checkCajasAporCajasCD,
    # 'orden':130000,
    # },
    # 'Chequeo_15' :{
    # 'desc':'Chequea consistencia entre areas de distribucion y cajas CD, A y B',
    # 'test': checkConsistencyAreasCDyCajas,
    # 'orden':140000,
    # },
    # 'Chequeo_16' :{
    # 'desc':'Chequea nombre de jumpers duplicados y conexiones',
    # 'test': CheckJumpersDuplicadosYConexiones,
    # 'orden':150000,
    # },
    # 'Chequeo_17' :{
    # 'desc':'Chequea atenuacion maxima permitida en nodos',
    # 'test': CheckAtenuacion,
    # 'orden':160000,
    # },
    # 'Chequeo_18' :{
    # 'desc':'Chequea que las CD no se asocien a mas de 4 jumpers A y que los nodos A no se asocien a mas de 3 jumpers B',
    # 'test': checkJumpersNodosCDyCajaA,
    # 'orden':170000,
    # },
    # 'Chequeo_19' :{
    # 'desc':'Chequea que un Jumper A o B no conecte a nodos del mismo nivel',
    # 'test': checkCableConectDelNodosMismoNivel,
    # 'orden':180000,
    # },
    # 'Chequeo_20' :{
    # 'desc':'Chequea que no existan areas de distribucion con demanda mayor a 128HH',
    # 'test': checkAreasCDdemanda128,
    # 'orden':190000,
    # },
    'Chequeo_21' :{
    'desc':'Chequea que los cables troncal tengan los CE de continuidad necesarios',
    'test': checkCierresEmpalme,
    'orden':200000,
    },
    'Chequeo_22' :{
    'desc':'Chequea que los cierres de empalme (CE) tengan al menos una derivacion asociada. (Revisar Nodo inicio en cables)',
    'test': CheckCEsinDerivacion,
    'orden':210000,
    },
    # 'Chequeo_23' :{
    # 'desc':'Chequea que las areas SDU tengan al menos un poste dentro de su geometria',
    # 'test': checkAreasConPoste,
    # 'orden':220000,
    # },
    # 'Chequeo_24' :{
    # 'desc':'Chequea que la suma de HH de UFs, ejes y areas SDU/MDU coincidan',
    # 'test': checkSumHHEjesAreas,
    # 'orden':230000,
    # },
    # 'Chequeo_25' :{
    # 'desc':'Chequea que las areas de distribucion tengan como maximo 16 cajas (iniciales + futuras)',
    # 'test': checkMaxCajasAreasDistribucion,
    # 'orden':240000,
    # },
    # 'Chequeo_26' :{
    # 'desc':'Chequea que las areas troncales tengan excatamente 60 areas de distribucion',
    # 'test': checkAreasTroncales,
    # 'orden':250000,
    # },
    # 'Chequeo_27' :{
    # 'desc':'Chequea cables troncales de 288 y 144 que intersectan entre sí solo lo hagan en postes criticos o ductos',
    # 'test': checkCableEnPostesCriticosYDuctos,
    # 'orden':260000,
    # }
    'Chequeo_28' :{
    'desc':'Chequea que ningún nodo PC esté asociado a más de 4 cables de 32 fibras',
    'test': checkMaxCables32PorPC,
    'orden':280000,
    },
    'Chequeo_29' :{
    'desc':'Chequea que las veredas no tengan CTOs de distinta rama asociados',
    'test': checkRamasDistintasEnVereda,
    'orden':290000,
    },  
        
    'Chequeo_40' :{
    'desc':'Determina si hay manzanas con el mismo ID',
    'test': checkManzanas,
    'orden':400000,
    },
    
    'Chequeo_50' :{
    'desc':'Determina si las Cámaras en uso tienen nodo',
    'test': checkCamaras,
    'orden':500000,
    },

    'Chequeo_30' :{
    'desc':'Valida que los cables tengan infraestructura asignada en sus nodos extremos, exceptuando cables (Fase MDU) ',
    'test': checkInfraestructuraEnCables,
    'orden':30000,
    }


})



QAQC_DICT_UNIFICADO=({
  
    'Chequeo_23' :{
    'desc':'Chequea que las areas SDU tengan al menos un poste dentro de su geometria',
    'test': checkAreasConPoste,
    'orden':220000,
    },
    # 'Chequeo_24' :{
    # 'desc':'Chequea que la suma de HH de UFs, ejes y areas SDU/MDU coincidan',
    # 'test': checkSumHHEjesAreas,
    # 'orden':230000,
    # },
    'Chequeo_25' :{
    'desc':'Chequea que las areas de distribucion tengan como maximo 16 cajas (iniciales + futuras)',
    'test': checkMaxCajasAreasDistribucion,
    'orden':240000,
    },
    'Chequeo_26' :{
    'desc':'Chequea que las areas troncales tengan excatamente 60 areas de distribucion',
    'test': checkAreasTroncales,
    'orden':250000,
    },
    'Chequeo_27' :{
    'desc':'Chequea que los cables troncal de fibras 288 y 144 que intersectan entre sí solo lo hagan en postes criticos o ductos',
    'test': checkCableEnPostesCriticosYDuctos,
    'orden':260000,
    }




})


QAQC_DICT_PREDISENO=({
    
    'Chequeo_24' :{
    'desc':'Chequea que la suma de HH de UFs, ejes y areas SDU/MDU coincidan',
    'test': checkSumHHEjesAreasPrediseno,
    'orden':230000,
    },
    'Chequeo_25' :{
    'desc':'Chequea que las areas de distribucion tengan como maximo 16 cajas (iniciales + futuras)',
    'test': checkMaxCajasAreasDistribucion,
    'orden':240000,
    },
    
    'Chequeo_26' :{
        'desc':'Chequea que las areas SDU y MDU esten intersectadas por un area CD',
        'test': CheckAreasSduMduIntersectadasPorCD,
        'orden':260000,
    },
    'Chequeo_27' :{
    'desc':'Chequea que las areas troncales tengan excatamente 60 areas de distribucion',
    'test': checkAreasTroncales,
    'orden':250000,
    }


})



QAQC_DICT_POSTES=({
    
    'Chequeo_10' :{
    'desc':'Chequea que todos los postes que tengan un comentario de factibilidad este en uso ',
    'test': checkComFactInfraFk,
    'orden':100000,


}

})

QAQC_DICT_CAJAS=({

# 'Chequeo_29' :{
#     'desc':'Chequea que las veredas no tengan CTOs de distinta rama asociados',
#     'test': checkRamasDistintasEnVereda,
#     'orden':290000,
#     },

'Chequeo_30' :{
    'desc':'Valida que los cables tengan infraestructura asignada en sus nodos extremos, exceptuando cables (Fase MDU)',
    'test': checkInfraestructuraEnCables,
    'orden':300000,
    }


})