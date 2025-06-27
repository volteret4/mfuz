import sqlite3
import random
from datetime import datetime, timedelta
from sys import argv
import json

class SQLiteSchemaExtractor:
    def __init__(self, db_path):
        self.db_path = db_path
        
    def connect(self):
        """Conecta a la base de datos SQLite"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            return True
        except sqlite3.Error as e:
            print(f"Error al conectar a la base de datos: {e}")
            return False
    
    def get_tables(self):
        """Obtiene todas las tablas de la base de datos"""
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [table[0] for table in self.cursor.fetchall()]
    
    def get_table_schema(self, table_name):
        """Obtiene el schema de una tabla específica"""
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = self.cursor.fetchall()
        
        schema = []
        for col in columns:
            schema.append({
                'name': col[1],
                'type': col[2],
                'not_null': bool(col[3]),
                'default_value': col[4],
                'primary_key': bool(col[5])
            })
        return schema
    
    def get_real_examples(self, table_name, column_name, limit=3):
        """Obtiene ejemplos reales de la base de datos para una columna específica"""
        try:
            # Verificar si la tabla tiene datos
            self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = self.cursor.fetchone()[0]
            
            if row_count == 0:
                return ["(sin datos en la tabla)"]
            
            # Obtener valores únicos no nulos de la columna
            query = f"""
            SELECT DISTINCT {column_name} 
            FROM {table_name} 
            WHERE {column_name} IS NOT NULL 
            AND {column_name} != '' 
            LIMIT {limit * 2}
            """
            
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            
            if not results:
                return ["(sin valores en esta columna)"]
            
            # Extraer solo los valores (sin la tupla)
            values = [str(row[0]) for row in results]
            
            # Si tenemos más valores de los necesarios, tomar una muestra aleatoria
            if len(values) > limit:
                values = random.sample(values, limit)
            
            return values[:limit] if values else ["(sin datos válidos)"]
            
        except sqlite3.Error as e:
            return [f"(error: {str(e)})"]
    
    def get_table_row_count(self, table_name):
        """Obtiene el número total de filas en una tabla"""
        try:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return self.cursor.fetchone()[0]
        except sqlite3.Error:
            return 0
    
    def extract_schema_with_examples(self):
        """Extrae el schema completo con ejemplos reales para cada campo"""
        if not self.connect():
            return None
            
        try:
            tables = self.get_tables()
            schema_info = {}
            
            for table in tables:
                print(f"\n📋 Procesando tabla: {table}")
                table_schema = self.get_table_schema(table)
                row_count = self.get_table_row_count(table)
                
                schema_info[table] = {
                    'columns': [],
                    'total_columns': len(table_schema),
                    'row_count': row_count
                }
                
                for column in table_schema:
                    # Obtener ejemplos reales de la base de datos
                    real_examples = self.get_real_examples(table, column['name'])
                    
                    column_info = {
                        'name': column['name'],
                        'type': column['type'],
                        'not_null': column['not_null'],
                        'default_value': column['default_value'],
                        'primary_key': column['primary_key'],
                        'examples': real_examples
                    }
                    
                    schema_info[table]['columns'].append(column_info)
                    
            return schema_info
            
        except sqlite3.Error as e:
            print(f"Error al extraer el schema: {e}")
            return None
        finally:
            if hasattr(self, 'conn'):
                self.conn.close()
    
    def print_schema_report(self, schema_info):
        """Imprime un reporte detallado del schema"""
        if not schema_info:
            print("❌ No se pudo extraer información del schema")
            return
            
        print("\n" + "="*80)
        print("📊 REPORTE DE SCHEMA DE BASE DE DATOS SQLite")
        print("="*80)
        print(f"📁 Base de datos: {self.db_path}")
        print(f"🏷️  Total de tablas: {len(schema_info)}")
        
        for table_name, table_info in schema_info.items():
            print(f"\n🔷 TABLA: {table_name}")
            print(f"   Columnas: {table_info['total_columns']}")
            print(f"   Filas: {table_info['row_count']}")
            print("   " + "-"*60)
            
            for column in table_info['columns']:
                print(f"   📌 {column['name']} ({column['type']})")
                
                # Información adicional
                flags = []
                if column['primary_key']:
                    flags.append("🔑 PRIMARY KEY")
                if column['not_null']:
                    flags.append("❗ NOT NULL")
                if column['default_value']:
                    flags.append(f"📋 DEFAULT: {column['default_value']}")
                    
                if flags:
                    print(f"      {' | '.join(flags)}")
                
                # Ejemplos reales
                examples_str = ', '.join(map(str, column['examples']))
                print(f"      💡 Ejemplos reales: {examples_str}")
                print()
    
    def print_summary_report(self, schema_info):
        """Imprime un reporte resumido más compacto"""
        if not schema_info:
            print("❌ No se pudo extraer información del schema")
            return
            
        print("\n" + "="*80)
        print("📊 RESUMEN DE BASE DE DATOS SQLite")
        print("="*80)
        print(f"📁 Base de datos: {self.db_path}")
        
        total_tables = len(schema_info)
        total_columns = sum(table['total_columns'] for table in schema_info.values())
        total_rows = sum(table['row_count'] for table in schema_info.values())
        
        print(f"🏷️  Total de tablas: {total_tables}")
        print(f"📊 Total de columnas: {total_columns}")
        print(f"📈 Total de filas: {total_rows}")
        
        for table_name, table_info in schema_info.items():
            print(f"\n📋 {table_name} ({table_info['row_count']} filas)")
            for column in table_info['columns']:
                examples_str = ', '.join(map(str, column['examples'][:2]))  # Solo 2 ejemplos
                print(f"   • {column['name']} ({column['type']}) → {examples_str}")
    
    def export_to_json(self, schema_info, output_file):
        """Exporta el schema a un archivo JSON"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(schema_info, f, indent=2, ensure_ascii=False, default=str)
            print(f"✅ Schema exportado a: {output_file}")
        except Exception as e:
            print(f"❌ Error al exportar a JSON: {e}")

def main():
    """Función principal"""
    print("🔍 Extractor de Schema SQLite con Ejemplos REALES")
    print("-" * 55)
    
    # Solicitar ruta de la base de datos
    if len(argv) < 2:
        print("❌ Uso: python script.py <ruta_base_datos.db>")
        return
        
    db_path = argv[1]
    
    # Crear extractor
    extractor = SQLiteSchemaExtractor(db_path)
    
    # Extraer schema
    print("\n🔄 Extrayendo schema y ejemplos reales...")
    schema_info = extractor.extract_schema_with_examples()
    
    if schema_info:
        # Preguntar tipo de reporte
        print("\n📋 Selecciona el tipo de reporte:")
        print("1. Reporte detallado")
        print("2. Reporte resumido")
        
        choice = input("Opción (1 o 2, por defecto 1): ").strip()
        
        if choice == "2":
            extractor.print_summary_report(schema_info)
        else:
            extractor.print_schema_report(schema_info)
        
        # Preguntar si exportar a JSON
        export = input("\n💾 ¿Deseas exportar el schema a un archivo JSON? (s/n): ").strip().lower()
        if export in ['s', 'si', 'yes', 'y']:
            output_file = input("📝 Nombre del archivo JSON (schema.json): ").strip()
            if not output_file:
                output_file = "schema.json"
            extractor.export_to_json(schema_info, output_file)
    
    print("\n✨ ¡Proceso completado!")

if __name__ == "__main__":
    main()