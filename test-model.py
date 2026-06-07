import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from solver import resolver
from data import PLANTAS, CLIENTES, CENTROS, MAX_RUTAS_ACTIVAS


def test_estado_optimo():
    sol = resolver()
    assert sol["factible"], "Debe encontrar solución factible"
    assert sol["estado"] == "Optimal", f"Estado inesperado: {sol['estado']}"
    print("  [OK] Estado: Optimal")


def test_oferta_no_excedida():
    sol = resolver()
    oferta = {p.id: p.oferta for p in PLANTAS}
    enviado = {p.id: 0.0 for p in PLANTAS}
    for (p, c), v in sol["flujo_directo"].items():
        enviado[p] += v
    for (p, d), v in sol["flujo_planta_cd"].items():
        enviado[p] += v
    for p_id, total in enviado.items():
        assert total <= oferta[p_id] + 1e-4, \
            f"{p_id} supera oferta: envía {total} > {oferta[p_id]}"
    print("  [OK] Oferta de todas las plantas respetada")


def test_capacidad_centros():
    sol = resolver()
    cap = {d.id: d.capacidad for d in CENTROS}
    recibido = {d.id: 0.0 for d in CENTROS}
    for (p, d), v in sol["flujo_planta_cd"].items():
        recibido[d] += v
    for d_id, total in recibido.items():
        assert total <= cap[d_id] + 1e-4, \
            f"{d_id} supera capacidad: {total} > {cap[d_id]}"
    print("  [OK] Capacidad de centros respetada")


def test_balance_centros():
    sol = resolver()
    for d in [c.id for c in CENTROS]:
        entrada = sum(v for (p, dd), v in sol["flujo_planta_cd"].items() if dd == d)
        salida  = sum(v for (dd, c), v in sol["flujo_cd_cliente"].items() if dd == d)
        assert abs(entrada - salida) < 1e-3, \
            f"Desbalance en {d}: entrada={entrada:.2f}, salida={salida:.2f}"
    print("  [OK] Balance entrada=salida en todos los CDs")


def test_demanda_cubierta():
    sol = resolver()
    demanda = {c.id: c.demanda for c in CLIENTES}
    deficit = sol.get("deficit", {})
    for c_id, dem in demanda.items():
        rec_dir = sum(v for (p, cc), v in sol["flujo_directo"].items()   if cc == c_id)
        rec_cd  = sum(v for (d, cc), v in sol["flujo_cd_cliente"].items() if cc == c_id)
        def_    = deficit.get(c_id, 0)
        assert abs(rec_dir + rec_cd + def_ - dem) < 1e-3, \
            f"Demanda de {c_id} no cuadra: rec={rec_dir+rec_cd}, def={def_}, dem={dem}"
    print("  [OK] Demanda cubierta o compensada con déficit en todos los clientes")


def test_max_rutas():
    sol = resolver()
    n = len(sol["rutas_directas"]) + len(sol["rutas_cd"])
    assert n <= MAX_RUTAS_ACTIVAS, f"Rutas activas ({n}) supera máximo ({MAX_RUTAS_ACTIVAS})"
    print(f"  [OK] Rutas activas: {n} ≤ {MAX_RUTAS_ACTIVAS}")


def test_centros_cerrados_sin_flujo():
    sol = resolver()
    abiertos = set(sol["centros_abiertos"])
    for (p, d) in sol["flujo_planta_cd"]:
        assert d in abiertos, f"Flujo a {d} pero ese CD no está abierto"
    print("  [OK] Solo CDs abiertos reciben flujo")


def test_costo_positivo():
    sol = resolver()
    assert sol["costo_total"] > 0
    print(f"  [OK] Costo total: ${sol['costo_total']:,.2f}")


def test_solucion_esperada():
    """Verifica que el resultado coincida con la solución analítica del enunciado."""
    sol = resolver()
    # Sin CDs abiertos, déficit solo en C4 (penalización más baja = $18/u)
    assert sol["centros_abiertos"] == [], \
        f"Se esperaba ningún CD abierto, se obtuvo: {sol['centros_abiertos']}"
    assert "C4" in sol["deficit"], "C4 debe tener déficit"
    assert abs(sol["deficit"]["C4"] - 75) < 1e-3, \
        f"Déficit de C4 debe ser 75 u., se obtuvo {sol['deficit'].get('C4')}"
    print(f"  [OK] Solución coherente con el análisis del enunciado")


if __name__ == "__main__":
    tests = [
        test_estado_optimo,
        test_oferta_no_excedida,
        test_capacidad_centros,
        test_balance_centros,
        test_demanda_cubierta,
        test_max_rutas,
        test_centros_cerrados_sin_flujo,
        test_costo_positivo,
        test_solucion_esperada,
    ]
    print("\n══════════════════════════════════════════")
    print("  TESTS — Red de distribución MILP v2")
    print("══════════════════════════════════════════")
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {t.__name__}: {e}")
            failed += 1
    print("──────────────────────────────────────────")
    if failed == 0:
        print(f"  Todos los tests pasaron ({len(tests)}/{len(tests)})")
    else:
        print(f"  {failed} test(s) fallaron")
    print("══════════════════════════════════════════\n")
    