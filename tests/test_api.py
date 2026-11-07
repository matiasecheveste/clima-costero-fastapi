"""
Clima costero — Matías Nicolás Echeveste Cardozo
Pruebas de la API con un transporte HTTP simulado (sin acceso a Internet).
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.clima import ServicioClima, evaluar, punto_cardinal
from app.main import app, servicio
from app.playas import POR_SLUG

PRONOSTICO = {
    "current": {
        "time": "2026-01-15T15:00",
        "temperature_2m": 27.4,
        "wind_speed_10m": 12.0,
        "wind_gusts_10m": 25.0,
        "wind_direction_10m": 135,
    }
}
MARINO = {"current": {"wave_height": 0.8, "wave_period": 7.5, "sea_surface_temperature": 21.3}}


class Simulador:
    def __init__(self, marino_estado: int = 200) -> None:
        self.llamadas: list[httpx.Request] = []
        self.marino_estado = marino_estado

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.llamadas.append(request)
        if request.url.host == "marine-api.open-meteo.com":
            return httpx.Response(self.marino_estado, json=MARINO if self.marino_estado == 200 else {})
        return httpx.Response(200, json=PRONOSTICO)


def cliente_con(simulador: Simulador, reloj=lambda: 0.0) -> TestClient:
    clima = ServicioClima(httpx.AsyncClient(transport=httpx.MockTransport(simulador)), ttl=600, reloj=reloj)
    app.dependency_overrides[servicio] = lambda: clima
    return TestClient(app)


@pytest.fixture(autouse=True)
def limpiar():
    yield
    app.dependency_overrides.clear()


def test_lista_playas():
    r = cliente_con(Simulador()).get("/api/playas")
    assert r.status_code == 200
    assert {"slug": "barra-del-chuy", "nombre": "Barra del Chuy", "localidad": "Chuy"} in r.json()


def test_condiciones_combina_pronostico_y_mar():
    simulador = Simulador()
    r = cliente_con(simulador).get("/api/playas/la-paloma/condiciones")
    assert r.status_code == 200
    datos = r.json()
    assert datos["direccion_viento"] == "SE"
    assert datos["olas_m"] == 0.8
    assert datos["nivel"] == "favorable"
    consulta = simulador.llamadas[0].url.params
    assert consulta["latitude"] == str(POR_SLUG["la-paloma"].latitud)
    assert consulta["timezone"] == "America/Montevideo"


def test_usa_cache_hasta_que_vence():
    simulador = Simulador()
    ahora = [0.0]
    cliente = cliente_con(simulador, reloj=lambda: ahora[0])
    cliente.get("/api/playas/la-coronilla/condiciones")
    cliente.get("/api/playas/la-coronilla/condiciones")
    assert len(simulador.llamadas) == 2  # una de pronóstico y una marina
    ahora[0] = 601
    cliente.get("/api/playas/la-coronilla/condiciones")
    assert len(simulador.llamadas) == 4


def test_tolera_falla_del_modelo_marino():
    r = cliente_con(Simulador(marino_estado=503)).get("/api/playas/cabo-polonio/condiciones")
    assert r.status_code == 200
    assert r.json()["olas_m"] is None


def test_playa_inexistente():
    assert cliente_con(Simulador()).get("/api/playas/atlantida/condiciones").status_code == 404


@pytest.mark.parametrize(
    ("viento", "rafagas", "olas", "agua", "nivel"),
    [
        (10, 20, 0.5, 22, "favorable"),
        (25, 30, 0.5, 22, "precaucion"),
        (25, 30, 1.5, 22, "precaucion"),
        (40, 60, 2.5, 15, "desaconsejado"),
    ],
)
def test_evaluar(viento, rafagas, olas, agua, nivel):
    assert evaluar(viento, rafagas, olas, agua)[0] == nivel


def test_punto_cardinal():
    assert [punto_cardinal(g) for g in (0, 44, 90, 200, 359)] == ["N", "NE", "E", "S", "N"]
