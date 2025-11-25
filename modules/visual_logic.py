import json
from typing import List, Dict, Any, Optional

class DataExtractor:
    """Clase estática encargada de parsear estructuras internas de Power BI (QueryRefs, etc.)"""

    @staticmethod
    def analyze_config(config: Dict[str, Any]) -> List:
        results = []
        # 1. Detectar formato (Legacy vs PBIR)
        if 'singleVisual' in config:
            results = DataExtractor._analyze_legacy(config)
        elif 'query' in config and 'queryState' in config['query']:
            results = DataExtractor._analyze_pbir(config)
        else:
            results = []

        # 2. Extraer filtros
        filters = DataExtractor._extract_filters(config)
        results.extend(filters)
        return results

    @staticmethod
    def _analyze_legacy(config: Dict[str, Any]) -> List:
        results = []
        definitions_map = {}
        try:
            proto_query = config.get('singleVisual', {}).get('prototypeQuery', {})
            select_items = proto_query.get('Select', [])
            
            for item in select_items:
                name = item.get('Name')
                if 'Measure' in item:
                    display_name = item['Measure'].get('Property', name)
                    type_val = "Medida"
                elif 'Column' in item:
                    display_name = item['Column'].get('Property', name)
                    type_val = "Columna"
                elif 'Aggregation' in item:
                    display_name = item.get('Name')
                    type_val = "Columna (Agregada)"
                else:
                    display_name = name
                    type_val = "Desconocido"
                definitions_map[name] = {'real_name': display_name, 'type': type_val}
                
            projections = config.get('singleVisual', {}).get('projections', {})
            for role, refs in projections.items():
                for ref in refs:
                    query_ref = ref.get('queryRef')
                    if query_ref in definitions_map:
                        def_data = definitions_map[query_ref]
                        results.append({'Valor': def_data['real_name'], 'Tipo_Valor': def_data['type']})
                    else:
                        results.append({'Valor': query_ref, 'Tipo_Valor': "Incierto (Posible Medida)"})
        except Exception: pass
        return results

    @staticmethod
    def _analyze_pbir(config: Dict[str, Any]) -> List:
        results = []
        try:
            query_state = config.get('query', {}).get('queryState', {})
            for role, role_data in query_state.items():
                projections = role_data.get('projections', [])
                for proj in projections:
                    query_ref = proj.get('queryRef')
                    field_def = proj.get('field', {})
                    
                    if 'Measure' in field_def:
                        type_val = "Medida"
                        real_name = field_def['Measure'].get('Property', query_ref)
                    elif 'Column' in field_def:
                        type_val = "Columna"
                        real_name = field_def['Column'].get('Property', query_ref)
                    elif 'Aggregation' in field_def:
                        type_val = "Columna (Agregada)"
                        real_name = query_ref
                    elif 'HierarchyLevel' in field_def:
                         type_val = "Jerarquía"
                         real_name = field_def['HierarchyLevel'].get('Level', query_ref)
                    else:
                        type_val = "Desconocido"
                        real_name = query_ref
                        
                    results.append({'Valor': real_name, 'Tipo_Valor': type_val})
        except Exception: pass
        return results

    @staticmethod
    def _extract_filters(config: Dict[str, Any]) -> List:
        filters_found = []
        try:
            objects = {}
            if 'visual' in config and 'objects' in config['visual']:
                objects = config['visual']['objects']
            elif 'singleVisual' in config and 'objects' in config['singleVisual']:
                objects = config['singleVisual'].get('objects', {})
            elif 'objects' in config:
                objects = config['objects']
                
            general_list = objects.get('general', [])
            if not general_list: return []
            
            filter_prop = None
            if isinstance(general_list, list):
                for item in general_list:
                    props = item.get('properties', {})
                    if 'filter' in props:
                        filter_prop = props['filter']
                        break
            
            if not filter_prop: return []
            filter_def = filter_prop.get('filter')
            if not filter_def: return []

            where_clauses = filter_def.get('Where', [])
            for clause in where_clauses:
                condition = clause.get('Condition', {})
                if 'In' in condition:
                    exprs = condition['In'].get('Expressions', [])
                    for expr in exprs:
                        if 'Column' in expr:
                            col_name = expr['Column'].get('Property')
                            if col_name:
                                filters_found.append({'Valor': col_name, 'Tipo_Valor': 'Filtro Visual'})
                        elif 'Measure' in expr:
                             meas_name = expr['Measure'].get('Property')
                             if meas_name:
                                filters_found.append({'Valor': meas_name, 'Tipo_Valor': 'Filtro Visual (Medida)'})
        except Exception: pass
        return filters_found

    @staticmethod
    def translate_visual_type(vtype: str) -> str:
        translations = {
            'card': 'Tarjeta', 'cardVisual': 'Tarjeta', 'clusteredBarChart': 'Barras Agrupadas',
            'clusteredColumnChart': 'Columnas Agrupadas', 'columnChart': 'Columnas', 'barChart': 'Barras',
            'lineChart': 'Líneas', 'areaChart': 'Área', 'donutChart': 'Anillo', 'pieChart': 'Circular',
            'slicer': 'Segmentador', 'tableEx': 'Tabla', 'pivotTable': 'Matriz', 'textbox': 'Cuadro de Texto',
            'actionButton': 'Botón', 'shape': 'Forma', 'image': 'Imagen',
        }
        if vtype not in translations:
            return vtype.replace('Chart', ' (Gráfico)').replace('Visual', '')
        return translations[vtype]

    @staticmethod
    def get_first_field(query_state: dict) -> Optional[str]:
        for role, role_data in query_state.items():
            projs = role_data.get('projections', [])
            if projs: return projs[0].get('nativeQueryRef')
        return None

    @staticmethod
    def get_fields_in_role(query_state: dict, role_names: List[str], max_count: int = 2) -> List[str]:
        fields = []
        for role_name in role_names:
            if role_name in query_state:
                projs = query_state[role_name].get('projections', [])
                for proj in projs[:max_count]:
                    ref = proj.get('nativeQueryRef')
                    if ref: fields.append(ref)
                if fields: break
        return fields

    @staticmethod
    def get_all_fields(query_state: dict, max_count: int = 4) -> List[str]:
        fields = []
        seen = set()
        for role, role_data in query_state.items():
            projs = role_data.get('projections', [])
            for proj in projs:
                ref = proj.get('nativeQueryRef')
                if ref and ref not in seen:
                    fields.append(ref)
                    seen.add(ref)
                    if len(fields) >= max_count: return fields
        return fields

class VisualObject:
    def __init__(self, container_json: Dict[str, Any]):
        self.raw = container_json
        self.config = self._parse_config()
        self.visual_type = self._extract_type()
        self.visual_title = self._extract_title()

    def _parse_config(self) -> Dict:
        try:
            config_str = self.raw.get('config')
            if config_str: return json.loads(config_str)
            visual_prop = self.raw.get('visual')
            if visual_prop: return visual_prop
        except json.JSONDecodeError: return {}
        return {}

    def _extract_type(self) -> str:
        v_type = self.config.get('singleVisual', {}).get('visualType')
        if not v_type: v_type = self.config.get('visualType')
        if not v_type: v_type = self.raw.get('type', 'Unknown')
        return v_type

    def _extract_title(self) -> str:
        title_found = None
        # Estrategia 1: Legacy
        try:
            vc_objects = self.config.get('singleVisual', {}).get('vcObjects', {})
            title_obj = vc_objects.get('title', [])
            if title_obj:
                for prop in title_obj:
                    val = prop.get('properties', {}).get('text', {}).get('expr', {}).get('Literal', {}).get('Value')
                    if val: title_found = val; break
        except: pass
        if title_found: return self._clean_title(title_found)

        # Estrategia 2: Moderno
        try:
            objects = {}
            if 'objects' in self.config: objects = self.config['objects']
            elif 'singleVisual' in self.config and 'objects' in self.config['singleVisual']: objects = self.config['singleVisual']['objects']
            general_props = objects.get('general', [])
            for item in general_props:
                props = item.get('properties', {})
                title_prop = props.get('title') 
                if title_prop:
                    val_expr = title_prop.get('text', {}).get('expr', {}).get('Literal', {}).get('Value')
                    if val_expr: title_found = val_expr; break
                    val_direct = title_prop.get('text')
                    if isinstance(val_direct, str): title_found = val_direct; break
        except: pass
        if title_found: return self._clean_title(title_found)

        # Estrategia 3: PBIR
        try:
            vco = self.config.get('visualContainerObjects', {})
            title_list = vco.get('title', [])
            if title_list and isinstance(title_list, list):
                for item in title_list:
                    val = item.get('properties', {}).get('text', {}).get('expr', {}).get('Literal', {}).get('Value')
                    if val: title_found = val; break
        except: pass
        if title_found: return self._clean_title(title_found)
            
        return self._generate_smart_identifier()

    def _clean_title(self, raw_title: str) -> str:
        if not raw_title: return ""
        if raw_title.startswith("'") and raw_title.endswith("'"): return raw_title[1:-1]
        return raw_title

    def _generate_smart_identifier(self) -> str:
        query_state = self.config.get('query', {}).get('queryState', {})
        tipo_es = DataExtractor.translate_visual_type(self.visual_type)
        
        if not query_state:
            # Legacy fallback
            return tipo_es
        
        if self.visual_type in ['card', 'cardVisual']:
            first = DataExtractor.get_first_field(query_state)
            return first or tipo_es
        elif self.visual_type == 'slicer':
            first = DataExtractor.get_first_field(query_state)
            return f"Segmentador - {first}" if first else "Segmentador"
        elif 'Chart' in self.visual_type or 'chart' in self.visual_type:
            cat = DataExtractor.get_fields_in_role(query_state, ['Category', 'Axis'])
            val = DataExtractor.get_fields_in_role(query_state, ['Values', 'Y'])
            parts = []
            if cat: parts.append(', '.join(cat))
            if val: parts.append(', '.join(val))
            return f"{tipo_es}: {' por '.join(parts)}" if parts else tipo_es
        elif self.visual_type in ['tableEx', 'pivotTable']:
            fields = DataExtractor.get_all_fields(query_state, max_count=3)
            return f"{tipo_es} - {', '.join(fields)}" if fields else tipo_es
        else:
            first = DataExtractor.get_first_field(query_state)
            return f"{tipo_es} - {first}" if first else tipo_es

    def get_usage_data(self) -> List:
        if not self.config: return []
        fields = DataExtractor.analyze_config(self.config)
        for f in fields:
            f['Objeto Visual'] = self.visual_type
            f['Titulo'] = self.visual_title
        return fields
