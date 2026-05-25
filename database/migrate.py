#!/usr/bin/env python3
"""
Migra los datos de Excel a PostgreSQL (Neon o cualquier Postgres).
Idempotente: usa UPSERT — correrlo dos veces no duplica datos.

Uso:
    # Opción A: variable de entorno
    $env:DATABASE_URL = "postgresql://user:pass@host/db?sslmode=require"
    python database/migrate.py

    # Opción B: secrets.toml ya configurado (lee via streamlit)
    python database/migrate.py
"""

import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2

_ROOT = Path(__file__).parent.parent


def get_conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            import streamlit as st
            url = st.secrets.get("DATABASE_URL", "")
        except Exception:
            pass
    if not url:
        print("ERROR: DATABASE_URL no está configurada.")
        print("  Opción A: $env:DATABASE_URL = 'postgresql://...'")
        print("  Opción B: agregar DATABASE_URL en .streamlit/secrets.toml")
        sys.exit(1)
    return psycopg2.connect(url)


def _str(val):
    if pd.isna(val):
        return ""
    return str(val).strip()


def _num(val):
    if pd.isna(val):
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def migrate_catalogo(conn, cat_df):
    print("Migrando catálogo de cuentas...")
    cur = conn.cursor()

    rows = []
    for _, row in cat_df.iterrows():
        n5 = _str(row.get("N5 Cuenta", ""))
        if not n5:
            continue
        rows.append((
            n5,
            _str(row.get("N5 Nombre Cuenta", n5)),
            _str(row.get("N4 Cuenta", "")),
            _str(row.get("N4 Nombre Cuenta", "")),
            _str(row.get("N3 Cuenta", "")),
            _str(row.get("N3 Nombre Cuenta", "")),
            _str(row.get("N2 Cuenta", "")),
            _str(row.get("N2 Nombre Cuenta", "")),
            _str(row.get("N1 Cuenta", "")),
            _str(row.get("N1 Nombre Cuenta", "")),
            _str(row.get("Resultaods/Balance", "")),
        ))

    cur.executemany("""
        INSERT INTO catalogo_cuentas
            (n5_cuenta, n5_nombre, n4_cuenta, n4_nombre, n3_cuenta, n3_nombre,
             n2_cuenta, n2_nombre, n1_cuenta, n1_nombre, tipo_cuenta)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (n5_cuenta) DO UPDATE SET
            n5_nombre   = EXCLUDED.n5_nombre,
            n4_cuenta   = EXCLUDED.n4_cuenta,
            n4_nombre   = EXCLUDED.n4_nombre,
            n3_cuenta   = EXCLUDED.n3_cuenta,
            n3_nombre   = EXCLUDED.n3_nombre,
            n2_cuenta   = EXCLUDED.n2_cuenta,
            n2_nombre   = EXCLUDED.n2_nombre,
            n1_cuenta   = EXCLUDED.n1_cuenta,
            n1_nombre   = EXCLUDED.n1_nombre,
            tipo_cuenta = EXCLUDED.tipo_cuenta
    """, rows)

    conn.commit()
    print(f"  {len(rows)} cuentas insertadas/actualizadas.")


def migrate_movimientos(conn, fin_df):
    print("Migrando movimientos financieros...")
    cur = conn.cursor()

    rows = []
    skipped = 0
    for _, row in fin_df.iterrows():
        n5 = _str(row.get("N5 Cuenta", ""))
        if not n5:
            skipped += 1
            continue
        rows.append((
            int(row["Año"]),
            int(row["Mes"]),
            n5,
            _num(row.get("Saldo Movimientos del Mes OK", 0)),
            _num(row.get("Saldo Final de Mes OK", 0)),
            _num(row.get("Saldo Inicial de Mes OK", 0)),
        ))

    cur.executemany("""
        INSERT INTO movimientos
            (año, mes, n5_cuenta, saldo_movimientos_mes, saldo_final_mes, saldo_inicial_mes)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (año, mes, n5_cuenta) DO UPDATE SET
            saldo_movimientos_mes = EXCLUDED.saldo_movimientos_mes,
            saldo_final_mes       = EXCLUDED.saldo_final_mes,
            saldo_inicial_mes     = EXCLUDED.saldo_inicial_mes
    """, rows)

    conn.commit()
    print(f"  {len(rows)} movimientos insertados/actualizados. {skipped} filas sin N5 omitidas.")


def main():
    print("=" * 55)
    print("  Migración Grupo Cinko: Excel → PostgreSQL")
    print("=" * 55)

    print("\nLeyendo archivos Excel...")
    fin_df = pd.read_excel(_ROOT / "data" / "Tabla_Financieros_G5.xlsx", sheet_name="Financieros")
    cat_df = pd.read_excel(_ROOT / "data" / "CatCuentas_G5.xlsx",        sheet_name="Cuentas")
    print(f"  Financieros: {len(fin_df):,} filas | años: {sorted(fin_df['Año'].unique())}")
    print(f"  Catálogo:    {len(cat_df):,} cuentas")

    print("\nConectando a PostgreSQL...")
    conn = get_conn()
    print("  Conexión exitosa.")

    try:
        print()
        migrate_catalogo(conn, cat_df)
        migrate_movimientos(conn, fin_df)
        print("\n✅ Migración completada exitosamente.")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
