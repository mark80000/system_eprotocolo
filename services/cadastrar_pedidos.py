# Puxa detalhes/informações dos pedidos em aberto a partir de ListPedidosAC e GetPedidoAC_V7, e salva no banco.

import os
import sqlite3
import json
from services.lista_pedidos import listar_pedidos
from services.detalhes_pedido import get_pedido_ac_v7
from zeep.helpers import serialize_object
from decimal import Decimal
from datetime import datetime

DB_PATH = os.path.join("database", "cartorio.db")

# Transforma valor decimal em float.
def to_float(val):
    if isinstance(val, Decimal):
        return float(val)
    return val

# 1. Tabela atualizada com as novas colunas e restrições de unicidade.
def criar_tabela_se_nao_existir():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Adicionadas as colunas: cod_entrada, entrada, protocolo_numero
    # Adicionadas restrições UNIQUE para garantir a integridade dos dados
    c.execute("""
        CREATE TABLE IF NOT EXISTS pedidos_onr (
            IDContrato INTEGER PRIMARY KEY,
            cod_entrada TEXT UNIQUE,
            entrada INTEGER UNIQUE,
            protocolo_numero INTEGER UNIQUE,
            Protocolo TEXT UNIQUE,
            DataRemessa TEXT,
            Solicitante TEXT,
            Telefone TEXT,
            TipoDocumento TEXT,
            NomeComprador TEXT,
            CPFCNPJComprador TEXT,
            NomeVendedor TEXT,
            CPFCNPJVendedor TEXT
        )
    """)
    conn.commit()
    conn.close()

# 2. Função de salvar reescrita com a nova lógica de geração de códigos.
def salvar_detalhes_pedido(d):
    """
    Gera os códigos sequenciais e salva os detalhes de um novo pedido no banco de dados.
    Não salva se o Protocolo ONR já existir.
    Retorna True se um novo pedido foi salvo, False caso contrário.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Etapa 1: Verificar se o pedido da ONR já foi cadastrado para evitar duplicatas.
        onr_protocolo = d.get("Protocolo")
        cursor.execute("SELECT 1 FROM pedidos_onr WHERE Protocolo = ?", (onr_protocolo,))
        if cursor.fetchone():
            print(f"Pedido com Protocolo ONR {onr_protocolo} já existe. Ignorando.")
            return False  # Indica que nenhum novo pedido foi salvo.

        # --- Início da Lógica de Geração de Códigos ---

        # Etapa 2: Gerar os números de 'entrada' e 'protocolo_numero' (sequencial global).
        cursor.execute("SELECT MAX(entrada) FROM pedidos_onr")
        max_entrada = cursor.fetchone()[0]
        proxima_entrada = (max_entrada or 0) + 1

        cursor.execute("SELECT MAX(protocolo_numero) FROM pedidos_onr")
        max_protocolo = cursor.fetchone()[0]
        proximo_protocolo = (max_protocolo or 0) + 1

        # Etapa 3: Gerar o 'cod_entrada' (formato CCCDDMM/YY com contador diário).
        hoje = datetime.now()
        dd = hoje.strftime("%d")
        mm = hoje.strftime("%m")
        yy = hoje.strftime("%y")
        
        # Busca pelo último código do dia atual para encontrar o último contador.
        # Ex: Busca por '___2008/25' para pegar o maior contador do dia 20/08/2025.
        padrao_busca_diario = f"%{dd}{mm}/{yy}"
        cursor.execute("SELECT cod_entrada FROM pedidos_onr WHERE cod_entrada LIKE ? ORDER BY cod_entrada DESC LIMIT 1", (padrao_busca_diario,))
        resultado = cursor.fetchone()
        
        contador_diario = 1
        if resultado:
            ultimo_cod_hoje = resultado[0]
            contador_anterior = int(ultimo_cod_hoje[:3]) # Pega os 3 primeiros dígitos (o contador)
            contador_diario = contador_anterior + 1
        
        # Monta o código final no formato CCCDDMM/YY
        proximo_cod_entrada = f"{contador_diario:03d}{dd}{mm}/{yy}"

        # --- Fim da Lógica de Geração de Códigos ---

        # Etapa 4: Preparar todos os dados para a inserção no banco.
        imovel_transacao = d.get('DadosImovelTransacao') or {}
        
        pedido_data = {
            "IDContrato": d.get("IDContrato"),
            "cod_entrada": proximo_cod_entrada,
            "entrada": proxima_entrada,
            "protocolo_numero": proximo_protocolo,
            "Protocolo": onr_protocolo,
            "DataRemessa": d.get("DataRemessa"),
            "Solicitante": d.get("Solicitante"),
            "Telefone": d.get("Telefone"),
            "TipoDocumento": d.get("TipoDocumento"),
            "NomeComprador": imovel_transacao.get("NomeComprador"),
            "CPFCNPJComprador": imovel_transacao.get("CPFCNPJComprador"),
            "NomeVendedor": imovel_transacao.get("NomeVendedor"),
            "CPFCNPJVendedor": imovel_transacao.get("CPFCNPJVendedor")
        }

        colunas = ", ".join(pedido_data.keys())
        placeholders = ", ".join(["?"] * len(pedido_data))
        query = f"INSERT INTO pedidos_onr ({colunas}) VALUES ({placeholders})"
        
        cursor.execute(query, tuple(pedido_data.values()))
        conn.commit()
        
        print(f"Pedido salvo com sucesso! Entrada: {proxima_entrada}, Protocolo: {proximo_protocolo}, Código: {proximo_cod_entrada}")
        return True # Retorna True indicando que um novo pedido foi inserido.

    except sqlite3.Error as e:
        print(f"Erro ao salvar pedido no banco de dados: {e}")
        return False
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
def cadastrar_pedidos():
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
        detalhes_lista = get_detalhes_pedidos_listados(pedidos)

        with open("detalhes.txt", "w", encoding="utf-8") as f:
            for detalhes in detalhes_lista:
                json_string = json.dumps(serialize_object(detalhes), indent=4, ensure_ascii=False, default=str)
                f.write(json_string + "\n" + ("=" * 80) + "\n\n")

        for detalhes in detalhes_lista:
            try:
                # A lógica de geração de código agora está dentro de salvar_detalhes_pedido
                salvar_detalhes_pedido(serialize_object(detalhes))
            except Exception as e:
                print(f"Erro ao processar contrato {detalhes.IDContrato}: {e}")
    except Exception as e:
        print("Erro geral na sincronização:", e)


if __name__ == "__main__":
    cadastrar_pedidos()