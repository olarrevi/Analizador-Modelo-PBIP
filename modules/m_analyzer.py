import re

RX_M_LET = re.compile(r'let\s+(.*)\s+in', re.DOTALL)
RX_M_STEP_ASSIGN = re.compile(r'^(?:#?"?([\w\s\-\.\(\)/]+)"?)\s*=\s*(.*)')

class MCodeAnalyzer:
    """ Analizador Forense de Código M (Power Query) """
    def __init__(self, model_context):
        self.context = model_context
        self.nested_joins_map = {}

    def resolve_source_info(self, m_code):
        if not m_code: return "Calculada / DirectQuery", "Modelo Interno", {}, ""
        
        origin_type = "Transformación General"
        origin_path = "Lógica Interna"
        param_detected = False

        # Detección Parámetros
        for param_name in self.context.parameters:
            if f'#"{param_name}"' in m_code or re.search(r'\b' + re.escape(param_name) + r'\b', m_code):
                origin_path = f"Parámetro: {param_name}"
                param_detected = True
                break
        
        if "Excel.Workbook" in m_code or "Excel.Database" in m_code: origin_type = "Excel"
        elif "Sql.Database" in m_code: origin_type = "SQL Database"
        elif "Csv.Document" in m_code: origin_type = "CSV"
        elif "Web.Contents" in m_code: origin_type = "Web"
        elif "SharePoint" in m_code: origin_type = "SharePoint"
        elif "PowerPlatform.Dataflows" in m_code: origin_type = "Dataflow"
        
        if not param_detected:
            if origin_type == "Excel": origin_path = self._extract_path(m_code, r'Web\.Contents\(\s*"([^"]+)"') or self._extract_path(m_code, r'File\.Contents\(\s*"([^"]+)"') or "Excel Dinámico"
            elif origin_type == "SQL Database": origin_path = self._extract_sql(m_code)
            elif origin_type == "SharePoint": origin_path = self._extract_path(m_code, r'SharePoint\.\w+\(\s*"([^"]+)"') or "SharePoint Site"
            elif origin_type == "Dataflow": origin_path = "Dataflow ID"

        # Sustitución Parámetros para análisis
        code_resolved = m_code
        for param, value in self.context.parameters.items():
            code_resolved = code_resolved.replace(f'#"{param}"', f'"{value}"')
            code_resolved = re.sub(r'\b' + re.escape(param) + r'\b', f'"{value}"', code_resolved)

        # Parsing
        steps = {}
        let_match = RX_M_LET.search(code_resolved)
        if let_match:
            lines = let_match.group(1).split('\n')
            current_step = "Inicio"; buffer = []
            for line in lines:
                ls = line.strip()
                if not ls: continue
                step_match = RX_M_STEP_ASSIGN.match(ls)
                if step_match and not ls.startswith("in"):
                    if buffer: steps[current_step] = "\n".join(buffer)
                    current_step = step_match.group(1); buffer = [step_match.group(2)]
                else: buffer.append(line)
            if buffer: steps[current_step] = "\n".join(buffer)
        else: steps = {"Consulta Directa": code_resolved}

        # Mapeo Joins
        flat_code = code_resolved.replace('\n', ' ').replace('\r', '')
        join_matches = re.finditer(r'Table\.NestedJoin\s*\(\s*[^,]+,\s*\{[^}]+\}\s*,\s*([^,]+)\s*,\s*\{[^}]+\}\s*,\s*"([^"]+)"', flat_code)
        self.nested_joins_map = {} 
        for match in join_matches:
            raw_table = match.group(1).strip().replace('#"', '').replace('"', '')
            new_col_name = match.group(2).strip()
            self.nested_joins_map[new_col_name] = raw_table
        
        return origin_type, origin_path, steps, code_resolved

    def _extract_path(self, text, pattern):
        m = re.search(pattern, text); return m.group(1) if m else None
    def _extract_sql(self, text):
        m = re.search(r'Sql\.Database\(\s*"([^"]+)"\s*,\s*"([^"]+)"', text); return f"{m.group(1)} | {m.group(2)}" if m else "SQL"

    def trace_column(self, col_name, steps, full_code):
        col_regex = re.escape(col_name)
        rx_expand = re.compile(r'Table\.ExpandTableColumn\s*\(\s*([^,]+)\s*,\s*"([^"]+)"\s*,\s*(\{.*?\})(?:,\s*(\{.*?\})?)?\s*\)', re.DOTALL)
        for match in rx_expand.finditer(full_code):
            bridge_col = match.group(2).strip() 
            cols_source = match.group(3); cols_new = match.group(4)           
            search_list = cols_new if cols_new else cols_source
            if f'"{col_name}"' in search_list:
                if bridge_col in self.nested_joins_map: return f"Expandido de: {self.nested_joins_map[bridge_col]}", "Expand"
                else: return f"Expandido de columna: {bridge_col}", "Expand"
        add_col_search = re.search(r'Table\.AddColumn\(.*?"' + col_regex + r'"\s*,\s*(?:each\s*)?(.*)', full_code, re.IGNORECASE)
        if add_col_search: return f"Calculado (M): {add_col_search.group(1).split(',')[0][:100]}...", "Transformación"
        rename_search = re.search(r'\{\s*\{"([^"]+)"\s*,\s*"' + col_regex + r'"\}\s*\}', full_code)
        if rename_search: return f"Renombrada desde: [{rename_search.group(1)}]", "Transformación"
        return "Cargada desde Origen", "Origen"
