# Código base para os serviços. Procura token, faz login para solicitar tokens, gera hash, executa serviço.

from zeep import Client
from zeep.transports import Transport
from requests import Session
from tokens_db import CHAVE, obter_token_valido, gerar_hash, marcar_token_como_usado, salvar_tokens
from login import obter_dados_certificado, chamar_login

ID_PARCEIRO_WS = 5  #ID FORNECIDO PELA ONR.  

CERTIFICADO_FIXO = {
    "SUBJECTCN": "DANIEL AFONSO MARCILIO DE MAGALHAES FILHO:00805111476",
    "ISSUERO": "ICP-Brasil",
    "PUBLICKEY": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwBsXbZRN4oZHRRnh8kLus1YCtpqddiBB4kX12G9W13+HeGidg3Fa4HmIxgxlpUvh6QEVL65obIWyqlX7Uz33NX4nbsqSIad/mU09vS79xJfg2ZjvBrjti0zXKtMrxv6sfZyumRqLc7WxrmbFzVwQK0XS7lyQymR2P+thCVA1OBRXGUOw9+BFJrPdavqaevnXTw3fPPNhkqLFhbGwY1Qu+PXN15jsj+BEkGH1mpZU4ajAf+6U1uTbm2ZTRJySCm0nZ4LtjsPVPk/2iXl9K5Vfi3vD1o++uGukoMd/w1aVJsmsFZhR3mXfblUtE9jLCK4EFoa/B4pP4PMl9ILr5n1GGQIDAQAB",
    "SERIALNUMBER": "4173fc12c765e15bd94af80932b8963e",
    "VALIDUNTIL": "2027-04-22T19:16:44+00:00",
    "CPF": "00805111476",
    "EMAIL": "DANIELFILHO@MAGALHAES.NET.BR"
}

def obter_token_ou_fazer_login():
    resultado = obter_token_valido()
    if resultado:
        return resultado

    print("Nenhum token válido. Realizando login...")
    dados = CERTIFICADO_FIXO
    resposta = chamar_login(dados, ID_PARCEIRO_WS)

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