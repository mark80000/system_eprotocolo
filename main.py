from services.sincronizar_pedidos import sincronizar_pedidos
from database.tokens_db import inicializar_banco

if __name__ == "__main__":
    inicializar_banco()
    print("Iniciando sincronização com a ONR...")
    sincronizar_pedidos()