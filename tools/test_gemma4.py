import requests
import time

# Pega aquí el anuncio real, sin importar saltos de línea o comillas
descripcion_larga = """
Opel corsa edition /  aÑo 2020 / 64.600 km

- 1.5 cdti edition / 100 cv / diesel
- 64.700km
- cambio manual 6 vel.
- sensores del / tras
-camara trasera
- control carril
- cierre centralizado / 2 llaves mando
- climatizador 
- aÑo 2020
- elevalunas electricos 
- control velocidad y crucero
- carroceria 5 puertas
- radio pantalla conect tactil
- ordenador abordo 
- car play
- revision completa  
- kilometros certificados dgt



-financiacion variable en condiciones 
-anuncio verificado salvo error tipografico
"""

payload = {
    "model": "gemma4:e4b",
    "prompt": "Evalúa esta descripción. Responde SOLO en formato JSON estricto con la clave 'averia_grave' y valor booleano true o false. Descripción: " + descripcion_larga,
    "stream": False,
    "format": "json",
    "options": {
        "num_predict": 15, 
        "temperature": 0.0
    }
}

print("Analizando descripción...")
start_time = time.time()

try:
    response = requests.post("http://localhost:11434/api/generate", json=payload)
    end_time = time.time()
    
    data = response.json()
    print(f"\n[TIEMPO REAL]: {end_time - start_time:.2f} segundos")
    print(f"[JSON OLLAMA]: {data.get('response')}")
    
except Exception as e:
    print(f"Error de conexión: {e}")