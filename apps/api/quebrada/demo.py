"""Levanta la demo completa en una máquina: el backend y un proceso por estación simulada.

python -m quebrada.demo
"""

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from quebrada import cuencas


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--puerto", type=int, default=8000)
    p.add_argument("--escala", type=float, default=60.0, help="segundos simulados por segundo real")
    p.add_argument("--dir", default="var")
    p.add_argument("--conservar", action="store_true", help="no borrar los datos de la corrida anterior")
    a = p.parse_args()

    carpeta = Path(a.dir)
    if carpeta.exists() and not a.conservar:
        shutil.rmtree(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)

    nodos = {c.node_id: (c.basin_id, a.puerto + 101 + i) for i, c in enumerate(cuencas.cargar().values())}
    entorno = {
        **os.environ,
        "QUEBRADA_DB": str(carpeta / "central.duckdb"),
        "QUEBRADA_NODOS": ",".join(f"{n}={puerto}" for n, (_, puerto) in nodos.items()),
    }
    procesos = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "quebrada.backend.app:app",
                "--port",
                str(a.puerto),
                "--log-level",
                "warning",
            ],  # fmt: skip
            env=entorno,
        )
    ]
    for _ in range(100):  # los nodos arrancan cuando el backend ya escucha
        with socket.socket() as conexion:
            if conexion.connect_ex(("127.0.0.1", a.puerto)) == 0:
                break
        time.sleep(0.1)
    for node_id, (basin_id, puerto) in nodos.items():
        procesos.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "quebrada.edge.proceso",
                    "--node",
                    node_id,
                    "--basin",
                    basin_id,
                    "--puerto",
                    str(puerto),
                    "--backend",
                    f"http://127.0.0.1:{a.puerto}",
                    "--escala",
                    str(a.escala),
                    "--dir",
                    str(carpeta),
                ]  # fmt: skip
            )
        )
    print(f"Tablero: http://127.0.0.1:{a.puerto}  (Ctrl+C para detener)")
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        procesos[0].wait()
    except KeyboardInterrupt:
        pass
    finally:
        for proceso in procesos:
            proceso.terminate()
        for proceso in procesos:
            try:
                proceso.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait()


if __name__ == "__main__":
    main()
