import os
import re
from enum import Enum

class OriginType(Enum):
    COLUMN = "Columna"
    MEASURE = "Medida"
    TABLE = "Tabla Completa"

# Regex patterns needed for parsing
RX_EXPRESSION = re.compile(r'expression\s+[\'"]?([\w\s\-\.%]+)[\'"]?\s*=\s*(?:```)?(.*?)(?:```)?(?:\s+meta|$)', re.DOTALL)

class TmdlParser:
    def __init__(self, root_folder):
        self.root = root_folder
        self.tables = {}        
        self.measures = {}      
        self.relationships = [] 
        self.parameters = {}    
        self.global_objects = {"tables": set(), "measures": set(), "columns": set()}

    def parse_model(self):
        print(f"Iniciando análisis en: {self.root}")
        if not os.path.exists(self.root):
            print(f"ERROR: La ruta no existe: {self.root}")
            return

        # 1. Relaciones
        rel_file = os.path.join(self.root, "relationships.tmdl")
        if os.path.exists(rel_file):
            self._parse_relationships(rel_file)
        
        # 2. Archivos TMDL
        all_files = []
        for subdir, dirs, files in os.walk(self.root):
            for file in files:
                if file.endswith('.tmdl') and "relationships.tmdl" not in file:
                    all_files.append(os.path.join(subdir, file))

        print(f"Archivos TMDL encontrados: {len(all_files)}")
        for file_path in all_files:
            self._parse_file(file_path)
            
        print(f"Modelo ingestados: {len(self.tables)} tablas, {len(self.measures)} medidas y {len(self.parameters)} parámetros.")

    def _parse_relationships(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            rel_blocks = re.split(r'relationship\s+[a-f0-9\-]+', content)[1:]
            for block in rel_blocks:
                # Inicializamos con el orden deseado, aunque luego forzaremos el DataFrame
                rel_data = {
                    "Tabla Origen": "", 
                    "Columna Origen": "",
                    "Columna Destino": "",
                    "Tabla Destino": "",
                    "Tipo Relacion": "N -> 1",
                    "Activo?": "Sí"
                }
                
                from_col_match = re.search(r"fromColumn:\s*(.*)", block)
                to_col_match = re.search(r"toColumn:\s*(.*)", block)
                is_active_match = re.search(r"isActive:\s*(false|true)", block, re.IGNORECASE)
                from_card = re.search(r"fromCardinality:\s*(\w+)", block)
                to_card = re.search(r"toCardinality:\s*(\w+)", block)

                if from_col_match and to_col_match:
                    t_origin, c_origin = self._split_tmdl_ref(from_col_match.group(1).strip())
                    t_dest, c_dest = self._split_tmdl_ref(to_col_match.group(1).strip())
                    
                    rel_data["Tabla Origen"] = t_origin
                    rel_data["Columna Origen"] = c_origin
                    rel_data["Tabla Destino"] = t_dest
                    rel_data["Columna Destino"] = c_dest
                    
                    if is_active_match and is_active_match.group(1).lower() == 'false': 
                        rel_data["Activo?"] = "No"
                    
                    fc = from_card.group(1) if from_card else "many"
                    tc = to_card.group(1) if to_card else "one"
                    
                    if fc == "many" and tc == "many": rel_data["Tipo Relacion"] = "N -> N"
                    elif fc == "one" and tc == "one": rel_data["Tipo Relacion"] = "1 -> 1"
                    elif fc == "one" and tc == "many": rel_data["Tipo Relacion"] = "1 -> N"
                    else: rel_data["Tipo Relacion"] = "N -> 1"
                    
                    self.relationships.append(rel_data)
        except Exception: pass

    def _split_tmdl_ref(self, ref_str):
        if "." in ref_str:
            parts = ref_str.split('.')
            if len(parts) >= 2:
                return ".".join(parts[:-1]).replace("'", "").strip(), parts[-1].replace("'", "").strip()
        return ref_str, "Unknown"

    def _parse_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
        except: return

        # Buscar la declaración 'table' en las primeras 20 líneas (para manejar comentarios)
        table_line = None
        for i, line in enumerate(lines[:20]):
            stripped = line.strip()
            if stripped.startswith("table"):
                table_line = stripped
                break
        
        if table_line:
            self._parse_table_logic(table_line, lines, content)
        elif "expression" in content:
            self._parse_expression_logic(content)

    def _parse_expression_logic(self, content):
        for match in RX_EXPRESSION.finditer(content):
            name = match.group(1).strip()
            code = match.group(2).strip()
            if code.startswith('"') and code.endswith('"') and "let" not in code:
                self.parameters[name] = code.strip('"')

    def _parse_table_logic(self, first_line, lines, full_content):
        table_name = first_line.replace("table", "").strip().strip("'")
        m_code = ""
        source_search = re.search(r'\s+source\s*=\s*(?:```)?(.*)', full_content, re.DOTALL)
        if source_search:
            raw_code = source_search.group(1)
            end_markers = ["\n\tcolumn", "\n\tmeasure", "\n\tpartition", "\n\thierarchy", "\n\tannotation"]
            min_idx = len(raw_code)
            for marker in end_markers:
                idx = raw_code.find(marker)
                if idx != -1 and idx < min_idx: min_idx = idx
            m_code = raw_code[:min_idx].strip().replace('```', '')

        self.tables[table_name] = {"columns": [], "m_code": m_code}
        self.global_objects["tables"].add(table_name)
        
        current_measure = None
        in_measure_exp = False
        for line in lines:
            stripped = line.strip()
            if not stripped: continue
            if stripped.startswith("column"):
                col_name = stripped.replace("column", "", 1).split("dataType:")[0].strip().strip("'").strip('"')
                self.tables[table_name]["columns"].append(col_name)
                self.global_objects["columns"].add(col_name)
                in_measure_exp = False; current_measure = None
                continue
            if stripped.startswith("measure"):
                in_measure_exp = True
                parts = stripped.split("=", 1)
                m_part = parts[0].replace("measure", "").strip().strip("'")
                self.measures[m_part] = {"expression": parts[1].strip() if len(parts)>1 else "", "home_table": table_name}
                self.global_objects["measures"].add(m_part); current_measure = m_part
                continue
            if in_measure_exp and current_measure:
                if any(stripped.startswith(k) for k in ["column", "measure", "partition", "hierarchy"]):
                    in_measure_exp = False; current_measure = None
                elif ":" in stripped and "=" not in stripped: pass
                else: self.measures[current_measure]["expression"] += " " + stripped
