# Analizador de Modelos y Reportes Power BI

Este proyecto contiene un conjunto de herramientas en Python diseñadas para auditar, documentar y analizar modelos semánticos y reportes de Power BI.

## Descripción

El proyecto se divide en dos scripts principales que permiten extraer información detallada de los archivos de definición de Power BI (formatos PBIP/TMDL):

1.  **`main.py` (Auditoría del Modelo):** Analiza la estructura del modelo de datos.
2.  **`objetos_visuales.py` (Documentación de Visuales):** Analiza los objetos visuales utilizados en los reportes.

## Características

### Auditoría del Modelo (`main.py`)
-   **Análisis TMDL:** Lee la definición del modelo semántico desde carpetas TMDL.
-   **Relaciones:** Extrae y documenta las relaciones entre tablas.
-   **Análisis Power Query (M):** Rastrea el origen de las columnas y las transformaciones aplicadas.
-   **Dependencias DAX:** Analiza las medidas DAX para identificar de qué columnas y tablas dependen.
-   **Uso de Columnas:** Identifica qué columnas están siendo utilizadas en medidas y cuáles no.
-   **Inventario:** Genera un inventario completo de tablas, columnas y medidas con sus expresiones.

### Documentación de Visuales (`objetos_visuales.py`)
-   **Extracción de Visuales:** Lee la definición del reporte (PBIP) para listar todos los objetos visuales por página.
-   **Identificación de Datos:** Detecta qué campos y medidas se utilizan en cada visual.
-   **Integración con el Modelo:** Cruza la información de los visuales con el modelo de datos para determinar qué elementos del modelo están en uso en los reportes.

## Requisitos

-   Python 3.x
-   Librerías Python:
    -   `pandas`
    -   `openpyxl` (recomendado para la exportación a Excel)

Puedes instalar las dependencias con:
```bash
pip install pandas openpyxl
```

## Estructura del Proyecto

```
.
├── main.py                 # Script principal de auditoría del modelo
├── objetos_visuales.py     # Script de análisis de objetos visuales
├── modules/                # Módulos auxiliares
│   ├── tmdl_parser.py      # Parser de archivos TMDL
│   ├── m_analyzer.py       # Analizador de código M
│   ├── dax_analyzer.py     # Analizador de expresiones DAX
│   ├── excel_manager.py    # Gestor de exportación a Excel
│   ├── report_logic.py     # Lógica de parsing de reportes PBIP
│   └── usage_integrator.py # Integrador de uso visuales/modelo
└── ...
```

## Uso

### 1. Configuración
Antes de ejecutar los scripts, debes configurar las rutas a tus archivos de Power BI en las variables de configuración al inicio de cada archivo.

**En `main.py`:**
```python
ROOT_FOLDER = r"C:\Ruta\A\Tu\Modelo.SemanticModel\definition"
OUTPUT_EXCEL = "Nombre_Reporte_Modelo.xlsx"
```

**En `objetos_visuales.py`:**
```python
input_report_path = r"C:\Ruta\A\Tu\Reporte.Report"
modelo_ruta = r"C:\Ruta\A\Tu\Modelo.SemanticModel\definition"
output_file = "Nombre_Reporte_Visuales.xlsx"
```

### 2. Ejecución

Para auditar el modelo de datos:
```bash
python main.py
```
Esto generará un archivo Excel (por defecto `AUDITORIA_MODELO_OBS.xlsx`) con hojas para Relaciones, Transformaciones M, Dependencias DAX, etc.

Para documentar los visuales:
```bash
python objetos_visuales.py
```
Esto generará un archivo Excel (por defecto `DOCUMENTACION UCMA SC.xlsx`) con el detalle de los visuales y el inventario de uso.

## Salida

Los scripts generan archivos Excel con múltiples pestañas que facilitan la revisión y documentación técnica de tus proyectos de Power BI.
