# Código base para os serviços. Procura token, faz login para solicitar tokens, gera hash, executa serviço.

from zeep import Client
from zeep.transports import Transport
from requests import Session
from database.tokens_db import CHAVE, obter_token_valido, gerar_hash, marcar_token_como_usado, salvar_tokens, limpar_tokens_antigos
from services.login import chamar_login 

# Pega token disponível, caso não tenha, faz login.
def obter_token_ou_fazer_login():

    limpar_tokens_antigos(horas=24)
    resultado = obter_token_valido()
    if resultado:
        return resultado

    print("Nenhum token válido. Realizando login...")
    resposta = chamar_login()

    if not resposta.RETORNO:
        raise RuntimeError(f"Login falhou: {resposta.CODIGOERRO} - {resposta.ERRODESCRICAO}")

    tokens = resposta.Tokens.string
    if not tokens:
        raise RuntimeError("Login bem-sucedido, mas nenhum token retornado.")

    salvar_tokens(tokens)

    resultado = obter_token_valido()
    if not resultado:
        raise RuntimeError("Nenhum token válido mesmo após login.")

    return resultado


def executar_servico(wsdl_url: str, nome_metodo: str, parametros: dict):
    """
    Executa um serviço SOAP da ONR com autenticação via token.
    - wsdl_url: URL completa do serviço
    - nome_metodo: nome da operação (ex: 'ListPedidosAC')
    - parametros: dicionário com parâmetros SOAP (exceto 'Hash', que será injetado)
    """
    token_id, token = obter_token_ou_fazer_login()
    hash_valido = gerar_hash(CHAVE, token)

    parametros_completos = {
        "Hash": hash_valido,
        **parametros
    }

    session = Session()
    client = Client(wsdl=wsdl_url, transport=Transport(session=session))

    metodo = getattr(client.service, nome_metodo)
    resposta = metodo(oRequest=parametros_completos)

    marcar_token_como_usado(token_id)
    return resposta