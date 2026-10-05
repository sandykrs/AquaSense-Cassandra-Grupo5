import os
import sys
import csv
import subprocess

CARPETA = os.path.dirname(os.path.abspath(__file__))
LOAD = os.path.join(CARPETA, "load_data.py")
RESULTADOS = os.path.join(CARPETA, "resultados_carga.csv")
LIMITE = 100_000

# (tamaño de batch, concurrencia, buffer)
CONFIGS = [
    (1,   32, 20_000),    # base: casi sin agrupar
    (10,  32, 20_000),
    (25,  32, 20_000),
    (50,  32, 20_000),    # configuración actual
    (100, 32, 20_000),
    (50,  32, 50_000),    # buffer más grande
    (50,  32, 100_000),
    (50,  16, 20_000),    # menos concurrencia
    (50,  64, 20_000),    # más concurrencia
    (50, 128, 20_000),
]


def correr(batch, conc, buf, limite):
    return subprocess.run(
        [sys.executable, LOAD, "--limit", str(limite), "--batch", str(batch),
         "--concurrency", str(conc), "--buffer", str(buf)],
        capture_output=True, text=True,
    )


if __name__ == "__main__":
    print("Calentamiento (no cuenta en el ranking)...")
    r = correr(50, 32, 20_000, 20_000)
    if r.returncode != 0:
        print(r.stderr)
        sys.exit("Falló el calentamiento. Revisá que Cassandra esté corriendo.")

    for i, (b, c, f) in enumerate(CONFIGS, 1):
        print(f"Prueba {i}/{len(CONFIGS)}: batch={b} concurrencia={c} buffer={f:,} ...")
        r = correr(b, c, f, LIMITE)
        if r.returncode != 0:
            print(r.stderr)
            sys.exit(f"Falló la prueba {i}.")

    with open(RESULTADOS, newline="", encoding="utf-8") as f:
        corridas = list(csv.DictReader(f))[-len(CONFIGS):]
    corridas.sort(key=lambda x: int(x["filas_por_seg"]), reverse=True)

    print("\n" + "=" * 62)
    print(f"{'batch':>6} {'concurr.':>9} {'buffer':>9} {'batches':>9} {'seg':>7} {'filas/s':>9}")
    print("=" * 62)
    for x in corridas:
        print(f"{x['tamano_batch']:>6} {x['concurrencia']:>9} "
              f"{int(x['tamano_buffer']):>9,} {int(x['batches']):>9,} "
              f"{x['segundos']:>7} {int(x['filas_por_seg']):>9,}")
    print("=" * 62)
    mejor = corridas[0]
    print(f"Mejor: batch={mejor['tamano_batch']} concurrencia={mejor['concurrencia']} "
          f"buffer={int(mejor['tamano_buffer']):,} ({int(mejor['filas_por_seg']):,} filas/s)")