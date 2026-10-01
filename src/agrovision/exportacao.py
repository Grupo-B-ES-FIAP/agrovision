import csv
import io
import json
from datetime import datetime

CAMPOS = ["nome_imagem", "categoria", "acuracia", "data", "localidade", "origem"]


def gerar_csv(resultados):
    buffer = io.StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=CAMPOS, delimiter=";")
    escritor.writeheader()
    for linha in resultados:
        escritor.writerow({campo: linha.get(campo, "") for campo in CAMPOS})
    return "\ufeff" + buffer.getvalue()


def gerar_json(resultados):
    return json.dumps({"gerado_em": datetime.now().isoformat(timespec="seconds"),
                       "total_imagens": len(resultados), "resultados": resultados},
                      ensure_ascii=False, indent=2)
