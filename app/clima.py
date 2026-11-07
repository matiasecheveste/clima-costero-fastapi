"""
Clima costero — Matías Nicolás Echeveste Cardozo
Cliente de Open-Meteo (pronóstico y modelo marino) con caché en memoria y evaluación de condiciones.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import BaseModel

from .playas import Playa

URL_PRONOSTICO = "https://api.open-meteo.com/v1/forecast"
URL_MARINO = "https://marine-api.open-meteo.com/v1/marine"

Nivel = Literal["favorable", "precaucion", "desaconsejado"]


class Condiciones(BaseModel):
    playa: str
    hora: str
    temperatura_c: float
    viento_kmh: float
    rafagas_kmh: float
    direccion_viento: str
    olas_m: float | None
    periodo_olas_s: float | None
    temperatura_agua_c: float | None
    nivel: Nivel
    motivos: list[str]


PUNTOS = ("N", "NE", "E", "SE", "S", "SO", "O", "NO")


def punto_cardinal(grados: float) -> str:
    return PUNTOS[round((grados % 360) / 45) % 8]


def evaluar(viento: float, rafagas: float, olas: float | None, agua: float | None) -> tuple[Nivel, list[str]]:
    """Clasifica las condiciones para el baño y actividades de playa con umbrales conservadores."""
    motivos: list[str] = []
    puntaje = 0
    if rafagas >= 50 or viento >= 35:
        motivos.append("viento fuerte")
        puntaje += 2
    elif viento >= 20:
        motivos.append("viento moderado")
        puntaje += 1
    if olas is not None:
        if olas >= 2.0:
            motivos.append("oleaje alto")
            puntaje += 2
        elif olas >= 1.2:
            motivos.append("oleaje moderado")
            puntaje += 1
    if agua is not None and agua < 16:
        motivos.append("agua fría")
        puntaje += 1
    nivel: Nivel = "favorable" if puntaje == 0 else "precaucion" if puntaje <= 2 else "desaconsejado"
    return nivel, motivos


@dataclass
class _Entrada:
    vence: float
    valor: Condiciones


class ServicioClima:
    """Consulta Open-Meteo y guarda cada resultado durante `ttl` segundos para no repetir llamadas."""

    def __init__(self, cliente: httpx.AsyncClient, ttl: float = 600, reloj=time.monotonic) -> None:
        self._cliente = cliente
        self._ttl = ttl
        self._reloj = reloj
        self._cache: dict[str, _Entrada] = {}
        self._candados: dict[str, asyncio.Lock] = {}

    async def condiciones(self, playa: Playa) -> Condiciones:
        entrada = self._cache.get(playa.slug)
        if entrada and entrada.vence > self._reloj():
            return entrada.valor
        candado = self._candados.setdefault(playa.slug, asyncio.Lock())
        async with candado:
            entrada = self._cache.get(playa.slug)
            if entrada and entrada.vence > self._reloj():
                return entrada.valor
            valor = await self._consultar(playa)
            self._cache[playa.slug] = _Entrada(self._reloj() + self._ttl, valor)
            return valor

    async def _consultar(self, playa: Playa) -> Condiciones:
        coordenadas = {"latitude": playa.latitud, "longitude": playa.longitud, "timezone": "America/Montevideo"}
        pronostico, marino = await asyncio.gather(
            self._cliente.get(
                URL_PRONOSTICO,
                params={**coordenadas, "current": "temperature_2m,wind_speed_10m,wind_gusts_10m,wind_direction_10m"},
            ),
            self._cliente.get(
                URL_MARINO,
                params={**coordenadas, "current": "wave_height,wave_period,sea_surface_temperature"},
            ),
        )
        pronostico.raise_for_status()
        actual = pronostico.json()["current"]
        mar = marino.json().get("current", {}) if marino.is_success else {}

        olas = mar.get("wave_height")
        agua = mar.get("sea_surface_temperature")
        nivel, motivos = evaluar(actual["wind_speed_10m"], actual["wind_gusts_10m"], olas, agua)
        return Condiciones(
            playa=playa.nombre,
            hora=actual["time"],
            temperatura_c=actual["temperature_2m"],
            viento_kmh=actual["wind_speed_10m"],
            rafagas_kmh=actual["wind_gusts_10m"],
            direccion_viento=punto_cardinal(actual["wind_direction_10m"]),
            olas_m=olas,
            periodo_olas_s=mar.get("wave_period"),
            temperatura_agua_c=agua,
            nivel=nivel,
            motivos=motivos,
        )
