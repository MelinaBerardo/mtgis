INSERT OR IGNORE INTO gpkg_spatial_ref_sys 
VALUES (
'POSGAR 98 / Argentina 6',
22175,
'EPSG',
22175,
'PROJCS["POSGAR 98 / Argentina 6",
    GEOGCS["POSGAR 98",
        DATUM["POSGAR_1998",
            SPHEROID["GRS 1980",6378137,298.257222101]],
        PRIMEM["Greenwich",0],
        UNIT["degree",0.0174532925199433]],
    PROJECTION["Transverse_Mercator"],
    PARAMETER["latitude_of_origin",-90],
    PARAMETER["central_meridian",-57],
    PARAMETER["scale_factor",1],
    PARAMETER["false_easting",6500000],
    PARAMETER["false_northing",0],
    UNIT["metre",1]]',
NULL
);

SELECT 
'UPDATE "' || table_name || 
'" SET "' || column_name || 
'" = asgpb(transform(geomfromgpb("' || column_name || '"),22175));'
FROM gpkg_geometry_columns;


SELECT 
'UPDATE "' || table_name || 
'" SET "' || column_name || 
'" = asgpb(snaptogrid(geomfromgpb("' || column_name || '"),0.001));'
FROM gpkg_geometry_columns;

UPDATE gpkg_contents 
SET srs_id = 22175 
WHERE srs_id = 22176;

UPDATE gpkg_geometry_columns 
SET srs_id = 22175 
WHERE srs_id = 22176;