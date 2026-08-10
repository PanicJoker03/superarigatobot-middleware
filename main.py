# fast api example middleware to link watson assistant x to knowledge base
from fastapi import FastAPI
import os

app = FastAPI()

def buscar_disponibilidad_aproximada(handle_recibido: str) -> str:
    file_path = "knowledge_base.txt"
    
    if not os.path.exists(file_path):
        return "No"
        
    # 1. Limpiar el handle y extraer palabras clave de más de 3 letras
    # Ejemplo: "tasa-mario-verde" -> ["tasa", "mario", "verde"]
    palabras_handle = [
        p.lower() for p in handle_recibido.replace("-", " ").split() 
        if len(p) > 3
    ]
    
    # Si el handle no tiene palabras significativas, no podemos buscar de forma segura
    if not palabras_handle:
        return "No"

    # 2. Leer e iterar el archivo línea por línea
    with open(file_path, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    for i, linea in enumerate(lineas):
        linea_lower = linea.lower()
        
        # 3. Filtrar solo las líneas que pregunten por disponibilidad
        if "is" in linea_lower and "available" in linea_lower:
            # Extraer palabras de la línea de más de 3 letras
            palabras_linea = [p for p in linea_lower.split() if len(p) > 3]
            
            # 4. Verificar si ALGUNA palabra del handle coincide con la línea
            # Ejemplo: Si el handle tiene "mario" y la línea tiene "mario", hay coincidencia
            coincidencia = any(palabra in palabras_linea for palabra in palabras_handle)
            
            if coincidencia:
                # 5. Si coincide la pregunta (Q:), revisamos la respuesta (A:) que está en la siguiente línea (i + 1)
                if i + 1 < len(lineas):
                    siguiente_linea = lineas[i + 1].lower()
                    # Validamos si la respuesta confirma la compra exitosa
                    if "currently available" in siguiente_linea and "archived" not in siguiente_linea:
                        return "Yes"
                    else:
                        return "No"

    return "No"

@app.get("/product/{handle}")
async def get_product(handle: str):
    # Query Shopify here
    status = buscar_disponibilidad_aproximada(handle)
    return {"product_availability": status}