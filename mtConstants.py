from enum import Enum, IntEnum,IntFlag,auto

from qgis.core import (

    QgsProject,
    QgsFeatureRequest,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeatureIterator,
    QgsFeature,
    QgsGeometry,
    NULL

)
from typing import Optional

############# Constantes del diseño ###############

EFECTO_FLECHA = 0.01
GANANCIA_EN_ELEMENTO = 12.5
GANANCIA_JUMPER = 5
RESERVA_FIBRAS = 0.2
GANANCIA_TECNICA = 50
JUMPER_EXCEDIDO = 999
DISTANCELVL = 10
MAX_BUFFERS = 48
MAX_CD = 60
DIST_ENTRE_GANANCIAS = 400 * 1.10 # 10% de margen 
SPLITTERS_HUB =2 

HWPASO_MAX_CONTIGUOUS=6 # Maximum number of contiguous mounting HW of type PASO in a cable befor DUPLO is used
HWPASO_MIN_ANGLE=160 #minium internal angle betwee traces  to allow the use of PASO HW (180 is straigh ahead)
MAX_ATENUACION_UPSTREAM=32.4   #Atenuacion max upstream 
MAX_ATENUACION_DOWNSTREAM=30.9 #Atenuacion max downstream 

DIST_ENTRE_CE_CONTINUIDAD = 2000
MARGEN_CE_CONTINUIDAD = 300 # Addiional distance allowed 

DIST_MAX_INTRAPOSTE=2.5
MAX_CTOHUB_IN_AREA_CP = 20
MAX_CTOHUB_POR_CP = 8

OFFSET_CARRIL_JUMPER = 3
OVERLAP_ABSOLUTE_TOLERANCE = 6.5
OVERLAP_RELATIVE_TOLERANCE = 0.25


############## Models para diseño ################

OFFSET_CABLE_MODEL = 'project:offsetCables_v10'
ORDEN_CTO_MANZANA = 'project:ordenCTOenManzana'
CHIRALITY = 'project:chirality'
CREAR_COTAS = 'project:createCotas'
JUMPER_TABLE = 'project:groupJumpers'
ORIENT_CTO = 'project:orientCTOs'
#####################Constantes para Offset #############################tra

CHIRALITY_THRESHOLD=30
SEPARACION_JUMPERS= 0.5
OFFSET_EVITAR_COLISIONES = 0.25 #Esto es para evitar que se solapen los cables que van y vuelven
CARRIL_JUMPERS = 3 #NO PUEDE ESTAR EN LOS POSIBLES OFFSET DE CABLES MULTIFIBRA



class layerIDs(Enum):

    Nodo = 'nodo_b976684d_bf6f_4ab4_93bc_f532f0f8b6a8'
    eje = 'eje_1ab8ee99_7e67_4654_8679_a1544a1a088f' #en el unificado el id es: eje_ad682659_fc63_4c3e_a802_922a470aa710
    Cable = 'cable_d026d414_2ae2_4724_a4bb_bfc8ef2dfdbc'
    Area = 'area_743f2669_6a0f_42f2_89e2_c8c86342b15a'
    Infra = 'nodoInfraestructura_7e006e3f_2c08_4494_9a3c_59f477903b84'
    Vivienda = 'unidadFuncional_2b8da094_154c_4d07_b21e_b16978f227e0'
    QAQC = 'QAQC_6a21b55a_1518_4410_9f4b_78972be55f26'
    Comentario = 'comentario_a9beeb3a_6089_470c_a9f8_67e4cfb4f7c7'
    ASY_assembly = 'ASY_assembly_18bba9d1_5e82_4fcd_8524_dca624459c0e'
    ASY_condiciones = 'ASY_condiciones_c0cb8b5b_8a46_4d28_9045_eba125cbba0d'
    ASY_inUse = 'ASY_assemblies_in_use_d0b9371b_ea10_4bbb_bff3_af0865aee6f7'
    Segmento = 'segmento_2aa86a29_21b1_4500_9895_cb92add6ecc6'
    Herraje = 'herrajeria_c03b1a1e_5964_4b8a_b593_3d07089eb533'
    Splices = 'Splices_6df8d65a_43fe_4e8f_bdd1_4d645520fb27'
    Segmento_OFF = 'segmento_OFF_9982e166_12ed_4c1e_bf4f_38369b73fc83'
    Suspensor = 'suspensor_5de4d5c0_4219_4035_98f8_25bd84a1c01c'
    cableTraces = 'cable_trace_e9807667_6be5_4cbc_8c35_1acf321e0b05'
    AreaNode = 'Area_node_3d54921a_4a0c_407d_917b_65e95bfefaa6'
    CableNode = 'Node_Cable_471d0b7c_1760_4589_8475_96dd177b00d6'
    InfraNode = 'nodoInfraestructura_7e006e3f_2c08_4494_9a3c_59f477903b84'
    ValueMapTable = 'valueMaps_c1cda780_f9ae_426b_b3fa_76a0ee980f0e'
    Veredas = 'vereda_a8862de6_bcf2_4f3b_81f3_b273aaba5615'
    Anotacion_cable = 'Anotacion_Cable_69328627_ff31_4389_8974_cb74f5b75444'
    Anotacion_ER = 'Anotacion_Elemento_Red_48365b72_303a_4542_a4e8_1b303b2aec94'
    Anotacion_poste = 'Anotacion_Poste_12851a6b_d8b3_428f_83ae_a83c5a655192'
    Anotacion_DesplazarER = 'Anotacion_Desplazar_Elemento_Red_914f1f1a_d954_4257_9684_27e693a3bc75'
    Anotacion_DesplazarPX = 'Anotacion_Desplazar_Poste_ecdc1838_45c5_457f_993a_e29c2b099415'
    Anotacion_Poligono = 'Anotacion_Poligono_8471f760_722d_44ac_bc6e_f8869d50d192'
    atributosGenerlaes = 'atributosGenerales_3bfd6c03_99f8_4dc8_8feb_f09270bcd3d0'
    trazaInfra = 'trazaInfra_33cea03a_9902_4d38_a72e_ea692efe7e73'
    Manzana = 'manzana_4121630d_4ca6_484e_94d9_7f5560285d0c'
    AreaProyectoTasa = 'AreasProyectoTASA_9d46a61e_caa4_4b01_8ac6_33da2bf31dc1'
    
    
    def __get__(self,instance,owner):
        return self.value
    
    @classmethod
    def getName(cls, thisValue: str) -> str:
        return cls._value2member_map_[thisValue].name

class hardcodes(Enum):

    NO_PARENT = 'NO_PARENT'
    ROOT_NODE = 'ROOT_NODE'

    def __get__(self,instance,owner):
        return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name
    
class HWFields(Enum):
    
    LONG_CABLE = 'longitudCable'
    
    def __get__(self,instance,owner) -> str:
        return self.value

class mountingHwType(IntEnum):

    OFFSET_HERRAJES_TRONCAL=0
    TERMINAL=30
    PASO=10
    DUPLO=20
    GANANCIA_T = 40
    OFFSET_HERRAJES_JUMPER=1
    CRUCE=50
    CADENA_JUMPER=60
    DROP_TERMNAL=TERMINAL+OFFSET_HERRAJES_JUMPER
    DROP_PASO=PASO+OFFSET_HERRAJES_JUMPER
    DROP_DUPLO=DUPLO+OFFSET_HERRAJES_JUMPER
    SUSPENSOR = 70
    SUSPENSOR_PUNTO_MEDIO= 71
    RIENDA = 80
    TOMA_TIERRA=90
    CRUCE_VANO_ELECTRICO = 100

    def __get__(self,instance,owner) -> int:
        return self.value

    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name



class suspensionWireCategory(IntEnum):

    CRUCE_MEDIO=10
    CRUCE_COMPLETO=20
 

    def __get__(self,instance,owner) -> int:
        return self.value

    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name
    
class trazaInfraType(IntEnum):

    TRAZA_ELECTRICA=10
    DUCTOS=20
 

    def __get__(self,instance,owner) -> int:
        return self.value

    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name
    


class infraNodeType(IntEnum):

    POSTE=10
    CAMARA=20
    SUSPENSOR=30
    VERTICE_DUCTO=40
 

    def __get__(self,instance,owner) -> int:
        return self.value

    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name
    
class cableTraceType(Enum):

    AEREO = 10
    CAMARA = 20
    TRANSICION = 30
    
    def __get__(self,instance,owner) -> int:
        return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name
        
    
class feasibilityComment(IntFlag):

    CAMBIO = 1
    SOLICITAR_INST = 2
    NO_RELEVADO = 3
    NO_RELEVADO_CAMBIO = 4
    APLOMAR = 5
    ELUDIR = 6
    NO_USAR = 7
    OTRO = 8


    # def __get__(self,instance,owner):
    #     return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name

    def getStatus(self):
        statusList = [statusType.getName(x) for x in list(self)]
        statusText = ' | '.join(statusList)
        return statusText
    

class material(IntFlag):

    MADERA = 10
    METALICO = 20   


    # def __get__(self,instance,owner):
    #     return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name

    def getStatus(self):
        statusList = [statusType.getName(x) for x in list(self)]
        statusText = ' | '.join(statusList)

class statusType(IntFlag):

    OK = auto()
    NO_COINCIDE_PADRE = auto()
    SELECCION_MANUAL_PADRE = auto()
    SIN_AREA_DE_MISMO_NIVEL = auto()
    ERROR_MULTIPLES_AREAS = auto()
    SIN_INFRAESTRUCTURA = auto()
    ERROR_MULTIPLE_INFRA = auto()
    ASOCIADO_ABUELO = auto()
    SIN_VEREDA = auto()
    ERROR_MULTIPLE_VEREDAS = auto()
    FIBRAS_EXCEDIDAS = auto()
    FIBRAS_SOBREDIMENSIONADAS = auto()
    SIN_MANZANA = auto()


    # def __get__(self,instance,owner):
    #     return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name

    def getStatus(self):
        statusList = [statusType.getName(x) for x in list(self)]
        statusText = ' | '.join(statusList)
        return statusText

class numHarcodes(Enum):
    #NO_ORDER = 999.999.999.999.999.999
    NO_ORDER = 999999999999999999

    def __get__(self,instance,owner):
        return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name
    def getStatus(self):
        return [numHarcodes.getName(x) for x in list(self)]

class elementType(Enum):
    POP = 10 
    CE_ACCESO = 20 
    CE_ALIMENTACION = 21 
    PC = 30 
    HUB = 40 
    CTO = 50 
    GANANCIA_TECNICA_ACCESO = 60
    GANANCIA_TECNICA_ALIMENTACION = 61
    CE_EXT = 70
    
    
    def __get__(self,instance,owner) -> int:
        return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name
    
class teleco(Enum):
    TASA = 10
    
    
    def __get__(self,instance,owner) -> int:
        return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name

class networkLevel(Enum):

    CENTRAL=10
    RED_ACCESO=20 #128/256FO->CE
    RED_ALIMENTACION=30 #32FO->HUB
    RED_DISTRIBUCION=40 #JUMPER->CTO

    
    def __get__(self,instance,owner) -> int:
        return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name
    
class colocacion(Enum):

    POSTE = 10
    LIBRE = 999
    CAMARA = 20
    
    def __get__(self,instance,owner) -> int:
        return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name

class geomType(Enum):

    NODE = 1
    LINE = 2
    AREA = 3
    TABLE = 99

    def __get__(self,instance,owner) -> int:
        return self.value

    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name

class spliceReportType(IntEnum):

    BY_ELEMENT=1
    BY_CIRCUIT=2
    BY_CIRCUIT_V2=3
        
    def __get__(self,instance,owner) -> int:
        return self.value

    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name

class cableType(Enum):

    JUMPER = 1
    MULTIFIBRE= 2
    
    def __get__(self,instance,owner) -> int:
        return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name
    

class areaType(Enum):
    CP  = 20
    HUB = 30
    SDU = 40
    MDU = 50
    
    def __get__(self,instance,owner) -> int:
        return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name
    
    
class faseConstruccion(Enum):

    FASE_1 = 10
    FASE_2 = 20
    FASE_MDU = 30
    DESPLEGADO = 40
    NO_DESPLEGADO = 50
    
    def __get__(self,instance,owner) -> int:
        return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name
        
    
class clasificacionUF(Enum):

    SDU = 10
    MDU = 20
    
    def __get__(self,instance,owner) -> int:
        return self.value
    
    @classmethod
    def getName(cls, thisValue: int) -> str:
        return cls._value2member_map_[thisValue].name


    



class fields(Enum):
    
    LEVEL = 'nivel'
    FID = 'fid'
    UUID = 'UUID'
    PARENT_NODE = 'nodo_FK'
    PARENT_CABLE = 'cable_FK'
    ASSIGNED_AREA = 'area_FK'
    ASSIGNED_INFRA = 'infra_FK'
    ASSIGNED_EJE = 'eje_FK'
    MANZANA_FK='manzana_FK'
    NOMBRE = 'nombre'
    STATUS_VINCULO = 'statusVinculo'
    ERROR_FLAGS = 'errorFlags'
    COLOCACION = 'colocacion'
    DEMANDA = 'demandaArea'
    ES_DERIVACION = 'esDerivacion'
    CABLE_HERMANO = 'cableHermanoFK'
    AREA_PADRE= 'areaFK'
    ID_INFRA = 'idInfra'
    DIRECCION = 'nombreCalle'
    ALTURA = 'altura'
    TIPO = 'tipo'
    DISTANCE_ALONG = 'distanceAlong'
    DISTANCE_TOTAL = 'distanceAlongTotal'
    DERIV_LVL = 'derivLVL'
    ORDEN = 'orden'
    SEGMENTO = 'segmento'
    FIB_ASIG = 'fibrasAsignadas'
    FIB_RESERV = 'fibrasReserva'
    FIB_CALC = 'fibrasCalculadas'
    STATUS_CAPACIDAD = 'statusCapacidad'
    IS_MDU= 'esMDU'
    NODO_INICIO = 'nodoInicio_FK'
    NODO_FIN = 'nodoFin_FK'
    ID_POSTE = 'ID_POSTE'
    ID_HP = 'ID_HP'
    DIRECCION_RELEV = 'DIRECCION'
    ALTURA_RELEV = 'NUM_CATAST'
    CANT_FIBRAS = 'fibras'
    NOMBRE_CABLE = 'nombreCable'
    NRO_SEG = 'numeroSeg'
    LONG_TOTAL = 'longitudTotal'
    DISTANCE_INICIO = 'distanceAlongInicio'
    DISTANCE_FIN = 'distanceAlongFin'
    DESPLEGADO = 'desplegado'
    ASSEMBLY_FK = 'assembly_FK'
    ASSEMBLY = 'assembly'
    BLOCKASSEMBLY = 'blockAssembly'
    FABRICANTE = 'fabricante'
    LARGO_JUMPER = 'largoJumper'
    DESP_INICIAL = 'despliegueInicial'
    BUFFER_SIZE = 'bufferSize'
    CAPACIDAD_DERIV = 'capDeriv'
    ATENUACION_US = 'atenuacionPropiaUS'
    ATENUACION_DS = 'atenuacionPropiaDS'
    COMENTARIO_FACT = 'comFact'
    FOTO1 = 'foto1'
    NODO_UUID = 'nodo_uuid'
    CABLE_UUID = 'cable_uuid'
    NODO_NIVEL = 'nodo_nivel'
    CABLE_NIVEL = 'cable_nivel'
    START_POINT = 'start_point'
    END_POINT = 'end_point'
    AREA_UUID = 'area_uuid'
    AREA_NIVEL = 'area_nivel'
    AREA_TIPO = 'area_tipo'
    NODO_TIPO = 'nodo_tipo'
    INFRA_UUID = 'infra_uuid'
    MANZANA_UUID = 'manzana_uuid'
    VEREDA_UUID = 'vereda_uuid'
    TARGET_UUID = 'target_uuid'
    NODO_TELECO ='nodo_telco'
    CABLE_TELECO = 'cable_telco'
    NODO_COLOCACION = 'nodo_colocacion'
    INFRA_TIPO = 'tipoInfraestructura'
    OVERRIDES = 'overrideJson'
    CAPAS = 'capas'
    CAMPO = 'campo' 
    VALUE = 'value'
    HABILITADO = 'habilitado'
    ATRIBUTOS_SEC = 'atributosSecundarios'
    CLASIF_USO = 'clasificacionUso'
    VEREDA_FK = 'vereda_FK'
    FASE = 'fase'
    PUERTOS = 'puertos'
    FIBRAS_PRE_OCUPADAS = 'fibrasPreOcupadas'
    PUERTOS_PRE_OCUPADOS = 'puertosPreOcupados'
    TELECO = 'teleco'
    NETPARENT_FK ='netParentNode_FK'
    DEMANDA_SDU='demandaSDU'
    DEMANDA_MDU='demandaMDU'
    CAJAS_INICIALES = 'cajasIniciales'
    CAJAS_FUTURAS = 'cajasFuturas'
    AUTOGENERADO = 'autoGenerado'
    MATERIAL = 'material'
    RECORRIDO = 'recorrido'
    SPLICE_BUFFERS = 'spliceBuffers'
    LONG_CABLE= 'longitudCable'
    INFRA_INICIO_FK = 'infraInicio_FK'
    INFRA_FIN_FK = 'infraFin_FK'
    OFFSET = 'offset'
    CROSS_STREETS_FK = 'crossStreets_FK'
    SUSPENSOR_HERMANO = 'suspensorHermano_FK'
    CLASIFICACION_UF = 'clasificacionUF'
    DEMANDAAREA = 'demanda'
    NUMERACION = 'numeracion'
    HH_UF = 'HH'
    AREA_SERVI= 'AREA_SERVI'
    ORDEN_MANZANA='ordenEnManzana'
    ID='ID'
    FIBRAS_EN_USO = 'fibrasEnUso'
    FIBRAS_UTILIZADAS= 'fibrasUtilizadas'
    ETIQUETA_FIBRAS='etiquetaFibras'
    MT_FEATURE='_mtFeature'
    ASIGNACION='asignacion'
    POSTE_EN_USO= 'enUso'
    FUSIONES='fusiones'
    SECUNDARIO='secundario'
    IS_ENDPOINT='isEndPoint'
    ROTULADO = 'ROTULADO'
    SUSPENSOR_FK = 'suspensor_FK'
    CHIRALITY = 'chirality'
    TASA_PROJECT = 'proyectoTasa'
    TASA_PROJECT_INTERSECT = 'proyectoTasaIntersect'
    PARENT_PROJECT_FK='parentProject_FK'
    PARENT_PROJECT='parentProject'
    UNIDADES = 'unidades'
    ROTULADO_PDF = 'rotuladoPDF'
    AZI = 'azi'
    OVERRIDE_ASIGNACION = 'overrideAsignacion'
    BLOCK_CHILD_ORDEN =   'blockChildOrden'
    GROUP_SPLICES = 'groupSplices'
    NODOS_CABLETRACE = 'nodos'


    def __get__(self,instance,owner) -> str:
        return self.value
