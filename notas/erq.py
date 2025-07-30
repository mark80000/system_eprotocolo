from zeep import Client

WSDL_URL = "https://origin-hml3-wsoficio.onr.org.br/login.asmx?WSDL"
client = Client(WSDL_URL)

Login_WSReq = client.get_type("ns0:Login_WSReq")
request_data = Login_WSReq(
    SUBJECTCN="MARCUS VINICIUS ANDRADE DA SILVA:13778462458",
    ISSUERO="AC Certisign RFB G5",
    PUBLICKEY="3MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAx9mI2FAgazMlf56g+i09P2vqSzmgrlNEi16Yh00CkafsO6WSbUED3g2lLpXXiozK6PQaxmKjSzq1MSRzJSyEu8IMWCE9cjqt08aDgkVVmnjwRzsZpCzyFFNSTebZP/GSmro4Ip5vnlhn3NsXttuaDbh7ukcBu/nGC8x7fug7ZOgloNXCrEZG2f9XrLAT3XKDuchEd2ucFxy4MncOJDtWinWKJcnnUoyCkqK5Fw2GyGDbeG8VjIaMULgAV3KT0NY/N7T5NTEBcPca+P2jnlem4IE17UIF7oC4TAchXmGuXvhqSySr+qypYKdAtT2Gr+DTprCby+FEBtcTn72bwTz+IQIDAQAB",  # insira a chave real
    SERIALNUMBER="7ec3fba6cb5d68762e8cf8961efcc8af",
    VALIDUNTIL="2028-04-23T18:33:15+00:00",
    CPF="13778462458",
    EMAIL="marcusviniandrade0@gmail.com",
    IDParceiroWS=5
)

# Chamada correta ao serviço
response = client.service.LoginUsuarioCertificado(oRequest=request_data)

print(response)