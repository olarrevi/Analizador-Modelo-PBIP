import re
from .tmdl_parser import OriginType

class DaxAnalyzer:
    def __init__(self, model_context, tables_data, measures_data):
        self.context = model_context
        self.tables_lower = {t.lower(): t for t in self.context["tables"]}
        self.measures_lower = {m.lower(): m for m in self.context["measures"]}

    def get_dependencies(self, expression):
        deps = []
        if not expression: return []
        
        expression = re.sub(r'//.*|--.*|/\*.*?\*/', '', expression, flags=re.DOTALL)
        
        for table_lower, original_name in self.tables_lower.items():
            pattern = r"\b" + re.escape(original_name) + r"\b(?!\[)"
            if re.search(pattern, expression, re.IGNORECASE):
                deps.append((f"Tabla: {original_name}", OriginType.TABLE))

        rx_cols = re.finditer(r"('?)([^'\[\]\r\n\(\),]+)\1\s*\[([^\]]+)\]", expression)
        
        for m in rx_cols:
            raw_table = m.group(2).strip()
            col_name = m.group(3).strip()
            if raw_table.lower() in self.tables_lower:
                real_table_name = self.tables_lower[raw_table.lower()]
                deps.append((f"{real_table_name}[{col_name}]", OriginType.COLUMN))
        
        rx_measures = re.finditer(r"\[([^\]]+)\]", expression)
        for m in rx_measures:
            raw_measure = m.group(1).strip()
            if raw_measure.lower() in self.measures_lower:
                real_measure_name = self.measures_lower[raw_measure.lower()]
                deps.append((real_measure_name, OriginType.MEASURE))

        return list(set(deps))
