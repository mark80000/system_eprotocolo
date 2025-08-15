from services.servico_base import executar_servico
from datetime import datetime, timedelta

# Adicionado um parâmetro para que o status possa ser dinâmico
def listar_pedidos(data_inicial: str, data_final: str, id_status: int = 1):
    """
    Busca pedidos na API da ONR com base em um status e um período de datas.

    Args:
        data_inicial (str): A data de início do período de busca, no formato "AAAA-MM-DD".
        data_final (str): A data de fim do período de busca, no formato "AAAA-MM-DD".
        id_status (int): O ID do status do pedido (por exemplo, 1 para "Em aberto").
                         O padrão é 1.
    """
    wsdl = "https://origin-hml3-wsoficio.onr.org.br/eprotocolo.asmx?wsdl"

    parametros = {
        "MaxRowPerPage": 300,
        "PageNumber": 1,
        "Protocolo": "",
        "Instituicao": "",
        "IDTipoServico": -1,
        "IDStatus": id_status,
        "DataSolicitacaoInicial": data_inicial,
        "DataSolicitacaoFinal": data_final,
        "NumeroBanco": -1
    }

    # Se o id_status for None, removemos a chave para não filtrar por status
    if id_status is None:
        del parametros["IDStatus"]

    resposta = executar_servico(wsdl_url=wsdl, nome_metodo="ListPedidosAC", parametros=parametros)
    return resposta

# Teste de execução direta para demonstrar como a função deve ser chamada.
if __name__ == "__main__":
    try:
        # Define as datas para o teste.
        hoje = datetime.now().date()
        um_dia_antes = hoje - timedelta(days=1)
        data_inicial_str = um_dia_antes.strftime("%Y-%m-%d")
        data_final_str = hoje.strftime("%Y-%m-%d")

        # Testando com o status padrão (1)
        resposta_aberto = listar_pedidos(
            data_inicial=data_inicial_str,
            data_final=data_final_str,
            id_status=1
        )
        print("Pedidos em aberto:", resposta_aberto)

        # Testando com o status "Reaberto" (8)
        resposta_reaberto = listar_pedidos(
            data_inicial=data_inicial_str,
            data_final=data_final_str,
            id_status=8
        )
        print("Pedidos reabertos:", resposta_reaberto)
        
        with open("lista.txt", "w", encoding="utf-8") as f:
            f.write(f"Pedidos em aberto: {resposta_aberto}\n")
            f.write(f"Pedidos reabertos: {resposta_reaberto}\n")

    except Exception as e:
        print(f"Ocorreu um erro: {e}")