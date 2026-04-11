CREATE TABLE pipeline_errors (
    error_id INT IDENTITY(1,1) PRIMARY KEY,
    tabla_origen NVARCHAR(100),
    row_id NVARCHAR(500),
    motivo_error NVARCHAR(1000),
    datos_json NVARCHAR(MAX),
    timestamp_error DATETIME DEFAULT GETDATE(),
    batch_id NVARCHAR(50),
    procesado BIT DEFAULT 0
);

CREATE TABLE pipeline_quality_report (
    report_id INT IDENTITY(1,1) PRIMARY KEY,
    tabla_nombre NVARCHAR(100),
    batch_id NVARCHAR(50),
    filas_leidas INT,
    filas_limpias INT,
    duplicados_detectados INT,
    nulos_detectados INT,
    integridad_violaciones INT,
    timestamp_reporte DATETIME DEFAULT GETDATE(),
    duracion_segundos FLOAT,
    estado NVARCHAR(20) -- 'EXITOSO' o 'CON_ERRORES'
);

CREATE INDEX idx_pipeline_errors_tabla_batch ON pipeline_errors(tabla_origen, batch_id);
CREATE INDEX idx_pipeline_quality_tabla_batch ON pipeline_quality_report(tabla_nombre, batch_id);
