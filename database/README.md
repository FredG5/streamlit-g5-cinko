# Migración a PostgreSQL — Grupo Cinko

## Paso 1 — Crear cuenta en Neon

1. Ir a [neon.tech](https://neon.tech) → **Start for free**
2. Crear un proyecto (ej. `cinko-financieros`)
3. En el dashboard del proyecto, copiar la **Connection string** (formato pooled):
   ```
   postgresql://usuario:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

## Paso 2 — Crear el esquema

En el **SQL Editor** de Neon (o con cualquier cliente Postgres), ejecutar:

```sql
-- Pegar el contenido completo de database/schema.sql
```

O desde la terminal:
```powershell
$env:DATABASE_URL = "postgresql://..."
psql $env:DATABASE_URL -f database/schema.sql
```

## Paso 3 — Configurar la connection string en la app

Agregar en `.streamlit/secrets.toml` (antes de cualquier `[sección]`):

```toml
DATABASE_URL = "postgresql://usuario:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require"
```

Para Streamlit Cloud: en **Settings → Secrets** del proyecto, agregar la misma línea.

## Paso 4 — Correr la migración

```powershell
# Desde la raíz del proyecto
$env:DATABASE_URL = "postgresql://..."
python database/migrate.py
```

Salida esperada:
```
=======================================================
  Migración Grupo Cinko: Excel → PostgreSQL
=======================================================

Leyendo archivos Excel...
  Financieros: X,XXX filas | años: [2024, 2025]
  Catálogo:    XXX cuentas

Conectando a PostgreSQL...
  Conexión exitosa.

Migrando catálogo de cuentas...
  XXX cuentas insertadas/actualizadas.
Migrando movimientos financieros...
  X,XXX movimientos insertados/actualizados.

✅ Migración completada exitosamente.
```

La migración es **idempotente** — puede correrse múltiples veces sin duplicar datos.

## Paso 5 — Activar el modo PostgreSQL

En `utils/data.py`, cambiar la línea:

```python
DATA_SOURCE = "excel"
```
por:
```python
DATA_SOURCE = "postgres"
```

Reiniciar la app (`streamlit run app.py`). Los 4 tabs deben mostrar exactamente los mismos números que con Excel.

## Verificación

Ejecutar la app con ambos modos y comparar:
- Estado de Resultados — KPIs y tabla mensual
- Flujo de Efectivo — saldo inicial/final cuadra
- Balance General — Total Activos = Total Pasivos + Capital Contable
- Balance Analítico — mismo desglose N2/N3

## Actualizar datos

Cuando haya nuevos datos en Excel, volver a correr `migrate.py`. El UPSERT actualiza los registros existentes y agrega los nuevos. La app refresca la caché de postgres cada hora (`ttl=3600`); para forzar el refresco inmediato, reiniciar la app.

## Seguridad — usuario de solo lectura

El usuario de PostgreSQL que usa la app en producción **SOLO debe tener permisos SELECT**. Nunca usar el usuario administrador en la connection string de la app.

En Neon (o cualquier Postgres), crear un usuario de lectura:

```sql
-- Ejecutar como administrador
CREATE USER cinko_readonly WITH PASSWORD 'password_seguro';
GRANT CONNECT ON DATABASE neondb TO cinko_readonly;
GRANT USAGE ON SCHEMA public TO cinko_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO cinko_readonly;
-- Para tablas futuras:
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO cinko_readonly;
```

Luego usar la connection string de `cinko_readonly` en `.streamlit/secrets.toml` y Streamlit Cloud.

La validación de SQL en `utils/ai_chat.py` (`execute_safe_query`) es una capa adicional de defensa: verifica que la query sea SELECT y rechaza keywords de escritura/DDL. Nunca se expone el SQL generado al usuario final — solo la respuesta interpretada en lenguaje natural.

## Estructura de tablas

| Tabla | Filas aprox. | Descripción |
|---|---|---|
| `catalogo_cuentas` | ~500 | Jerarquía N1→N5 de cuentas contables |
| `movimientos` | ~6,000–12,000 | Movimientos mensuales por cuenta y año |
