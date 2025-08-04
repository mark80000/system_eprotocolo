# Consulta os detalhes/informações de um pedido específico via GetPedidoAC_V7.

from services.servico_base import executar_servico

def get_pedido_ac_v7(id_contrato: int):
    wsdl = "https://origin-hml3-wsoficio.onr.org.br/eprotocolo.asmx?wsdl"

    parametros = {
        "IDContrato": id_contrato
    }

    resposta = executar_servico(wsdl, "GetPedidoAC_V7", parametros)
    return resposta


# Teste execução direta.
if __name__ == "__main__":
    try:
        contrato_id = 2483636  
        resultado = get_pedido_ac_v7(contrato_id)
        print(resultado)
    except Exception as e:
        print("Erro ao consultar pedido:", e)