"""
Clima costero — Matías Nicolás Echeveste Cardozo
Catálogo de playas de Rocha (Uruguay) con coordenadas aproximadas.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Playa:
    slug: str
    nombre: str
    localidad: str
    latitud: float
    longitud: float


PLAYAS: tuple[Playa, ...] = (
    Playa("barra-del-chuy", "Barra del Chuy", "Chuy", -33.7470, -53.3870),
    Playa("la-coronilla", "La Coronilla", "La Coronilla", -33.8960, -53.5170),
    Playa("punta-del-diablo", "Playa de la Viuda", "Punta del Diablo", -34.0440, -53.5480),
    Playa("cabo-polonio", "Playa Sur", "Cabo Polonio", -34.4030, -53.7890),
    Playa("la-pedrera", "El Desplayado", "La Pedrera", -34.5930, -54.1250),
    Playa("la-paloma", "La Aguada", "La Paloma", -34.6450, -54.1620),
)

POR_SLUG = {p.slug: p for p in PLAYAS}
