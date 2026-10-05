
--NODOS
UPDATE nodo
SET "ROTULADO" =
CASE
    WHEN tipo = 50 THEN
        asignacion || ',1-8' ||
        char(10) ||
        CASE substr(CAST(orden AS TEXT),3,1)
            WHEN '1' THEN 'SS'
            WHEN '2' THEN 'ST'
            WHEN '3' THEN 'SC'
            WHEN '4' THEN 'SQ'
            ELSE ''
        END ||
        substr(asignacion,instr(asignacion, ',') + 1) || ' 1:8 ' ||
        'e:' || substr(asignacion, 1, length(asignacion) - 1)

    WHEN tipo = 40 THEN
        'CTO_HUB' || nombre ||
        char(10) ||
        'SP' ||
        substr(
            asignacion,
            instr(asignacion, ':') + 1,
            instr(asignacion, ';') - instr(asignacion, ':') - 1
        ) || ' 1:2' ||
        char(10) ||
        'SP' ||
        CASE
            WHEN instr(substr(asignacion, instr(asignacion, ';') + 1), ';') > 0 THEN
                substr(
                    substr(asignacion, instr(asignacion, ';') + 1),
                    instr(substr(asignacion, instr(asignacion, ';') + 1), ':') + 1,
                    instr(substr(asignacion, instr(asignacion, ';') + 1), ';')
                    - instr(substr(asignacion, instr(asignacion, ';') + 1), ':') - 1
                )
            ELSE
                substr(
                    substr(asignacion, instr(asignacion, ';') + 1),
                    instr(substr(asignacion, instr(asignacion, ';') + 1), ':') + 1
                )
        END || ' 1:2' ||
        char(10) ||
        'V:25'

    ELSE nombre
END;

update nodo set "nombreCalle" =  coalesce( (select eje.nombreCalle from eje where eje.uuid = eje_FK), "nombreCalle");
update nodo set "numeracion" = coalesce((SELECT nodoInfraestructura.numeracion from nodoInfraestructura where nodoInfraestructura.uuid=infra_FK), "numeracion");

WITH fusionesCable AS (
    SELECT
        s.CEedge_cableFK AS cable_FK,
        COUNT(*) AS fusiones
    FROM Splices s
    WHERE s.splice_report_type = 3
      AND s.CEedge_cableSegmentName = 'SEG01'
    GROUP BY s.CEedge_cableFK
)
UPDATE cable
SET fusiones = (
    SELECT f.fusiones
    FROM fusionesCable f
    WHERE f.cable_FK = cable.uuid
);

--Segmentos
update segmento_OFF set "nodoInicio" = (SELECT nodo.nombre from nodo where nodo.uuid=nodoInicio_FK);

--SINPLEX
update Suspensor set "DIAMETRO" = ('4.8mm'); --

UPDATE segmento_OFF SET "CATEGORIA" = (1);
update segmento_OFF set "NUMERO_TUBOS" = CEIL("fibras" / 8);--
update segmento_OFF set "SITUACION" = 
    CASE    WHEN "fibras" = 256 THEN  ('Canalizacion')
            WHEN "fibras" = 128 THEN ('Canalizacion') 
            ELSE ('Poste/aereo') 
    END;
update segmento_OFF set "NOMBRE_NODO_PADRE" = (SELECT nodo.nombre from nodo where nodo.uuid=nodoInicio_FK);

update nodo set "TIPO_SIMPLEX" = 
    CASE    WHEN "tipo" = 10 THEN 10 
            WHEN "tipo" = 40 THEN 40 
            WHEN "tipo" = 60 THEN 30 
            ELSE 20 
    END;--
update nodo set "NOMBRE_SIMPLEX" = 
    CASE    WHEN "tipo" = 40 THEN "CTO_HUB" || "nombre" 
            WHEN "tipo" = 10 THEN 'ROM' 
            WHEN "tipo" = 60 THEN 'V' || "nombre" 
            WHEN "tipo"=20 and "colocacion"=10 THEN 'EP'||"nombre"
            WHEN "tipo"=30 and "colocacion"=10 THEN 'EP'||"nombre"
            ELSE 'E'||"nombre" 
    END;
update nodo set "CAPACIDAD" = (SELECT cable.fibras from cable where cable.UUID=cable_FK);
update nodo set "NOMBRE_CABLE_PADRE_SIMPLEX" = (SELECT cable.nombre from cable where cable.UUID=cable_FK);
update nodo set "NOMBRESP1" = "SP" || substr(asignacion,instr(asignacion, ':') + 1,instr(asignacion, ';') - instr(asignacion, ':') - 1) ; 
update nodo set "NOMBRESP2" =  "SP" || substr(asignacion,instr(substr(asignacion, instr(asignacion, ';') + 1), ':')+ instr(asignacion, ';') + 1);
update nodo set "FACTOR_DIVISION_SIMPLEX" = ('2');--
update nodo set "NUMERO_DE_FIBRAS" = (SELECT cable.fibras from cable where cable.UUID=cable_FK);




UPDATE segmento
SET longitudTotal = (
    SELECT cable.longitudTotal
    FROM cable
    WHERE cable.uuid = segmento.cable_FK
);

UPDATE segmento_OFF
SET longitudTotal = (
    SELECT cable.longitudTotal
    FROM cable
    WHERE cable.uuid = segmento_OFF.cable_FK
);

UPDATE segmento 
SET "ROTULADO" =

    (SELECT atributosGenerales.value
     FROM atributosGenerales
     WHERE atributosGenerales.nombre = 'nombreCentral')

    || '-' ||
    fibras || 'F.O.-' ||
    CAST(longitudTotal AS INTEGER) || 'M'
    || '&' ||

    CASE
        WHEN instr(etiquetaFibras, char(9)) > 0
            THEN substr(etiquetaFibras, 1, instr(etiquetaFibras, char(9)) - 1)

        ELSE etiquetaFibras
    END;
 
UPDATE segmento_OFF
SET "ROTULADO" =

    (SELECT atributosGenerales.value
     FROM atributosGenerales
     WHERE atributosGenerales.nombre = 'nombreCentral')

    || '-' ||
    fibras || 'F.O.-' ||
    CAST(longitudTotal AS INTEGER) || 'M'
    || '&' ||

    CASE
        WHEN instr(etiquetaFibras, char(9)) > 0
            THEN substr(etiquetaFibras, 1, instr(etiquetaFibras, char(9)) - 1)

        ELSE etiquetaFibras
    END;

UPDATE unidadFuncional SET Area_FK = ( CASE WHEN clasificacionUF = 10 THEN ( SELECT area_FK FROM eje WHERE eje.UUID = unidadFuncional.eje_FK )
                                            WHEN clasificacionUF = 20 THEN Area_FK
                                            ELSE '' END );


update unidadFuncional set "manzana_FK" = coalesce((select parcela.manzana_FK from parcela where parcela.UUID = unidadFuncional.parcela_FK), "manzana_FK");

--update nodoInfraestructura set "nombreCalle" = (SELECT eje.nombreCalle from eje where eje.uuid=eje_FK);
update nodoInfraestructura set "nombreCalle" = coalesce( (select eje.nombreCalle from eje where eje.uuid = eje_FK), "nombreCalle");


UPDATE "manzana" AS m
SET "proyectoTasa" = COALESCE((
    SELECT GROUP_CONCAT(DISTINCT n."proyectoTasa")
    FROM "nodo" AS n
    WHERE n."tipo" = 50
      AND n."manzana_FK" = m."UUID"
), '');

UPDATE "manzana"
SET "UIPs" = COALESCE((
    SELECT SUM(uf."HH")
    FROM "unidadFuncional" AS uf
    WHERE uf."manzana_FK" = "Manzana"."UUID"
), 0);

UPDATE "manzana"SET "memoria" = "ID" || '(' || "UIPs" || 'v)';

UPDATE parcela SET "proyectoTasa" = COALESCE((SELECT m."proyectoTasa" FROM manzana AS m WHERE m."UUID" = parcela."manzana_FK"),"proyectoTasa");

UPDATE unidadFuncional SET "proyectoTasa" = COALESCE((SELECT p."proyectoTasa" FROM parcela AS p WHERE p."UUID" = unidadFuncional."parcela_FK"),"proyectoTasa");

UPDATE "area" AS a SET "proyectoTasa" = COALESCE(( SELECT GROUP_CONCAT(DISTINCT n."proyectoTasa") FROM "nodo" AS n WHERE n."area_FK" = a."UUID"), a."proyectoTasa");

UPDATE eje AS a SET "proyectoTasa" = COALESCE(( SELECT GROUP_CONCAT(DISTINCT n."proyectoTasa") FROM area AS n WHERE n."eje_FK" = a."UUID"), a."proyectoTasa");

UPDATE "AreasProyectoTasa" AS a
SET "memoriaManzanas" =
    'CANTIDAD DE MANZANAS=' ||
    (
        SELECT COUNT(m."fid")
        FROM "manzana" AS m
        WHERE m."proyectoTasaIntersect" = a."proyectoTasa"
    )
    || CHAR(10) ||
    'NUMERO DE MANZANAS=' ||
    COALESCE(
        (
            SELECT GROUP_CONCAT(DISTINCT m."memoria")
            FROM "manzana" AS m
            WHERE m."proyectoTasaIntersect" = a."proyectoTasa"
        ),
        ''
    )
    || CHAR(10) ||
    'CANTIDAD DE VIVIENDAS=' ||
    COALESCE(
        (
            SELECT SUM(m."UIPs")
            FROM "manzana" AS m
            WHERE m."proyectoTasaIntersect" = a."proyectoTasa"
        ),
        0
    )
WHERE a."nivel" = 30;




UPDATE cable SET longitudTotal = CEIL(longitudTotal);


UPDATE nodoInfraestructura
SET "clasificacionUSO" = 40
WHERE nodoInfraestructura."clasificacionUSO" IS NULL
  AND EXISTS (
      SELECT 1
      FROM Suspensor
      WHERE Suspensor.infraInicio_FK = nodoInfraestructura.uuid
  );
  
UPDATE nodoInfraestructura
SET "clasificacionUSO" = 40
WHERE nodoInfraestructura."clasificacionUSO" IS NULL
  AND EXISTS (
      SELECT 1
      FROM Suspensor
      WHERE Suspensor.infraFin_FK = nodoInfraestructura.uuid
  );

UPDATE nodoInfraestructura SET "eje_FK" = coalesce( (select vereda.eje_FK from vereda where vereda.uuid = vereda_FK), "eje_FK");
UPDATE nodoInfraestructura SET "azi" = coalesce( (select eje.azi from eje where eje.uuid = eje_FK), "azi");
UPDATE nodo SET "azi" = coalesce( (select nodoInfraestructura.azi from nodoInfraestructura where nodoInfraestructura.uuid = infra_FK), "azi");


update segmento_OFF set "SITUACION" = ('Poste/aereo'); --
update segmento_OFF set "DIAMETRO" = ('4.8mm'); --
update segmento_OFF set "NUMERO_TUBOS" = CEIL(fibras/8); 

WITH fusionesCable AS (
    SELECT
        s.CEedge_cableFK AS cable_FK,
        COUNT(*) AS fusiones
    FROM Splices s
    WHERE s.splice_report_type = 3
      AND s.CEedge_cableSegmentName = 'SEG01'
    GROUP BY s.CEedge_cableFK
)
UPDATE cable
SET fusiones = (
    SELECT f.fusiones
    FROM fusionesCable f
    WHERE f.cable_FK = cable.uuid
);



DELETE FROM Valoraciones;

INSERT INTO Valoraciones (
    assembly,
    proyectoTasa,
    fase,
    longitudTotal,
    secundario,
    multiplier,
    unitarioContador,
    unidades,
    rotuladoPDF
)
SELECT
    a.assembly,
    a.proyectoTasa,
    a.fase,

    SUM(
        (
            SELECT c.longitudTotal
            FROM cable c
            WHERE c.UUID = a.feature_FK
              AND a.secundario = 0
              AND c.fibras > 1
        )
    ) AS longitudTotal,

    a.secundario,

    SUM(a.multiplier) AS multiplier,
    SUM(a.unitarioContador) AS unitarioContador,
    a.unidades AS unidades,
    a.rotuladoPDF AS rotuladoPDF


FROM ASY_assemblies_in_use a
GROUP BY
    a.assembly,
    a.fase,
    a.secundario,
    a.proyectoTasa;

UPDATE Valoraciones
SET rotuloValoraciones =
CASE
    WHEN multiplier IS NOT NULL THEN
        assembly || ': ' || COALESCE(longitudTotal, multiplier) || unidades
    ELSE
        assembly || ': ' || unitarioContador || unidades
END;


UPDATE AreasProyectoTASA
SET rotuloValoraciones = (
    SELECT group_concat(v.rotuloValoraciones, char(10))
    FROM Valoraciones v
    WHERE v.proyectoTasa = AreasProyectoTASA.proyectoTasa
      AND v.rotuladoPDF = 1
);

UPDATE atributosGenerales
SET "value" = 'false'
WHERE "nombre" = 'check';