from solver import resolver
from report import imprimir
from plot import graficar

if __name__ == "__main__":
    solucion = resolver()
    imprimir(solucion)
    graficar(solucion, guardar_como="red_logistica.png")
    