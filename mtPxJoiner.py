from qgis.core import (
    QgsFeatureRequest,
    QgsProject,
    QgsField, # Lo importe para poder agregar campos JMY
    NULL,
    QgsGeometry,
)
from enum import Enum, IntEnum

from itertools import groupby

from PyQt5.QtCore import QVariant # Lo importe para poder agregar campos JMY

from .mtConstants import *   #Importamos todas las constantes de mtConstants

from .mtFuncs import *
from .mtConstants import *
from .mtQAQC import *
from .mtHerrajes import *
from .mtLayer import *
from .mtTree import *

import json

from qgis import processing

def numberNewPx():

    startingNumber = 1
    localidad = mtGenAtt.getValue(mtGenAtt.attName.LOCALIDAD)
    projectName = mtGenAtt.getValue(mtGenAtt.attName.POP)


    for poste in layerInfra.getFeaturesBy(fields.AUTOGENERADO,True):
        if poste[fields.ID_POSTE] != NULL or poste[fields.ID_POSTE] != '':
            try:
                numero = int(poste[fields.ID_POSTE][-4:])
                if numero >= startingNumber:
                    startingNumber = numero + 1
            except:
                pass

    posteNumber = startingNumber

    layerInfra.startEditing()
    for poste in layerInfra.getFeaturesBy(fields.AUTOGENERADO,True):
        poste[fields.ID_POSTE] = f'{localidad}_PX_2{str(posteNumber).zfill(9)}'
        layerInfra.updateFeature(poste)
        posteNumber = posteNumber + 1
        
    layerInfra.commitChanges()


def joinPxAttributes():
   
    layerComentarios = QgsProject().instance().mapLayer(layerIDs.Anotacion_poste)
    layerInfra.startEditing()
    layerComentarios.startEditing()

    for pxFeature in layerInfra.getFeatures():      
        comentNumber = NULL if pxFeature[fields.COMENTARIO_FACT] == NULL else int(pxFeature[fields.COMENTARIO_FACT])
       
        if(comentNumber == NULL):
            pxFeature[fields.COMENTARIO_FACT] = NULL
            layerInfra.updateFeature(pxFeature)
        
        if pxFeature[fields.AUTOGENERADO] == True:
            layerInfra.deleteFeatures([pxFeature[fields.FID]])       
           
    
    postesCambio = postesCambio = str(tuple([material.MADERA.value, material.METALICO.value]))

    postesMaxDist = 10
    for comentario in layerComentarios.getFeatures():
 
        comentNumber = int(comentario[fields.COMENTARIO_FACT])
 
        if(comentNumber == feasibilityComment.SOLICITAR_INST or comentNumber == feasibilityComment.NO_RELEVADO
            or comentNumber == feasibilityComment.NO_RELEVADO_CAMBIO):
            tempFeat = QgsFeature(layerInfra.fields())
            tempFeat.setGeometry(comentario.geometry())
            tempFeat[fields.AUTOGENERADO] =True
            tempFeat[fields.COMENTARIO_FACT] = comentario[fields.COMENTARIO_FACT]
            tempFeat[fields.ATRIBUTOS_SEC] = json.dumps({"material": material.MADERA})
            expression1 = QgsExpression('uuid(\'Id128\')')
            context = QgsExpressionContext()
            tempFeat[fields.UUID]=expression1.evaluate(context)
            comentario[fields.ASSIGNED_INFRA] = expression1.evaluate(context)
            if comentario['foto1Fact'] != NULL:
                tempFeat["foto1"] = f'https://ufinet-postes.cf.mt-gis.com/quilmes/{comentario["foto1Fact"].split("/")[-1]}'
                tempFeat["foto1Fact"] = f'https://ufinet-postes.cf.mt-gis.com/quilmes/{comentario["foto1Fact"].split("/")[-1]}'
            if comentario['foto2Fact'] != NULL:
                tempFeat["foto2Fact"] = f'https://ufinet-postes.cf.mt-gis.com/quilmes/{comentario["foto2Fact"].split("/")[-1]}'
                tempFeat["foto2"] = f'https://ufinet-postes.cf.mt-gis.com/quilmes/{comentario["foto2Fact"].split("/")[-1]}'
            if comentario['foto3Fact'] != NULL:           
                tempFeat["foto3"] = f'https://ufinet-postes.cf.mt-gis.com/quilmes/{comentario["foto3Fact"].split("/")[-1]}'
                tempFeat["foto3Fact"] = f'https://ufinet-postes.cf.mt-gis.com/quilmes/{comentario["foto3Fact"].split("/")[-1]}'
            
            veredasIntersect = layerInfra.getIntersectingFeatures(layerIDs.Veredas,tempFeat)
            tempFeat[fields.VEREDA_FK]=veredasIntersect[0][fields.UUID] if len(veredasIntersect)==1 else None
            if tempFeat[fields.VEREDA_FK]==None:
                print(f'El comentario {comentario[fields.FID]} no se pudo asignar a una vereda')
            else:
                tempFeat[fields.ASSIGNED_EJE]=layerVeredas.getFeaturesBy(fields.UUID,tempFeat[fields.VEREDA_FK])[0][fields.ASSIGNED_EJE]
                tempFeat[fields.DIRECCION]=layerEjes.getFeaturesBy(fields.UUID,tempFeat[fields.ASSIGNED_EJE])[0][fields.DIRECCION]             
                nearestUF = layerInfra.getNearestFeatures(layerIDs.Vivienda,tempFeat,limit=30)

                for uf in nearestUF:
                     
                    if uf[fields.NUMERACION] != NULL and (uf[fields.ASSIGNED_EJE] == tempFeat[fields.ASSIGNED_EJE]):
                        tempFeat[fields.NUMERACION] = uf[fields.NUMERACION]
                        break
                if tempFeat[fields.NUMERACION] == NULL:
                    print(f'Poste sin numeracion asignada, {tempFeat[fields.UUID]}')
            
            
            layerInfra.addFeature(tempFeat)
            layerComentarios.updateFeature(comentario)
 
        else:
            """(comentNumber == COMENTARIO_FACT.CAMBIO or comentNumber == COMENTARIO_FACT.APLOMAR
            or comentNumber == COMENTARIO_FACT.ELUDIR or comentNumber == COMENTARIO_FACT.NO_USAR or
            comentNumber == COMENTARIO_FACT.OTRO):"""
    
            context = QgsExpressionContext()
            context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layerComentarios))
            context.setFeature(comentario)
            expression = QgsExpression(f'overlay_nearest(\'{layerIDs.InfraNode}\', "UUID", filter:= map_get(from_json(atributosSecundarios),\'material\') IN {postesCambio}, max_distance:= {postesMaxDist})')
            result = expression.evaluate(context)
            

            if result != None:
                foundNearestFid = result
                
                if(len(foundNearestFid) == 1):
                    px = foundNearestFid[0]
                    pxFeature = layerInfra.getFeaturesBy(fields.UUID,px)[0]            

                    if comentario['foto1Fact'] != NULL:                        
                            pxFeature["foto1Fact"] = f'https://ufinet-postes.cf.mt-gis.com/quilmes/{comentario["foto1Fact"].split("/")[-1]}'
                    if comentario['foto2Fact'] != NULL:
                            pxFeature["foto2Fact"] = f'https://ufinet-postes.cf.mt-gis.com/quilmes/{comentario["foto2Fact"].split("/")[-1]}'
                    if comentario['foto3Fact'] != NULL:
                            pxFeature["foto3Fact"] = f'https://ufinet-postes.cf.mt-gis.com/quilmes/{comentario["foto3Fact"].split("/")[-1]}'
                    comentario[fields.ASSIGNED_INFRA] = pxFeature[fields.UUID]        
                
                    pxFeature[fields.COMENTARIO_FACT] = comentario[fields.COMENTARIO_FACT]
                    
                    layerInfra.updateFeature(pxFeature)
                    layerComentarios.updateFeature(comentario)
                    result =[]
                else:
                    print(f'El comentario {comentario[fields.FID]} NO se pudo asociar')
            
            if pxFeature[fields.NUMERACION] == NULL:
                nearestUF = layerInfra.getNearestFeatures(layerIDs.Vivienda,pxFeature,limit=30)

                for uf in nearestUF:
                   
                    if uf[fields.NUMERACION] != NULL and (uf[fields.ASSIGNED_EJE] == pxFeature[fields.ASSIGNED_EJE]):
                        pxFeature[fields.NUMERACION] = uf[fields.NUMERACION]
                        break
                if pxFeature[fields.NUMERACION] == NULL:
                    print(f'Poste sin numeracion asignada, {pxFeature[fields.UUID]}')
            layerInfra.updateFeature(pxFeature)

   
    layerInfra.commitChanges()
    layerComentarios.commitChanges()
    numberNewPx()
    print('Listo el pollo')