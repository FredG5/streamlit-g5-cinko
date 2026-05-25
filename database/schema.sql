-- Esquema PostgreSQL — Grupo Cinko Financieros
-- Ejecutar una sola vez en la base de datos de Neon (o cualquier PostgreSQL)

CREATE TABLE IF NOT EXISTS catalogo_cuentas (
    n5_cuenta   VARCHAR(20)  PRIMARY KEY,
    n5_nombre   VARCHAR(255),
    n4_cuenta   VARCHAR(20),
    n4_nombre   VARCHAR(255),
    n3_cuenta   VARCHAR(20),
    n3_nombre   VARCHAR(255),
    n2_cuenta   VARCHAR(20),
    n2_nombre   VARCHAR(255),
    n1_cuenta   VARCHAR(20),
    n1_nombre   VARCHAR(255),
    -- Corresponde a la columna "Resultaods/Balance" del Excel (typo intencional)
    tipo_cuenta VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS movimientos (
    id                    SERIAL PRIMARY KEY,
    año                   INTEGER      NOT NULL,
    mes                   INTEGER      NOT NULL CHECK (mes BETWEEN 1 AND 12),
    n5_cuenta             VARCHAR(20)  NOT NULL REFERENCES catalogo_cuentas(n5_cuenta),
    -- "Saldo Movimientos del Mes OK" — movimiento mensual (P&L usa esta columna)
    saldo_movimientos_mes NUMERIC(18, 2) NOT NULL DEFAULT 0,
    -- "Saldo Final de Mes OK" — saldo de cierre (Balance General usa esta columna)
    saldo_final_mes       NUMERIC(18, 2) NOT NULL DEFAULT 0,
    -- "Saldo Inicial de Mes OK" — saldo de apertura (Flujo de Efectivo lo usa para efectivo N3=110-000)
    saldo_inicial_mes     NUMERIC(18, 2) NOT NULL DEFAULT 0,
    UNIQUE (año, mes, n5_cuenta)
);

CREATE INDEX IF NOT EXISTS idx_mov_año_mes      ON movimientos (año, mes);
CREATE INDEX IF NOT EXISTS idx_mov_n5_cuenta    ON movimientos (n5_cuenta);
