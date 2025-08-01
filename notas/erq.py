from zeep import Client

WSDL_URL = "https://origin-hml3-wsoficio.onr.org.br/login.asmx?WSDL"
client = Client(WSDL_URL)

Login_WSReq = client.get_type("ns0:Login_WSReq")
request_data = Login_WSReq(
    SUBJECTCN="DANIEL AFONSO MARCILIO DE MAGALHAES FILHO:00805111476",
    ISSUERO="ICP-Brasil",
    PUBLICKEY="MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwBsXbZRN4oZHRRnh8kLus1YCtpqddiBB4kX12G9W13+HeGidg3Fa4HmIxgxlpUvh6QEVL65obIWyqlX7Uz33NX4nbsqSIad/mU09vS79xJfg2ZjvBrjti0zXKtMrxv6sfZyumRqLc7WxrmbFzVwQK0XS7lyQymR2P+thCVA1OBRXGUOw9+BFJrPdavqaevnXTw3fPPNhkqLFhbGwY1Qu+PXN15jsj+BEkGH1mpZU4ajAf+6U1uTbm2ZTRJySCm0nZ4LtjsPVPk/2iXl9K5Vfi3vD1o++uGukoMd/w1aVJsmsFZhR3mXfblUtE9jLCK4EFoa/B4pP4PMl9ILr5n1GGQIDAQAB",  # insira a chave real
    SERIALNUMBER="4173fc12c765e15bd94af80932b8963e",
    VALIDUNTIL="2027-04-22T19:16:44+00:00",
    CPF="00805111476",
    EMAIL="DANIELFILHO@MAGALHAES.NET.BR",
    IDParceiroWS=5
)

# Chamada correta ao serviço
response = client.service.LoginUsuarioCertificado(oRequest=request_data)

print(response)