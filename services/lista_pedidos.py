# Lista os pedidos em aberto via ListPedidosAC.

from services.servico_base import executar_servico

def listar_pedidos():
    wsdl = "https://origin-hml3-wsoficio.onr.org.br/eprotocolo.asmx?wsdl"

    parametros = {
        "MaxRowPerPage": 300,
        "PageNumber": 1,
        "Protocolo": "",
        "Instituicao": "",
        "IDTipoServico": -1,
        "IDStatus": 1,  # 1 = Em aberto
        "DataSolicitacaoInicial": "2025-07-01",
        "DataSolicitacaoFinal": "2025-08-07",
        "NumeroBanco": -1
    }

    resposta = executar_servico(wsdl_url=wsdl, nome_metodo="ListPedidosAC", parametros=parametros)
    return resposta

# Teste execução direta.
if __name__ == "__main__":
    try:
        resposta = listar_pedidos()
        print(resposta)
        with open("lista.txt", "w", encoding="utf-8") as f:
            f.write(str(resposta))
    except Exception as e:
        print("Erro ao listar pedidos em aberto:", e)