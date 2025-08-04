# Chamada da função para Login, responsável por solicitar Tokens mandando dados do Certificado Digital e ID como parâmetros de entrada.

import ctypes
from ctypes import wintypes
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import base64
import re
from zeep import Client
from zeep.transports import Transport
from requests import Session
from database.tokens_db import inicializar_banco, salvar_tokens

# Função para extrair dados do certificado.
def obter_dados_certificado():
    crypt32 = ctypes.WinDLL('crypt32.dll')

    crypt32.CertOpenSystemStoreW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR]
    crypt32.CertOpenSystemStoreW.restype = wintypes.HANDLE

    crypt32.CertEnumCertificatesInStore.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
    crypt32.CertEnumCertificatesInStore.restype = ctypes.POINTER(ctypes.c_void_p)

    crypt32.CertCloseStore.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    crypt32.CertCloseStore.restype = wintypes.BOOL

    class CERT_CONTEXT(ctypes.Structure):
        _fields_ = [
            ("dwCertEncodingType", wintypes.DWORD),
            ("pbCertEncoded", ctypes.POINTER(ctypes.c_byte)),
            ("cbCertEncoded", wintypes.DWORD),
            ("pCertInfo", ctypes.c_void_p),
            ("hCertStore", wintypes.HANDLE)
        ]

    crypt32.CertEnumCertificatesInStore.argtypes = [wintypes.HANDLE, ctypes.POINTER(CERT_CONTEXT)]
    crypt32.CertEnumCertificatesInStore.restype = ctypes.POINTER(CERT_CONTEXT)

    hCertStore = crypt32.CertOpenSystemStoreW(0, "MY")
    if not hCertStore:
        raise RuntimeError("Não foi possível abrir a store 'MY'.")

    pCertContext = crypt32.CertEnumCertificatesInStore(hCertStore, None)

    if not pCertContext:
        crypt32.CertCloseStore(hCertStore, 0)
        raise RuntimeError("Nenhum certificado encontrado.")

    cert_array = ctypes.cast(
        pCertContext.contents.pbCertEncoded,
        ctypes.POINTER(ctypes.c_ubyte * pCertContext.contents.cbCertEncoded)
    )
    cert_bytes = bytes(cert_array.contents)
    cert = x509.load_der_x509_certificate(cert_bytes, default_backend())

    subject_cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value

    try:
        issuer_o = cert.issuer.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)[0].value
    except IndexError:
        issuer_o = ""

    public_key = cert.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    public_key_b64 = ''.join(public_key.replace("-----BEGIN PUBLIC KEY-----", "")
                                         .replace("-----END PUBLIC KEY-----", "")
                                         .splitlines())

    serial_number = hex(cert.serial_number)[2:].lower()
    valid_until = cert.not_valid_after_utc.isoformat()

    cpf_match = re.search(r"(\d{11})", subject_cn)
    cpf = cpf_match.group(1) if cpf_match else ""

    email = ""
    try:
        ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        san = ext.value
        emails = san.get_values_for_type(x509.RFC822Name)
        if emails:
            email = emails[0]
    except x509.ExtensionNotFound:
        pass

    crypt32.CertCloseStore(hCertStore, 0)

    return {
        "SUBJECTCN": subject_cn,
        "ISSUERO": issuer_o,
        "PUBLICKEY": public_key_b64,
        "SERIALNUMBER": serial_number,
        "VALIDUNTIL": valid_until,
        "CPF": cpf,
        "EMAIL": email
    }

# Função para chamar serviço SOAP LoginUsuarioCertificado.
def chamar_login(cert_data, id_parceiro):
    cert_data["IDParceiroWS"] = id_parceiro

    wsdl = "https://origin-hml3-wsoficio.onr.org.br/login.asmx?WSDL"
    
    # Configuração com certificado A3
    session = Session()
    session.mount('https://', Pkcs12Adapter(
        pkcs12_filename="caminho/do/certificado.p12",  # Substitua
        pkcs12_password="sua_senha"  # Substitua
    ))
    
    client = Client(
        wsdl=wsdl,
        transport=Transport(session=session),
        settings=Settings(raw_response=True)
    )

    print("Enviando dados para ONR com autenticação TLS...")
    resposta = client.service.LoginUsuarioCertificado(oRequest=cert_data)
    
    # Debug: mostra o XML completo
    print("Resposta bruta:")
    print(resposta.content.decode('utf-8'))
    
    return resposta

# Execução principal.
if __name__ == "__main__":
    try:
        from database.tokens_db import inicializar_banco, salvar_tokens  # importante importar funções

        id_parceiro_ws = 2507  # ID FORNECIDO PELA ONR.

        print("Inicializando banco de dados de tokens...")
        inicializar_banco()

        print("Obtendo dados do certificado...")
        dados = obter_dados_certificado()

        print("Fazendo login na ONR...")
        resposta = chamar_login(dados, id_parceiro_ws)
        print(dados)
        print('-'*80)

        print("Resposta da ONR:")
        print(resposta)

        if resposta.RETORNO:
            tokens = resposta.Tokens.string
            print(f"{len(tokens)} tokens recebidos. Salvando no banco...")
            salvar_tokens(tokens)
        else:
            print(f"Erro no login: {resposta.CODIGOERRO} - {resposta.ERRODESCRICAO}")

    except Exception as e:
        print("Erro:", e)