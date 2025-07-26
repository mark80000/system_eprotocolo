import ctypes
from ctypes import wintypes
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import base64
import re

crypt32 = ctypes.WinDLL('crypt32.dll')

# Assinaturas corretas das funções
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

# Atualiza o tipo de retorno da função
crypt32.CertEnumCertificatesInStore.argtypes = [wintypes.HANDLE, ctypes.POINTER(CERT_CONTEXT)]
crypt32.CertEnumCertificatesInStore.restype = ctypes.POINTER(CERT_CONTEXT)

# Abre a store "MY"
hCertStore = crypt32.CertOpenSystemStoreW(0, "MY")
if not hCertStore:
    print("Não foi possível abrir a store 'MY'.")
    exit(1)

pCertContext = crypt32.CertEnumCertificatesInStore(hCertStore, None)

while pCertContext:
    cert_array = ctypes.cast(
        pCertContext.contents.pbCertEncoded,
        ctypes.POINTER(ctypes.c_ubyte * pCertContext.contents.cbCertEncoded)
    )
    cert_bytes = bytes(cert_array.contents)
    cert = x509.load_der_x509_certificate(cert_bytes, default_backend())

    # SUBJECTCN
    subject_cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value

    # ISSUERO
    try:
        issuer_o = cert.issuer.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)[0].value
    except IndexError:
        issuer_o = ""

    # PUBLICKEY (em base64 sem quebras)
    public_key = cert.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    public_key_b64 = ''.join(public_key.replace("-----BEGIN PUBLIC KEY-----", "")
                                         .replace("-----END PUBLIC KEY-----", "")
                                         .splitlines())

    # SERIALNUMBER
    serial_number = hex(cert.serial_number)[2:].lower()

    # VALIDUNTIL
    valid_until = cert.not_valid_after_utc.isoformat()

    # CPF (extraído do CN com regex)
    cpf_match = re.search(r"(\d{11})", subject_cn)
    cpf = cpf_match.group(1) if cpf_match else ""

    # EMAIL (se existir em SubjectAlternativeName)
    email = ""
    try:
        ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        san = ext.value
        emails = san.get_values_for_type(x509.RFC822Name)
        if emails:
            email = emails[0]
    except x509.ExtensionNotFound:
        pass

    # Exibe os dados formatados
    print("-" * 80)
    print("SUBJECTCN:", subject_cn)
    print("ISSUERO:", issuer_o)
    print("PUBLICKEY:", public_key_b64)
    print("SERIALNUMBER:", serial_number)
    print("VALIDUNTIL:", valid_until)
    print("CPF:", cpf)
    print("EMAIL:", email)
    print("-" * 80)

    pCertContext = crypt32.CertEnumCertificatesInStore(hCertStore, pCertContext)

crypt32.CertCloseStore(hCertStore, 0)