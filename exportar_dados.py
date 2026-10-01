import csv
import io
import json
from datetime import datetime


CAMPOS = ["nome_imagem", "categoria", "acuracia"]

def gerar_csv(resultados: list[dict]) -> str: 
    buffer = io.StringIO()
    
    escritor = csv.DictWriter(buffer, fieldnames=CAMPOS, delimiter=";")
    escritor.writeheader()
    
    for linha in resultados:
        escritor.writerow({
            "nome_imagem": linha.get("nome_imagem", ""),
            "categoria": linha.get("categoria",""),
            "acuracia": f"{linha.get('acuracia', 0)}%",
        })
    return "\ufeff" + buffer.getvalue()

def gerar_json(resultados: list[dict]) -> str: 
    
    pacote = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_imagens": len(resultados),
        "resultados": [
            {
                "nome_imagem": linha.get("nome_imagem", ""),
                "categoria": linha.get("categoria",""),
                "acuracia": f"{linha.get('acuracia', 0)}%",
            }
            for linha in resultados
        ],
    }
    return json.dumps(pacote, ensure_ascii=False, indent=2)
