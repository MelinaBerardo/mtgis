# This file is Copyright (C) 2021 Mediatel S.A., all rights reserved.
# Este archivo y su contenido son Copyright (C) 2021 Mediatel S.A. Todos los derechos reservados

from math import inf
from qgis.core import (
    QgsFeatureRequest,
    QgsProject,
    QgsFeature,
    NULL,
    QgsMessageLog,
    Qgis,
)
import json
from .mtConstants import *   #Importamos todas las constantes de mtConstants
from enum import Enum
from fnmatch import fnmatch
from .mtLayer import *
from .mtGenAtt import mtGenAtt

DEBUG=True

PARENT_PREFIX='#PARENT#'
PROJECT_PREFIX='#PROJECT#'
ORDEN_PREFIX='#ORDEN#'
class fieldsAsy(Enum):

    CAMPO_OBJ = 'campoObjetivo'
    VALOR_CAMPO = 'valorCampo'
    FASE = 'fase'
    LAYER = 'layer'
    FEATURE_FK = 'feature_FK'
    CAMPO_MULT = 'campoMultiplo'
    MULT = 'multiplier'
    PRIORIDAD = 'prioridad'
    ASSEMBLY = 'assembly'
    FABRICANTE = 'fabricante'
    ASSEMBLY_FK = 'assembly_FK'
    ASY_GENERICO = 'assemblyGenerico'
    UNIT = 'unitarioContador'
    OVERRIDES = 'overrideJson'
    OPERADOR  = 'operador'

    def __get__(self,instance,owner):
        return self.value

# see https://stackoverflow.com/a/40486992
# this class allows us to put functions as callable objects inside the enum
class FunctionProxy:
    """Allow to mask a function as an Object."""
    def __init__(self, function):
        self.function = function

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)

class argType(IntEnum):
    NUMERIC=2
    TEXT=1
    BOTH=TEXT+NUMERIC

    def __get__(self,instance,owner):
        return self.value

class asyOperators(Enum):
    EQ = '=', FunctionProxy(lambda a,b: a==b),argType.BOTH
    NEQ = '<>', FunctionProxy(lambda a,b: a!=b),argType.BOTH
    LT = '<', FunctionProxy(lambda a,b: a<b),argType.NUMERIC
    LEQ = '<=', FunctionProxy(lambda a,b: a<=b),argType.NUMERIC
    GT = '>', FunctionProxy(lambda a,b: a>b),argType.NUMERIC
    GEQ = '>=', FunctionProxy(lambda a,b: a>=b),argType.NUMERIC
    IS = 'IS', FunctionProxy(lambda a,b: a is b),argType.BOTH
    ISNOT = 'IS NOT', FunctionProxy(lambda a,b: a is not b),argType.BOTH
    ILIKE = 'ILIKE', FunctionProxy(lambda a,b: myLike(a,b)),argType.BOTH
    BETWEEN = 'BETWEEN', FunctionProxy(lambda a,b,c: b<=a<=c),argType.BOTH
   
    def __get__(self,instance,owner):
        return self.value

def myLike(haystack:str, needle:str)-> bool:
    # we use fnmatch that does shell/dos-like wildcards for SQL LIKE searches. We need to replace % for * and _ for ?
    replNeedle=str(needle).replace('%','*').replace('_','?')
    replNeedle=replNeedle.upper()
    strHaystack=str(haystack).upper()
    return fnmatch(strHaystack,replNeedle)

class mtFilter():
    field:str
    operator:'Optional[str]'
    value:str
    def __init__(self,field,value,operator) -> None:
        self.field=field
        self.value=value
        self.operator=operator
    def __str__(self):
        return f"MTFILTER-> field:{self.field} || operator:{self.operator} || value:{self.value} ||"

def checkFilterOnFeature(feature: mtFeature, filterArray:'list[mtFilter]'):
    retval=False
    #print("filter array",filterArray)
    for thisFilter in filterArray:
        retval=checkSingleFilter(operator=thisFilter.operator, value=feature[thisFilter.field], match=thisFilter.value )
        if retval==False:
            break
    #print("retval",retval)
    return retval

def checkSingleFilter(operator:str, value, match):
        operTuple=getFullOperator(operator)
        #print("check filter")
        #print(operTuple, thisFilter.__dict__, thisFilter.field, value, match)
        if is_number(value) and is_number(match):
            if operTuple[2]==argType.TEXT:
                # requested operator is for strings and operands are numbers
                retval=False
            else:
                # we invoke the requested function (tuple 1) on the fields
                retval=operTuple[1](float(value),float(match))
        else:
            if operTuple[2]==argType.NUMERIC:
                # requested operator is for numbers and operands are strings
                retval=False
            else:
                retval=operTuple[1](str(value),str(match))
        return retval

def is_number(s):
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False

def defineAssembly(layerObj : mtLayer): #Funcion que si le pasas un layer le define los assembly a todos los objetos de ese layer

    expression1 = QgsExpression('uuid(\'Id128\')')
    context = QgsExpressionContext()

    clearAssembly(layerObj)
    clearAssemblyInUse(layerObj.LID)

    layerObj.startEditing()
    layerAssemblyInUse.startEditing()

    # Populamos todos los assemblys_in_use para assemblies bloqueados (porque los borramos antes)
    deleteFeatures = layerObj.getFeaturesByFilter(f'\"{fields.ASSEMBLY_FK}\" IS NOT NULL AND \"{fields.BLOCKASSEMBLY}\"')

    for feature in deleteFeatures:
        nuevoAssembly = layerAssemblyInUse.newFeature()
        assembly = layerAssembly.getFeature([fields.ASSEMBLY_FK])
        nuevoAssembly[fieldsAsy.LAYER] = layerObj.LID
        nuevoAssembly[fieldsAsy.FEATURE_FK] = feature[fields.UUID]
        nuevoAssembly[fieldsAsy.ASSEMBLY_FK] = feature[fields.ASSEMBLY_FK]
        if assembly[fieldsAsy.CAMPO_MULT]:
            nuevoAssembly[fieldsAsy.MULT] = assembly[fieldsAsy.CAMPO_MULT]
        layerAssemblyInUse.addFeature(nuevoAssembly)
        
    # ahora si iteramos por todos los assemblies aplicables a este layer
    assert layerObj.friendlyName is not None

    secundarios:'set'
    secundarios=layerAssembly.uniqueValues(fields.SECUNDARIO)
    #si hay NULL lo quito porque uso el 0, que siempre agrego. Como es un SET no hay items repetidos
    secundarios.discard(NULL)
    secundarios.add(0)

    for thisSecundario in sorted(secundarios):
        assemblies = getLayerAssemblies(layerObj.friendlyName, thisSecundario) #Obtengo una lista de assemblies para el layer que estoy procesando, ordenados por prioridad
        # hago una lista de FIDs a quien ya le asigne Assmblies - porque la busquedad anda mal
        # solo importa en secundario=0
        assignedAssemblies=[]
        # Inicializo el cache de parent Features
        parentFeatures={}
        
        for assembly in assemblies:
            Filtro,ParentFiltro, genAttBool = getConditions(assembly[fieldsAsy.ASY_GENERICO])     
            if genAttBool: 
                assignedAssemblyFilter= f'\"{fields.ASSEMBLY_FK}\" IS NULL AND \"{fields.BLOCKASSEMBLY}\" IS NOT True' if thisSecundario==0 else ""
                Filtro = Filtro + (" and " if len(Filtro)>0 and len(assignedAssemblyFilter)>0 else " ") + f'{assignedAssemblyFilter}'               
                features = layerObj.getFeaturesByFilter(Filtro)
                for feature in features:                    
                    feature = mtFeature(feature)
                    if feature[fields.UUID] in assignedAssemblies:
                        # ya lo asigne.. no lo vuelvo a recorrer (la busqueda parece no actualizar el cache)
                        continue
                    if len(ParentFiltro)>0:    
                        # Hacemos un cache de parentFeatures para agilizar la busqueda
                        featId=feature[fields.UUID]
                        parentFeature=parentFeatures.get(featId)
                        if parentFeature is None:                        
                            parentFeature=layerObj.getParentFeature(feature)
                            parentFeatures[featId]=parentFeature
                        if not parentFeature.isValid():
                            continue
                        parentCheck=checkFilterOnFeature(parentFeature,ParentFiltro)
                        if not parentCheck:
                            continue
                    assignedAssemblies.append(feature[fields.UUID])    
                    if thisSecundario==0:
                        # Solo aplica para el assemly principal        
                        feature[fields.ASSEMBLY_FK] = assembly[fields.UUID]
                        feature[fields.ASSEMBLY] = assembly[fields.ASSEMBLY]
                        # We override any fields in the target feature with the override JSON coming from the assembly
                        overrideString=mtFeature().nullToNone(assembly[fieldsAsy.OVERRIDES])
                        if overrideString is not None:
                            try:
                                overrideDict=json.loads(overrideString)
                                if type(overrideDict) is dict:
                                    for k,v in overrideDict.items():
                                        if layerObj.isValidFieldName(k) and v is not None:
                                            if isinstance(v, dict | list):
                                                feature[k]=json.dumps(v)  #Save value as json as its a list or dict
                                            else:
                                                feature[k]=v
                                else:
                                    QgsMessageLog.logMessage( f"!!!!!! Assembly {assembly.id()} con override no DICT!!!", 'Assembly.py', level=Qgis.Warning)
                            except json.JSONDecodeError as msg:
                                QgsMessageLog.logMessage( f"!!!!!! Assembly {assembly.id()} con error when decoding DICT!!! {msg}", 'Assembly.py', level=Qgis.Critical)

                    layerObj.updateFeature(feature)

                    fase = feature[fields.FASE] if layerObj.isValidFieldName(fields.FASE) else faseConstruccion.FASE_1
                
                    nuevoAssembly = layerAssemblyInUse.newFeature()
                    context.setFeature(nuevoAssembly)
                    nuevoAssembly[fields.UUID]=expression1.evaluate(context)
                    nuevoAssembly[fieldsAsy.LAYER]=layerObj.LID
                    nuevoAssembly[fieldsAsy.FEATURE_FK]=feature[fields.UUID]
                    nuevoAssembly[fieldsAsy.ASSEMBLY_FK]=assembly[fields.UUID]
                    nuevoAssembly[fieldsAsy.ASSEMBLY]=assembly[fieldsAsy.ASSEMBLY]
                    nuevoAssembly[fields.TASA_PROJECT] = feature[fields.TASA_PROJECT]
                    nuevoAssembly[fields.SECUNDARIO]=thisSecundario
                    nuevoAssembly[fields.FASE] = fase
                    nuevoAssembly[fields.ROTULADO_PDF] = assembly[fields.ROTULADO_PDF]
                    nuevoAssembly[fields.UNIDADES] = assembly[fields.UNIDADES]

                    if assembly[fieldsAsy.CAMPO_MULT]:
                        nuevoAssembly[fieldsAsy.MULT]=feature[assembly[fieldsAsy.CAMPO_MULT]]
                    
                    nuevoAssembly[fieldsAsy.UNIT]=1
                        
                    layerAssemblyInUse.addFeature(nuevoAssembly)

    layerObj.commitChanges()
    layerAssemblyInUse.commitChanges()


def clearAssembly(layerObj : mtLayer):
    layerObj.startEditing()
    for feature in layerObj.getFeatures(QgsFeatureRequest()
                                        .setFilterExpression(f'\"{fields.BLOCKASSEMBLY}\" IS NOT True')):
        
        feature[fields.ASSEMBLY_FK] = NULL
        feature[fields.ASSEMBLY] = NULL
        layerObj.updateFeature(feature)
    layerObj.commitChanges()

def clearAssemblyInUse(LayerID : str):
    layerAssemblyInUse.startEditing()
    
    featsToDelete=layerAssemblyInUse.getFeaturesByFilter( f'\"{fieldsAsy.LAYER}\" = \'{LayerID}\'')
    
    layerAssemblyInUse.deleteFeatures([feat.id() for feat in featsToDelete])
    layerAssemblyInUse.commitChanges()

def getLayerAssemblies(friendlyName : str, secundario):
    clause1 = QgsFeatureRequest.OrderByClause(fieldsAsy.PRIORIDAD, ascending=True)
    orderby1 = QgsFeatureRequest.OrderBy([clause1])

    if secundario==0:
        filterSec=f'(\"{fields.SECUNDARIO}\" = 0 OR \"{fields.SECUNDARIO}\" IS NULL )'
    else:
         filterSec=f'\"{fields.SECUNDARIO}\" = {secundario}'
    assemblys = layerAssembly.getFeatures(QgsFeatureRequest()
        .setOrderBy(orderby1)
        .setFilterExpression( f'\"{fieldsAsy.LAYER}\" = \'{friendlyName}\' AND {filterSec}'))
    return list(assemblys)
    
def getConditions(assemblyName):
    expresionFiltro = []
    expresionParentFiltro=[]
    genAttConditions=True

    allCondiciones=list(layerAssemblyCondiciones.getFeaturesBy(fieldsAsy.ASY_GENERICO, assemblyName))

    for condiciones in allCondiciones:
        condiciones=mtFeature(condiciones)
        campoObjetivo:str=condiciones.get(fieldsAsy.CAMPO_OBJ)
        valorCampo=condiciones.get(fieldsAsy.VALOR_CAMPO)
        operador=condiciones.getNN(fieldsAsy.OPERADOR)        

        assert campoObjetivo is not None
        if campoObjetivo.startswith(PROJECT_PREFIX):
            campoGenAtt=campoObjetivo.removeprefix(PROJECT_PREFIX)
            valorGenAtt=mtGenAtt.getValue(campoGenAtt)
            # comparo el valor del campo de atributos generales contra la condicion y valor del assembly. Todos tienen que ser true 
            # para que sigua siendo True
            genAttConditions = genAttConditions and checkSingleFilter(operator=operador, value=valorGenAtt, match=valorCampo)
        elif campoObjetivo.startswith(PARENT_PREFIX):
            campoParent=campoObjetivo.removeprefix(PARENT_PREFIX)
            expresionParentFiltro.append(mtFilter(field=campoParent, value=valorCampo, operator=operador))
        else:
            # si el valor es numerico, se evalua sin comillas en la condicion
            if is_number(condiciones[fieldsAsy.VALOR_CAMPO]) or getOperator(operador) == 'BETWEEN':
                expresionFiltro.append( f"\"{campoObjetivo}\" {getOperator(operador)} {valorCampo}")
            else:
                expresionFiltro.append( f"\"{campoObjetivo}\" {getOperator(operador)} \'{valorCampo}\'")
            

    retFilter="" + " and ".join(expresionFiltro)

    return retFilter, expresionParentFiltro, genAttConditions

def getFullOperator(operator: 'Optional[str]')->'tuple[str,FunctionProxy,int]':
    if operator is None or operator is NULL:
        retVal=asyOperators.EQ
    else:
        operator=operator.upper().strip()
        if operator not in asyOperators.__members__:
            retVal=asyOperators.EQ
        else:
            retVal=asyOperators[operator].value
    return retVal
    
def getOperator(operator:'Optional[str]')->str:
    return getFullOperator(operator)[0]

def getOperatorFunction(operator:'Optional[str]')->'FunctionProxy':
    return getFullOperator(operator)[1]