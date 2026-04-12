# Linaje de Datos — RetailMax

**Fase 5 — Escenario B: Retail y Comercio Electrónico**  
Fecha: Abril 12, 2026

---

## Flujo General

```mermaid
flowchart LR
    subgraph ORIGEN["Azure SQL Database"]
        T1[MSTR_ARTICULOS]
        T2[MSTR_TIENDAS]
        T3[MSTR_PROVEEDORES]
        T4[CRM_MIEMBROS]
        T5[TRANS_VENTAS]
        T6[INV_STOCK_DIARIO]
        T7[POST_DEVOLUCIONES]
    end

    subgraph BRONZE["Bronze — Storage"]
        B1[MSTR_ARTICULOS.parquet]
        B2[MSTR_TIENDAS.parquet]
        B3[MSTR_PROVEEDORES.parquet]
        B4[CRM_MIEMBROS.parquet]
        B5[TRANS_VENTAS.parquet]
        B6[INV_STOCK_DIARIO.parquet]
        B7[POST_DEVOLUCIONES.parquet]
    end

    subgraph SILVER["Silver — Storage"]
        S1[MSTR_ARTICULOS_clean.parquet]
        S2[MSTR_TIENDAS_clean.parquet]
        S3[MSTR_PROVEEDORES_clean.parquet]
        S4[CRM_MIEMBROS_clean.parquet]
        S5[TRANS_VENTAS_clean.parquet]
        S6[INV_STOCK_DIARIO_clean.parquet]
        S7[POST_DEVOLUCIONES_clean.parquet]
    end

    subgraph GOLD["Gold — Vistas SQL + Storage"]
        G1[dim_productos]
        G2[dim_tiendas]
        G3[dim_clientes]
        G4[fact_ventas]
        G5[fact_inventario]
        G6[fact_devoluciones]
        G7[fact_rfm_clientes]
        G8[kpi_ejecutivo]
    end

    T1 -->|PL_Ingesta_Bronze| B1
    T2 -->|PL_Ingesta_Bronze| B2
    T3 -->|PL_Ingesta_Bronze| B3
    T4 -->|PL_Ingesta_Bronze| B4
    T5 -->|PL_Ingesta_Bronze| B5
    T6 -->|PL_Ingesta_Bronze| B6
    T7 -->|PL_Ingesta_Bronze| B7

    B1 -->|PL_Limpieza_Silver| S1
    B2 -->|PL_Limpieza_Silver| S2
    B3 -->|PL_Limpieza_Silver| S3
    B4 -->|PL_Limpieza_Silver| S4
    B5 -->|PL_Limpieza_Silver| S5
    B6 -->|PL_Limpieza_Silver| S6
    B7 -->|PL_Limpieza_Silver| S7

    S1 -->|PL_Vistas_Gold| G1
    S3 -->|PL_Vistas_Gold| G1
    S2 -->|PL_Vistas_Gold| G2
    S4 -->|PL_Vistas_Gold| G3
    S5 -->|PL_Vistas_Gold| G4
    S5 -->|PL_Vistas_Gold| G5
    S6 -->|PL_Vistas_Gold| G5
    S5 -->|PL_Vistas_Gold| G6
    S7 -->|PL_Vistas_Gold| G6
    S4 -->|PL_Vistas_Gold| G7
    S5 -->|PL_Vistas_Gold| G7
    S5 -->|PL_Vistas_Gold| G8
    S2 -->|PL_Vistas_Gold| G8
```

---

## Detalle por Vista Gold

### dim_productos
| Campo calculado | Tablas origen | Regla de negocio |
|---|---|---|
| `supplier_name` | `MSTR_ARTICULOS` + `MSTR_PROVEEDORES` | LEFT JOIN por `id_proveedor` |
| `supplier_quality_score` | `MSTR_PROVEEDORES` | Directo de la fuente |
| `estimated_margin` | `MSTR_ARTICULOS` | `precio_lista * 0.30` |

### dim_tiendas
| Campo calculado | Tablas origen | Regla de negocio |
|---|---|---|
| `zona_distribucion` | `MSTR_TIENDAS` | `CASE id_pais % 5` → Norte/Sur/Este/Oeste/Centro |

### dim_clientes
| Campo calculado | Tablas origen | Regla de negocio |
|---|---|---|
| `gender` | `CRM_MIEMBROS` | Estandarización: O/NULL → `No_informado` |
| `age_range` | `CRM_MIEMBROS` | Imputación de nulos con moda por `canal_pref` |
| `antiguedad_dias` | `CRM_MIEMBROS` | `DATEDIFF(DAY, fec_registro, GETDATE())` |

### fact_ventas
| Campo calculado | Tablas origen | Regla de negocio |
|---|---|---|
| `customer_id` | `TRANS_VENTAS` | `COALESCE(id_miembro, 'ANONIMO')` |
| `gross_amount` | `TRANS_VENTAS` | `qty_vendida * precio_unitario_venta` |
| `net_amount` | `TRANS_VENTAS` | `gross_amount - descuento_aplicado` |
| `ind_con_descuento` | `TRANS_VENTAS` | `1` si `descuento > 0`, `0` si no |

### fact_inventario
| Campo calculado | Tablas origen | Regla de negocio |
|---|---|---|
| `avg_daily_sales_14d` | `INV_STOCK_DIARIO` + `TRANS_VENTAS` | CTE ventas últimos 14 días / 14 |
| `cobertura_dias` | Calculado | `stock_fisico / avg_daily_sales_14d` |
| `alerta_quiebre` | Calculado | `1` si cobertura < 7 días con demanda activa |

### fact_devoluciones
| Campo calculado | Tablas origen | Regla de negocio |
|---|---|---|
| `original_unit_price` | `POST_DEVOLUCIONES` + `TRANS_VENTAS` | JOIN por `id_trans_origen` |
| `return_rate_by_product` | Calculado | CTE: `SUM(devueltas) / SUM(vendidas)` por artículo |

### fact_rfm_clientes
| Campo calculado | Tablas origen | Regla de negocio |
|---|---|---|
| `recency_days` | `CRM_MIEMBROS` + `TRANS_VENTAS` | `DATEDIFF` desde última compra (ventana 90 días) |
| `frequency_purchases` | `TRANS_VENTAS` | `COUNT(DISTINCT id_trans)` en 90 días |
| `monetary_value` | `TRANS_VENTAS` | `SUM(qty * precio - descuento)` en 90 días |
| `r_score`, `f_score`, `m_score` | Calculado | `NTILE(5)` sobre cada métrica |
| `rfm_segment` | Calculado | Concatenación `R#-F#-M#` |
| `rfm_classification` | Calculado | Champions / Loyal / At_Risk / Other |

### kpi_ejecutivo
| Campo calculado | Tablas origen | Regla de negocio |
|---|---|---|
| `total_transacciones` | `TRANS_VENTAS` + `MSTR_TIENDAS` | `COUNT(DISTINCT id_trans)` por fecha/país/canal |
| `clientes_unicos` | `TRANS_VENTAS` | `COUNT(DISTINCT id_miembro)` |
| `ventas_brutas` | `TRANS_VENTAS` | `SUM(qty * precio)` |
| `ventas_netas` | `TRANS_VENTAS` | `SUM(qty * precio - descuento)` |

---

## Trazabilidad de Ejecución

| Tabla SQL | Propósito |
|---|---|
| `pipeline_quality_report` | Registro de métricas por tabla: filas leídas, limpias, duplicados, nulos, estado |
| `pipeline_errors` | Registro de errores individuales con timestamp y detalle |

---

## Cadena de Orquestación

```mermaid
flowchart TD
    TRIGGER["Trigger_Diario_0200\n02:00 AM UTC"] --> MASTER["PL_Orquestador_Maestro"]
    MASTER --> BRONZE["PL_Ingesta_Bronze\n7 tablas → Parquet bronze/"]
    BRONZE -->|Succeeded| SILVER["PL_Limpieza_Silver\nSELECT DISTINCT + métricas calidad"]
    SILVER -->|Succeeded| GOLD["PL_Vistas_Gold\n8 vistas SQL + export Parquet gold/"]
    GOLD -->|Succeeded| CALIDAD["PL_Calidad_Datos\nConsulta pipeline_quality_report + errors"]
    CALIDAD -->|Completado| FIN["Pipeline completado ✓"]
    BRONZE -->|Failed| ALERTA["Action Group → Email de alerta"]
    SILVER -->|Failed| ALERTA
    GOLD -->|Failed| ALERTA
```
