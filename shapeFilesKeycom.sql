-- Net_Nodes----------------------------------------------------------------------------------------

select 
    "Nodo Primario" as LEVEL, 
    fid as fid, 
    Assembly as SUPPORT,
    nombre as ELEMENTID, 
    geometry as mygeom,
    NULL as EXTKEY,
    NULL as CONNSUPPRT,
    NULL as EQUIPMENT,
    NULL as NODEFC
    from "Nodo Primario" 
	where despliegueInicial is true
union 
select 
    "NAP" as LEVEL, 
    fid + 1000000 as fid, 
    "Caja_B_F" as SUPPORT, 
    nombre as ELEMENTID, 
    geometry as mygeom,
    NULL as EXTKEY,
    NULL as CONNSUPPRT,
    NULL as EQUIPMENT,
    NULL as NODEFC
	from "Caja B"
	where despliegueInicial is true

-- Net_Cables---------------------------------------------------------------------------------------

select distinct
    2 as LEVEL, 
    fid as fid, 
    nombre as ELEMENTID, 
    geometry as mygeom,
    cantFibras as FIBERS,
    IIF(cantFibras = 12,"UF Genérico 12FO - 6T/2H",IIF(cantFibras = 24,"UF Genérico 24FO - 4T/6H",IIF(cantFibras = 72,"UF Genérico 72FO - 6T/12H",IIF(cantFibras = 144,"UF Genérico 144FO - 12T/12H","No_Model")))) as MODELNUM,
    NULL as ALLOCFIB
    from "Cable Troncal"
	where despliegueInicial is true
    GROUP BY nombre
union 
select distinct
    3 as LEVEL, 
    fid + 1000000 as fid, 
    nombre as ELEMENTID, 
    geometry as mygeom,
    1 as FIBERS,
    "UF Genérico 1FO - 1T/1H" as MODELNUM,
    1 as ALLOCFIB
    from "Cables de Acceso"
	where despliegueInicial is true
    GROUP BY nombre

-- Net_Cables_ClosureSections-----------------------------------------------------------------------


with mysegmentunion as (
    select 
        "Troncal" as capaorigen, 
        fid as fid, 
        nombre as nombrelocal, 
        iif (NumPoints(geometry)=1,MakeLine(PointN(geometry,1),PointN(geometry,1)), geometry ) as mygeom,
        "Nodo Primario" as tipo_inicio,
        nodoInicioFK,
        "Nodo Primario" as tipo_fin,
        nodoFinFK,
        substring(nombre, instr(nombre,'SEG'),length(nombre)) as localseqnum,
        cantFibras as localcantpelos
        from CBL_T_SEG_OFF
        where despliegueInicial is true
    union 
    select 
        "Acceso" as capaorigen, 
        fid + 1000000 as fid, 
        nombre as nombrelocal, 
        iif (NumPoints(geometry)=1,MakeLine(PointN(geometry,1),PointN(geometry,1)), geometry ) as mygeom,
        "Nodo Primario" as tipo_inicio,
        nodoPadreFK as nodoInicioFK,
        "NAP" as tipo_fin,
        nodoFinFK,
        1 as localseqnum,
        cantFibras as localcantpelos
        from "CBL_A_SEG_OFF "
        where despliegueInicial is true

), mynodeunion as (
    select 
        "Nodo Primario" as tiponodo,
        fid,
        fid as localfk,
        nombre
        from "Nodo Primario" 
    union
    select 
        "NAP" as tiponodo,
        fid + 10000,
        fid as localfk,
        nombre
        from "Caja B"
    )

select mysegmentunion.mygeom as
    geom /*:LineString:32617*/,
    mysegmentunion.nombrelocal as SECTIONID,
    IIF( instr(mysegmentunion.nombrelocal,'SEG')>0, substring(mysegmentunion.nombrelocal,1, instr(mysegmentunion.nombrelocal,'SEG')-1), mysegmentunion.nombrelocal) as ELEMENTID,
    mysegmentunion.fid,
    n1.nombre as ENDAID,
    n1.nombre as NODEAID,
    n2.nombre as ENDBID,
    n2.nombre as NODEBID,
    mysegmentunion.localseqnum as SEQNUM,
    localcantpelos as FIBERS,
    NULL as EXTKEY,
    NULL as ALLOCFIB,
    NULL as ENDPTBID,
    NULL as CLOSUREAID,
    NULL as CLOSUREBID
from mysegmentunion
join mynodeunion n1 on (mysegmentunion.tipo_inicio=n1.tiponodo AND mysegmentunion.nodoInicioFK=n1.localfk)
join mynodeunion n2 on  (mysegmentunion.tipo_fin=n2.tiponodo AND mysegmentunion.nodoFinFK=n2.localfk)