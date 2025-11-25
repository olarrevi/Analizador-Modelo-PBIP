import pandas as pd
import os

class ExcelManager:
    def __init__(self, output_path):
        self.output_path = output_path

    def write_sheets(self, data_dict):
        """
        Escribe múltiples DataFrames en un archivo Excel.
        data_dict: Diccionario donde la clave es el nombre de la hoja y el valor es el DataFrame.
        """
        try:
            with pd.ExcelWriter(self.output_path, engine='openpyxl') as writer:
                for sheet_name, df in data_dict.items():
                    if not df.empty:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        print(f"Hoja '{sheet_name}' escrita con {len(df)} filas.")
                    else:
                        # Opcional: Escribir hoja vacía o con mensaje
                        pd.DataFrame(["Sin datos"]).to_excel(writer, sheet_name=sheet_name, index=False)
                        print(f"Hoja '{sheet_name}' escrita (vacía/sin datos).")
            print(f"Proceso completado. Archivo guardado en: {self.output_path}")
        except PermissionError:
            print(f"ERROR: No se puede escribir en {self.output_path}. Cierra el archivo si lo tienes abierto e inténtalo de nuevo.")
        except Exception as e:
            print(f"ERROR al escribir Excel: {e}")
