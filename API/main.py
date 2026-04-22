"""
main.py
API REST de Accidentes de Tránsito — Colombia
Construida con FastAPI + SQLAlchemy + MySQL

Ejecutar:
    uvicorn main:app --reload --port 8000

Documentación interactiva disponible en:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""

from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from database import engine, get_db

# ─────────────────────────────────────────────
# INICIALIZACIÓN
# ─────────────────────────────────────────────
# Crea las tablas si no existen (útil en desarrollo)
# En producción, usa Alembic para migraciones controladas.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Alerta Vial — API de Accidentes de Tránsito",
    description=(
        "API REST para consultar y gestionar los registros de accidentes "
        "de tránsito en Colombia. Datos normalizados en 3FN."
    ),
    version="1.0.0",
)


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def _not_found(entidad: str, id_valor):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entidad} con id={id_valor} no encontrado.",
    )


# ══════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "mensaje": "Alerta Vial API en línea 🚦"}


# ══════════════════════════════════════════════════════════════
#  RESUMEN / ESTADÍSTICAS
# ══════════════════════════════════════════════════════════════

@app.get(
    "/estadisticas/resumen",
    response_model=schemas.ResumenOut,
    tags=["Estadísticas"],
    summary="Resumen global de accidentes",
)
def resumen_global(db: Session = Depends(get_db)):
    """Devuelve totales globales y participación de motos."""
    total = db.query(func.count(models.Accidente.id_accidente)).scalar()

    heridos = (
        db.query(func.count(models.Accidente.id_accidente))
        .join(models.GravedadAccidente)
        .filter(models.GravedadAccidente.descripcion.ilike("%heridos%"))
        .scalar()
    )
    muertos = (
        db.query(func.count(models.Accidente.id_accidente))
        .join(models.GravedadAccidente)
        .filter(models.GravedadAccidente.descripcion.ilike("%muertos%"))
        .scalar()
    )
    motos = (
        db.query(func.count(models.Accidente.id_accidente))
        .join(models.Vehiculo)
        .join(models.TipoVehiculo)
        .filter(models.TipoVehiculo.nombre_tipo.ilike("%moto%"))
        .scalar()
    )

    pct_motos = round((motos / total * 100), 2) if total else 0.0

    return schemas.ResumenOut(
        total_accidentes=total,
        total_con_heridos=heridos,
        total_con_muertos=muertos,
        porcentaje_motos=pct_motos,
    )


@app.get(
    "/estadisticas/por-departamento",
    response_model=List[schemas.AccidentesPorDepartamentoOut],
    tags=["Estadísticas"],
    summary="Accidentes agrupados por departamento",
)
def accidentes_por_departamento(
    limit: int = Query(default=33, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Ranking de departamentos por número de accidentes."""
    rows = (
        db.query(
            models.Departamento.nombre_depto,
            func.count(models.Accidente.id_accidente).label("total"),
        )
        .join(models.Municipio, models.Municipio.id_departamento == models.Departamento.id_departamento)
        .join(models.Accidente, models.Accidente.id_municipio == models.Municipio.id_municipio)
        .group_by(models.Departamento.nombre_depto)
        .order_by(func.count(models.Accidente.id_accidente).desc())
        .limit(limit)
        .all()
    )
    return [schemas.AccidentesPorDepartamentoOut(nombre_depto=r[0], total=r[1]) for r in rows]


@app.get(
    "/estadisticas/por-gravedad",
    response_model=List[schemas.AccidentesPorGravedadOut],
    tags=["Estadísticas"],
    summary="Distribución por nivel de gravedad",
)
def accidentes_por_gravedad(db: Session = Depends(get_db)):
    rows = (
        db.query(
            models.GravedadAccidente.descripcion,
            models.GravedadAccidente.nivel,
            func.count(models.Accidente.id_accidente).label("total"),
        )
        .join(models.Accidente, models.Accidente.id_gravedad == models.GravedadAccidente.id_gravedad)
        .group_by(models.GravedadAccidente.descripcion, models.GravedadAccidente.nivel)
        .order_by(func.count(models.Accidente.id_accidente).desc())
        .all()
    )
    return [
        schemas.AccidentesPorGravedadOut(descripcion=r[0], nivel=r[1], total=r[2])
        for r in rows
    ]


@app.get(
    "/estadisticas/por-tipo-vehiculo",
    response_model=List[schemas.AccidentesPorTipoVehiculoOut],
    tags=["Estadísticas"],
    summary="Distribución por tipo de vehículo",
)
def accidentes_por_tipo_vehiculo(db: Session = Depends(get_db)):
    rows = (
        db.query(
            models.TipoVehiculo.nombre_tipo,
            func.count(models.Accidente.id_accidente).label("total"),
        )
        .join(models.Vehiculo, models.Vehiculo.id_tipo == models.TipoVehiculo.id_tipo)
        .join(models.Accidente, models.Accidente.id_vehiculo == models.Vehiculo.id_vehiculo)
        .group_by(models.TipoVehiculo.nombre_tipo)
        .order_by(func.count(models.Accidente.id_accidente).desc())
        .all()
    )
    return [schemas.AccidentesPorTipoVehiculoOut(nombre_tipo=r[0], total=r[1]) for r in rows]


# ══════════════════════════════════════════════════════════════
#  ACCIDENTES  (tabla de hechos — CRUD completo)
# ══════════════════════════════════════════════════════════════

@app.get(
    "/accidentes",
    response_model=List[schemas.AccidenteListOut],
    tags=["Accidentes"],
    summary="Listar accidentes con filtros opcionales",
)
def listar_accidentes(
    departamento: Optional[str]  = Query(None, description="Nombre del departamento"),
    municipio:    Optional[str]  = Query(None, description="Nombre del municipio"),
    tipo_vehiculo:Optional[str]  = Query(None, description="Tipo de vehículo (ej: MOTOCICLETA)"),
    gravedad:     Optional[str]  = Query(None, description="Nivel de gravedad: BAJO, MEDIO o ALTO"),
    fecha_desde:  Optional[str]  = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta:  Optional[str]  = Query(None, description="Fecha fin YYYY-MM-DD"),
    skip: int = Query(default=0,   ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Lista accidentes con paginación y filtros opcionales.
    Usa `skip` y `limit` para paginar (ej: skip=100&limit=50 → página 3).
    """
    q = db.query(models.Accidente)

    if departamento:
        q = (
            q.join(models.Municipio)
            .join(models.Departamento)
            .filter(models.Departamento.nombre_depto.ilike(f"%{departamento}%"))
        )
    if municipio:
        q = q.join(models.Municipio, isouter=True).filter(
            models.Municipio.nombre_municipio.ilike(f"%{municipio}%")
        )
    if tipo_vehiculo:
        q = (
            q.join(models.Vehiculo, isouter=True)
            .join(models.TipoVehiculo, isouter=True)
            .filter(models.TipoVehiculo.nombre_tipo.ilike(f"%{tipo_vehiculo}%"))
        )
    if gravedad:
        q = q.join(models.GravedadAccidente, isouter=True).filter(
            models.GravedadAccidente.nivel.ilike(f"%{gravedad}%")
        )
    if fecha_desde:
        q = q.filter(models.Accidente.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(models.Accidente.fecha <= fecha_hasta)

    return q.offset(skip).limit(limit).all()


@app.get(
    "/accidentes/{id_accidente}",
    response_model=schemas.AccidenteOut,
    tags=["Accidentes"],
    summary="Obtener un accidente por ID (con relaciones completas)",
)
def obtener_accidente(id_accidente: int, db: Session = Depends(get_db)):
    accidente = (
        db.query(models.Accidente)
        .options(
            joinedload(models.Accidente.vehiculo).joinedload(models.Vehiculo.marca),
            joinedload(models.Accidente.vehiculo).joinedload(models.Vehiculo.tipo_vehiculo),
            joinedload(models.Accidente.municipio).joinedload(models.Municipio.departamento),
            joinedload(models.Accidente.autoridad),
            joinedload(models.Accidente.gravedad),
        )
        .filter(models.Accidente.id_accidente == id_accidente)
        .first()
    )
    if not accidente:
        _not_found("Accidente", id_accidente)
    return accidente


@app.post(
    "/accidentes",
    response_model=schemas.AccidenteListOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Accidentes"],
    summary="Registrar un nuevo accidente",
)
def crear_accidente(payload: schemas.AccidenteCreate, db: Session = Depends(get_db)):
    # Validar FKs antes de insertar
    for modelo_fk, id_val, nombre in [
        (models.Vehiculo,          payload.id_vehiculo,  "Vehículo"),
        (models.Municipio,         payload.id_municipio, "Municipio"),
        (models.AutoridadTransito, payload.id_autoridad, "Autoridad"),
        (models.GravedadAccidente, payload.id_gravedad,  "Gravedad"),
    ]:
        if not db.get(modelo_fk, id_val):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{nombre} con id={id_val} no existe.",
            )

    nuevo = models.Accidente(**payload.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@app.put(
    "/accidentes/{id_accidente}",
    response_model=schemas.AccidenteListOut,
    tags=["Accidentes"],
    summary="Actualizar un accidente existente",
)
def actualizar_accidente(
    id_accidente: int,
    payload: schemas.AccidenteCreate,
    db: Session = Depends(get_db),
):
    acc = db.get(models.Accidente, id_accidente)
    if not acc:
        _not_found("Accidente", id_accidente)

    for campo, valor in payload.model_dump().items():
        setattr(acc, campo, valor)

    db.commit()
    db.refresh(acc)
    return acc


@app.delete(
    "/accidentes/{id_accidente}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Accidentes"],
    summary="Eliminar un accidente",
)
def eliminar_accidente(id_accidente: int, db: Session = Depends(get_db)):
    acc = db.get(models.Accidente, id_accidente)
    if not acc:
        _not_found("Accidente", id_accidente)
    db.delete(acc)
    db.commit()


# ══════════════════════════════════════════════════════════════
#  VEHÍCULOS  (CRUD)
# ══════════════════════════════════════════════════════════════

@app.get(
    "/vehiculos",
    response_model=List[schemas.VehiculoOut],
    tags=["Vehículos"],
    summary="Listar vehículos",
)
def listar_vehiculos(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Vehiculo)
        .options(
            joinedload(models.Vehiculo.marca),
            joinedload(models.Vehiculo.tipo_vehiculo),
        )
        .offset(skip).limit(limit).all()
    )


@app.get(
    "/vehiculos/{id_vehiculo}",
    response_model=schemas.VehiculoOut,
    tags=["Vehículos"],
)
def obtener_vehiculo(id_vehiculo: int, db: Session = Depends(get_db)):
    v = (
        db.query(models.Vehiculo)
        .options(joinedload(models.Vehiculo.marca), joinedload(models.Vehiculo.tipo_vehiculo))
        .filter(models.Vehiculo.id_vehiculo == id_vehiculo)
        .first()
    )
    if not v:
        _not_found("Vehículo", id_vehiculo)
    return v


@app.post(
    "/vehiculos",
    response_model=schemas.VehiculoOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Vehículos"],
)
def crear_vehiculo(payload: schemas.VehiculoCreate, db: Session = Depends(get_db)):
    nuevo = models.Vehiculo(**payload.model_dump())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return db.query(models.Vehiculo).options(
        joinedload(models.Vehiculo.marca),
        joinedload(models.Vehiculo.tipo_vehiculo),
    ).filter(models.Vehiculo.id_vehiculo == nuevo.id_vehiculo).first()


# ══════════════════════════════════════════════════════════════
#  CATÁLOGOS (solo lectura — los datos los carga la migración)
# ══════════════════════════════════════════════════════════════

@app.get("/marcas",         response_model=List[schemas.MarcaOut],        tags=["Catálogos"])
def listar_marcas(db: Session = Depends(get_db)):
    return db.query(models.Marca).order_by(models.Marca.nombre_marca).all()

@app.get("/tipos-vehiculo", response_model=List[schemas.TipoVehiculoOut], tags=["Catálogos"])
def listar_tipos(db: Session = Depends(get_db)):
    return db.query(models.TipoVehiculo).order_by(models.TipoVehiculo.nombre_tipo).all()

@app.get("/departamentos",  response_model=List[schemas.DepartamentoOut], tags=["Catálogos"])
def listar_departamentos(db: Session = Depends(get_db)):
    return db.query(models.Departamento).order_by(models.Departamento.nombre_depto).all()

@app.get("/municipios",     response_model=List[schemas.MunicipioOut],    tags=["Catálogos"])
def listar_municipios(
    departamento_id: Optional[int] = Query(None, description="Filtrar por id_departamento"),
    db: Session = Depends(get_db),
):
    q = db.query(models.Municipio).options(joinedload(models.Municipio.departamento))
    if departamento_id:
        q = q.filter(models.Municipio.id_departamento == departamento_id)
    return q.order_by(models.Municipio.nombre_municipio).all()

@app.get("/autoridades",    response_model=List[schemas.AutoridadOut],    tags=["Catálogos"])
def listar_autoridades(db: Session = Depends(get_db)):
    return db.query(models.AutoridadTransito).order_by(models.AutoridadTransito.nombre_autoridad).all()

@app.get("/gravedades",     response_model=List[schemas.GravedadOut],     tags=["Catálogos"])
def listar_gravedades(db: Session = Depends(get_db)):
    return db.query(models.GravedadAccidente).all()
