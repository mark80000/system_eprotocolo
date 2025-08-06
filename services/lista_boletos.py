from services.servico_base import executar_servico

def listar_boletos(id_contrato: int):
    wsdl = "https://origin-hml3-wsoficio.onr.org.br/eprotocolo.asmx?wsdl"

    parametros = {
        "IDContrato": id_contrato
    }

    resposta = executar_servico(wsdl, "ListBoletosAC", parametros)
    return resposta


# Teste execução direta.
if __name__ == "__main__":
    try:
        contrato_id = 3460100  
        resultado = listar_boletos(contrato_id)
        print(resultado)
    except Exception as e:
        print("Erro ao consultar pedido:", e)