import pandas as pd

class UsageIntegrator:
    def __init__(self, visuals_df: pd.DataFrame, model_parser):
        self.df_visuals = visuals_df
        self.model = model_parser

    def generate_inventory_sheet(self) -> pd.DataFrame:
        """Crea una hoja maestra cruzando el modelo con el uso visual"""
        if not self.model or not hasattr(self.model, 'tables'):
            return pd.DataFrame()

        print("Generando hoja de inventario y conteo de uso...")
        
        # 1. Contar uso en visuales
        if 'Valor' in self.df_visuals.columns:
            usage_counts = self.df_visuals['Valor'].value_counts().reset_index()
            # Pandas v2 usa 'count' o el nombre original, aseguramos nombres:
            usage_counts.columns = ['Nombre Objeto', 'Conteo Visuales']
        else:
            usage_counts = pd.DataFrame(columns=['Nombre Objeto', 'Conteo Visuales'])

        # 2. Construir inventario completo desde el modelo
        inventory_rows = []

        # A) Columnas
        for tbl_name, data in self.model.tables.items():
            for col in data.get("columns", []):
                inventory_rows.append({
                    "Tabla": tbl_name,
                    "Nombre Objeto": col,
                    "Tipo": "Columna",
                    "Ubicacion": f"{tbl_name}[{col}]"
                })
        
        # B) Medidas
        for meas_name, data in self.model.measures.items():
            inventory_rows.append({
                "Tabla": data.get("home_table", "Desconocida"),
                "Nombre Objeto": meas_name,
                "Tipo": "Medida",
                "Ubicacion": f"[{meas_name}]"
            })

        df_inventory = pd.DataFrame(inventory_rows)

        if df_inventory.empty:
            return df_inventory

        # 3. Cruce (Left Join)
        df_final = pd.merge(df_inventory, usage_counts, on='Nombre Objeto', how='left')
        
        # Rellenar nulos con 0
        df_final['Conteo Visuales'] = df_final['Conteo Visuales'].fillna(0).astype(int)
        
        # --- CAMBIO DE ORDENACIÓN AQUÍ ---
        # Primero por 'Tabla' (Ascendente A-Z)
        # Luego por 'Conteo Visuales' (Descendente: los más usados arriba)
        df_final = df_final.sort_values(by=['Tabla', 'Conteo Visuales'], ascending=[True, False])
        # ---------------------------------

        return df_final
