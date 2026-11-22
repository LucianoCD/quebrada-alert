"""Ingesta periódica de fuentes externas (capa de referencia, no mezclada con nodos simulados)."""

from quebrada.fuentes.controllers.fuentes_controller import crear_router
from quebrada.fuentes.services.fuentes_service import FuentesService
from quebrada.fuentes.services.scheduler import FuentesScheduler

__all__ = ["FuentesService", "FuentesScheduler", "crear_router"]
