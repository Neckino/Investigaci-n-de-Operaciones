"""
Verifica que el modelo produzca resultados coherentes con el enunciado.
Ejecutar con: python test_model.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from solver import resolver
from data import PLANTAS, CLIENTES, CENTROS, MAX_RUTAS_ACTIVAS


def test_estado_optimo():
    sol = resolver()
    assert sol["factible"], "El modelo debe encontrar solución factible"
    assert sol["estado"] == "Optimal", f"Estado inesperado: {sol['estado']}"
    print("  [OK] Estado: Optimal")


def test_oferta_no_excedida():
    sol = resolver()
    oferta = {p.id: p.oferta for p in PLANTAS}
    enviado = {p.id: 0.0 for p in PLANTAS}
    for (p, d), v in sol["flujo_planta_cd"].items():
        enviado[p] += v
    for p_id, total in enviado.items():
        assert total <= oferta[p_id] + 1e-4, (
            f"{p_id} supera su oferta: envía {total} > {oferta[p_id]}"
        )
    print("  [OK] Oferta de todas las plantas respetada")


def test_capacidad_centros():
    sol = resolver()
    cap = {d.id: d.capacidad for d in CENTROS}
    recibido = {d.id: 0.0 for d in CENTROS}
    for (p, d), v in sol["flujo_planta_cd"].items():
        recibido[d] += v
    for d_id, total in recibido.items():
        assert total <= cap[d_id] + 1e-4, (
            f"{d_id} supera capacidad: recibe {total} > {cap[d_id]}"
        )
    print("  [OK] Capacidad de centros respetada")


def test_balance_centros():
    sol = resolver()
    D = [d.id for d in CENTROS]
    for d in D:
        entrada = sum(v for (p, dd), v in sol["flujo_planta_cd"].items() if dd == d)
        salida  = sum(v for (dd, c), v in sol["flujo_cd_cliente"].items() if dd == d)
        assert abs(entrada - salida) < 1e-3, (
            f"Desbalance en {d}: entrada={entrada:.2f}, salida={salida:.2f}"
        )
    print("  [OK] Balance entrada=salida en todos los centros")


def test_demanda_con_deficit():
    sol = resolver()
    demanda = {c.id: c.demanda for c in CLIENTES}
    deficit = sol.get("deficit", {})
    for c_id, dem in demanda.items():
        recibido = sum(v for (d, cc), v in sol["flujo_cd_cliente"].items() if cc == c_id)
        def_ = deficit.get(c_id, 0)
        assert abs(recibido + def_ - dem) < 1e-3, (
            f"Demanda de {c_id} no cuadra: recibido={recibido}, déficit={def_}, demanda={dem}"
        )
    print("  [OK] Demanda satisfecha o compensada con déficit en todos los clientes")


def test_max_rutas():
    sol = resolver()
    n_rutas = len(sol["rutas_activas"])
    assert n_rutas <= MAX_RUTAS_ACTIVAS, (
        f"Rutas activas ({n_rutas}) supera el máximo ({MAX_RUTAS_ACTIVAS})"
    )
    print(f"  [OK] Rutas activas: {n_rutas} ≤ {MAX_RUTAS_ACTIVAS}")


def test_centros_abiertos_necesarios():
    sol = resolver()
    abiertos = set(sol["centros_abiertos"])
    usados   = {d for (d, c) in sol["rutas_activas"]}
    assert usados.issubset(abiertos), (
        f"Centros con rutas pero no abiertos: {usados - abiertos}"
    )
    print("  [OK] Solo centros abiertos tienen rutas activas")


def test_costo_positivo():
    sol = resolver()
    assert sol["costo_total"] > 0, "El costo total debe ser positivo"
    print(f"  [OK] Costo total: ${sol['costo_total']:,.2f}")


if __name__ == "__main__":
    tests = [
        test_estado_optimo,
        test_oferta_no_excedida,
        test_capacidad_centros,
        test_balance_centros,
        test_demanda_con_deficit,
        test_max_rutas,
        test_centros_abiertos_necesarios,
        test_costo_positivo,
    ]
    print("\n══════════════════════════════════════")
    print("  TESTS — Red de distribución MILP")
    print("══════════════════════════════════════")
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
    print("──────────────────────────────────────")
    if failed == 0:
        print(f"  Todos los tests pasaron ({len(tests)}/{len(tests)})")
    else:
        print(f"  {failed} test(s) fallaron")
    print("══════════════════════════════════════\n")
    