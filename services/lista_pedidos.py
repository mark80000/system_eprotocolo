from services.servico_base import executar_servico

# Adicionado um parâmetro para que o status possa ser dinâmico
def listar_pedidos(id_status: int = 1):
    wsdl = "https://origin-hml3-wsoficio.onr.org.br/eprotocolo.asmx?wsdl"

    parametros = {
        "MaxRowPerPage": 300,
        "PageNumber": 1,
        "Protocolo": "",
        "Instituicao": "",
        "IDTipoServico": -1,
        "IDStatus": id_status,  # Usa o ID do status passado como parâmetro
        "DataSolicitacaoInicial": "2025-07-01",
        "DataSolicitacaoFinal": "2025-08-13",
        "NumeroBanco": -1
    }

    # Se o id_status for None, removemos a chave para não filtrar por status
    if id_status is None:
        del parametros["IDStatus"]

    resposta = executar_servico(wsdl_url=wsdl, nome_metodo="ListPedidosAC", parametros=parametros)
    return resposta

# Teste execução direta.
if __name__ == "__main__":
    try:
        # Testando com o status padrão (1) e com o status "Reaberto" (8)
        resposta_aberto = listar_pedidos(id_status=1)
        print("Pedidos em aberto:", resposta_aberto)

        resposta_reaberto = listar_pedidos(id_status=8)
        print("Pedidos reabertos:", resposta_reaberto)
        
        with open("lista.txt", "w", encoding="utf-8") as f:
            f.write(f"Pedidos em aberto: {resposta_aberto}\n")
            f.write(f"Pedidos reabertos: {resposta_reaberto}\n")

    except Exception as e:
        print(f"Ocorreu um erro: {e}")