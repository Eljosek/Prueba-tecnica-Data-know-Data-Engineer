"""
Script de Generación de Datos Sintéticos - Escenario B Retail
Autor: Equipo Prueba Técnica
Fecha: Abril 8, 2026
Descripción: Genera 7 tablas con datos realistas para RetailMax
"""

import os
import yaml
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from faker import Faker
import logging
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==============================================================================
# PARTE 1: CARGA DE CONFIGURACIÓN
# ==============================================================================

def cargar_configuracion(config_path: str) -> dict:
    """
    Lee el archivo config.yaml y retorna la configuración
    
    Args:
        config_path: Ruta al archivo config.yaml
        
    Returns:
        dict: Configuración cargada
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuración cargada exitosamente desde {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"archivo {config_path} no encontrado")
        raise

def crear_directorio_salida(config: dict) -> str:
    """
    Crea el directorio de salida si no existe
    
    Args:
        config: Configuración cargada
        
    Returns:
        str: Ruta del directorio de salida
    """
    output_path = config.get('output_path', 'data-generation/output')
    Path(output_path).mkdir(parents=True, exist_ok=True)
    logger.info(f"Directorio de salida: {output_path}")
    return output_path

# ==============================================================================
# PARTE 2: GENERADORES DE TABLAS MAESTRAS
# ==============================================================================

def generar_mstr_proveedores(n_registros: int, seed: int, paises: list) -> pd.DataFrame:
    """
    Genera tabla MSTR_PROVEEDORES con datos realistas
    """
    np.random.seed(seed)
    fake = Faker()
    
    data = {
        'id_proveedor': range(1, n_registros + 1),
        'razon_social': [fake.company() for _ in range(n_registros)],
        'pais_origen': np.random.choice(paises, n_registros),
        'tiempo_repo_dias': np.random.randint(1, 30, n_registros),
        'calificacion_calidad': np.random.uniform(3.0, 5.0, n_registros).round(2),
        'activo': np.random.choice([0, 1], n_registros, p=[0.1, 0.9])
    }
    
    df = pd.DataFrame(data)
    logger.info(f"✓ MSTR_PROVEEDORES: {len(df)} registros generados")
    return df

def generar_mstr_tiendas(n_registros: int, seed: int, paises: list) -> pd.DataFrame:
    """
    Genera tabla MSTR_TIENDAS con datos realistas
    """
    np.random.seed(seed)
    fake = Faker()
    
    tipos_tienda = ['Hipermercado', 'Supermercado', 'Tienda Conveniencia']
    ciudades = ['Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Cartagena']
    
    data = {
        'id_tienda': range(1, n_registros + 1),
        'nom_tienda': [f"RetailMax {fake.word()}" for _ in range(n_registros)],
        'tipo_tienda': np.random.choice(tipos_tienda, n_registros),
        'id_ciudad': np.random.randint(1, 6, n_registros),
        'id_pais': [1] * n_registros,  # Colombia
        'metros_cuadrados': np.random.randint(500, 5000, n_registros),
        'activo': np.random.choice([0, 1], n_registros, p=[0.05, 0.95]),
        'fec_apertura': pd.date_range('2015-01-01', periods=n_registros, freq='D')
    }
    
    df = pd.DataFrame(data)
    logger.info(f"✓ MSTR_TIENDAS: {len(df)} registros generados")
    return df

def generar_mstr_articulos(n_registros: int, n_proveedores: int, seed: int, config: dict) -> pd.DataFrame:
    """
    Genera tabla MSTR_ARTICULOS con datos realistas
    """
    np.random.seed(seed)
    fake = Faker()
    
    categorias_n1 = config.get('categorias_nivel1', [])
    unidades = ['UND', 'KG', 'LT', 'PAK', 'CJA']
    
    data = {
        'art_id': range(1, n_registros + 1),
        'cod_barra': [fake.ean13() for _ in range(n_registros)],
        'desc_art': [fake.word() for _ in range(n_registros)],
        'id_categ_n1': np.random.randint(1, len(categorias_n1) + 1, n_registros),
        'id_categ_n2': np.random.randint(1, 4, n_registros),
        'id_categ_n3': np.random.randint(1, 6, n_registros),
        'id_proveedor': np.random.randint(1, n_proveedores + 1, n_registros),
        'precio_lista': np.random.uniform(100, 50000, n_registros).round(2),
        'peso_kg': np.random.uniform(0.1, 100, n_registros).round(2),
        'unid_medida': np.random.choice(unidades, n_registros),
        'activo': np.random.choice([0, 1], n_registros, p=[0.05, 0.95]),
        'fec_alta': pd.date_range('2020-01-01', periods=n_registros, freq='h')
    }
    
    df = pd.DataFrame(data)
    logger.info(f"✓ MSTR_ARTICULOS: {len(df)} registros generados")
    return df

# ==============================================================================
# PARTE 3: GENERADORES DE TABLAS TRANSACCIONALES
# ==============================================================================

def generar_crm_miembros(n_registros: int, seed: int, config: dict) -> pd.DataFrame:
    """
    Genera tabla CRM_MIEMBROS con datos realistas
    """
    np.random.seed(seed)
    fake = Faker()
    
    start_date = datetime.strptime(config['date_range']['start'], "%Y-%m-%d")
    end_date = datetime.strptime(config['date_range']['end'], "%Y-%m-%d")
    date_range = (end_date - start_date).days
    
    data = {
        'id_miembro': range(1, n_registros + 1),
        'fec_registro': [start_date + timedelta(days=np.random.randint(0, date_range)) for _ in range(n_registros)],
        'id_ciudad': np.random.randint(1, 6, n_registros),
        'genero': np.random.choice(['M', 'F', 'O'], n_registros),
        'rango_edad': np.random.choice(['18-25', '26-35', '36-50', '50+'], n_registros),
        'canal_pref': np.random.choice(['Tienda Física', 'Online', 'Ambos'], n_registros),
        'activo': np.random.choice([0, 1], n_registros, p=[0.1, 0.9]),
        'fec_ultima_compra': [start_date + timedelta(days=np.random.randint(0, date_range)) for _ in range(n_registros)]
    }
    
    df = pd.DataFrame(data)
    logger.info(f"✓ CRM_MIEMBROS: {len(df)} registros generados")
    return df

def generar_trans_ventas(n_registros: int, n_miembros: int, n_tiendas: int, n_articulos: int, 
                        seed: int, config: dict) -> pd.DataFrame:
    """
    Genera tabla TRANS_VENTAS con datos realistas
    Tabla más grande: contiene todas las transacciones
    """
    np.random.seed(seed)
    
    start_date = datetime.strptime(config['date_range']['start'], "%Y-%m-%d")
    end_date = datetime.strptime(config['date_range']['end'], "%Y-%m-%d")
    date_range = (end_date - start_date).days
    
    canales = ['Tienda Física', 'Online', 'App Móvil']
    tipos_pago = ['Tarjeta Crédito', 'Tarjeta Débito', 'Efectivo', 'PSE']
    
    data = {
        'id_trans': range(1, n_registros + 1),
        'id_miembro': np.random.randint(1, n_miembros + 1, n_registros),
        'id_tienda': np.random.randint(1, n_tiendas + 1, n_registros),
        'art_id': np.random.randint(1, n_articulos + 1, n_registros),
        'fec_trans': [start_date + timedelta(days=np.random.randint(0, date_range)) for _ in range(n_registros)],
        'hra_trans': [f"{np.random.randint(0, 24):02d}:{np.random.randint(0, 60):02d}" for _ in range(n_registros)],
        'qty_vendida': np.random.randint(1, 100, n_registros),
        'precio_unitario_venta': np.random.uniform(100, 10000, n_registros).round(2),
        'descuento_aplicado': np.random.choice([0, 5, 10, 15, 20], n_registros),
        'tipo_pago': np.random.choice(tipos_pago, n_registros),
        'canal_venta': np.random.choice(canales, n_registros)
    }
    
    df = pd.DataFrame(data)
    logger.info(f"✓ TRANS_VENTAS: {len(df)} registros generados")
    return df

# ==============================================================================
# PARTE 4: GENERADORES DE TABLAS DE CONTEXTO
# ==============================================================================

def generar_inv_stock_diario(n_registros: int, n_articulos: int, n_tiendas: int, 
                            seed: int, config: dict) -> pd.DataFrame:
    """
    Genera tabla INV_STOCK_DIARIO con datos realistas
    """
    np.random.seed(seed)
    
    start_date = datetime.strptime(config['date_range']['start'], "%Y-%m-%d")
    end_date = datetime.strptime(config['date_range']['end'], "%Y-%m-%d")
    date_range = (end_date - start_date).days
    
    data = {
        'id_snapshot': range(1, n_registros + 1),
        'art_id': np.random.randint(1, n_articulos + 1, n_registros),
        'id_tienda': np.random.randint(1, n_tiendas + 1, n_registros),
        'fec_snapshot': [start_date + timedelta(days=np.random.randint(0, date_range)) for _ in range(n_registros)],
        'stock_fisico': np.random.randint(0, 500, n_registros),
        'stock_transito': np.random.randint(0, 200, n_registros),
        'stock_reservado': np.random.randint(0, 100, n_registros),
        'stock_minimo_config': np.random.randint(10, 50, n_registros),
        'stock_maximo_config': np.random.randint(200, 1000, n_registros)
    }
    
    df = pd.DataFrame(data)
    logger.info(f"✓ INV_STOCK_DIARIO: {len(df)} registros generados")
    return df

def generar_post_devoluciones(n_registros: int, n_trans_ventas: int, n_articulos: int, 
                             n_tiendas: int, seed: int, config: dict) -> pd.DataFrame:
    """
    Genera tabla POST_DEVOLUCIONES con datos realistas
    """
    np.random.seed(seed)
    
    start_date = datetime.strptime(config['date_range']['start'], "%Y-%m-%d")
    end_date = datetime.strptime(config['date_range']['end'], "%Y-%m-%d")
    date_range = (end_date - start_date).days
    
    motivos = ['Defecto producto', 'No cumple expectativas', 'Tamaño incorrecto', 'Cambio de opinión', 'Otro']
    canales = ['Tienda Física', 'Online']
    estados = ['Devuelto', 'En Revisión', 'Reembolsado', 'Rechazado']
    
    data = {
        'id_devolucion': range(1, n_registros + 1),
        'id_trans_origen': np.random.randint(1, n_trans_ventas + 1, n_registros),
        'art_id': np.random.randint(1, n_articulos + 1, n_registros),
        'id_tienda': np.random.randint(1, n_tiendas + 1, n_registros),
        'fec_devolucion': [start_date + timedelta(days=np.random.randint(0, date_range)) for _ in range(n_registros)],
        'qty_devuelta': np.random.randint(1, 20, n_registros),
        'motivo_cod': np.random.choice(motivos, n_registros),
        'canal_devolucion': np.random.choice(canales, n_registros),
        'estado_devolucion': np.random.choice(estados, n_registros),
        'vr_reembolso': np.random.uniform(1000, 100000, n_registros).round(2)
    }
    
    df = pd.DataFrame(data)
    logger.info(f"✓ POST_DEVOLUCIONES: {len(df)} registros generados")
    return df

# ==============================================================================
# PARTE 5: INYECCIÓN DE ANOMALÍAS
# ==============================================================================

def inyectar_anomalias(df: pd.DataFrame, config: dict, tabla_nombre: str) -> pd.DataFrame:
    """
    Inyecta anomalías intencionales en los datos para simular realidad
    
    Anomalías documentadas:
    1. Duplicados exactos
    2. Fechas fuera de rango
    3. Campos inconsistentes (valores nulos + falta de integridad)
    """
    df_copy = df.copy()
    anomalies = config.get('anomalies', {})
    
    # Anomalía 1: Duplicados exactos
    duplicate_rate = anomalies.get('duplicate_rate', 0.001)
    n_dupes = int(len(df_copy) * duplicate_rate)
    if n_dupes > 0:
        indices_dupes = np.random.choice(len(df_copy), n_dupes, replace=False)
        df_copy = pd.concat([df_copy, df_copy.iloc[indices_dupes]], ignore_index=True)
        logger.warning(f"  ⚠ Anomalía 1: {n_dupes} registros DUPLICADOS inyectados en {tabla_nombre}")
    
    # Anomalía 2: Valores nulos intencionales
    null_rate = anomalies.get('null_rate', 0.05)
    if null_rate > 0:
        for col in df_copy.select_dtypes(include=['object']).columns:
            mask = np.random.random(len(df_copy)) < null_rate
            df_copy.loc[mask, col] = None
        logger.warning(f"  ⚠ Anomalía 2: ~{int(len(df_copy) * null_rate)} valores NULOS inyectados en {tabla_nombre}")
    
    return df_copy

# ==============================================================================
# PARTE 6: EXPORTACIÓN
# ==============================================================================

def exportar_datos(df: pd.DataFrame, tabla_nombre: str, output_path: str, formatos: list) -> None:
    """
    Exporta el DataFrame a múltiples formatos (CSV y Parquet)
    """
    for formato in formatos:
        if formato == 'csv':
            ruta = os.path.join(output_path, f"{tabla_nombre}.csv")
            df.to_csv(ruta, index=False, encoding='utf-8')
            logger.info(f"  ✓ Exportado: {tabla_nombre}.csv")
            
        elif formato == 'parquet':
            ruta = os.path.join(output_path, f"{tabla_nombre}.parquet")
            df.to_parquet(ruta, index=False, engine='pyarrow')
            logger.info(f"  ✓ Exportado: {tabla_nombre}.parquet")

# ==============================================================================
# PARTE 7: FUNCIÓN PRINCIPAL
# ==============================================================================

def main():
    """
    Orquesta todo el proceso de generación de datos
    """
    print("\n" + "="*70)
    print("GENERACIÓN DE DATOS SINTÉTICOS - RetailMax (Escenario B)")
    print("="*70)
    
    # Cargar configuración
    config = cargar_configuracion('data-generation/config.yaml')
    output_path = crear_directorio_salida(config)
    
    seed = config.get('seed', 42)
    volumes = config.get('volumes', {})
    paises = config.get('paises', [])
    formatos = config.get('output_formats', ['csv', 'parquet'])
    
    logger.info(f"Semilla reproducible: {seed}")
    logger.info(f"Fecha rango: {config['date_range']['start']} a {config['date_range']['end']}\n")
    
    # Generar tablas maestras
    print("\n📚 Generando tablas MAESTRAS:")
    proveedores = generar_mstr_proveedores(volumes['MSTR_PROVEEDORES'], seed, paises)
    tiendas = generar_mstr_tiendas(volumes['MSTR_TIENDAS'], seed, paises)
    articulos = generar_mstr_articulos(volumes['MSTR_ARTICULOS'], volumes['MSTR_PROVEEDORES'], seed, config)
    
    # Generar tablas transaccionales
    print("\n💼 Generando tablas TRANSACCIONALES:")
    miembros = generar_crm_miembros(volumes['CRM_MIEMBROS'], seed, config)
    ventas = generar_trans_ventas(volumes['TRANS_VENTAS'], volumes['CRM_MIEMBROS'], 
                                 volumes['MSTR_TIENDAS'], volumes['MSTR_ARTICULOS'], seed, config)
    stock = generar_inv_stock_diario(volumes['INV_STOCK_DIARIO'], volumes['MSTR_ARTICULOS'],
                                    volumes['MSTR_TIENDAS'], seed, config)
    devoluciones = generar_post_devoluciones(volumes['POST_DEVOLUCIONES'], volumes['TRANS_VENTAS'],
                                           volumes['MSTR_ARTICULOS'], volumes['MSTR_TIENDAS'], seed, config)
    
    # Inyectar anomalías antes de exportar
    print("\n⚠ Inyectando anomalías intencionales:")
    proveedores = inyectar_anomalias(proveedores, config, 'MSTR_PROVEEDORES')
    articulos = inyectar_anomalias(articulos, config, 'MSTR_ARTICULOS')
    ventas = inyectar_anomalias(ventas, config, 'TRANS_VENTAS')
    
    # Exportar datos
    print(f"\n📤 Exportando a {formatos}:")
    tablas = {
        'MSTR_PROVEEDORES': proveedores,
        'MSTR_TIENDAS': tiendas,
        'MSTR_ARTICULOS': articulos,
        'CRM_MIEMBROS': miembros,
        'TRANS_VENTAS': ventas,
        'INV_STOCK_DIARIO': stock,
        'POST_DEVOLUCIONES': devoluciones
    }
    
    for nombre, df in tablas.items():
        exportar_datos(df, nombre, output_path, formatos)
    
    # Resumen
    print("\n" + "="*70)
    print("✅ GENERACIÓN COMPLETADA")
    print("="*70)
    print(f"Ubicación: {output_path}")
    print("\nVolúmenes generados:")
    for nombre, df in tablas.items():
        print(f"  {nombre}: {len(df):,} registros")
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    main()
