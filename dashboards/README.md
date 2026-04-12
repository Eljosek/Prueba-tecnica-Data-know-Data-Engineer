# Dashboard Power BI – RetailMax Gold Layer

## Conexion a Azure SQL

Power BI Desktop (gratuito) se conecta directamente a las **8 vistas Gold** de
`sqldb-retailmax-brs-dev`.

### Requisitos

| Componente | Version minima |
|---|---|
| Power BI Desktop | Marzo 2024+ |
| Driver ODBC SQL Server | 18 |
| Acceso de red | Puerto 1433 al SQL Server de Azure |

### Pasos de conexion

1. Abrir **Power BI Desktop** → **Obtener datos** → **Azure SQL Database**.
2. Servidor: `sqlsrv-retailmax-brs-dev.database.windows.net`
3. Base de datos: `sqldb-retailmax-brs-dev`
4. Modo de conectividad: **Import** (recomendado para desarrollo; DirectQuery para produccion).
5. Autenticacion: **SQL Server** con usuario `sqladmin` o **Azure Active Directory** si se
   configuro.
6. En el navegador, seleccionar las 8 vistas:
   - `dim_productos`
   - `dim_tiendas`
   - `dim_clientes`
   - `fact_ventas`
   - `fact_inventario`
   - `fact_devoluciones`
   - `fact_rfm_clientes`
   - `kpi_ejecutivo`
7. Hacer clic en **Transformar datos** para validar en Power Query, luego **Cerrar y aplicar**.

### Modelo de datos (relaciones)

Configurar las relaciones en la vista **Modelo** de Power BI:

| Origen | Columna | Destino | Columna | Cardinalidad |
|---|---|---|---|---|
| `fact_ventas` | `product_id` | `dim_productos` | `product_id` | Muchos a uno |
| `fact_ventas` | `store_id` | `dim_tiendas` | `store_id` | Muchos a uno |
| `fact_ventas` | `customer_id` | `dim_clientes` | `customer_id` | Muchos a uno |
| `fact_inventario` | `product_id` | `dim_productos` | `product_id` | Muchos a uno |
| `fact_inventario` | `store_id` | `dim_tiendas` | `store_id` | Muchos a uno |
| `fact_devoluciones` | `product_id` | `dim_productos` | `product_id` | Muchos a uno |
| `fact_devoluciones` | `store_id` | `dim_tiendas` | `store_id` | Muchos a uno |
| `fact_rfm_clientes` | `customer_id` | `dim_clientes` | `customer_id` | Muchos a uno |

> **Nota:** `kpi_ejecutivo` es una vista agregada; se conecta a `dim_tiendas` via
> `country_id` para filtrado por pais.

### Medidas DAX sugeridas

Ver archivo [`dax_measures.md`](dax_measures.md) con las medidas clave del dashboard.

### Paginas del dashboard

| Pagina | Contenido principal |
|---|---|
| **Resumen Ejecutivo** | KPIs: ventas netas, transacciones, clientes unicos, ticket promedio. Grafico de tendencia diaria desde `kpi_ejecutivo`. |
| **Analisis de Ventas** | Ventas por canal, por pais, por categoria. Top 10 productos. Segmentacion con/sin descuento. |
| **Inventario** | Productos con alerta de quiebre, cobertura promedio por categoria, stock disponible vs reservado. |
| **Devoluciones** | Tasa de devolucion por producto y categoria, motivos principales, tendencia mensual. |
| **Clientes RFM** | Distribucion de segmentos RFM, clasificacion Champions/Loyal/At_Risk, clientes activos vs inactivos. |

### Paleta de colores sugerida

- Primario: `#2E86AB` (azul corporativo)
- Secundario: `#A23B72` (magenta)
- Acento: `#F18F01` (naranja)
- Positivo: `#2CA02C` (verde)
- Negativo: `#D62728` (rojo)
- Fondo: `#F5F5F5` (gris claro)
