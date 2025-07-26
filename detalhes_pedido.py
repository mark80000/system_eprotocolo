# Consulta os detalhes/informações de um pedido específico via GetPedidoAC_V7.

from servico_base import executar_servico

def get_pedido_ac_v7(id_pedido: int):
    wsdl = "https://origin-hml3-wsoficio.onr.org.br/Pedido.asmx?wsdl"

    parametros = {
        "IDPedido": id_pedido
    }

    resposta = executar_servico(wsdl, "GetPedidoAC_V7", parametros)
    return resposta


# Teste simples
if __name__ == "__main__":
    try:
        pedido_id = 123456  # Substituir pelo ID real de algum pedido
        resultado = get_pedido_ac_v7(pedido_id)
        print(resultado)
    except Exception as e:
        print("Erro ao consultar pedido:", e)