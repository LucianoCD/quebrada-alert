"""Persistencia DuckDB de lecturas externas y bitácora de sincronización."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import duckdb

from quebrada.fuentes.models import FuenteId, LecturaExterna, ResultadoSincronizacion

ESQUEMA = """
create table if not exists fuente_lectura (
    fuente varchar,
    estacion_id varchar,
    variable varchar,
    ts timestamptz,
    valor double,
    unidad varchar,
    origen varchar,
    lat double,
    lon double,
    meta json,
    recibido timestamptz default now(),
    primary key (fuente, estacion_id, variable, ts, origen)
);
create table if not exists fuente_sincronizacion (
    id bigint primary key,
    fuente varchar,
    iniciado timestamptz,
    finalizado timestamptz,
    estado varchar,
    nuevas integer,
    repetidas integer,
    detalle varchar
);
"""


class FuentesRepository:
    def __init__(self, db: duckdb.DuckDBPyConnection):
        self.db = db
        self.db.execute(ESQUEMA)
        self._id = self.db.execute("select coalesce(max(id), 0) from fuente_sincronizacion").fetchone()[0]

    def guardar_lecturas(self, lecturas: list[LecturaExterna]) -> tuple[int, int]:
        """Inserta lecturas nuevas. Devuelve (nuevas, repetidas)."""
        nuevas = repetidas = 0
        for lectura in lecturas:
            existe = self.db.execute(
                """
                select 1 from fuente_lectura
                where fuente = ? and estacion_id = ? and variable = ? and ts = ? and origen = ?
                """,
                [lectura.fuente.value, lectura.estacion_id, lectura.variable, lectura.ts, lectura.origen.value],
            ).fetchone()
            if existe:
                repetidas += 1
                continue
            self.db.execute(
                """
                insert into fuente_lectura
                (fuente, estacion_id, variable, ts, valor, unidad, origen, lat, lon, meta)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    lectura.fuente.value,
                    lectura.estacion_id,
                    lectura.variable,
                    lectura.ts,
                    lectura.valor,
                    lectura.unidad,
                    lectura.origen.value,
                    lectura.lat,
                    lectura.lon,
                    json.dumps(lectura.meta, ensure_ascii=False),
                ],
            )
            nuevas += 1
        return nuevas, repetidas

    def registrar_sincronizacion(self, resultado: ResultadoSincronizacion) -> ResultadoSincronizacion:
        self._id += 1
        self.db.execute(
            """
            insert into fuente_sincronizacion
            (id, fuente, iniciado, finalizado, estado, nuevas, repetidas, detalle)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                self._id,
                resultado.fuente.value,
                resultado.iniciado,
                resultado.finalizado or datetime.now(timezone.utc),
                resultado.estado,
                resultado.nuevas,
                resultado.repetidas,
                resultado.detalle,
            ],
        )
        return resultado

    def ultima_sincronizacion(self, fuente: FuenteId) -> ResultadoSincronizacion | None:
        fila = self.db.execute(
            """
            select fuente, iniciado, finalizado, estado, nuevas, repetidas, detalle
            from fuente_sincronizacion where fuente = ? order by id desc limit 1
            """,
            [fuente.value],
        ).fetchone()
        if not fila:
            return None
        return ResultadoSincronizacion(
            fuente=FuenteId(fila[0]),
            iniciado=fila[1],
            finalizado=fila[2],
            estado=fila[3],
            nuevas=fila[4],
            repetidas=fila[5],
            detalle=fila[6] or "",
        )

    def listar_sincronizaciones(self, limite: int = 50) -> list[ResultadoSincronizacion]:
        filas = self.db.execute(
            """
            select fuente, iniciado, finalizado, estado, nuevas, repetidas, detalle
            from fuente_sincronizacion order by id desc limit ?
            """,
            [limite],
        ).fetchall()
        return [
            ResultadoSincronizacion(
                fuente=FuenteId(f),
                iniciado=ini,
                finalizado=fin,
                estado=estado,
                nuevas=nuevas,
                repetidas=repetidas,
                detalle=detalle or "",
            )
            for f, ini, fin, estado, nuevas, repetidas, detalle in filas
        ]

    def listar_lecturas(
        self,
        fuente: FuenteId | None = None,
        estacion_id: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int = 2000,
    ) -> list[dict]:
        filtros = ["1=1"]
        params: list = []
        if fuente is not None:
            filtros.append("fuente = ?")
            params.append(fuente.value)
        if estacion_id:
            filtros.append("estacion_id = ?")
            params.append(estacion_id)
        if desde is not None:
            filtros.append("ts >= ?")
            params.append(desde)
        if hasta is not None:
            filtros.append("ts <= ?")
            params.append(hasta)
        params.append(limite)
        filas = self.db.execute(
            f"""
            select fuente, estacion_id, variable, ts, valor, unidad, origen, lat, lon, meta, recibido
            from fuente_lectura
            where {" and ".join(filtros)}
            order by ts desc
            limit ?
            """,
            params,
        ).fetchall()
        return [
            {
                "fuente": f,
                "estacion_id": est,
                "variable": var,
                "ts": ts.isoformat() if hasattr(ts, "isoformat") else ts,
                "valor": valor,
                "unidad": unidad,
                "origen": origen,
                "lat": lat,
                "lon": lon,
                "meta": json.loads(meta) if isinstance(meta, str) else meta,
                "recibido": rec.isoformat() if hasattr(rec, "isoformat") else rec,
            }
            for f, est, var, ts, valor, unidad, origen, lat, lon, meta, rec in filas
        ]

    def contar_lecturas(self, fuente: FuenteId | None = None) -> int:
        if fuente is None:
            return self.db.execute("select count(*) from fuente_lectura").fetchone()[0]
        return self.db.execute("select count(*) from fuente_lectura where fuente = ?", [fuente.value]).fetchone()[0]
