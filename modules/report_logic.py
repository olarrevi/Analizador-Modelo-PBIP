import os
import glob
import json
from typing import List
from .visual_logic import VisualObject

class ReportPage:
    def __init__(self, name: str, visuals_data: List):
        self.name = name
        self.visuals_raw = visuals_data

    def process(self) -> List:
        page_results = []
        for v_data in self.visuals_raw:
            visual = VisualObject(v_data)
            fields = visual.get_usage_data()
            for field in fields:
                field['Nombre_Pag'] = self.name
                page_results.append(field)
        return page_results

class PBIPReport:
    def __init__(self, root_path: str):
        self.root = root_path
        self.report_folder = self._find_report_folder()
        self.is_pbir = self._check_is_pbir()

    def _find_report_folder(self):
        if self.root.endswith('.Report'): return self.root
        candidates = glob.glob(os.path.join(self.root, "*.Report"))
        if candidates: return candidates[0]
        raise FileNotFoundError("No se encontró la carpeta *.Report en la ruta dada.")

    def _check_is_pbir(self) -> bool:
        return os.path.exists(os.path.join(self.report_folder, 'definition', 'pages'))

    def run(self):
        print(f"Iniciando análisis de INFORME en: {self.report_folder}")
        if self.is_pbir: return self._process_pbir()
        else: return self._process_legacy()

    def _process_legacy(self):
        json_path = os.path.join(self.report_folder, 'report.json')
        if not os.path.exists(json_path): raise FileNotFoundError("No se encontró report.json")
        with open(json_path, 'r', encoding='utf-8-sig') as f: data = json.load(f)
        rows = []
        for section in data.get('sections', []):
            page_name = section.get('displayName', section.get('name'))
            visuals = section.get('visualContainers', [])
            rows.extend(ReportPage(page_name, visuals).process())
        return rows

    def _process_pbir(self):
        pages_dir = os.path.join(self.report_folder, 'definition', 'pages')
        rows = []
        for page_folder in os.listdir(pages_dir):
            page_path = os.path.join(pages_dir, page_folder)
            if not os.path.isdir(page_path): continue
            page_meta_path = os.path.join(page_path, 'page.json')
            page_name = page_folder
            if os.path.exists(page_meta_path):
                with open(page_meta_path, 'r', encoding='utf-8-sig') as f:
                    pm = json.load(f)
                    page_name = pm.get('displayName', page_name)
            visuals_dir = os.path.join(page_path, 'visuals')
            visuals_list = []
            if os.path.exists(visuals_dir):
                for v_folder in os.listdir(visuals_dir):
                    v_path = os.path.join(visuals_dir, v_folder)
                    if os.path.isdir(v_path):
                        v_json_path = os.path.join(v_path, 'visual.json')
                        if os.path.exists(v_json_path):
                            with open(v_json_path, 'r', encoding='utf-8-sig') as f:
                                visuals_list.append(json.load(f))
            rows.extend(ReportPage(page_name, visuals_list).process())
        return rows
