# Lista os pedidos em aberto via ListPedidosAC.

from servico_base import executar_servico

def listar_pedidos_em_aberto():
    wsdl = "https://origin-hml3-wsoficio.onr.org.br/Pedido.asmx?wsdl"

    parametros = {
        "MaxRowPerPage": 50,
        "PageNumber": 1,
        "Protocolo": "",
        "Instituicao": "",
        "IDTipoServico": -1,
        "IDStatus": 1,  # 1 = Em aberto
        "DataSolicitacaoInicial": "",
        "DataSolicitacaoFinal": "",
        "NumeroBanco": -1
    }

    resposta = executar_servico(wsdl_url=wsdl, nome_metodo="ListPedidosAC", parametros=parametros)
    return resposta


# Execução de teste direta.
if __name__ == "__main__":
    try:
        resposta = listar_pedidos_em_aberto()
        print(resposta)
    except Exception as e:
        print("Erro ao listar pedidos em aberto:", e)