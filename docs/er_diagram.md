# Diagrama Entidad-Relación - RetailMax

**Fase 1 - Escenario B: Retail & E-commerce**
Fecha: Abril 9, 2026

## Diagrama ER (Mermaid)

```mermaid
erDiagram
    MSTR_PROVEEDORES {
        int id_proveedor PK
        string razon_social
        string pais_origen
        int tiempo_repo_dias
        float calificacion_calidad
        int activo
    }

    MSTR_TIENDAS {
        int id_tienda PK
        string nom_tienda
        string tipo_tienda
        int id_ciudad
        int id_pais
        int metros_cuadrados
        int activo
        date fec_apertura
    }

    MSTR_ARTICULOS {
        int art_id PK
        string cod_barra
        string desc_art
        int id_categ_n1
        int id_categ_n2
        int id_categ_n3
        int id_proveedor FK
        float precio_lista
        float peso_kg
        string unid_medida
        int activo
        datetime fec_alta
    }

    CRM_MIEMBROS {
        int id_miembro PK
        date fec_registro
        int id_ciudad
        string genero
        string rango_edad
        string canal_pref
        int activo
        date fec_ultima_compra
    }

    TRANS_VENTAS {
        int id_trans PK
        int id_miembro FK
        int id_tienda FK
        int art_id FK
        date fec_trans
        string hra_trans
        int qty_vendida
        float precio_unitario_venta
        float descuento_aplicado
        string tipo_pago
        string canal_venta
    }

    INV_STOCK_DIARIO {
        int id_snapshot PK
        int art_id FK
        int id_tienda FK
        date fec_snapshot
        int stock_fisico
        int stock_transito
        int stock_reservado
        int stock_minimo_config
        int stock_maximo_config
    }

    POST_DEVOLUCIONES {
        int id_devolucion PK
        int id_trans_origen FK
        int art_id FK
        int id_tienda FK
        date fec_devolucion
        int qty_devuelta
        string motivo_cod
        string canal_devolucion
        string estado_devolucion
        float vr_reembolso
    }

    MSTR_ARTICULOS ||--o{ TRANS_VENTAS         : "art_id"
    MSTR_TIENDAS   ||--o{ TRANS_VENTAS         : "id_tienda"
    CRM_MIEMBROS   ||--o{ TRANS_VENTAS         : "id_miembro"
    MSTR_PROVEEDORES ||--o{ MSTR_ARTICULOS     : "id_proveedor"
    MSTR_ARTICULOS ||--o{ INV_STOCK_DIARIO     : "art_id"
    MSTR_TIENDAS   ||--o{ INV_STOCK_DIARIO     : "id_tienda"
    TRANS_VENTAS   ||--o{ POST_DEVOLUCIONES    : "id_trans_origen"
    MSTR_ARTICULOS ||--o{ POST_DEVOLUCIONES    : "art_id"
    MSTR_TIENDAS   ||--o{ POST_DEVOLUCIONES    : "id_tienda"
```

## Descripción de tablas

### Tablas Maestras (MSTR)

| Tabla | Registros | Descripción |
|---|---|---|
| `MSTR_PROVEEDORES` | 800 | Proveedores de productos. Incluye calificación de calidad y tiempo de reposición |
| `MSTR_TIENDAS` | 150 | Tiendas físicas y online. Clasificadas por tipo (Hipermercado, Supermercado, Conveniencia) |
| `MSTR_ARTICULOS` | 5 000 | Catálogo de artículos con jerarquía de categorías (3 niveles) y vínculo al proveedor |

### Tablas Transaccionales (TRANS / POST)

| Tabla | Registros | Descripción |
|---|---|---|
| `TRANS_VENTAS` | 1 000 000 | Todas las transacciones de venta. Tabla central del modelo |
| `POST_DEVOLUCIONES` | 50 000 | Devoluciones vinculadas a transacciones origen |

### Tabla CRM

| Tabla | Registros | Descripción |
|---|---|---|
| `CRM_MIEMBROS` | 50 000 | Clientes del programa de fidelización |

### Tabla de Inventario (INV)

| Tabla | Registros | Descripción |
|---|---|---|
| `INV_STOCK_DIARIO` | 750 000 | Snapshot diario de inventario por artículo y tienda |

## Anomalías intencionales en los datos

Los datos incluyen las siguientes anomalías documentadas para validar la robustez de los pipelines:

| Tipo | Tasa | Descripción |
|---|---|---|
| Duplicados exactos | 0.1% | Registros duplicados íntegros |
| Valores nulos | 5% | Nulos en columnas de texto |
| Valores fuera de rango | 0.1% | Outliers numéricos extremos |
| Violaciones de FK | 0.5% | Referencias a IDs inexistentes |

## Relaciones principales

- **TRANS_VENTAS** es la tabla central: referencia artículo, tienda y miembro
- **MSTR_ARTICULOS** está vinculada al proveedor por `id_proveedor`
- **POST_DEVOLUCIONES** referencia la transacción origen por `id_trans_origen`
- **INV_STOCK_DIARIO** captura el inventario diario cruzando artículo y tienda
