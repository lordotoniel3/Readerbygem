-- Tabla metadata: dataload
CREATE TABLE dataload (
    id_carga     BIGINT        NOT NULL,
    id_archivo   BIGINT        PRIMARY KEY,
    "name"         TEXT,
    "date"       DATE,
    "status"       VARCHAR(300),
    "format"       VARCHAR(300)
);

-- Tabla metadata: logs
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    id_contenido BIGINT NOT NULL,
    id_carga BIGINT NOT NULL,
    "name" TEXT,
    "date" DATE,
    "status" TEXT,
    format TEXT,
    parent_file TEXT,
    is_duplicate BOOLEAN,
    invalid_format BOOLEAN,
    identified_format TEXT
);

-- Tabla maestra: facturas_invoice
CREATE TABLE facturas_invoice (
    id_archivo           BIGINT       NOT NULL,
    id_contenido         BIGINT       PRIMARY KEY,
    invoice_id           VARCHAR(300),
    nit                  VARCHAR(300),
    invoice_date         DATE,
    supplier_name        TEXT,
    total_amount         DOUBLE PRECISION,
    total_tax_amount     DOUBLE PRECISION,
    net_amount           DOUBLE PRECISION,
    score                DOUBLE PRECISION,
    explicacion_score    TEXT,
    filename             TEXT,
is_duplicate BOOLEAN
);

-- Tabla relacionada: facturas_product
CREATE TABLE facturas_product (
    id_contenido   BIGINT         NOT NULL,
    product_id     VARCHAR(300),
    description    TEXT,
    quantity       NUMERIC(15,2),
    unit_price     DOUBLE PRECISION,
    amount         DOUBLE PRECISION
);

-- Tabla maestra: hoja_de_vida
CREATE TABLE hoja_de_vida (
    id_contenido         BIGINT              PRIMARY KEY,
    id_archivo           BIGINT              NOT NULL,
    nombre_completo      TEXT,
    tipo_documento       VARCHAR(300),
    documento_identidad  VARCHAR(300),
    email                TEXT,
    telefono             VARCHAR(300),
    descripcion_perfil   TEXT,
    direccion_completa   TEXT,
    score                DOUBLE PRECISION,
    explicacion_score    TEXT,
    filename             VARCHAR(300),
is_duplicate BOOLEAN
);

-- Tabla relacionada: habilidad
CREATE TABLE habilidad (
    id_contenido       BIGINT        NOT NULL,
    nombre_habilidad   VARCHAR(300)
);

-- Tabla relacionada: idioma
CREATE TABLE idioma (
    id_contenido   BIGINT        NOT NULL,
    nombre         VARCHAR(300),
    nivel          VARCHAR(300),
    examen         VARCHAR(300)
);

-- Tabla relacionada: educacion
CREATE TABLE educacion (
    id_contenido       BIGINT        NOT NULL,
    titulo TEXT,
    institucion TEXT,
    fecha_inicio   VARCHAR(300),
    fecha_fin   VARCHAR(300),
    semestres_cursados   VARCHAR(100),
    tipo   VARCHAR(300)
);

-- Tabla relacionada: experiencia
CREATE TABLE experiencia (
    id_contenido       BIGINT        NOT NULL,
    puesto TEXT,
    empresa TEXT,
    fecha_inicio   VARCHAR(300),
    fecha_fin   VARCHAR(300),
    total_meses   VARCHAR(300),
    descripcion TEXT
);

-- Tabla maestra: cc
CREATE TABLE cc (
    id_contenido BIGINT PRIMARY KEY,
    id_archivo BIGINT,
    tipo_documento VARCHAR(30),
    numero_cedula VARCHAR(30),
    apellidos VARCHAR(300),
    nombres VARCHAR(300),
    fecha_nacimiento DATE,
    lugar_nacimiento VARCHAR(300),
    fecha_expedicion DATE,
    lugar_expedicion VARCHAR(300),
    estatura NUMERIC(3,2),
    grupo_sanguineo VARCHAR(3),
    sexo CHAR(1),
    score NUMERIC,
    explicacion_score TEXT,
    filename VARCHAR(300),
is_duplicate BOOLEAN
);

-- Tabla maestra: orden_compra
CREATE TABLE orden_compra (
    id_contenido BIGINT PRIMARY KEY,
    id_archivo BIGINT NOT NULL,
    numero_orden TEXT,
    fecha_emision DATE,
    moneda TEXT,
    nombre_comprador TEXT,
    identificacion_comprador TEXT,
    direccion_comprador TEXT,
    telefono_comprador TEXT,
    email_comprador TEXT,
    nombre_proveedor TEXT,
    identificacion_proveedor TEXT,
    direccion_proveedor TEXT,
    telefono_proveedor TEXT,
    email_proveedor TEXT,
    subtotal NUMERIC,
    impuestos NUMERIC,
    descuentos NUMERIC,
    total NUMERIC,
    forma_pago TEXT,
    plazo_entrega TEXT,
    lugar_entrega TEXT,
    observaciones TEXT,
    score NUMERIC,
    explicacion_score TEXT,
    filename TEXT,
is_duplicate BOOLEAN
);

-- Tabla relacionada: orden_compra_items
CREATE TABLE orden_compra_items (
    id SERIAL PRIMARY KEY,
    id_contenido BIGINT,
    descripcion TEXT,
    cantidad NUMERIC,
    unidad_medida TEXT,
    precio_unitario NUMERIC,
    subtotal NUMERIC
);

-- Tabla maestra: extracto_bancario
CREATE TABLE extracto_bancario (
    id_contenido BIGINT PRIMARY KEY,
    id_archivo BIGINT NOT NULL,
    nombre_banco TEXT,
    direccion_banco TEXT,
    telefono_banco TEXT,
    nombre_titular TEXT,
    numero_cliente TEXT,
    direccion_titular TEXT,
    tipo_cuenta TEXT,
    numero_cuenta TEXT,
    moneda TEXT,
    fecha_inicial_periodo DATE,
    fecha_final_periodo DATE,
    saldo_anterior NUMERIC,
    saldo_actual NUMERIC,
    total_depositos NUMERIC,
    total_retiros NUMERIC,
    total_comisiones NUMERIC,
    tasa_interes NUMERIC,
    intereses_generados NUMERIC,
    retenciones NUMERIC,
    fecha_corte_siguiente DATE,
    fecha_emision_extracto DATE,
    numero_extracto TEXT,
    score NUMERIC,
    explicacion_score TEXT,
    filename TEXT,
is_duplicate BOOLEAN
);

-- Tabla relacionada: extracto_bancario_movimientos
CREATE TABLE extracto_bancario_movimientos (
    id SERIAL PRIMARY KEY,
    id_contenido BIGINT NOT NULL,
    fecha DATE,
    descripcion TEXT,
    referencia TEXT,
    valor NUMERIC,
    tipo TEXT,
    saldo_posterior NUMERIC
);

-- Tabla maestra: rub
CREATE TABLE rub (
    id_contenido BIGINT PRIMARY KEY,
    id_archivo BIGINT NOT NULL,
    numero_formulario TEXT,
    fecha_reporte DATE,
    tipo_reporte TEXT,
    razon_social TEXT,
    nit TEXT,
    dv TEXT,
    tipo_entidad TEXT,
    direccion TEXT,
    municipio TEXT,
    departamento TEXT,
    telefono TEXT,
    email TEXT,
    nombre_representante_legal TEXT,
    apellido_representante_legal TEXT,
    tipo_documento_representante_legal TEXT,
    numero_documento_representante_legal TEXT,
    telefono_representante_legal TEXT,
    email_representante_legal TEXT,
    declarante TEXT,
    cargo TEXT,
    fecha_declaracion DATE,
    score NUMERIC,
    explicacion_score TEXT,
    filename TEXT,
is_duplicate BOOLEAN
);

-- Tabla relacionada: rub_beneficiarios
CREATE TABLE rub_beneficiarios (
    id SERIAL PRIMARY KEY,
    id_contenido BIGINT NOT NULL,
    tipo_persona TEXT,
    nombre TEXT,
    apellido TEXT,
    razon_social TEXT,
    tipo_documento TEXT,
    numero_documento TEXT,
    dv TEXT,
    pais_documento TEXT,
    fecha_nacimiento DATE,
    pais_nacimiento TEXT,
    nacionalidad TEXT,
    pais_residencia TEXT,
    direccion TEXT,
    municipio TEXT,
    departamento TEXT,
    telefono TEXT,
    email TEXT,
    tipo_beneficiario TEXT,
    criterio_determinacion TEXT,
    porcentaje_participacion NUMERIC,
    fecha_inicio DATE,
    fecha_fin DATE
);

-- Tabla maestra: rut
CREATE TABLE rut (
    id_contenido BIGINT PRIMARY KEY,
    id_archivo BIGINT NOT NULL,
    numero_formulario TEXT,
    fecha_expedicion DATE,
    fecha_ultima_actualizacion DATE,
    tipo_documento TEXT,
    numero_documento TEXT,
    dv TEXT,
    razon_social TEXT,
    primer_apellido TEXT,
    primer_nombre TEXT,
    fecha_nacimiento DATE,
    pais_nacimiento TEXT,
    departamento_nacimiento TEXT,
    ciudad_nacimiento TEXT,
    direccion TEXT,
    pais TEXT,
    departamento TEXT,
    ciudad TEXT,
    email TEXT,
    telefono_fijo TEXT,
    telefono_movil TEXT,
    notificacion_electronica TEXT,
    tipo_contribuyente TEXT,
    regimen TEXT,
    fecha_inicio_actividades DATE,
    estado_rut TEXT,
    score NUMERIC,
    explicacion_score TEXT,
    filename TEXT,
is_duplicate BOOLEAN
);

-- Tabla relacionada: rut_actividades
CREATE TABLE rut_actividades (
    id SERIAL PRIMARY KEY,
    id_contenido BIGINT NOT NULL,
    codigo_ciiu TEXT,
    descripcion TEXT,
    actividad_principal TEXT,
    fecha_inicio DATE
);

-- Tabla relacionada: rut_responsabilidades
CREATE TABLE rut_responsabilidades (
    id SERIAL PRIMARY KEY,
    id_contenido BIGINT NOT NULL,
    codigo TEXT,
    descripcion TEXT,
    fecha_inicio DATE,
    fecha_fin DATE
);

-- Tabla relacionada: rut_establecimientos
CREATE TABLE rut_establecimientos (
    id SERIAL PRIMARY KEY,
    id_contenido BIGINT NOT NULL,
    nombre TEXT,
    direccion TEXT,
    ciudad TEXT,
    departamento TEXT,
    actividad_principal TEXT,
    fecha_apertura DATE
);

-- Tabla relacionada: rut_representante
CREATE TABLE rut_representante (
    id SERIAL PRIMARY KEY,
    id_contenido BIGINT NOT NULL,
    tipo_documento TEXT,
    numero_documento TEXT,
    nombre_completo TEXT,
    cargo TEXT
);

-- Tabla maestra: existencia
CREATE TABLE existencia (
    id_contenido BIGINT NOT NULL,
    id_archivo BIGINT NOT NULL,
    fecha_expedicion DATE,
    codigo_verificacion VARCHAR(100),
    numero_recibo VARCHAR(100),
    razon_social TEXT NOT NULL,
    sigla VARCHAR(255),
    nit VARCHAR(30) NOT NULL,
    organizacion_juridica VARCHAR(50) NOT NULL,
    categoria VARCHAR(100),
    matricula_mercantil VARCHAR(50) NOT NULL,
    fecha_matricula DATE NOT NULL,
    domicilio VARCHAR(255),
    direccion_principal TEXT,
    telefono_comercial VARCHAR(50),
    email_comercial VARCHAR(255),
    sitio_web VARCHAR(500),
    fecha_constitucion DATE,
    escritura_constitucion VARCHAR(100),
    notaria_constitucion VARCHAR(255),
    fecha_vigencia DATE,
    objeto_social TEXT NOT NULL,
    codigo_ciiu VARCHAR(20),
    descripcion_ciiu TEXT,
    sector_economico VARCHAR(255),
    activo_total DECIMAL(20,2),
    tamano_empresa VARCHAR(50),
    ingresos_actividad_ordinaria DECIMAL(20,2),
    tipo_capital VARCHAR(100),
    valor_capital DECIMAL(20,2),
    facultades_representante TEXT,
    limitaciones_representante TEXT,
    revisor_fiscal VARCHAR(255),
    estado_matricula VARCHAR(50) NOT NULL,
    score DECIMAL(3,2),
    explicacion_score TEXT,
    "filename" VARCHAR(500),
    is_duplicate BOOLEAN DEFAULT FALSE
);

-- Tabla relacionada: existencia_socios
CREATE TABLE existencia_socios (
    id SERIAL PRIMARY KEY,
    id_contenido BIGINT NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    tipo_identificacion VARCHAR(10),
    numero_identificacion VARCHAR(50) NOT NULL,
    numero_cuotas_acciones INTEGER,
    valor_participacion DECIMAL(20,2),
    porcentaje_participacion DECIMAL(5,2)
);

-- Tabla relacionada: existencia_representantes_legales
CREATE TABLE existencia_representantes_legales (
    id SERIAL PRIMARY KEY,
    id_contenido BIGINT NOT NULL,
    cargo VARCHAR(100) NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    tipo_identificacion VARCHAR(10),
    numero_identificacion VARCHAR(50) NOT NULL,
    es_suplente VARCHAR(2),
    fecha_nombramiento DATE,
    documento_nombramiento VARCHAR(255)
);

-- Tabla relacionada: existencia_establecimientos
CREATE TABLE existencia_establecimientos (
    id SERIAL PRIMARY KEY,
    id_contenido BIGINT NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    matricula VARCHAR(50),
    fecha_matricula DATE,
    direccion TEXT NOT NULL,
    ciudad VARCHAR(255),
    telefono_1 VARCHAR(50),
    telefono_2 VARCHAR(50),
    email VARCHAR(255),
    actividad_principal VARCHAR(20),
    descripcion_actividad TEXT,
    valor_establecimiento DECIMAL(20,2) 
);

-- Table embeddings: hoja_de_vida_embedding
-- 1) Crear tabla para almacenar embeddings de hoja_de_vida
CREATE EXTENSION IF NOT EXISTS vector; -- Asegurarse de que la extensión vector esté habilitada
CREATE TABLE hoja_de_vida_embedding (
  id_contenido BIGINT PRIMARY KEY
    REFERENCES hoja_de_vida(id_contenido) ON DELETE CASCADE,
  embedding    VECTOR(768) NOT NULL, --768 dimensiones para text-multilingual-embedding-002, se debería usar modelo mas grande, pero postgresql en gcp tiene hard limit de 2000 dimensiones para el index
  created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- 2) Crear índice para búsqueda k-NN (HNSW) usando distancia coseno
CREATE INDEX idx_hv_embedding_hnsw
  ON hoja_de_vida_embedding
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);