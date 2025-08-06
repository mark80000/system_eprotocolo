from services.cadastrar_pedidos import  cadastrar_pedidos
from database.tokens_db import inicializar_banco
from services.lista_anexos import listar_anexos
from services.lista_pedidos import listar_pedidos
from services.lista_boletos import listar_boletos

def menu():
    print("1. Cadastrar pedidos em aberto.")
    print("2. Listar pedidos em aberto.")
    print("3. Listar anexos de um pedido.")
    print("4. Listar boletos de um pedido.")
    print("0. Sair.")

def executar():
    while True:
        menu()
        escolha = input("Escolha uma opção: ").strip()

        if escolha == "1":
            inicializar_banco()
            print("Iniciando sincronização com a ONR...")
            cadastrar_pedidos()

        elif escolha == "2":
            try:
                resposta = listar_pedidos()
                print(resposta)
                with open("lista.txt", "w", encoding="utf-8") as f:
                    f.write(str(resposta))
                print("Pedidos salvos em lista.txt")
            except Exception as e:
                print("Erro ao listar pedidos:", e)

        elif escolha == "3":
            try:
                contrato_id = int(input("Informe o ID do contrato: "))
                resultado = listar_anexos(contrato_id)
                print(resultado)
            except Exception as e:
                print("Erro ao listar anexos:", e)

        elif escolha == "4":
            try:
                contrato_id = int(input("Informe o ID do contrato: "))
                resultado = listar_boletos(contrato_id)
                print(resultado)
            except Exception as e:
                print("Erro ao listar boletos:", e)

        elif escolha == "0":
            print("Encerrando...")
            break

        else:
            print("Opção inválida. Tente novamente.")

if __name__ == "__main__":
    executar()
    