# Puxa detalhes/informações dos pedidos em aberto a partir de ListPedidosAC e GetPedidoAC_V7.

import sqlite3
from listar_pedidos import listar_pedidos_em_aberto
from detalhes_pedido import get_pedido_ac_v7

DB_PATH = "pedidos_onr.db"

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
            UrlArquivoMandado TEXT
        )
    """)
    conn.commit()
    conn.close()


def salvar_detalhes_pedido(detalhes):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    d = detalhes  # atalho

    apresentante = d.DadosApresentante or {}
    dados_constricao = d.DadosConstricao or {}
    dados_aceite = d.DadosAceite or {}

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
            DataAutoTermoConstricao, UrlArquivoMandado
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        d.IDContrato, d.Protocolo, d.IDStatus, d.IDCartorio, d.DataRemessa, d.Solicitante,
        d.Telefone, d.Instituicao, d.Email, d.TipoDocumento, d.TipoServico,
        d.ImportacaoExtratoXML,
        apresentante.get("Nome"), apresentante.get("CPFCNPJ"), apresentante.get("Email"), apresentante.get("Via"),
        apresentante.get("Endereco"), apresentante.get("Numero"), apresentante.get("Complemento"),
        apresentante.get("Bairro"), apresentante.get("Cidade"), apresentante.get("Estado"), apresentante.get("CEP"),
        apresentante.get("DDD"), apresentante.get("Telefone"),
        d.PrenotacaoDataInclusao, d.PrenotacaoDataVencimento, d.PrenotacaoDataReenvio,
        d.ValorServico, d.DataResposta, d.Resposta,
        dados_aceite.get("Nome"), dados_aceite.get("Data"),
        d.TipoCobranca, d.CertidaoInteiroTeor, d.TipoIsencao,
        d.NrProcesso, d.FolhasProcesso, d.DataGratuidade,
        d.FundamentoLegal, d.UrlArquivoGratuidade, d.ProtocoloOrigem,
        dados_constricao.get("TipoConstricao"), dados_constricao.get("Processo"),
        dados_constricao.get("Vara"), dados_constricao.get("Usuario"),
        dados_constricao.get("NumeroProcesso"), dados_constricao.get("NaturezaProcesso"),
        dados_constricao.get("ValorDivida"), dados_constricao.get("DataAutoTermo"),
        d.UrlArquivoMandado
    ))

    conn.commit()
    conn.close()


def sincronizar_pedidos_em_aberto():
    try:
        criar_tabela_se_nao_existir()

        resposta_lista = listar_pedidos_em_aberto()

        if not resposta_lista.RETORNO or not resposta_lista.Pedidos:
            print("Nenhum pedido em aberto encontrado.")
            return

        pedidos = resposta_lista.Pedidos.PedidoAC

        if not isinstance(pedidos, list):
            pedidos = [pedidos]

        print(f"{len(pedidos)} pedidos encontrados.")

        for pedido in pedidos:
            id_pedido = pedido.IDPedido
            print(f"\nConsultando detalhes do pedido ID {id_pedido}...")

            detalhes = get_pedido_ac_v7(id_pedido)

            if detalhes.RETORNO:
                try:
                    salvar_detalhes_pedido(detalhes)
                    print(f"Pedido {id_pedido} salvo com sucesso.")
                except Exception as e:
                    print(f"Erro ao salvar pedido {id_pedido}: {e}")
            else:
                print(f"Erro ao buscar detalhes do pedido {id_pedido}: {detalhes.ERRODESCRICAO}")

    except Exception as e:
        print("Erro geral na sincronização:", e)


if __name__ == "__main__":
    sincronizar_pedidos_em_aberto()