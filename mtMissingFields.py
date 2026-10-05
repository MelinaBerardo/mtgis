from qgis.core import (

    QgsProject,
    QgsField, # Lo importe para poder agregar campos JMY
    QgsApplication,
    QgsProcessingModelAlgorithm,
    QgsXmlUtils,
)

from PyQt5.QtCore import (
    QVariant, # Lo importe para poder agregar campos JMY
)
from PyQt5.QtXml import(
    QDomDocument,
)
import os
from importlib import reload
from .mtConstants import *

from . import missingModels
from . import missingFields

import json
import sqlite3


PROVIDER_PROJECT='project'
CURRPATH=os.path.dirname(os.path.abspath(__file__))
MISSINGMODELS_FILENAME='missingModels.py'
MISSINGFIELDS_FILENAME='missingFields.py'

# =============================================================================================
# ----------------------------- PROJECT TABLES ------------------------------------------------
# =============================================================================================

TABLES_DIRNAME = 'tablas'

PROJECT_TABLES = [
    'ASY_condiciones',
    'valueMaps',
    'ASY_assembly',
]


def getProjectDatabasePath():
    """
    Busca entre las capas cargadas en QGIS una DB que contenga
    todas las tablas definidas en PROJECT_TABLES.
    """

    possibleDatabases = set()

    # *Buscar archivos de base de datos usados por las capas cargadas*
    for layer in QgsProject.instance().mapLayers().values():

        source = layer.source()

        # *En un GeoPackage normalmente el source es:*
        # C:/ruta/db.gpkg|layername=NombreTabla

        dbPath = source.split('|')[0]

        if os.path.isfile(dbPath):

            extension = os.path.splitext(dbPath)[1].lower()

            if extension in ['.gpkg', '.sqlite', '.db']:
                possibleDatabases.add(dbPath)

    databasesWithTables = []

    # *Buscar cuál contiene las tres tablas*
    for dbPath in possibleDatabases:

        connection = sqlite3.connect(dbPath)

        try:

            cursor = connection.cursor()

            cursor.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
            """)

            existingTables = {
                row[0]
                for row in cursor.fetchall()
            }

            if all(
                tableName in existingTables
                for tableName in PROJECT_TABLES
            ):
                databasesWithTables.append(dbPath)

        finally:

            connection.close()

    # -------------------------------------------------------------------------
    # RESULTADO
    # -------------------------------------------------------------------------

    if len(databasesWithTables) == 0:

        raise Exception(
            "No se encontró ninguna DB cargada en QGIS "
            "que contenga las tablas: "
            + ", ".join(PROJECT_TABLES)
        )

    if len(databasesWithTables) > 1:

        raise Exception(
            "Se encontró más de una DB con las tablas necesarias:\n"
            + "\n".join(databasesWithTables)
        )

    return databasesWithTables[0]


def getTableColumns(cursor, tableName):
    """
    Devuelve las columnas de una tabla.
    """

    cursor.execute(
        f'PRAGMA table_info("{tableName}")'
    )

    return [
        row[1]
        for row in cursor.fetchall()
    ]


def getTablePrimaryKeys(cursor, tableName):
    """
    Devuelve las columnas que forman la Primary Key.
    Se usa para mantener un orden estable en los JSON.
    """

    cursor.execute(
        f'PRAGMA table_info("{tableName}")'
    )

    tableInfo = cursor.fetchall()

    primaryKeys = [
        (row[5], row[1])
        for row in tableInfo
        if row[5] > 0
    ]

    primaryKeys.sort()

    return [
        fieldName
        for order, fieldName in primaryKeys
    ]


def encodeJsonValue(value):
    """
    Convierte valores SQLite a valores compatibles con JSON.

    Normalmente SQLite devuelve:
        None
        int
        float
        str

    También soportamos BLOB por seguridad.
    """

    if isinstance(value, bytes):

        return {
            "__type__": "bytes",
            "hex": value.hex()
        }

    return value


def decodeJsonValue(value):
    """
    Proceso inverso a encodeJsonValue().
    """

    if (
        isinstance(value, dict)
        and value.get("__type__") == "bytes"
    ):

        return bytes.fromhex(
            value["hex"]
        )

    return value


# =============================================================================================
# EXPORT TABLES
# =============================================================================================

def exportProjectTables():
    """
    Exporta las tablas indicadas en PROJECT_TABLES
    a archivos JSON dentro de la carpeta /tablas.
    """

    dbPath = getProjectDatabasePath()

    outputDir = os.path.join(
        CURRPATH,
        TABLES_DIRNAME
    )

    # *Crear la carpeta tablas si todavía no existe*
    os.makedirs(
        outputDir,
        exist_ok=True
    )

    connection = sqlite3.connect(dbPath)

    try:

        cursor = connection.cursor()

        print("")
        print("------------------------------------------------------")
        print("EXPORTING PROJECT TABLES")
        print("------------------------------------------------------")
        print(f"Database: {dbPath}")
        print("")

        for tableName in PROJECT_TABLES:

            columns = getTableColumns(
                cursor,
                tableName
            )

            if len(columns) == 0:

                raise Exception(
                    f'Table "{tableName}" does not exist.'
                )

            # -----------------------------------------------------------------
            # ORDEN
            # -----------------------------------------------------------------
            # *Es importante mantener siempre el mismo orden para que Git*
            # *solamente muestre los registros que realmente cambiaron.*

            primaryKeys = getTablePrimaryKeys(
                cursor,
                tableName
            )

            if len(primaryKeys) > 0:

                orderColumns = primaryKeys

            else:

                # *Si no hay PK ordenamos por todas las columnas*
                orderColumns = columns

            orderBy = ", ".join(
                f'"{column}"'
                for column in orderColumns
            )

            cursor.execute(
                f'''
                SELECT *
                FROM "{tableName}"
                ORDER BY {orderBy}
                '''
            )

            rows = cursor.fetchall()

            jsonRows = []

            for row in rows:

                jsonRow = {}

                for column, value in zip(
                    columns,
                    row
                ):

                    jsonRow[column] = encodeJsonValue(
                        value
                    )

                jsonRows.append(
                    jsonRow
                )

            # -----------------------------------------------------------------
            # JSON
            # -----------------------------------------------------------------

            data = {
                "table": tableName,
                "columns": columns,
                "rows": jsonRows
            }

            outputFile = os.path.join(
                outputDir,
                f"{tableName}.json"
            )

            with open(
                outputFile,
                'w',
                encoding='utf-8'
            ) as fs:

                json.dump(
                    data,
                    fs,
                    ensure_ascii=False,
                    indent=4
                )

            print(
                f"Exported: {tableName} "
                f"({len(rows)} rows)"
            )

        print("")
        print("Project tables exported successfully.")
        print("------------------------------------------------------")

    finally:

        connection.close()


# =============================================================================================
# UPDATE TABLES
# =============================================================================================

def updateProjectTables():
    """
    Reemplaza completamente el contenido de PROJECT_TABLES
    usando los JSON guardados dentro de /tablas.

    NO modifica la estructura de las tablas.
    Solamente elimina e inserta registros.
    """

    dbPath = getProjectDatabasePath()

    tablesDir = os.path.join(
        CURRPATH,
        TABLES_DIRNAME
    )

    # =========================================================================
    # PRIMERO LEER Y VALIDAR TODOS LOS JSON
    # =========================================================================
    # *Esto se hace antes de tocar la DB.*
    # *Si falta un JSON o tiene algún problema, no modificamos nada.*

    tablesData = {}

    for tableName in PROJECT_TABLES:

        jsonFile = os.path.join(
            tablesDir,
            f"{tableName}.json"
        )

        if not os.path.isfile(jsonFile):

            raise Exception(
                f'JSON file not found: "{jsonFile}"'
            )

        with open(
            jsonFile,
            'r',
            encoding='utf-8'
        ) as fs:

            data = json.load(fs)

        # *Verificar que el JSON corresponda a la tabla*
        if data.get("table") != tableName:

            raise Exception(
                f'JSON "{jsonFile}" belongs to table '
                f'"{data.get("table")}" instead of "{tableName}".'
            )

        if "columns" not in data:

            raise Exception(
                f'JSON "{jsonFile}" does not contain "columns".'
            )

        if "rows" not in data:

            raise Exception(
                f'JSON "{jsonFile}" does not contain "rows".'
            )

        tablesData[tableName] = data

    # =========================================================================
    # ABRIR DB
    # =========================================================================

    connection = sqlite3.connect(dbPath)

    try:

        cursor = connection.cursor()

        # =====================================================================
        # VALIDAR COLUMNAS
        # =====================================================================

        for tableName in PROJECT_TABLES:

            dbColumns = getTableColumns(
                cursor,
                tableName
            )

            if len(dbColumns) == 0:

                raise Exception(
                    f'Table "{tableName}" does not exist.'
                )

            jsonColumns = tablesData[
                tableName
            ]["columns"]

            missingInDatabase = [
                column
                for column in jsonColumns
                if column not in dbColumns
            ]

            missingInJson = [
                column
                for column in dbColumns
                if column not in jsonColumns
            ]

            if len(missingInDatabase) > 0:

                raise Exception(
                    f'Table "{tableName}" is missing columns '
                    f'present in JSON: {missingInDatabase}'
                )

            if len(missingInJson) > 0:

                raise Exception(
                    f'JSON for "{tableName}" is missing '
                    f'database columns: {missingInJson}'
                )

        print("")
        print("------------------------------------------------------")
        print("UPDATING PROJECT TABLES")
        print("------------------------------------------------------")
        print(f"Database: {dbPath}")
        print("")

        # =====================================================================
        # TRANSACCIÓN
        # =====================================================================
        # *Todo se actualiza junto.*
        #
        # *Si falla una de las tres tablas hacemos rollback.*
        # *De esta forma nunca queda una DB actualizada a medias.*

        cursor.execute("BEGIN")

        try:

            # -----------------------------------------------------------------
            # BORRAR CONTENIDO ACTUAL
            # -----------------------------------------------------------------

            for tableName in PROJECT_TABLES:

                cursor.execute(
                    f'DELETE FROM "{tableName}"'
                )

            # -----------------------------------------------------------------
            # CARGAR JSON
            # -----------------------------------------------------------------

            for tableName in PROJECT_TABLES:

                data = tablesData[
                    tableName
                ]

                columns = data["columns"]
                rows = data["rows"]

                if len(rows) == 0:

                    print(
                        f"Updated: {tableName} "
                        f"(0 rows)"
                    )

                    continue

                columnsSql = ", ".join(
                    f'"{column}"'
                    for column in columns
                )

                placeholders = ", ".join(
                    "?"
                    for column in columns
                )

                sql = f'''
                    INSERT INTO "{tableName}"
                    ({columnsSql})
                    VALUES ({placeholders})
                '''

                values = []

                for row in rows:

                    rowValues = []

                    for column in columns:

                        value = row.get(
                            column
                        )

                        value = decodeJsonValue(
                            value
                        )

                        rowValues.append(
                            value
                        )

                    values.append(
                        rowValues
                    )

                cursor.executemany(
                    sql,
                    values
                )

                print(
                    f"Updated: {tableName} "
                    f"({len(rows)} rows)"
                )

            # -----------------------------------------------------------------
            # TODO OK
            # -----------------------------------------------------------------

            connection.commit()

        except Exception:

            # *Si ocurre cualquier error restauramos todo*
            connection.rollback()

            raise

        print("")
        print("Project tables updated successfully.")
        print("------------------------------------------------------")

    finally:

        connection.close()

    # =========================================================================
    # RECARGAR TABLAS EN QGIS
    # =========================================================================

    reloadProjectTables()


def reloadProjectTables():
    """
    Si alguna de las tablas está cargada actualmente en QGIS,
    fuerza su recarga después de actualizar la DB.
    """

    for layer in QgsProject.instance().mapLayers().values():

        source = layer.source()

        for tableName in PROJECT_TABLES:

            if (
                f'layername={tableName}' in source
                or layer.name() == tableName
            ):

                layer.reload()

                layer.triggerRepaint()
def exportProjectModels():
    outFileName=os.path.join(CURRPATH,MISSINGMODELS_FILENAME)
    fs=open(outFileName,'w')
    fs.truncate()
    fs.write("# ----------------------------- MODELS --------------------------\n")
    fs.write("# This file is autogenerated and will be overwritten by the exportProjectModels() function\n")
    fs.write("# ---------------------------------------------------------------\n")
    fs.write("MISSINGMODELS=[\n")
    allModels=QgsApplication.processingRegistry().providerById(PROVIDER_PROJECT).algorithms()
    thisModel: QgsProcessingModelAlgorithm
    for thisModel in allModels:
        thisDoc=QDomDocument('model')   #esto es hardcoded, sacado de https://github.com/qgis/QGIS/blob/0b4e023b566cacbb6048a750a31df465a4a92820/src/core/processing/models/qgsprocessingmodelalgorithm.cpp#L1765
        thisElem=QgsXmlUtils.writeVariant(thisModel.toVariant(),thisDoc)
        thisDoc.appendChild(thisElem)
        fs.write("#####################################################\n")
        fs.write(f"# Model: ID:\'{thisModel.id()}\' Name:\'{thisModel.name()}\'\n")
        fs.write("#####################################################\n")
        fs.write(f'[\'{thisModel.id()}\', """\n{thisDoc.toString()}"""],')
        fs.write("\n\n\n")
    fs.write("]\n\n# -------------------------- END OF MISSINGMODELS ------------")
    fs.close()


def updateProjectModels():
    reload(missingModels)
    allModels=QgsApplication.processingRegistry().providerById(PROVIDER_PROJECT).algorithms()
    for thisModel in missingModels.MISSINGMODELS:
        name=thisModel[0]
        modelAlg=QgsApplication.processingRegistry().providerById(PROVIDER_PROJECT).algorithm(name)
        if modelAlg is not None:
            # we already have a model with the same name. Delete and we'll load it again
            QgsApplication.processingRegistry().providerById(PROVIDER_PROJECT).remove_model(modelAlg.id())
        modelXml=thisModel[1]
        # copied from here: https://github.com/qgis/QGIS/blob/0b4e023b566cacbb6048a750a31df465a4a92820/src/core/processing/models/qgsprocessingmodelalgorithm.cpp#L1799
        thisDoc=QDomDocument()
        thisDoc.setContent(modelXml)
        thisAlg=QgsProcessingModelAlgorithm()
        thisAlg.loadVariant(QgsXmlUtils.readVariant(thisDoc.firstChildElement()))
        # add_model is not documented!!! https://github.com/qgis/QGIS/blob/3c62cff490e619f066cc87e4fc756f7dd1e22e00/python/plugins/processing/modeler/ModelerDialog.py#L164C4-L164C4
        QgsApplication.processingRegistry().providerById(PROVIDER_PROJECT).add_model(thisAlg)
        QgsProject.instance().setDirty(True)



def CommitLayers():
    for layer in layerIDs:
        thisLayer = QgsProject().instance().mapLayer(layer.value)
        modificada = thisLayer.isModified()
        if modificada == True:  #Verifica si hubo cambios en la capa
            thisLayer.commitChanges()

def createMissingFields():
    reload(missingFields)
    prevLayerId=None
    layerFields: 'list[str]'=[]
    thisLayer=None
    
    for thisField in missingFields.MISSINGFIELDS:
        thisLayerId=thisField[0]
        fieldName=thisField[1]
        fieldType=thisField[2]

        if thisLayerId != prevLayerId:
            thisLayer = QgsProject().instance().mapLayer(thisLayerId)
            if thisLayer is not None: # Tiene que existir la capa
                thisLayer.startEditing()
                layerFields = thisLayer.dataProvider().fields().names()

       #verifico si los campos existen, sino los creo
       
        if thisLayer is not None: # Tiene que existir la capa

            if fieldName not in layerFields:
                thisLayer.dataProvider().addAttributes([QgsField(fieldName, QVariant.nameToType(fieldType))])
                thisLayer.updateFields()
                print(f"Adding Missing Field: {fieldName} in table: {thisLayerId}")

            else:
                fieldIndex=thisLayer.dataProvider().fields().indexOf(fieldName)
                layerField=thisLayer.dataProvider().fields().field(fieldIndex)
                if layerField.type()!=QVariant.nameToType(fieldType):
                    print(f"Changing Field type: {fieldName} in table: {thisLayerId} from \'{QVariant.typeToName(layerField.type())}\' to \'{fieldType}\'")
                    thisLayer.dataProvider().deleteAttributes([fieldIndex])
                    thisLayer.dataProvider().addAttributes([QgsField(fieldName, QVariant.nameToType(fieldType))])
                    thisLayer.updateFields()

                     
    #CommitLayers()

MISSINGFIELDS_HEADER="""
# ----------------------------- FIELDS -------------------------------------------------------
# This file is autogenerated and will be overwritten by the printAllLayerFields() function
# --------------------------------------------------------------------------------------------

from .mtConstants import layerIDs
from PyQt5.QtCore import (
    QVariant, # Lo importe para poder agregar campos JMY
)
################### TIPOS DE DATOS ###########################################################
 # https://het.as.utexas.edu/HET/Software/html/qvariant.html

STRING = QVariant.typeToName(QVariant.String) # 10
DOUBLE = QVariant.typeToName(QVariant.Double) # 6
LONG = QVariant.typeToName(QVariant.LongLong) # 4
BOOL = QVariant.typeToName(QVariant.Bool) # 1
INT = QVariant.typeToName(QVariant.Int) # 2
###############################################################################################
\n\n
MISSINGFIELDS=[
"""
def dumpLayerFields(layerName:str)-> str:
    retStr=""
    thisLayer=QgsProject().instance().mapLayer(layerIDs[layerName].value)
    if thisLayer is None:
        retStr+="##############################################################\n"
        retStr+=f"########----- missing layer in project: \'{layerName}\' with ID:\'{layerIDs[layerName].value}\'\n"
        retStr+="##############################################################\n"
    else:
        for thisField in thisLayer.dataProvider().fields():
            retStr+=f"    [layerIDs.{layerName},\'{thisField.name()}\', \'{QVariant.typeToName(thisField.type())}\'],\n"
    return retStr
            
def exportAllLayerFields():
    outFileName=os.path.join(CURRPATH,MISSINGFIELDS_FILENAME)
    fs=open(outFileName,'w')
    fs.truncate()
    fs.write(MISSINGFIELDS_HEADER)
    for thisLayer in layerIDs:
        fs.write("\n")
        fs.write(dumpLayerFields(thisLayer.name))
        fs.write("\n")
    fs.write("]\n\n# -------------------------- END OF MISSINGFIELDS ------------")
    fs.close()
