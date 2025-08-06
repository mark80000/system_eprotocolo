# Puxa detalhes/informações dos pedidos em aberto a partir de ListPedidosAC e GetPedidoAC_V7, e salva no banco.
import os
import sqlite3
import json
from services.lista_pedidos import listar_pedidos
from services.detalhes_pedido import get_pedido_ac_v7
from zeep.helpers import serialize_object
from decimal import Decimal

DB_PATH = os.path.join("database", "pedidos_onr.db")

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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Serializa objetos complexos
    apresentante = serialize_object(d.DadosApresentante) if d.DadosApresentante else {}
    dados_constricao = serialize_object(d.DadosConstricao) if d.DadosConstricao else {}
    dados_aceite = serialize_object(d.DadosAceite) if d.DadosAceite else {}

    partes = serialize_object(d.Partes) if d.Partes else {}
    comprador = vendedor = {}

    # Divide as partes entre Comprador e Vendedor, e salva.
    for parte in partes.get("GetPedidoAC_DadosParte_WSResp", []):
        if parte.get("Qualidade") == "Comprador":
            comprador = parte
        elif parte.get("Qualidade") == "Vendedor":
            vendedor = parte

    c.execute("""
        INSERT OR REPLACE INTO pedidos_onr (
            IDContrato, Protocolo, IDStatus, IDCartorio, DataRemessa, Solicitante, Telefone, Instituicao,
            Email, TipoDocumento, TipoServico, ImportacaoExtratoXML,
            ApresentanteNome, ApresentanteCPFCNPJ, ApresentanteEmail, ApresentanteVia,
            ApresentanteEndereco, ApresentanteNumero, ApresentanteComplemento, ApresentanteBairro,
            ApresentanteCidade, ApresentanteEstado, ApresentanteCEP, ApresentanteDDD,
            ApresentanteTelefone,
            PrenotacaoDataInclusao, PrenotacaoDataVencimento, PrenotacaoDataReenvio,
            ValorServico, DataResposta, Resposta, AceiteNome, AceiteData,
            TipoCobranca, CertidaoInteiroTeor, TipoIsencao, NrProcesso, FolhasProcesso,
            DataGratuidade, FundamentoLegal, UrlArquivoGratuidade, ProtocoloOrigem,
            TipoConstricao, ProcessoConstricao, VaraConstricao, UsuarioConstricao,
            NumeroProcessoConstricao, NaturezaProcessoConstricao, ValorDividaConstricao,
            DataAutoTermoConstricao, UrlArquivoMandado, NomeComprador, CPFCNPJComprador, NomeVendedor, CPFCNPJVendedor
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        d.IDContrato, d.Protocolo, d.IDStatus, d.IDCartorio, d.DataRemessa, d.Solicitante,
        d.Telefone, d.Instituicao, d.Email, d.TipoDocumento, d.TipoServico,
        d.ImportacaoExtratoXML,
        apresentante.get("Nome"), apresentante.get("CPFCNPJ"), apresentante.get("Email"), apresentante.get("Via"),
        apresentante.get("Endereco"), apresentante.get("Numero"), apresentante.get("Complemento"),
        apresentante.get("Bairro"), apresentante.get("Cidade"), apresentante.get("Estado"), apresentante.get("CEP"),
        apresentante.get("DDD"), apresentante.get("Telefone"),
        d.PrenotacaoDataInclusao, d.PrenotacaoDataVencimento, d.PrenotacaoDataReenvio,
        to_float(d.ValorServico), d.DataResposta, d.Resposta,
        dados_aceite.get("Nome"), dados_aceite.get("Data"),
        d.TipoCobranca, d.CertidaoInteiroTeor, d.TipoIsencao,
        d.NrProcesso, d.FolhasProcesso, d.DataGratuidade,
        d.FundamentoLegal, d.UrlArquivoGratuidade, d.ProtocoloOrigem,
        dados_constricao.get("TipoConstricao"), dados_constricao.get("Processo"),
        dados_constricao.get("Vara"), dados_constricao.get("Usuario"),
        dados_constricao.get("NumeroProcesso"), dados_constricao.get("NaturezaProcesso"),
        to_float(dados_constricao.get("ValorDivida")), dados_constricao.get("DataAutoTermo"),
        d.UrlArquivoMandado, comprador.get("Nome"), comprador.get("CPFCNPJ"),
        vendedor.get("Nome"), vendedor.get("CPFCNPJ")
    ))

    conn.commit()
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