
#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% QUERYS %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


netEndNodesQuery = """
select 
	fid as fid,
    geometry as mygeom,
    'END' as ELEMENTID,
    NULL as RANK,
    NULL as CONNSTATUS,
    NULL as CONNSUPPRT,
    NULL as SUPPORT,
    NULL as NAME,
    NULL as EXTKEY,
    NULL as INFRAID,
    NULL as ROUTINGID,
    NULL as PREMISES,
    NULL as COST,
    NULL as PRIID,
    NULL as PRIDISTm,
    NULL as SUPID,
    NULL as SUPDIST,
    NULL as LOCFC,
    NULL as PPFC,
    NULL as USEFUS,
    NULL as SPRFUS,
    NULL as LKBDGT,
    NULL as SPLTMX
    FROM "nodos"
    where nodos.tipo = 10
    
"""
netCablesQuery = """
select distinct
    IIF(cables.fibras = 1,3,2) as LEVEL, 
    fid as fid, 
    nombre as ELEMENTID, 
    geometry as geometry,
    fibras as FIBERS,
    CASE 
        WHEN cables.fibras = 96 THEN 'UF Genérico 96FO - 8T/12H'
        WHEN cables.fibras = 48 THEN 'UF Genérico 48FO - 6T/8H'
        WHEN cables.fibras = 24 THEN 'UF Genérico 24FO - 2T/12H'
        WHEN cables.fibras = 1 THEN 'UF Genérico 1FO - 1T/1H'
        WHEN cables.fibras = 12 THEN 'UF Genérico 12FO - 1T/12H'
        WHEN cables.fibras = 6 THEN 'UF-Cable 6FO 6H 1T'
        ELSE 'No_Model'
    END AS MODELNUM,
    NULL as ALLOCFIB
    FROM "cables"
    where cables.fase = 10
    
"""
    
netNodosQuery =  """
select 
    "Nodo Primario" as LEVEL, 
    fid as fid, 
    "ODF" as SUPPORT,
    nombre as ELEMENTID, 
    geometry as geometry,
    NULL as EXTKEY,
    NULL as CONNSUPPRT,
    NULL as EQUIPMENT,
    NULL as NODEFC
    FROM "nodos" 
    where nodos.tipo = 10
union 
select 
    "Nodo Primario" as LEVEL, 
    fid + 1000000 as fid, 
    "CAJA_CD" as SUPPORT, 
    nombre as ELEMENTID, 
    geometry as geometry,
    NULL as EXTKEY,
    NULL as CONNSUPPRT,
    NULL as EQUIPMENT,
    NULL as NODEFC
	FROM "nodos" 
    where nodos.tipo = 40
union 
select 
    "NAP" as LEVEL, 
    fid + 2000000 as fid, 
    "Caja_A_F" as SUPPORT, 
    nombre as ELEMENTID, 
    geometry as geometry,
    NULL as EXTKEY,
    NULL as CONNSUPPRT,
    NULL as EQUIPMENT,
    NULL as NODEFC
	FROM "nodos" 
    where nodos.tipo = 50 and nodos.fase = 10
union 
select 
    "NAP" as LEVEL, 
    fid + 3000000 as fid, 
    "Caja_B_F" as SUPPORT, 
    nombre as ELEMENTID, 
    geometry as geometry,
    NULL as EXTKEY,
    NULL as CONNSUPPRT,
    NULL as EQUIPMENT,
    NULL as NODEFC
	FROM "nodos" 
    where nodos.tipo = 60 and nodos.fase = 10
union 
select 
    "CE_T" as LEVEL, 
    fid + 4000000 as fid, 
    "CE_144_F" as SUPPORT, 
    nombre as ELEMENTID, 
    geometry as geometry,
    NULL as EXTKEY,
    NULL as CONNSUPPRT,
    NULL as EQUIPMENT,
    NULL as NODEFC
	FROM "nodos" 
    where nodos.tipo = 20 or nodos.tipo = 110
 """   

netEnclosureQuery = """SELECT 
    s.geometry as geometry,
    IIF(c.fibras = 1,s.nombre||s.segmento,s.nombre) AS SECTIONID,
    c.nombre as ELEMENTID,
    nodoInicio.nombre as ENDAID,
    nodoInicio.nombre as NODEAID,
    nodoFin.nombre as ENDBID,
    nodoFin.nombre as NODEBID,
    s.segmento as SEQNUM,
    NULL as FIBERS,
    NULL as EXTKEY,
    NULL as ALLOCFIB,
    NULL as ENDPTBID,
    NULL as CLOSUREAID,
    NULL as CLOSUREBID
FROM "Segmento_OFF" as s
join "Nodos" as nodoInicio ON nodoInicio.UUID = s.nodoInicio_FK
join "Nodos" as nodoFin ON nodoFin.UUID = s.nodoFin_FK
join "Cables" as c ON c.UUID = s.cable_FK 
where s.fase = 10 and s.ZoomLevel = 500;

 """



