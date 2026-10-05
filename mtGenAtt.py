from .mtLayer import layerGeneralAtt
from .mtConstants import fields
from enum import Enum

class mtGenAtt:
    
    class attName(Enum):
        ALIMENTADOR='Alimentador'
        POP='POP'
        CABLE_TRONCAL='CableTroncal'
        OFFSET_TRONCAL='offsetTroncal'
        ATENAUACION_BASE='atencuacionBase'
        NOMBRE_NODO='nombreNodo'
        OLT_RACK='oltRack'
        OLT_SUB_RACK='oltSubRack'
        OLT_PREFIJO='oltPrefijo'
        NUMERO_TRONCAL='numeroTroncal'
        LOCALIDAD='Localidad'
        NOMBRE_ANILLO='nombreAnillo'
        SRID='SRID'

        def __get__(self,instance,owner) -> str:
            return self.value

    def getValue(attName: 'attName'):
        return layerGeneralAtt.getFeaturesBy(fields.NOMBRE,attName)[0][fields.VALUE]