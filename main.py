import pandas as pd
from modules.tmdl_parser import TmdlParser, OriginType
from modules.m_analyzer import MCodeAnalyzer
from modules.dax_analyzer import DaxAnalyzer
from modules.excel_manager import ExcelManager

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================
ROOT_FOLDER = r"C:\Ruta\A\Tu\Modelo.SemanticModel\definition"
OUTPUT_EXCEL = "AUDITORIA_MODELO_OBS.xlsx"

def main():
    print("--- Iniciando Auditoría Avanzada (TMDL + M + DAX) ---")
    model = TmdlParser(ROOT_FOLDER)
    model.parse_model()
    if not model.tables: return

    dax_analyzer = DaxAnalyzer(model.global_objects, model.tables, model.measures)
    m_analyzer = MCodeAnalyzer(model)
    
    print("Generando reportes...")
    df_relaciones = pd.DataFrame(model.relationships)
    
    # --- FORZAR ORDEN DE COLUMNAS EN RELACIONES ---
    if not df_relaciones.empty:
        cols_order = ["Tabla Origen", "Columna Origen", "Columna Destino", "Tabla Destino", "Tipo Relacion", "Activo?"]
        # Asegurar que solo seleccionamos columnas que existen
        cols_to_select = [c for c in cols_order if c in df_relaciones.columns]
        df_relaciones = df_relaciones[cols_to_select]

    rows_m = []
    table_id = 0
    for tbl_name, data in model.tables.items():
        table_id += 1
        m_code = data["m_code"]
        tbl_type, tbl_path, steps, resolved_code = m_analyzer.resolve_source_info(m_code)
        
        for col in data["columns"]:
            trans_desc, col_type = m_analyzer.trace_column(col, steps, resolved_code)
            final_path = tbl_path; final_type = tbl_type
            
            if col_type == "Transformación": final_type = "Transformación (Power Query)"
            elif col_type == "Expand":
                final_type = "Join/Expand"
                if "Expandido de:" in trans_desc: final_path = trans_desc.replace("Expandido de: ", "")
                else: final_path = "Tabla Relacionada"
            
            if not m_code: final_type = "DAX / Interno"; trans_desc = "Columna Calculada o Estática"

            rows_m.append({
                "Nombre Tabla": tbl_name, "Nombre Columna": col, "Transformacion": trans_desc,
                "Origen": final_path, "Tipo_Origen": final_type, "Color_ID": table_id
            })
            
    df_transf_m = pd.DataFrame(rows_m)
    if not df_transf_m.empty:
        df_transf_m = df_transf_m[["Nombre Tabla", "Nombre Columna", "Transformacion", "Origen", "Tipo_Origen", "Color_ID"]]
    
    rows_deps = []
    for m_name, m_data in model.measures.items():
        deps = dax_analyzer.get_dependencies(m_data["expression"])
        if not deps: rows_deps.append({"Medida": m_name, "Tabla Home": m_data["home_table"], "Dependencia": "Hardcoded", "Tipo Origen": "N/A", "Expresion": m_data["expression"][:100]})
        for dn, dt in deps: rows_deps.append({"Medida": m_name, "Tabla Home": m_data["home_table"], "Dependencia": dn, "Tipo Origen": dt.value, "Expresion": m_data["expression"][:5000]})
    df_deps = pd.DataFrame(rows_deps)
    
    # REPORTE PIVOT_LONGER
    col_usage_map = {} 
    if not df_deps.empty:
        deps_cols = df_deps[df_deps["Tipo Origen"] == OriginType.COLUMN.value]
        for _, row in deps_cols.iterrows():
            col_name_full = row["Dependencia"]
            measure_name = row["Medida"]
            if col_name_full not in col_usage_map: col_usage_map[col_name_full] = set()
            col_usage_map[col_name_full].add(measure_name)

    rows_usage = []
    for t_name, t_data in model.tables.items():
        for c_name in t_data["columns"]:
            full_name = f"{t_name}[{c_name}]"
            if full_name in col_usage_map and col_usage_map[full_name]:
                sorted_measures = sorted(list(col_usage_map[full_name]))
                for m_use in sorted_measures:
                    rows_usage.append({"Tabla": t_name, "Columna": c_name, "Estado Uso": "Usada", "Medida": m_use})
            else:
                rows_usage.append({"Tabla": t_name, "Columna": c_name, "Estado Uso": "No usada en medida", "Medida": ""})
    
    df_used = pd.DataFrame(rows_usage)

    # Inventario
    rows_inv = []
    for t, data in model.tables.items():
        rows_inv.append({"Tabla Pertenencia": t,"Nombre": t, "Tipo": "Tabla", "Expresion": data["m_code"][:5000] if data["m_code"] else ""})
        for c in data["columns"]:
            rows_inv.append({ "Tabla Pertenencia": t,"Nombre": c,  "Tipo": "Columna","Expresion": ""})
    for m, data in model.measures.items():
        rows_inv.append({"Tabla Pertenencia": data["home_table"],"Nombre": m,"Tipo": "Medida", "Expresion": data["expression"][:5000]})
    
    df_inv = pd.DataFrame(rows_inv)

    # Escritura Excel
    excel_mgr = ExcelManager(OUTPUT_EXCEL)
    sheets = {
        "Relaciones": df_relaciones,
        "Transformaciones M": df_transf_m,
        "Dependencias DAX": df_deps,
        "Resumen Columnas Usadas": df_used,
        "Inventario": df_inv
    }
    excel_mgr.write_sheets(sheets)

if __name__ == "__main__":
    main()