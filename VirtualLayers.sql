---Node_Cable

select Cables.uuid as cable_uuid,
		Nodos.uuid as nodo_uuid,
		Nodos.nivel as nodo_nivel,
		Cables.nivel as cable_nivel,
		intersects(start_point(Cables.geometry),Nodos.geometry)  as start_point,
		intersects(end_point(Cables.geometry),Nodos.geometry)  as end_point
from Cables,Nodos
where intersects(Cables.geometry,Nodos.geometry) 

---Node_Infra

select nodoInfraestructura.uuid as infra_uuid,
		Nodos.uuid as nodo_uuid,
		Nodos.colocacion as nodo_colocacion,
		nodoInfraestructura.tipoInfraestructura as tipoInfraestructura
from nodoInfraestructura,Nodos
where intersects(nodoInfraestructura.geometry,Nodos.geometry) 

---Area_Node

select Areas.uuid as area_uuid,
		Nodos.uuid as nodo_uuid,
		Nodos.nivel as nodo_nivel,
		Areas.nivel as area_nivel,
		Nodos.tipo as nodo_tipo,
		Nodos.fase as nodo_fase
from Areas ,Nodos
where intersects(Areas.geometry,Nodos.geometry) 