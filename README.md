# Clima costero de Rocha

API y página web que muestran las condiciones actuales de viento, oleaje y temperatura del agua en seis playas
del departamento de Rocha (Uruguay), con una clasificación orientativa: favorable, precaución o desaconsejado.

**Tecnologías:** Python 3.11+, FastAPI, Pydantic, httpx asíncrono, pytest, Ruff, Docker y GitHub Actions.
Datos de [Open-Meteo](https://open-meteo.com/) (pronóstico y modelo marino, licencia CC BY 4.0).

## Qué demuestra

- **API asíncrona** con FastAPI: dos consultas externas en paralelo (`asyncio.gather`) por cada playa.
- **Caché en memoria con vencimiento** y un candado por playa para que solicitudes simultáneas no repitan la
  consulta.
- **Tolerancia a fallos:** si el modelo marino no responde, devuelve el pronóstico con los datos de oleaje vacíos;
  si falla el pronóstico, responde 502 con un mensaje claro.
- **Inyección de dependencias** (`Depends`) para reemplazar el cliente HTTP en las pruebas por un
  `httpx.MockTransport`: las pruebas no acceden a Internet.
- **Documentación OpenAPI** automática en `/docs`.
- **Matriz de CI** en Python 3.11, 3.12 y 3.13, análisis con Ruff y construcción de la imagen Docker.

## Uso

```bash
python -m venv .venv && . .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload                  # http://localhost:8000 y /docs
```

Con Docker:

```bash
docker build -t clima-costero . && docker run -p 8000:8000 clima-costero
```

## Rutas

| Ruta | Descripción |
|---|---|
| `GET /` | Página con una tarjeta por playa |
| `GET /api/playas` | Catálogo de playas |
| `GET /api/playas/{slug}/condiciones` | Temperatura, viento, oleaje, temperatura del agua y clasificación |
| `GET /docs` | Documentación interactiva |

La clasificación es orientativa y usa umbrales conservadores (viento, ráfagas, altura de ola y temperatura del
agua). No sustituye las indicaciones de los guardavidas.

## Autoría

Desarrollado por **Matías Nicolás Echeveste Cardozo**. Licencia MIT.
