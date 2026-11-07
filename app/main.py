"""
Clima costero — Matías Nicolás Echeveste Cardozo
API FastAPI: catálogo de playas y condiciones actuales con datos abiertos de Open-Meteo.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from .clima import Condiciones, ServicioClima
from .playas import PLAYAS, POR_SLUG, Playa

ESTATICOS = Path(__file__).parent / "estatico"


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "clima-costero/1.0"}) as cliente:
        app.state.servicio = ServicioClima(cliente)
        yield


app = FastAPI(
    title="Clima costero de Rocha",
    version="1.0.0",
    description="Condiciones actuales de viento, oleaje y temperatura en playas de Rocha, Uruguay.",
    lifespan=ciclo_de_vida,
)


def servicio(request: Request) -> ServicioClima:
    return request.app.state.servicio


@app.get("/", include_in_schema=False)
async def inicio() -> FileResponse:
    return FileResponse(ESTATICOS / "index.html")


@app.get("/api/playas", response_model=list[dict])
async def listar_playas() -> list[dict]:
    return [{"slug": p.slug, "nombre": p.nombre, "localidad": p.localidad} for p in PLAYAS]


@app.get("/api/playas/{slug}/condiciones", response_model=Condiciones)
async def condiciones(slug: str, clima: Annotated[ServicioClima, Depends(servicio)]) -> Condiciones:
    playa: Playa | None = POR_SLUG.get(slug)
    if playa is None:
        raise HTTPException(status_code=404, detail="Playa inexistente")
    try:
        return await clima.condiciones(playa)
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="El servicio meteorológico no respondió") from error


@app.get("/salud")
async def salud() -> dict[str, str]:
    return {"estado": "ok"}
