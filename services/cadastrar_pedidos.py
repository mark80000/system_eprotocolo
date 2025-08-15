# Puxa detalhes/informações dos pedidos em aberto a partir de ListPedidosAC e GetPedidoAC_V7, e salva no banco.

import os
import sqlite3
import json
from services.lista_pedidos import listar_pedidos
from services.detalhes_pedido import get_pedido_ac_v7
from zeep.helpers import serialize_object
from decimal import Decimal

DB_PATH = os.path.join("database", "cartorio.db")

# Transforma valor decimal em float.
def to_float(val):
    if isinstance(val, Decimal):
        return float(val)
    return val

# Cria tabela para armazenamento dos dados.
def criar_tabela_se_nao_existir():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS pedidos_onr (
            IDContrato INTEGER PRIMARY KEY,
            Protocolo TEXT,
            IDStatus INTEGER,
            IDCartorio INTEGER,
            DataRemessa TEXT,
            Solicitante TEXT,
            Telefone TEXT,
            Instituicao TEXT,
            Email TEXT,
            TipoDocumento TEXT,
            TipoServico TEXT,
            ImportacaoExtratoXML BOOLEAN,
            ApresentanteNome TEXT,
            ApresentanteCPFCNPJ TEXT,
            ApresentanteEmail TEXT,
            ApresentanteVia TEXT,
            ApresentanteEndereco TEXT,
            ApresentanteNumero TEXT,
            ApresentanteComplemento TEXT,
            ApresentanteBairro TEXT,
            ApresentanteCidade TEXT,
            ApresentanteEstado TEXT,
            ApresentanteCEP TEXT,
            ApresentanteDDD TEXT,
            ApresentanteTelefone TEXT,
            PrenotacaoDataInclusao TEXT,
            PrenotacaoDataVencimento TEXT,
            PrenotacaoDataReenvio TEXT,
            ValorServico REAL,
            DataResposta TEXT,
            Resposta TEXT,
            AceiteNome TEXT,
            AceiteData TEXT,
            TipoCobranca INTEGER,
            CertidaoInteiroTeor INTEGER,
            TipoIsencao INTEGER,
            NrProcesso TEXT,
            FolhasProcesso TEXT,
            DataGratuidade TEXT,
            FundamentoLegal TEXT,
            UrlArquivoGratuidade TEXT,
            ProtocoloOrigem TEXT,
            TipoConstricao TEXT,
            ProcessoConstricao TEXT,
            VaraConstricao TEXT,
            UsuarioConstricao TEXT,
            NumeroProcessoConstricao TEXT,
            NaturezaProcessoConstricao TEXT,
            ValorDividaConstricao REAL,
            DataAutoTermoConstricao TEXT,
            UrlArquivoMandado TEXT,
            NomeComprador TEXT,
            CPFCNPJComprador TEXT,
            NomeVendedor TEXT,
            CPFCNPJVendedor TEXT
        )
    """)
    conn.commit()
    conn.close()

# Salva dados na tabela.
def salvar_detalhes_pedido(d):
    """
    Salva os detalhes de um pedido na tabela do banco de dados.

    Args:
        d (dict): Um dicionário contendo os detalhes do pedido.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Extrai os dados do dicionário de forma segura
        apresentante = d.get('DadosApresentante', {})
        imovel_transacao = d.get('DadosImovelTransacao', {})
        imovel_dados = d.get('DadosImovel', {})

        pedido_data = {
            "IDContrato": d.get("IDContrato"),
            "Protocolo": d.get("Protocolo"),
            "IDStatus": d.get("IDStatus"),
            "IDCartorio": d.get("IDCartorio"),
            "DataRemessa": d.get("DataRemessa"),
            "Solicitante": d.get("Solicitante"),
            "Telefone": d.get("Telefone"),
            "Instituicao": d.get("Instituicao"),
            "Email": d.get("Email"),
            "TipoDocumento": d.get("TipoDocumento"),
            "TipoServico": d.get("TipoServico"),
            "ImportacaoExtratoXML": d.get("ImportacaoExtratoXML"),
            "ApresentanteNome": apresentante.get("Nome"),
            "ApresentanteCPFCNPJ": apresentante.get("CPFCNPJ"),
            "ApresentanteEmail": apresentante.get("Email"),
            "ApresentanteVia": apresentante.get("Via"),
            "ApresentanteEndereco": apresentante.get("Endereco"),
            "ApresentanteNumero": apresentante.get("Numero"),
            "ApresentanteComplemento": apresentante.get("Complemento"),
            "ApresentanteBairro": apresentante.get("Bairro"),
            "ApresentanteCidade": apresentante.get("Cidade"),
            "ApresentanteEstado": apresentante.get("Estado"),
            "ApresentanteCEP": apresentante.get("CEP"),
            "ApresentanteDDD": apresentante.get("DDD"),
            "ApresentanteTelefone": apresentante.get("Telefone"),
            "PrenotacaoDataInclusao": d.get("PrenotacaoDataInclusao"),
            "PrenotacaoDataVencimento": d.get("PrenotacaoDataVencimento"),
            "PrenotacaoDataReenvio": d.get("PrenotacaoDataReenvio"),
            "ValorServico": d.get("ValorServico"),
            "DataResposta": d.get("DataResposta"),
            "Resposta": d.get("Resposta"),
            "AceiteNome": d.get("AceiteNome"),
            "AceiteData": d.get("AceiteData"),
            "TipoCobranca": d.get("TipoCobranca"),
            "CertidaoInteiroTeor": d.get("CertidaoInteiroTeor"),
            "TipoIsencao": d.get("TipoIsencao"),
            "NrProcesso": d.get("NrProcesso"),
            "FolhasProcesso": d.get("FolhasProcesso"),
            "DataGratuidade": d.get("DataGratuidade"),
            "FundamentoLegal": d.get("FundamentoLegal"),
            "UrlArquivoGratuidade": d.get("UrlArquivoGratuidade"),
            "ProtocoloOrigem": d.get("ProtocoloOrigem"),
            "TipoConstricao": d.get("TipoConstricao"),
            "ProcessoConstricao": d.get("ProcessoConstricao"),
            "VaraConstricao": d.get("VaraConstricao"),
            "UsuarioConstricao": d.get("UsuarioConstricao"),
            "NumeroProcessoConstricao": d.get("NumeroProcessoConstricao"),
            "NaturezaProcessoConstricao": d.get("NaturezaProcessoConstricao"),
            "ValorDividaConstricao": d.get("ValorDividaConstricao"),
            "DataAutoTermoConstricao": d.get("DataAutoTermoConstricao"),
            "UrlArquivoMandado": d.get("UrlArquivoMandado"),
            "NomeComprador": imovel_transacao.get("NomeComprador"),
            "CPFCNPJComprador": imovel_transacao.get("CPFCNPJComprador"),
            "NomeVendedor": imovel_transacao.get("NomeVendedor"),
            "CPFCNPJVendedor": imovel_transacao.get("CPFCNPJVendedor")
        }

        colunas = ", ".join(pedido_data.keys())
        placeholders = ", ".join(["?"] * len(pedido_data))
        query = f"INSERT OR REPLACE INTO pedidos_onr ({colunas}) VALUES ({placeholders})"
        cursor.execute(query, tuple(pedido_data.values()))
        conn.commit()

    except sqlite3.Error as e:
        print(f"Erro ao salvar pedido no banco de dados: {e}")
    finally:
        if conn:
            conn.close()    

# Função para puxar os detelhes dos pedidos.
def get_detalhes_pedidos_listados(pedidos):
    detalhes_pedidos = []

    for pedido in pedidos:
        id_contrato = pedido.IDContrato
        print(f"\nConsultando detalhes do contrato ID {id_contrato}...")

        try:
            detalhes = get_pedido_ac_v7(id_contrato)
            if detalhes.RETORNO:
                detalhes_pedidos.append(detalhes)
            else:
                print(f"Erro no contrato {id_contrato}: {detalhes.ERRODESCRICAO}")
        except Exception as e:
            print(f"Falha ao obter detalhes do contrato {id_contrato}: {e}")

    return detalhes_pedidos

# Apenas exibe os detalhes no console e salva em .txt para análise manual.
def exibir_detalhes_pedidos():
    try:
        resposta_lista = listar_pedidos()

        if not resposta_lista.RETORNO or not resposta_lista.Pedidos:
            print("Nenhum pedido em aberto encontrado.")
            return

        pedidos = resposta_lista.Pedidos.ListPedidosAC_Pedidos_WSResp
        if not isinstance(pedidos, list):
            pedidos = [pedidos]

        print(f"\n{len(pedidos)} pedidos encontrados:")
        for p in pedidos:
            print(f"IDContrato: {p.IDContrato}, Protocolo: {p.Protocolo}")

        detalhes_lista = get_detalhes_pedidos_listados(pedidos)

        for detalhes in detalhes_lista:
            print(f"\n{'='*80}\nPedido ID {detalhes.IDContrato}:")
            print(json.dumps(serialize_object(detalhes), indent=4, ensure_ascii=False, default=str))

        with open("visualizar_detalhes.txt", "w", encoding="utf-8") as f:
            for detalhes in detalhes_lista:
                json_string = json.dumps(serialize_object(detalhes), indent=4, ensure_ascii=False, default=str)
                f.write(json_string + "\n" + ("=" * 80) + "\n\n")

    except Exception as e:
        print("Erro ao exibir detalhes dos pedidos:", e)

# Lista os pedidos, puxa os detalhes, salva no banco e cria um .txt para vizualização.
def  cadastrar_pedidos():
    try:
        criar_tabela_se_nao_existir()

        resposta_lista = listar_pedidos()

        if not resposta_lista.RETORNO or not resposta_lista.Pedidos:
            print("Nenhum pedido em aberto encontrado.")
            return

        pedidos = resposta_lista.Pedidos.ListPedidosAC_Pedidos_WSResp
        if not isinstance(pedidos, list):
            pedidos = [pedidos]

        print(f"{len(pedidos)} pedidos encontrados.")
        for p in pedidos:
            print(f"IDContrato: {p.IDContrato}, Protocolo: {p.Protocolo}")

        detalhes_lista = get_detalhes_pedidos_listados(pedidos)

        with open("detalhes.txt", "w", encoding="utf-8") as f:
            for detalhes in detalhes_lista:
                json_string = json.dumps(serialize_object(detalhes), indent=4, ensure_ascii=False, default=str)
                f.write(json_string + "\n" + ("=" * 80) + "\n\n")

        for detalhes in detalhes_lista:
            try:
                salvar_detalhes_pedido(detalhes)
                print(f"Contrato {detalhes.IDContrato} salvo com sucesso.")
            except Exception as e:
                print(f"Erro ao salvar contrato {detalhes.IDContrato}: {e}")

    except Exception as e:
        print("Erro geral na sincronização:", e)


if __name__ == "__main__":
    cadastrar_pedidos()