# OptiNet — Optimizador de Redes de Distribución

Aplicación web para la optimización de redes de transporte mediante **Programación Entera Mixta (MILP)**. Permite modelar redes con plantas, centros de distribución opcionales y clientes, visualizar el grafo interactivo y obtener la solución óptima con desglose completo de costos.

> Proyecto académico — Investigación de Operaciones

---

## Características

- Modelado MILP con solver CBC (via PuLP)
- Decisión binaria de apertura de centros de distribución
- Gestión de déficit con penalización por cliente
- Restricción configurable de rutas activas simultáneas
- Visualización interactiva del grafo (vis-network)
- Dashboard de resultados con desglose de costos
- API REST con FastAPI

---

## Estructura del proyecto

```
optinet/
├── main.py              # Servidor FastAPI + rutas API
├── requirements.txt     # Dependencias Python
├── core/
│   ├── __init__.py
│   ├── data.py          # Modelos de dominio (Plant, DistCenter, Client, Arc)
│   ├── model.py         # Formulación MILP con PuLP
│   └── solver.py        # Resolución y extracción de resultados
└── static/
    ├── index.html       # SPA principal
    ├── editor.js        # Grafo interactivo (vis-network)
    ├── dashboard.js     # KPIs y panel de resultados
    └── style.css        # Estilos
```

---

## Instalación

**Requisitos:** Python 3.11 o 3.12

```bash
# 1. Clonar el repositorio
git clone https://github.com/Neckino/Investigaci-n-de-Operaciones
cd optinet

# 2. Crear entorno virtual
python -m venv env
env\Scripts\activate        # Windows
source env/bin/activate     # Linux / Mac

# 3. Instalar dependencias
pip install -r requirements.txt
```

---

## Uso

```bash
uvicorn main:app --reload --port 8000
```

Abrir en el navegador: `http://localhost:8000`

---

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/data` | Datos de la red (nodos, arcos, costos) |
| POST | `/api/solve` | Ejecuta el MILP y devuelve la solución |
| POST | `/api/nodes` | Edita atributos de un nodo |
| POST | `/api/params` | Actualiza parámetros del solver |
| POST | `/api/reset` | Reinicia la red al escenario base |

---

## Formulación MILP

**Variables de decisión**

| Variable | Tipo | Descripción |
|----------|------|-------------|
| `x[a]` | Continua ≥ 0 | Flujo en el arco `a` |
| `z[a]` | Binaria | Ruta activa en el arco `a` |
| `y[d]` | Binaria | Apertura del centro de distribución `d` |
| `s[c]` | Continua ≥ 0 | Déficit del cliente `c` |

**Función objetivo**

```
min  Σ unit_cost[a]·x[a]  +  Σ fixed_cost[d]·y[d]  +  Σ penalty[c]·s[c]
```

**Restricciones principales**
- Oferta máxima por planta
- Satisfacción de demanda con déficit permitido
- Capacidad de CD condicionada a su apertura (Big-M)
- Conservación de flujo en centros de distribución
- Límite global de rutas activas simultáneas

---

## Dependencias

| Paquete | Versión | Uso |
|---------|---------|-----|
| fastapi | 0.111.1 | Servidor web y API REST |
| uvicorn | 0.30.1 | Servidor ASGI |
| pulp | 2.8.0 | Modelado y resolución MILP (solver CBC) |
| pydantic | 2.7.4 | Validación de datos |

---

## Autores

Desarrollado para el curso de **Investigación de Operaciones**  
Universidad — 2026
