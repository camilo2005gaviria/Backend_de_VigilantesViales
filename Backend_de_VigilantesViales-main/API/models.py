"""
models.py
Modelos SQLAlchemy — reflejan exactamente las tablas del esquema normalizado
en 3FN de la base de datos 'accidentes'.
"""

from sqlalchemy import (
    Column, Date, ForeignKey, Index, Integer,
    SmallInteger, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


# ──────────────────────────────────────────────────────────────
# CATÁLOGOS INDEPENDIENTES
# ──────────────────────────────────────────────────────────────

class Marca(Base):
    """Marcas de vehículos (ej: YAMAHA, CHEVROLET, …)"""
    __tablename__ = "marca"

    id_marca     = Column(SmallInteger, primary_key=True, autoincrement=True)
    nombre_marca = Column(String(60), nullable=False, unique=True)

    # Relación inversa
    vehiculos = relationship("Vehiculo", back_populates="marca")


class TipoVehiculo(Base):
    """Tipos de vehículo (ej: MOTOCICLETA, AUTOMÓVIL, …)"""
    __tablename__ = "tipo_vehiculo"

    id_tipo     = Column(SmallInteger, primary_key=True, autoincrement=True)
    nombre_tipo = Column(String(60), nullable=False, unique=True)

    vehiculos = relationship("Vehiculo", back_populates="tipo_vehiculo")


class Departamento(Base):
    """Departamentos de Colombia"""
    __tablename__ = "departamento"

    id_departamento = Column(SmallInteger, primary_key=True, autoincrement=True)
    nombre_depto    = Column(String(80), nullable=False, unique=True)

    municipios = relationship("Municipio", back_populates="departamento")


class AutoridadTransito(Base):
    """Autoridades de tránsito que atendieron el accidente"""
    __tablename__ = "autoridad_transito"

    id_autoridad     = Column(SmallInteger, primary_key=True, autoincrement=True)
    nombre_autoridad = Column(String(150), nullable=False, unique=True)

    accidentes = relationship("Accidente", back_populates="autoridad")


class GravedadAccidente(Base):
    """
    Gravedad del accidente con clasificación semafórica.
    nivel: BAJO | MEDIO | ALTO
    """
    __tablename__ = "gravedad_accidente"

    id_gravedad = Column(Integer, primary_key=True, autoincrement=True)
    descripcion = Column(String(80), nullable=False, unique=True)
    nivel       = Column(String(20), nullable=False, default="MEDIO")

    accidentes = relationship("Accidente", back_populates="gravedad")


# ──────────────────────────────────────────────────────────────
# ENTIDADES CON DEPENDENCIAS
# ──────────────────────────────────────────────────────────────

class Municipio(Base):
    """Municipios de Colombia, asociados a su departamento"""
    __tablename__ = "municipio"
    __table_args__ = (
        UniqueConstraint("nombre_municipio", "id_departamento", name="uq_municipio_depto"),
    )

    id_municipio     = Column(SmallInteger, primary_key=True, autoincrement=True)
    nombre_municipio = Column(String(100), nullable=False)
    id_departamento  = Column(SmallInteger, ForeignKey("departamento.id_departamento"), nullable=False)

    departamento = relationship("Departamento", back_populates="municipios")
    accidentes   = relationship("Accidente", back_populates="municipio")


class Vehiculo(Base):
    """
    Vehículo involucrado en un accidente.
    La combinación (modelo, edad_vehiculo, id_marca, id_tipo) identifica
    un vehículo de forma lógica, aunque el PK es autoincremental.
    """
    __tablename__ = "vehiculo"

    id_vehiculo   = Column(Integer, primary_key=True, autoincrement=True)
    modelo        = Column(SmallInteger, nullable=False)        # año modelo (YEAR en MySQL)
    edad_vehiculo = Column(Integer, nullable=False)             # años de antigüedad
    id_marca      = Column(SmallInteger, ForeignKey("marca.id_marca"), nullable=False)
    id_tipo       = Column(SmallInteger, ForeignKey("tipo_vehiculo.id_tipo"), nullable=False)

    marca         = relationship("Marca",        back_populates="vehiculos")
    tipo_vehiculo = relationship("TipoVehiculo", back_populates="vehiculos")
    accidentes    = relationship("Accidente",    back_populates="vehiculo")


# ──────────────────────────────────────────────────────────────
# TABLA DE HECHOS
# ──────────────────────────────────────────────────────────────

class Accidente(Base):
    """
    Registro central de cada accidente de tránsito.
    Relaciona vehículo, ubicación, autoridad y gravedad.
    """
    __tablename__ = "accidente"
    __table_args__ = (
        Index("idx_fecha",     "fecha"),
        Index("idx_municipio", "id_municipio"),
        Index("idx_gravedad",  "id_gravedad"),
    )

    id_accidente = Column(Integer,      primary_key=True, autoincrement=True)
    fecha        = Column(Date,         nullable=False)
    id_vehiculo  = Column(Integer,      ForeignKey("vehiculo.id_vehiculo"),           nullable=False)
    id_municipio = Column(SmallInteger, ForeignKey("municipio.id_municipio"),         nullable=False)
    id_autoridad = Column(SmallInteger, ForeignKey("autoridad_transito.id_autoridad"),nullable=False)
    id_gravedad  = Column(Integer,      ForeignKey("gravedad_accidente.id_gravedad"), nullable=False)

    vehiculo  = relationship("Vehiculo",          back_populates="accidentes")
    municipio = relationship("Municipio",          back_populates="accidentes")
    autoridad = relationship("AutoridadTransito",  back_populates="accidentes")
    gravedad  = relationship("GravedadAccidente",  back_populates="accidentes")
