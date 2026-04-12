# Medidas DAX – RetailMax Dashboard

Crear estas medidas en Power BI Desktop dentro de la tabla `fact_ventas` o en una
tabla de medidas dedicada.

## Ventas

```dax
-- Ventas Netas
Ventas Netas = SUM(fact_ventas[net_amount])

-- Ventas Brutas
Ventas Brutas = SUM(fact_ventas[gross_amount])

-- Total Transacciones
Total Transacciones = COUNTROWS(fact_ventas)

-- Clientes Unicos
Clientes Unicos = DISTINCTCOUNT(fact_ventas[customer_id])

-- Ticket Promedio
Ticket Promedio =
    DIVIDE([Ventas Netas], [Total Transacciones], 0)

-- Descuento Promedio (%)
Descuento Promedio =
    DIVIDE(
        SUM(fact_ventas[discount_value]),
        SUM(fact_ventas[gross_amount]),
        0
    )

-- % Ventas con Descuento
Pct Ventas Descuento =
    DIVIDE(
        CALCULATE(COUNTROWS(fact_ventas), fact_ventas[ind_con_descuento] = 1),
        COUNTROWS(fact_ventas),
        0
    )

-- Ventas Netas MoM (%)
Ventas MoM =
    VAR _actual = [Ventas Netas]
    VAR _anterior = CALCULATE([Ventas Netas], DATEADD('fact_ventas'[sale_date], -1, MONTH))
    RETURN DIVIDE(_actual - _anterior, _anterior, 0)
```

## Inventario

```dax
-- Stock Disponible Total
Stock Disponible = SUM(fact_inventario[available_stock])

-- Productos en Alerta Quiebre
Productos Alerta Quiebre =
    CALCULATE(
        DISTINCTCOUNT(fact_inventario[product_id]),
        fact_inventario[alerta_quiebre] = 1
    )

-- Cobertura Promedio (dias)
Cobertura Promedio =
    AVERAGE(fact_inventario[cobertura_dias])

-- % Productos en Riesgo
Pct Productos Riesgo =
    DIVIDE([Productos Alerta Quiebre], DISTINCTCOUNT(fact_inventario[product_id]), 0)
```

## Devoluciones

```dax
-- Total Devoluciones
Total Devoluciones = COUNTROWS(fact_devoluciones)

-- Monto Reembolsado
Monto Reembolsado = SUM(fact_devoluciones[refund_amount])

-- Tasa de Devolucion Global
Tasa Devolucion =
    DIVIDE(
        SUM(fact_devoluciones[quantity_returned]),
        SUM(fact_ventas[quantity_sold]),
        0
    )
```

## Clientes RFM

```dax
-- Total Clientes Activos 90d
Clientes Activos 90d =
    CALCULATE(
        COUNTROWS(fact_rfm_clientes),
        fact_rfm_clientes[status_90d] = "active_90d"
    )

-- % Champions
Pct Champions =
    DIVIDE(
        CALCULATE(COUNTROWS(fact_rfm_clientes), fact_rfm_clientes[rfm_classification] = "Champions"),
        COUNTROWS(fact_rfm_clientes),
        0
    )

-- % At Risk
Pct At Risk =
    DIVIDE(
        CALCULATE(COUNTROWS(fact_rfm_clientes), fact_rfm_clientes[rfm_classification] = "At_Risk"),
        COUNTROWS(fact_rfm_clientes),
        0
    )

-- Valor Monetario Promedio
Valor Monetario Promedio =
    AVERAGE(fact_rfm_clientes[monetary_value])
```

## KPI Ejecutivo (medidas sobre la vista agregada)

```dax
-- Ventas Netas KPI
KPI Ventas Netas = SUM(kpi_ejecutivo[ventas_netas])

-- KPI Transacciones
KPI Transacciones = SUM(kpi_ejecutivo[total_transacciones])

-- KPI Clientes Unicos
KPI Clientes = SUM(kpi_ejecutivo[clientes_unicos])

-- KPI Unidades
KPI Unidades = SUM(kpi_ejecutivo[unidades_vendidas])
```
