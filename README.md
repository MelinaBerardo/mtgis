# mtGis2
mtgis  para panama


para reload las librerias:

from mtGis2 import mtSplices
from mtGis2 import mtTree

from mtGis2 import mtActions

from importlib import reload
reload(sys.modules['mtGis2.mtConstants'])
reload(sys.modules['mtGis2.mtFuncs'])
reload(sys.modules['mtGis2.mtTree'])
reload(sys.modules['mtGis2.mtSplices'])
reload(sys.modules['mtGis2.mtSegments'])
reload(sys.modules['mtGis2.mtLayer'])
from mtGis2.mtConstants import mtFeature
from mtGis2.mtTree import mtTree
from mtGis2.mtSplices import generateSplices

reload(mtActions)
sys.modules.pop('mtGis2.mtLayer')
sys.modules.pop('mtGis2.mtConstants')
sys.modules.pop('mtGis2.mtFuncs')
sys.modules.pop('mtGis2.mtTree')
sys.modules.pop('mtGis2.mtSplices')
sys.modules.pop('mtGis2.mtQAQC')
sys.modules.pop('mtGis2.mtSegments')
sys.modules.pop('mtGis2.mtActions')
sys.modules.pop('mtGis2.mtOffset')
sys.modules.pop('mtGis2.mtHerrajes')
sys.modules.pop('mtGis2.mtMissingFields')
sys.modules.pop('mtGis2.missingModels')
sys.modules.pop('mtGis2.missingFields')
sys.modules.pop('mtGis2.mtAssemblies')
sys.modules.pop('mtGis2.mtCableTraces')
sys.modules.pop('mtGis2.mtAttData')
sys.modules.pop('mtGis2.mtAttenuacion')
sys.modules.pop('mtGis2.mtOrder')
sys.modules.pop('mtGis2.mtSld')

sys.modules.pop('mtGis2')
del(myTraces)
del(mySegments)
del(segmentCable)
del(myTree)
del(atenuacionAll)
del(generateSplices)

#from mtGis2 import mtActions
#mtActions.scriptsCompletos()

from mtGis2.mtConstants import *
from mtGis2.mtSegments import mtSegments, segmentCable
from mtGis2.mtTree import mtTree
from mtGis2.mtAttenuacion import atenuacionAll
myTree = mtTree()
#segmentCable(myTree,layerCable,layerSEG)
mySegments = mtSegments()
mySegments.clear()
mySegments.loadFromTable(layerSEG)
atenuacionAll(myTree, mySegments)



from mtGis2 import mtHerrajes 
from mtGis2.mtConstants import *
from mtGis2 import mtCableTraces
from importlib import reload
reload(mtCableTraces)
reload(mtHerrajes)
reload(mtTree)

myTraces=mtCableTraces.mtCableTraces()
myTraces.loadAllFromTable()
layerHerrajes.truncate()
mtHerrajes.crearHerrajes(layerCable, myTraces,False)
mtHerrajes.crearHerrajes(layerCable, myTraces,False)



import timeit
def timedRun(command):
    start=timeit.default_timer()
    exec(command)
    stop=timeit.default_timer()
    print(f"Elapsed: {stop-start}")



from mtGis2.mtMissingFields import exportProjectModels
exportProjectModels()
del exportProjectModels

from mtGis2.mtMissingFields import exportAllLayerFields
exportAllLayerFields()
del exportAllLayerFields




from mtGis2.mtTree import mtTree
from mtGis2.mtSplices import generateSplices
from mtGis2.mtSegments import segmentCable
from mtGis2.mtConstants import *
myTree = mtTree()
mySegments = mtSegments()
mySegments=segmentCable(myTree,layerCable,layerSEG,mySegments)
generateSplices(myTree, mySegments)

del myTree
del mySegments
del generateSplices




from mtGis2.mtConstants import *
from mtGis2.mtTree import mtTree
from mtGis2.mtSegments import mtSegments
from mtGis2.mtSplices import generateSplices
mySegments = mtSegments()
mySegments.loadFromTable(layerSEG)

myTree = mtTree()
mySegments.clear()

generateSplices(myTree, mySegments)


from mtGis2 import mtActions
mtActions.scriptsShort()

mtActions.scriptsNoLink()

mtActions.scriptsCompletos()

agregar en /.vscode/settings.json lo siguiente:
{
    "python.analysis.extraPaths": [
            "C:\\PROGRA~1\\QGIS32~1.10\\apps\\qgis-ltr\\python",
            "C:\\Users\\garci\\AppData\\Roaming\\Python\\Python39\\site-packages",
            "C:\\PROGRA~1\\QGIS32~1.10\\apps\\qgis-ltr\\python\\qgis",
            "C:\\PROGRA~1\\QGIS32~1.10\\apps\\Python39\\lib\\site-packages\\",
        ],
    "python.autoComplete.extraPaths":  [
            "C:\\PROGRA~1\\QGIS32~1.10\\apps\\qgis-ltr\\python",
            "C:\\Users\\garci\\AppData\\Roaming\\Python\\Python39\\site-packages",
            "C:\\PROGRA~1\\QGIS32~1.10\\apps\\qgis-ltr\\python\\qgis",
            "C:\\PROGRA~1\\QGIS32~1.10\\apps\\Python39\\lib\\site-packages\\",
        ],
}

(el directorio .vscode no se pasa al git)


SQL para agregar tabla de atributos (no geometricas)

DROP TABLE IF EXISTS "Splices";
CREATE TABLE "Splices" ( "fid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "splice_circuit" TEXT, "splice_totalDepth" MEDIUMINT, "splice_order" MEDIUMINT, "splice_isRowPOP" BOOLEAN, "splice_isRowCTOA" BOOLEAN, "POP_nodeFK" MEDIUMINT, "POP_port" MEDIUMINT, "POP_cableFiberInBuffer" MEDIUMINT, "POP_cableBufferNumber" MEDIUMINT, "POP_cableSequencial" MEDIUMINT, "CEcore_cableFK" MEDIUMINT, "CEcore_cableName" TEXT, "CEcore_cableType" TEXT, "CEcore_cableSegmentFK" MEDIUMINT, "CEcore_cableSegmentName" TEXT, "CEcore_cableSegmentLength" REAL, "CEcore_cableSequencial" MEDIUMINT, "CEcore_cableBufferNumber" MEDIUMINT, "CEcore_cableFiberInBuffer" MEDIUMINT, "CEsplice_nodeFK" MEDIUMINT, "CEsplice_nodeName" TEXT, "CEsplice_type" TEXT, "CEsplice_port" MEDIUMINT, "CEedge_cableFiberInBuffer" MEDIUMINT, "CEedge_cableBufferNumber" MEDIUMINT, "CEedge_cableSequencial" MEDIUMINT, "CEedge_cableFK" MEDIUMINT, "CEedge_cableName" TEXT, "CEedge_cableType" TEXT, "CEedge_cableSegmentFK" MEDIUMINT, "CEedge_cableSegmentName" TEXT, "CEedge_cableSegmentLength" REAL, "CTOA_cableSequencial" MEDIUMINT, "CTOA_cableBufferNumber" MEDIUMINT, "CTOA_cableFiberInBuffer" MEDIUMINT, "CTOA_nodeFK" MEDIUMINT, "CTOA_nodeName" TEXT, "CTOA_nodeType" TEXT, "CTOA_port" MEDIUMINT);

DELETE FROM "main"."gpkg_contents" where table_name='Splices';
INSERT INTO "main"."gpkg_contents" ("table_name", "data_type", "identifier", "description", "last_change", "min_x", "min_y", "max_x", "max_y", "srs_id") VALUES ('Splices', 'attributes', 'Splices', '', '2023-11-27T20:03:43.665Z', '', '', '', '', '0');

DELETE FROM "main"."gpkg_ogr_contents" where table_name='Splices';
INSERT INTO "main"."gpkg_ogr_contents" ("table_name") VALUES ('Splices');




SQL Para poder usar las funcionces del spatialite:

SELECT autogpkgstart();
select InitSpatialMetadata();


    explode lines

    field calculator

  array_foreach( overlay_intersects( 'Postes_1147b04a_fd9d_46f9_a784_08b2fe43c7f5',$currentfeature), with_variable( 'thisFeat',@element,attribute(@thisFeat,'ID_POSTE')))


  array_foreach( overlay_intersects( 'Postes_1147b04a_fd9d_46f9_a784_08b2fe43c7f5',$currentfeature), with_variable( 'thisFeat',@element,if(intersects(geometry(@thisFeat),start_point($geometry)),map('start',attribute(@thisFeat,'fid')),NULL)))




---- update virtual layer All_cables to:
    select geometry,fid, concat("CableT-",fid) as orig_fid,nombre from 'CBL_T_SEG_OFF_918a8792_1193_4ef1_a816_9ff68a90cb4d' union
    select geometry,fid+ 1000000 as fid, concat("CableA-",fid) as orig_fid,nombre from 'CBL_A_SEG_OFF__de5ed579_000f_41d9_8fe6_789587dc70ad'



select geometry,fid, concat("CableT-",fid) as orig_fid,nombre from 'CBL_T_985dc20a_3f29_4cc4_9482_d5b0de5f954e' union
select geometry,fid+ 1000000 as fid, concat("CableA-",fid) as orig_fid,nombre from 'CBL_A_966a4e0b_6026_4103_bf72_edb20f5e1af6'


    explode lines

    field calculator

array_to_string(
  array_foreach(
    overlay_intersects(
      'Postes_1147b04a_fd9d_46f9_a784_08b2fe43c7f5',
      $currentfeature),
    with_variable(
      'thisFeat',
      @element,
      map_to_hstore(
        if(
          intersects(
            geometry(@thisFeat),
            start_point($geometry)
          ),
          map('startPfid',attribute(@thisFeat,'fid')),
          if(
            intersects(
              geometry(@thisFeat),
              end_point($geometry)
            ),
            map('endPfid',attribute(@thisFeat,'fid')),
            map()
          )
        )
      )
    )
  )
)



replace(
	to_json(
		with_variable('myRowId',"fid",
			array_foreach(
				overlay_intersects(
					'Ganancias_eff116be_6842_408e_9d75_41defdd5082f',
					$currentfeature
				),
				with_variable(
					'thisFeat',
					@element,
					if(
						intersects(
							geometry(@thisFeat),
							start_point($geometry)
						) AND (attribute(@thisFeat,'cablePadreFK')=@myRowId),
						map('startGanFid',attribute(@thisFeat,'fid')),
						if(
						intersects(
							geometry(@thisFeat),
							end_point($geometry)
						)AND (attribute(@thisFeat,'cablePadreFK')=@myRowId),
						map('endGanFid',attribute(@thisFeat,'fid')),
						NULL
						)
					)
				)
			)
		)
	),
	'null',
	''
)

explode hstore field

field calculator:

array_length( overlay_crosses( 'SegmentosCalle_0b099ec0_3a85_4027_94e1_176adee1f010',fid))


Herrajes:

- si angulo entre 160-180 - paso
- si es menor a 160 duplo

si hay elemento de red, va duplo (incluye ganancias)
si es inicio o fin va terminal
si hay 6 paso seguidos, ahi va duplo



map_get(
  overlay_intersects(
    'Modified_geometry_cdd74492_4d15_425b_9b51_4571c4944c0e', 
    "fid",
    nodo_fk=attribute(@feature,'nodo_FK'),
    limit:=1,
    return_details:=true,
    sort_by_intersection_size:=des
  )[0],
'overlap')




to_json(
	array_filter(
		with_variable('myRowId',"fid",
			array_foreach(
				overlay_intersects(
					'N_P_12935426_fc59_4843_9e47_ae40fb96379a',
					$currentfeature
				),
				with_variable(
					'thisFeat',
					@element,
					if(
						intersects(
							geometry(@thisFeat),
							start_point($geometry)
						) AND (attribute(@thisFeat,'cablePadreFK')=@myRowId),
						map('startCajFk',attribute(@thisFeat,'fid')),
						if(
						intersects(
							geometry(@thisFeat),
							end_point($geometry)
						)AND (attribute(@thisFeat,'cablePadreFK')=@myRowId),
						map('endCajFk',attribute(@thisFeat,'fid')),
						NULL
						)
					)
				)
			)
		)
	,
	@element IS NOT NULL)
)




del defineAssembly
sys.modules.pop('mtGis2.mtAssemblies')
from mtGis2.mtAssemblies import defineAssembly
defineAssembly(layerNode)




[
    {
        "id": 373,
        "_class": "formtemplate",
        "header": "",
        "display": "PAN - Certificacion CTO_V1"
    },
    {
        "id": 366,
        "_class": "formtemplate",
        "header": "",
        "display": "PAN - Despliegue Cable completo_V1"
    },
    {
        "id": 374,
        "_class": "formtemplate",
        "header": "",
        "display": "PAN - Despliegue CE_V1"
    },
    {
        "id": 273,
        "_class": "formtemplate",
        "header": "",
        "display": "PAN - Despliegue CTO"
    },
    {
        "id": 365,
        "_class": "formtemplate",
        "header": "",
        "display": "PAN - Despliegue CTO_V1"
    }
]


para el tema de chiralidad de jumpers y cables en general
    
@qgsfunction(group='Mediatel', usesgeometry=False)
def chirality(azimuths):
    """
    returns the twistiness / chirality
    """

    if len(azimuths) < 2:
        return 0.0
        
    total_twist = 0.0
    for i in range(len(azimuths) - 1):
        # Calculate the raw difference
        diff = azimuths[i+1] - azimuths[i]
        
        # Adjust for the 360-degree boundary wrap-around
        shortest_diff = (diff + 180) % 360 - 180
        
        # Accumulate the absolute turning angle
        total_twist += shortest_diff
        
    return total_twist


{
  "AGGREGATES": [
    {
      "aggregate": "array_agg",
      "delimiter": ",",
      "input": "\"azi\"",
      "length": 0,
      "name": "azi",
      "precision": 0,
      "sub_type": 6,
      "type": 9,
      "type_name": "doublelist"
    },
    {
      "aggregate": "first_value",
      "delimiter": ",",
      "input": "\"cable_FK\"",
      "length": 0,
      "name": "cable_FK",
      "precision": 0,
      "sub_type": 0,
      "type": 10,
      "type_name": "text"
    },
    {
      "aggregate": "sum",
      "delimiter": ",",
      "input": "\"longitud\"",
      "length": 0,
      "name": "longitud",
      "precision": 0,
      "sub_type": 0,
      "type": 6,
      "type_name": "double precision"
    }
  ],
  "GROUP_BY": "\"cable_FK\"",
  "INPUT": "C:/Users/garci/Desktop/prueba splices tasa/db-3.gpkg|layername=cable_trace",
  "OUTPUT": "TEMPORARY_OUTPUT"
}




layer NodoInfraestructura
    extract by expression
        ComFact=2
    out
        postesInstalar

layer vereda
    geom by expression
        type line
        boundary( buffer(@geometry,0.1))
    out
        veredaBoerder

layer veredaBoerder 
    clip 
        clip layer:
            manzana
    out 
        veredaBorderClip

layer veredaBorderClip
    multilinejoiner
    out 
        veredaBorderClipFix

layer veredaBorderClipFix
    geom by expression
        type line
        extend(line_substring($geometry, 3, length($geometry) - 3),3,3)
    out
        lineaPostes

layer lineaPostes
    offsetLines
        5 metros (no se porque pero todas quedan adentro de la manzana que es lo que queremos!)
    out
        lineaPostesOffset

layer postesInstalar
    geometryByExpression
        with_variable('linegeo', 
            geometry(get_feature('lineaPostesOffset','UUID', "vereda_FK")), 
            extend(shortest_line(@geometry,@linegeo),0,0.1))
    out
        cortepostes

layer lineaPostesOffset
    clip 
        clip layer
            manzana
    out
        lineaPostesOffetCut

layer lineaPostesOffetCut
    extract by expression
        aggregate( 'cortepostes','count',"UUID",filter:="vereda_FK" = attribute(@parent,'UUID'))>0
    out
        lineaPostesOffsetCutInUse

layer lineaPostesOffsetCutInUse
    split with lines
        split layer
            cortepostes
    out
        cotaspostes








with_variable('mzngeo', 
	buffer(
		geometry(get_feature('Manzana','UUID', "manzana_FK")),
		-0.2
	),
	 intersection(buffer(@geometry,0.1),@mzngeo))




    
@qgsfunction(group='Mediatel', usesgeometry=False)
def chirality(azimuths):
    """
    returns the twistiness / chirality
    """

    if len(azimuths) < 2:
        return 0.0
        
    total_twist = 0.0
    for i in range(len(azimuths) - 1):
        # Calculate the raw difference
        diff = azimuths[i+1] - azimuths[i]
        
        # Adjust for the 360-degree boundary wrap-around
        shortest_diff = (diff + 180) % 360 - 180
        
        # Accumulate the absolute turning angle
        total_twist += shortest_diff
        
    return total_twist


{
  "AGGREGATES": [
    {
      "aggregate": "array_agg",
      "delimiter": ",",
      "input": "\"azi\"",
      "length": 0,
      "name": "azi",
      "precision": 0,
      "sub_type": 6,
      "type": 9,
      "type_name": "doublelist"
    },
    {
      "aggregate": "first_value",
      "delimiter": ",",
      "input": "\"cable_FK\"",
      "length": 0,
      "name": "cable_FK",
      "precision": 0,
      "sub_type": 0,
      "type": 10,
      "type_name": "text"
    },
    {
      "aggregate": "sum",
      "delimiter": ",",
      "input": "\"longitud\"",
      "length": 0,
      "name": "longitud",
      "precision": 0,
      "sub_type": 0,
      "type": 6,
      "type_name": "double precision"
    }
  ],
  "GROUP_BY": "\"cable_FK\"",
  "INPUT": "C:/Users/garci/Desktop/prueba splices tasa/db-3.gpkg|layername=cable_trace",
  "OUTPUT": "TEMPORARY_OUTPUT"
}