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

from qgis import processing


from .mtFuncs import *
from .mtConstants import *
from .mtLayer import *
from .mtCableTraces import mtCableTraces, mtCableTrace
import json



def crearHerrajes (cableTraces: mtCableTraces, myTree: mtTree, delOld=True): 
    
    expression1 = QgsExpression('uuid(\'Id128\')')
    expression2 = QgsExpression('uuid(\'Id128\')')
    context = QgsExpressionContext()
    infraEnUso = set() 
    
    if delOld:
        layerHerrajes.startEditing()
        featsToDelete = layerHerrajes.getFeaturesBy(HWFields.LONG_CABLE,0,\
                                                    f'or {fields.TIPO} <> {mountingHwType.RIENDA}')  # Borro todo menos toma tierras y riendas
        layerHerrajes.deleteFeatures([feat.id() for feat in featsToDelete])
        layerHerrajes.commitChanges()
        
    layerHerrajes.startEditing()   

    for cable in layerCable.getFeatures():

        cable=mtFeature(cable)

        mountingHwOffset = mountingHwType.OFFSET_HERRAJES_TRONCAL

        cableTraceList=cableTraces.getTracesListForCable(cable[fields.UUID])
        lastCableTraceIter=len(cableTraceList)-1
        counterHwPaso:int=0
        
        nuevoHerraje=layerHerrajes.newFeature()
        nuevoHerraje[fields.PARENT_CABLE]=cable[fields.UUID]
        nuevoHerraje[fields.FASE]=cable[fields.FASE]
        nuevoHerraje[fields.TASA_PROJECT]=cable[fields.TASA_PROJECT]
       
        lastTrace: 'Optional[mtCableTrace]'=None

        for i,thisTrace in enumerate(cableTraceList):
            if thisTrace.getStartFid() is not None:
  
                # if we dont have a startFid, we skip
                startFeat=thisTrace.getStartFeature()                                           
                assert startFeat is not None
                
                infraEnUso.add(startFeat.id())      
                nuevoHerraje[fields.ASSIGNED_INFRA]=startFeat.get(fields.UUID)                  
                nuevoHerraje.setGeometry(startFeat.geometry())
                
                if cable[fields.CANT_FIBRAS]==1:
                    nuevaCadenaJumper=layerHerrajes.newFeature()
                    nuevaCadenaJumper[fields.TIPO]=mountingHwType.CADENA_JUMPER
                    nuevaCadenaJumper[fields.PARENT_CABLE]=cable[fields.UUID] 
                    nuevaCadenaJumper[fields.FASE]=cable[fields.FASE]
                    nuevaCadenaJumper[fields.ASSIGNED_INFRA]=startFeat.get(fields.UUID)   
                    nuevaCadenaJumper[fields.AUTOGENERADO] = True
                    nuevaCadenaJumper.setGeometry(startFeat.geometry())
                    context.setFeature(nuevaCadenaJumper)
                    nuevaCadenaJumper[fields.UUID]=expression2.evaluate(context)        
                    layerHerrajes.addFeature(nuevaCadenaJumper)
                    
                
                if i==0:
                    #startNode so type=TERMINAL
                    nuevoHerraje[fields.TIPO]=mountingHwType.TERMINAL + mountingHwOffset
                    counterHwPaso=0
                if lastTrace is not None:
                    hasGainsOrBoxes=max(len(thisTrace.startCajFk),len(thisTrace.startGanFk))
                    myAngle=thisTrace.getAngleBetween(lastTrace)
                    if (myAngle<HWPASO_MIN_ANGLE  or hasGainsOrBoxes>0):
                        nuevoHerraje[fields.TIPO]=mountingHwType.DUPLO + mountingHwOffset
                        counterHwPaso=0
                    else:
                        nuevoHerraje[fields.TIPO]=mountingHwType.PASO + mountingHwOffset
                        counterHwPaso+=1
                        

                context.setFeature(nuevoHerraje)
                nuevoHerraje[fields.UUID]=expression1.evaluate(context)
                nuevoHerraje[fields.AUTOGENERADO] = True        
                layerHerrajes.addFeature(nuevoHerraje)
               

            if i==lastCableTraceIter and thisTrace.getEndFid() is not None:
                # this is the last trace, add the last infra
                endFeat=thisTrace.getEndFeature()                
                
                infraEnUso.add(endFeat.id())

                nuevoHerraje[fields.ASSIGNED_INFRA]=endFeat.get(fields.UUID)
                nuevoHerraje.setGeometry(endFeat.geometry())
                nuevoHerraje[fields.TIPO]=mountingHwType.TERMINAL + mountingHwOffset
                context.setFeature(nuevoHerraje)
                nuevoHerraje[fields.UUID]=expression1.evaluate(context)
                nuevoHerraje[fields.AUTOGENERADO] = True 
                layerHerrajes.addFeature(nuevoHerraje)
                
                if cable[fields.CANT_FIBRAS]==1:
                    nuevaCadenaJumper=layerHerrajes.newFeature()
                    nuevaCadenaJumper[fields.TIPO]=mountingHwType.CADENA_JUMPER
                    nuevaCadenaJumper[fields.PARENT_CABLE]=cable[fields.UUID] 
                    nuevaCadenaJumper[fields.FASE]=cable[fields.FASE]
                    nuevaCadenaJumper[fields.TASA_PROJECT]=cable[fields.TASA_PROJECT]
                    nuevaCadenaJumper[fields.ASSIGNED_INFRA]=startFeat.get(fields.UUID)
                    nuevaCadenaJumper[fields.TASA_PROJECT]=cable[fields.TASA_PROJECT]
                    nuevaCadenaJumper[fields.AUTOGENERADO] = True             
                    nuevaCadenaJumper.setGeometry(startFeat.geometry())                   
                    context.setFeature(nuevaCadenaJumper)
                    nuevaCadenaJumper[fields.UUID]=expression2.evaluate(context) 
                    layerHerrajes.addFeature(nuevaCadenaJumper)

                    
            lastTrace=thisTrace

    deleteDuplicateChains()          
    setDistanceAlong(layerHerrajes)    
    
    layerHerrajes.commitChanges() 
    herrajesSuspensor()
    createHerrajeTomaTierra()
    createHerrajeRienda()
    layerInfra.batchUpdateField(infraEnUso, fields.POSTE_EN_USO, True)
    # print("iniciando creación de cruces de calle")
    processing.run("project:createCrucesCalle", {}) #v24 diseño
    



def herrajesSuspensor():
    layerHerrajes.startEditing()
    layerSuspensor.startEditing()
    expressionInicio = QgsExpression("uuid('Id128')")
    expressionFin = QgsExpression("uuid('Id128')")
    context = QgsExpressionContext()

    infraEnUso = set()

    suspensorToCable = {}
    infraSuspensores = layerInfra.getFeaturesBy(fields.INFRA_TIPO, infraNodeType.SUSPENSOR)

    for infra in infraSuspensores:
        atributosSecStr = infra[fields.ATRIBUTOS_SEC]
        if atributosSecStr:
            try:
                data = json.loads(atributosSecStr)
                suspensorFk = data.get(fields.SUSPENSOR_FK)
                cableFk = data.get(fields.PARENT_CABLE)

                if suspensorFk and cableFk:
                    suspensorToCable[suspensorFk] = cableFk
            except Exception:
                continue

    uuidToFidInfra = {infra[fields.UUID]: infra.id() for infra in layerInfra.getFeatures()}

    for suspensor in layerSuspensor.getFeatures():

        # Herraje del poste inicio
        nuevoHerrajeInicio = layerHerrajes.newFeature()
        nuevoHerrajeInicio[fields.TIPO] = mountingHwType.SUSPENSOR
        nuevoHerrajeInicio[fields.ASSIGNED_INFRA] = suspensor[fields.INFRA_INICIO_FK]
        nuevoHerrajeInicio[fields.TASA_PROJECT] = suspensor[fields.TASA_PROJECT]
        nuevoHerrajeInicio[fields.FASE] = faseConstruccion.FASE_1
        nuevoHerrajeInicio[fields.AUTOGENERADO] = True

        startPoint = mtFeature.getPointNthAsFeature(suspensor, 0)
        nuevoHerrajeInicio.setGeometry(startPoint.geometry())
        context.setFeature(nuevoHerrajeInicio)
        nuevoHerrajeInicio[fields.UUID] = expressionInicio.evaluate(context)
        layerHerrajes.addFeature(nuevoHerrajeInicio)

        fidInfraInicio = uuidToFidInfra.get(suspensor[fields.INFRA_INICIO_FK])
        if fidInfraInicio is not None:
            infraEnUso.add(fidInfraInicio)

        # Herraje del poste fin
        nuevoHerrajeFin = layerHerrajes.newFeature()
        nuevoHerrajeFin[fields.TIPO] = mountingHwType.SUSPENSOR
        nuevoHerrajeFin[fields.ASSIGNED_INFRA] = suspensor[fields.INFRA_FIN_FK]
        nuevoHerrajeFin[fields.TASA_PROJECT] = suspensor[fields.TASA_PROJECT]
        nuevoHerrajeFin[fields.FASE] = faseConstruccion.FASE_1
        nuevoHerrajeFin[fields.AUTOGENERADO] = True

        endPoint = mtFeature.getPointNthAsFeature(suspensor, -1)
        nuevoHerrajeFin.setGeometry(endPoint.geometry())
        context.setFeature(nuevoHerrajeFin)
        nuevoHerrajeFin[fields.UUID] = expressionFin.evaluate(context)
        layerHerrajes.addFeature(nuevoHerrajeFin)

        fidInfraFin = uuidToFidInfra.get(suspensor[fields.INFRA_FIN_FK])
        if fidInfraFin is not None:
            infraEnUso.add(fidInfraFin)

    for infraSuspensor in layerInfra.getFeaturesBy(fields.INFRA_TIPO, infraNodeType.SUSPENSOR):
        expression = QgsExpression("uuid('Id128')")
        context = QgsExpressionContext()
        nuevoHerrajeSuspensor = layerHerrajes.newFeature()
        nuevoHerrajeSuspensor[fields.TIPO] = mountingHwType.SUSPENSOR_PUNTO_MEDIO
        nuevoHerrajeSuspensor[fields.ASSIGNED_INFRA] = infraSuspensor[fields.UUID]
        nuevoHerrajeSuspensor[fields.TASA_PROJECT] = infraSuspensor[fields.TASA_PROJECT]
        nuevoHerrajeSuspensor[fields.FASE] = faseConstruccion.FASE_1
        nuevoHerrajeSuspensor[fields.AUTOGENERADO] = True
        nuevoHerrajeSuspensor.setGeometry(infraSuspensor.geometry())
        context.setFeature(nuevoHerrajeSuspensor)
        nuevoHerrajeSuspensor[fields.UUID] = expression.evaluate(context)
        layerHerrajes.addFeature(nuevoHerrajeSuspensor)

        infraEnUso.add(infraSuspensor.id())

    layerHerrajes.commitChanges()
    layerSuspensor.commitChanges()

    layerInfra.batchUpdateField(infraEnUso, fields.POSTE_EN_USO, True)


def createHerrajeTomaTierra(delOld: bool = True):
    layerHerrajes.startEditing()
    if delOld:
        featsToDelete = layerHerrajes.getFeaturesBy(fields.TIPO, mountingHwType.TOMA_TIERRA)
        if featsToDelete:            
            layerHerrajes.deleteFeatures([feat.id() for feat in featsToDelete])

    expression = QgsExpression("uuid('Id128')")
    context = QgsExpressionContext()

    # Clave (infra_FK asignada, suspensor_FK) de los herrajes ya creados en esta corrida,
    # para no duplicar cuando un mismo suspensor tiene mas de un nodoinfrasuspensor (midpoint)
    herrajesCreados = set()

    for midPointsInfra in layerInfra.getFeaturesBy(fields.INFRA_TIPO, infraNodeType.SUSPENSOR):
        proyectoTasaNodo = midPointsInfra[fields.TASA_PROJECT]
        atributosSec = json.loads(midPointsInfra[fields.ATRIBUTOS_SEC])
        
        cableFkList = atributosSec[fields.PARENT_CABLE]
        
        tieneCableNoJumper = False
        for cableUuid in cableFkList:
            cableFeats = layerCable.getFeaturesBy(fields.UUID, cableUuid)
            if cableFeats:
                cableFeat = cableFeats[0]
                # Validamos si el cable es distinto a la red de distribucion (Jumper)
                if cableFeat[fields.LEVEL] != networkLevel.RED_DISTRIBUCION:
                    tieneCableNoJumper = True
                    break # Encontramos al menos uno que no es Jumper, dejamos de buscar
        
        # Si TODOS los cables de la lista son Jumpers, lo ignoramos
        if not tieneCableNoJumper:
            continue     
        suspensorFeats = layerSuspensor.getFeaturesBy(fields.UUID, atributosSec[fields.SUSPENSOR_FK])
        if not suspensorFeats:
            continue
        suspensorFeat = suspensorFeats[0]
        
        posteInicioFeat = layerInfra.getFeaturesBy(fields.UUID, suspensorFeat[fields.INFRA_INICIO_FK])
        posteInicio = posteInicioFeat[0][fields.COMENTARIO_FACT] if posteInicioFeat else None
        
        posteFinFeat = layerInfra.getFeaturesBy(fields.UUID, suspensorFeat[fields.INFRA_FIN_FK])
        posteFin = posteFinFeat[0][fields.COMENTARIO_FACT] if posteFinFeat else None
       
        if posteInicio == feasibilityComment.SOLICITAR_INST and posteFin == feasibilityComment.SOLICITAR_INST:

            # Evitamos crear mas de un herraje para el mismo (infra de inicio, suspensor):
            # si un suspensor tiene varios nodosinfrasuspensor , este bloque  # se ejecutaria una vez por cada nodo, generando duplicados.
           
            claveHerraje = (suspensorFeat[fields.INFRA_INICIO_FK], suspensorFeat[fields.UUID])
            if claveHerraje in herrajesCreados:
                continue
            herrajesCreados.add(claveHerraje)

            nuevoHerraje = layerHerrajes.newFeature()
            nuevoHerraje[fields.TIPO] = mountingHwType.TOMA_TIERRA
            nuevoHerraje[fields.ASSIGNED_INFRA] = suspensorFeat[fields.INFRA_INICIO_FK]
            
           
            nuevoHerraje[fields.TASA_PROJECT] = proyectoTasaNodo
            nuevoHerraje[fields.FASE] = faseConstruccion.FASE_1 # fase 10

            startPoint = mtFeature.getPointNthAsFeature(suspensorFeat, 0)
            nuevoHerraje.setGeometry(startPoint.geometry())
            context.setFeature(nuevoHerraje)
            nuevoHerraje[fields.UUID] = expression.evaluate(context) 
            nuevoHerraje[fields.AUTOGENERADO] = True
            
            atributosSecundariosDict = {
                fields.SUSPENSOR_FK: suspensorFeat[fields.UUID]
            }
            nuevoHerraje[fields.ATRIBUTOS_SEC] = json.dumps(atributosSecundariosDict)
            
            layerHerrajes.addFeature(nuevoHerraje)
                
    layerHerrajes.commitChanges()
       
def createHerrajeRienda(delOld: bool = True):

    layerHerrajes.startEditing()
    if delOld:
        featsToDelete = layerHerrajes.getFeaturesBy(fields.TIPO, mountingHwType.RIENDA)
        if featsToDelete:            
            layerHerrajes.deleteFeatures([feat.id() for feat in featsToDelete])

    expression = QgsExpression("uuid('Id128')")
    context = QgsExpressionContext()
    
    for cableFeat in layerCable.getFeatures():
        
        if cableFeat[fields.LEVEL] != networkLevel.RED_ALIMENTACION: 
            continue
            
        #  Obtenemos el UUID de la caja nodo en el final del cable
        nodoFinUuid = cableFeat[fields.NODO_FIN]
        cajasNodo = layerNode.getFeaturesBy(fields.UUID, nodoFinUuid)
        
        if not cajasNodo:
            continue
            
        cajaNodoFeat = cajasNodo[0]
        assignedInfraUuid = cajaNodoFeat[fields.ASSIGNED_INFRA]
        
        if not assignedInfraUuid or assignedInfraUuid == NULL:
            continue
            
        # (poste) asociada a esa caja
        infraFeats = layerInfra.getFeaturesBy(fields.UUID, assignedInfraUuid)
        if not infraFeats:
            continue
            
        infraFeat = infraFeats[0]
        
        # poste SOLICITAR_INST
        if infraFeat[fields.COMENTARIO_FACT] != feasibilityComment.SOLICITAR_INST:
            continue # Si es de otro tipo, no se crea y saltamos al siguiente cable
            
        # Si pasa la verificación creamos el herraje
        nuevoHerraje = layerHerrajes.newFeature()
        nuevoHerraje[fields.TIPO] = mountingHwType.RIENDA
        nuevoHerraje[fields.PARENT_CABLE] = cableFeat[fields.UUID]
        nuevoHerraje[fields.FASE] = faseConstruccion.FASE_1 
        nuevoHerraje[fields.TASA_PROJECT] = cableFeat[fields.TASA_PROJECT]
        nuevoHerraje[fields.ASSIGNED_INFRA] = assignedInfraUuid
        nuevoHerraje[fields.AUTOGENERADO] = True  # herraje autogenerado
        
        
        cableUuid = cableFeat[fields.UUID]
        nuevoHerraje[fields.AZI] = getAzimutCableMayorOrden(cableUuid, layerCableTraces)
        
        # Extraemos el punto final del cable, y creamos a partir de este la rienda
        geom = cableFeat.geometry()
        if geom.isMultipart():
            endPoint = geom.asMultiPolyline()[-1][-1]
        else:
            endPoint = geom.asPolyline()[-1]
            
        nuevoHerraje.setGeometry(QgsGeometry.fromPointXY(endPoint))
        context.setFeature(nuevoHerraje)
        nuevoHerraje[fields.UUID] = expression.evaluate(context) 
        
        atributosSecundariosDict = {
            "cable_FK": cableFeat[fields.UUID]
        }
        nuevoHerraje[fields.ATRIBUTOS_SEC] = json.dumps(atributosSecundariosDict)
        
        layerHerrajes.addFeature(nuevoHerraje)
                
    layerHerrajes.commitChanges() 

def getAzimutCableMayorOrden(cableUuid, layerCableTraces):

    if not cableUuid or cableUuid == NULL:
        return 0
        
    # Obtengo todos los traces correspondientes a este cable
    traces = layerCableTraces.getFeaturesBy(fields.PARENT_CABLE, cableUuid)
    
    if not traces:
        return 0
        
    maxOrden = -1
    azimutSeleccionado = 0
    
    for trace in traces:
        
        ordenVal = trace[fields.ORDEN]
        if ordenVal and ordenVal != NULL:
            ordenInt = int(ordenVal)
            if ordenInt > maxOrden:
                maxOrden = ordenInt

                aziVal = trace[fields.AZI]
               
                azimutSeleccionado = float(aziVal) if aziVal and aziVal != NULL else 0
                
    return azimutSeleccionado
    
def setCrossStreets():

   
    deleteDuplicateByInfraPair()  

    layerHerrajes.startEditing()   
 
    for cable in layerCable.getFeatures():    
        listCrossings = []

      
        # Recolectamos cruces de ese cable
        for crossing in layerHerrajes.getFeaturesBy(fields.PARENT_CABLE,cable[fields.UUID],' and ' + fields.TIPO + f'={mountingHwType.CRUCE}'):
            
            
            listCrossings.append({
                "UUID": crossing[fields.UUID],
                "distanceAlong": crossing[fields.DISTANCE_ALONG],
                "feature": crossing,  # guardamos el feature para actualizar luego
            })

        # Ordenamos por distancia
        listCrossings.sort(key=lambda x: x["distanceAlong"])

        # Asignamos el orden y actualizamos el JSON
        for i, c in enumerate(listCrossings, start=1):
            crossingFeat = c["feature"]
            oldJson= crossingFeat[fields.ATRIBUTOS_SEC] or "{}"

            try:
                attrs = json.loads(oldJson)
            except Exception:
                attrs = {}

            attrs["orden"] = i  # agregamos el orden

            newJson = json.dumps(attrs, ensure_ascii=False)
            c["feature"][fields.ATRIBUTOS_SEC] = newJson


            layerHerrajes.updateFeature(c["feature"])



    layerHerrajes.commitChanges()




def deleteDuplicateChains():
    layerHerrajes.startEditing()

    featsToDelete = []

    for feat in layerInfra.getFeatures():
        chainsList = list(layerHerrajes.getFeaturesBy(
            fields.ASSIGNED_INFRA, feat[fields.UUID],
            ' and ' + f'{fields.TIPO}={mountingHwType.CADENA_JUMPER}'
        ))

        if len(chainsList) > 1:
            # Tomamos todos excepto el primero
            featsToDelete += [f.id() for f in chainsList[1:]]


    # Eliminamos duplicados
    if featsToDelete:
        layerHerrajes.deleteFeatures(featsToDelete)

    layerHerrajes.commitChanges()

def deleteDuplicateByInfraPair():
    layerHerrajes.startEditing()
    rawGroups = {}
    featsToDelete = []

    #cargar todos y generar claves simples
    for feat in layerHerrajes.getFeaturesBy(fields.TIPO, mountingHwType.CRUCE):
        rawJson = feat[fields.ATRIBUTOS_SEC]
        if not rawJson:
            continue

        try:
            attrs = json.loads(rawJson)
        except:
            continue

        startFk = attrs.get("startInfra_FK")
        endFk   = attrs.get("endInfra_FK")
        crossFk = attrs.get("crossStreets_FK")

        # --- generar clave base ---
        if startFk and endFk:
            baseKey = ("PAIR", tuple(sorted([startFk, endFk])))
            keyValues = set([startFk, endFk])
        elif startFk:
            baseKey = ("SINGLE", startFk)
            keyValues = set([startFk])
        elif endFk:
            baseKey = ("SINGLE", endFk)
            keyValues = set([endFk])
        else:
            baseKey = ("CROSS", crossFk)
            keyValues = set([crossFk])

        # Buscar cantidad de fibras
        cables = list(layerCable.getFeaturesBy(fields.UUID, feat[fields.PARENT_CABLE]))
        if not cables:
            continue

        fibers = cables[0][fields.CANT_FIBRAS]

        rawGroups.setdefault(baseKey, []).append({
            "feature": feat,
            "fibers": fibers,
            "values": keyValues
        })

    # === fusionar claves relacionadas ===
    merged = {}

    for baseKey, feats in rawGroups.items():
        values = set()
        for f in feats:
            values |= f["values"]  # union: todos los FK relevantes del grupo

        # clave final canónica: el conjunto de valores FK ordenados
        canonicalKey = tuple(sorted(values))

        merged.setdefault(canonicalKey, []).extend(feats)

    # eliminar duplicados ===
    for _, feats in merged.items():
        if len(feats) > 1:
            feats.sort(key=lambda x: x["fibers"], reverse=True)
            duplicates = feats[1:]
            for dup in duplicates:
                featsToDelete.append(dup["feature"].id())

    if featsToDelete:
        layerHerrajes.deleteFeatures(featsToDelete)

    layerHerrajes.commitChanges()




def assignSecondaryCable(myTree):
    
    
    rootNode=myTree.buildTree()
    layerHerrajes.startEditing()

    
    for parentCable in layerCable.getFeaturesBy(fields.LEVEL,networkLevel.SECUNDARIO):

        parentNode = myTree.getNodeFromUUID(parentCable[fields.UUID])
        
        for cable in PreOrderIterSorted(parentNode,childiter=distAlongTotSort,
                                    filter_= lambda n: (n.layer == layerCable.LID)):   
            cableFeat = cable.getFeature()
            for crossingFeat in layerHerrajes.getFeaturesBy(fields.PARENT_CABLE,cableFeat[fields.UUID],f'and {fields.TIPO}={mountingHwType.CRUCE}'):
                
                oldJson= crossingFeat[fields.ATRIBUTOS_SEC] or "{}"

                try:
                    attrs = json.loads(oldJson)
                except Exception:
                    attrs = {}

                attrs["cableSecundario_FK"] = parentCable[fields.UUID]  

                newJson = json.dumps(attrs, ensure_ascii=False)
                crossingFeat[fields.ATRIBUTOS_SEC] = newJson
                
                layerHerrajes.updateFeature(crossingFeat)
                
    layerHerrajes.commitChanges()
