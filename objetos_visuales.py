import os
import pandas as pd
from modules.report_logic import PBIPReport
from modules.usage_integrator import UsageIntegrator
from modules.excel_manager import ExcelManager

# IMPORTANTE: Intentamos importar la clase TmdlParser
try:
    from modules.tmdl_parser import TmdlParser
except ImportError:
    TmdlParser = None
    print("ADVERTENCIA: No se encontró 'tmdl_parser.py'. La funcionalidad de Inventario completo estará limitada.")

####PARAMETROS USUARIO#####

#Dentro de /Report/
input_report_path = r"C:\Users\uolv1a\OneDrive - Grupo Planeta\Documentos\Informes PowerBi\Analizar\UCM\KO\I_UCM - KO.Report"

#Dentro de /definition/

modelo_ruta = r"C:\Users\uolv1a\OneDrive - Grupo Planeta\Documentos\Informes PowerBi\Analizar\OBS\MODELO DATOS\MODELO DATOS OBS.SemanticModel\definition"

# Output file

output_file = "DOCUMENTACION UCMA SC.xlsx"

# ==========================================
# PUNTO DE ENTRADA
# ==========================================
if __name__ == "__main__":
    # INPUTS
   
    
    # IMPORTANTE: Pedir ruta del modelo para la nueva hoja
    # Si main.py no está importado, esto fallará controladamente
    if TmdlParser:
        input_model_path = modelo_ruta
    else:
        input_model_path = None

    try:
        # 1. Ejecutar análisis visual
        report = PBIPReport(input_report_path)
        raw_data = report.run()
        df_visuals = pd.DataFrame(raw_data)
        
        # Ordenar y limpiar DF Visuales
        columnas_finales = ['Nombre_Pag', 'Titulo', 'Objeto Visual', 'Valor', 'Tipo_Valor']
        for col in columnas_finales:
            if col not in df_visuals.columns: df_visuals[col] = None
        df_visuals = df_visuals[columnas_finales]

        # 2. Ejecutar análisis de modelo e integración (Si es posible)
        df_inventory = pd.DataFrame()
        
        if TmdlParser and input_model_path and os.path.exists(input_model_path):
            print(f"Analizando modelo semántico en: {input_model_path}")
            model_parser = TmdlParser(input_model_path)
            model_parser.parse_model()
            
            integrator = UsageIntegrator(df_visuals, model_parser)
            df_inventory = integrator.generate_inventory_sheet()
        else:
            print("Saltando análisis de inventario (Falta ruta del modelo o librería main.py)")

        
        # 3. Escritura Excel
        excel_mgr = ExcelManager(output_file)
        
        # Hoja 3 (Opcional): Resumen por página
        pivot_pag = df_visuals.pivot_table(index='Nombre_Pag', values='Valor', aggfunc='count').reset_index()
        
        sheets = {
            "Detalle Visuales": df_visuals,
            "Inventario y Uso": df_inventory,
            "Resumen Páginas": pivot_pag
        }
        excel_mgr.write_sheets(sheets)

    except Exception as e:
        print(f"\nERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()