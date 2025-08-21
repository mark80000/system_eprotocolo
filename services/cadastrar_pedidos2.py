import os
import psycopg2 # <-- Alterado de sqlite3
from psycopg2.extras import DictCursor # <-- Novo
import json
from services.lista_pedidos import listar_pedidos
from services.detalhes_pedido import get_pedido_ac_v7
from zeep.helpers import serialize_object
from decimal import Decimal
from datetime import datetime

# --- NOVA CONFIGURAÇÃO DE CONEXÃO POSTGRESQL ---
# Preencha com os dados do seu banco de dados PostgreSQL
DB_CONFIG = {
    "dbname": "cartorio",
    "user": "postgres",
    "password": "140406",
    "host": "localhost",  # ou o IP do servidor do banco
    "port": "5432"
}
# -------------------------------------------------

def to_float(val):
    if isinstance(val, Decimal):
        return float(val)
    return val

def preencher_vazio(valor):
    if valor is None or (isinstance(valor, str) and valor.strip() == ""):
        return "*PREENCHER*"
    return valor

def salvar_detalhes_pedido(d):
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # Etapa 1: Gerar os números de 'entrada' e 'protocolo_numero'
            cursor.execute('SELECT MAX("entrada") FROM registre.entradas')
            max_entrada = cursor.fetchone()[0]
            proxima_entrada = (max_entrada or 0) + 1

            cursor.execute('SELECT MAX("numero_protocolo") FROM registre.entradas')
            max_protocolo = cursor.fetchone()[0]
            proximo_protocolo = (max_protocolo or 0) + 1

            # Etapa 2: Gerar o 'cod_entrada'
            hoje = datetime.now()
            dd, mm, yy = hoje.strftime("%d"), hoje.strftime("%m"), hoje.strftime("%y")
            hora_atual = datetime.now().strftime("%H:%M") + "hs"
            
            # Placeholders mudam de '?' para '%s'
            padrao_busca_diario = f"%{dd}{mm}/{yy}"
            cursor.execute('SELECT "cod_entrada" FROM registre.entradas WHERE "cod_entrada" LIKE %s ORDER BY "cod_entrada" DESC LIMIT 1', (padrao_busca_diario,))
            resultado = cursor.fetchone()
            
            contador_diario = 1
            if resultado:
                contador_anterior = int(resultado[0][:3])
                contador_diario = contador_anterior + 1
            
            proximo_cod_entrada = f"{contador_diario:03d}{dd}{mm}/{yy}"

            imovel_transacao = d.get('DadosImovelTransacao') or {}
            
            pedido_data = {
                "cod_entrada": proximo_cod_entrada,
                "entrada": proxima_entrada,
                "numero_protocolo": proximo_protocolo,
                "titulo": "REGISTRO\n" + d.get("Protocolo"),
                "momento_cadastro": preencher_vazio(d.get("DataRemessa")),
                "partes": preencher_vazio(d.get("Solicitante")),
                "telefone": preencher_vazio(d.get("Telefone")),
                "natureza_titulo": preencher_vazio(d.get("TipoDocumento", "")[:25]),
                "nome_outorgante": preencher_vazio(imovel_transacao.get("NomeComprador")),
                "doc_outorgante": preencher_vazio(imovel_transacao.get("CPFCNPJComprador")),
                "nome_outorgado": preencher_vazio(imovel_transacao.get("NomeVendedor")),
                "doc_outorgado": preencher_vazio(imovel_transacao.get("CPFCNPJVendedor")),
                "assunto": "DOCUMENTO EM ANEXO",
                "onr": "SIM",
                "procedencia": "*PREENCHER*",
                "hora": hora_atual,
                "tipo_entrada": "Registro",
                "doc_parte": "NAO INFORMADO",
                "motivacao": "REGISTRAR IMOVEL",
                "para_exame": "NAO",
                "arquivodigital": "SIM"
            }

            # Etapa 3: Inserir usando a cláusula 'ON CONFLICT' do PostgreSQL
            colunas = ", ".join([f'"{k}"' for k in pedido_data.keys()])
            placeholders = ", ".join(["%s"] * len(pedido_data))
            
            # ON CONFLICT garante que não haverá erro se o Protocolo já existir
            query = f'INSERT INTO registre.entradas ({colunas}) VALUES ({placeholders}) ON CONFLICT ("entrada") DO NOTHING'
            
            cursor.execute(query, tuple(pedido_data.values()))
            
            # cursor.rowcount dirá se uma linha foi inserida (1) ou não (0)
            foi_salvo = cursor.rowcount > 0
            if foi_salvo:
                 print(f"Pedido salvo! Entrada: {proxima_entrada}, Código: {proximo_cod_entrada}")

            conn.commit()
            return foi_salvo

    except psycopg2.Error as e:
        print(f"Erro ao salvar pedido no PostgreSQL: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ... (O restante do arquivo, como get_detalhes_pedidos_listados, etc., não precisa ser alterado) ...
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