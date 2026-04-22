"""
schemas.py
Schemas Pydantic para validación y serialización de datos.

Convención de nombres:
  <Entidad>Base   → campos comunes (sin id)
  <Entidad>Create → hereda Base, usado en POST/PUT
  <Entidad>Out    → respuesta al cliente (incluye id y relaciones anidadas)
"""

from __future__ import annotations
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


# ──────────────────────────────────────────────────────────────
# CONFIGURACIÓN GLOBAL: permite leer atributos ORM directamente
# ──────────────────────────────────────────────────────────────
class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────
# MARCA
# ──────────────────────────────────────────────────────────────
class MarcaBase(_Base):
    nombre_marca: str

class MarcaCreate(MarcaBase):
    pass

class MarcaOut(MarcaBase):
    id_marca: int


# ──────────────────────────────────────────────────────────────
# TIPO DE VEHÍCULO
# ──────────────────────────────────────────────────────────────
class TipoVehiculoBase(_Base):
    nombre_tipo: str

class TipoVehiculoCreate(TipoVehiculoBase):
    pass

class TipoVehiculoOut(TipoVehiculoBase):
    id_tipo: int


# ──────────────────────────────────────────────────────────────
# DEPARTAMENTO
# ──────────────────────────────────────────────────────────────
class DepartamentoBase(_Base):
    nombre_depto: str

class DepartamentoCreate(DepartamentoBase):
    pass

class DepartamentoOut(DepartamentoBase):
    id_departamento: int


# ──────────────────────────────────────────────────────────────
# MUNICIPIO
# ──────────────────────────────────────────────────────────────
class MunicipioBase(_Base):
    nombre_municipio: str
    id_departamento: int

class MunicipioCreate(MunicipioBase):
    pass

class MunicipioOut(MunicipioBase):
    id_municipio: int
    departamento: DepartamentoOut   # anidado para contexto


# ──────────────────────────────────────────────────────────────
# AUTORIDAD DE TRÁNSITO
# ──────────────────────────────────────────────────────────────
class AutoridadBase(_Base):
    nombre_autoridad: str

class AutoridadCreate(AutoridadBase):
    pass

class AutoridadOut(AutoridadBase):
    id_autoridad: int


# ──────────────────────────────────────────────────────────────
# GRAVEDAD DEL ACCIDENTE
# ──────────────────────────────────────────────────────────────
class GravedadBase(_Base):
    descripcion: str
    nivel: str = "MEDIO"

class GravedadCreate(GravedadBase):
    pass

class GravedadOut(GravedadBase):
    id_gravedad: int


# ──────────────────────────────────────────────────────────────
# VEHÍCULO
# ──────────────────────────────────────────────────────────────
class VehiculoBase(_Base):
    modelo: int
    edad_vehiculo: int
    id_marca: int
    id_tipo: int

class VehiculoCreate(VehiculoBase):
    pass

class VehiculoOut(VehiculoBase):
    id_vehiculo: int
    marca: MarcaOut
    tipo_vehiculo: TipoVehiculoOut


# ──────────────────────────────────────────────────────────────
# ACCIDENTE
# ──────────────────────────────────────────────────────────────
class AccidenteBase(_Base):
    fecha: date
    id_vehiculo: int
    id_municipio: int
    id_autoridad: int
    id_gravedad: int

class AccidenteCreate(AccidenteBase):
    pass

class AccidenteOut(AccidenteBase):
    id_accidente: int
    # Relaciones anidadas para respuesta enriquecida
    vehiculo:  VehiculoOut
    municipio: MunicipioOut
    autoridad: AutoridadOut
    gravedad:  GravedadOut

# Versión ligera (sin relaciones) — útil para listados grandes
class AccidenteListOut(_Base):
    id_accidente: int
    fecha: date
    id_vehiculo: int
    id_municipio: int
    id_autoridad: int
    id_gravedad: int


# ──────────────────────────────────────────────────────────────
# SCHEMAS DE RESUMEN / ESTADÍSTICAS
# ──────────────────────────────────────────────────────────────
class ResumenOut(BaseModel):
    total_accidentes: int
    total_con_heridos: int
    total_con_muertos: int
    porcentaje_motos: float

class AccidentesPorDepartamentoOut(BaseModel):
    nombre_depto: str
    total: int

class AccidentesPorGravedadOut(BaseModel):
    descripcion: str
    nivel: str
    total: int

class AccidentesPorTipoVehiculoOut(BaseModel):
    nombre_tipo: str
    total: int
