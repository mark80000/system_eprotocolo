# Chamada da função para Login, responsável por solicitar Tokens, mandando dados do Certificado Digital e ID como parâmetros de entrada.

import os
from zeep import Client
from zeep.transports import Transport
from requests import Session
from database.tokens_db import inicializar_banco, salvar_tokens
from dotenv import load_dotenv

load_dotenv()  # Carrega o .env

# Função para chamar serviço SOAP LoginUsuarioCertificado.
def chamar_login():
    certificado = {
        "SUBJECTCN": os.getenv("CERT_SUBJECTCN"),
        "ISSUERO": os.getenv("CERT_ISSUERO"),
        "PUBLICKEY": os.getenv("CERT_PUBLICKEY"),
        "SERIALNUMBER": os.getenv("CERT_SERIALNUMBER"),
        "VALIDUNTIL": os.getenv("CERT_VALIDUNTIL"),
        "CPF": os.getenv("CERT_CPF"),
        "EMAIL": os.getenv("CERT_EMAIL"),
        "IDParceiroWS": int(os.getenv("ID_PARCEIRO_WS"))
    }

    wsdl = "https://origin-hml3-wsoficio.onr.org.br/login.asmx?WSDL"
    session = Session()
    transport = Transport(session=session)
    client = Client(wsdl=wsdl, transport=transport)

    print("Enviando dados do certificado para ONR...")
    return client.service.LoginUsuarioCertificado(oRequest=certificado)

# Teste execução direta.
if __name__ == "__main__":
    try:
        print("Inicializando banco de dados de tokens...")
        inicializar_banco()

        response = chamar_login()

        print("Resposta da ONR:")
        print(response)

        if response.RETORNO:
            tokens = response.Tokens.string
            print(f"{len(tokens)} tokens recebidos. Salvando no banco...")
            salvar_tokens(tokens)
        else:
            print(f"Erro no login: {response.CODIGOERRO} - {response.ERRODESCRICAO}")

    except Exception as e:
        print("Erro:", e)