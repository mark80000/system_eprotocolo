# -*- coding: utf-8 -*-
# Importações e configurações globais
import customtkinter as ctk
from tkinter import messagebox
import sqlite3
import webbrowser
from tkinter import ttk
from zeep.helpers import serialize_object
from services.lista_pedidos import listar_pedidos
from services.detalhes_pedido import get_pedido_ac_v7
from services.cadastrar_pedidos import (
    criar_tabela_se_nao_existir,
    get_detalhes_pedidos_listados,
    salvar_detalhes_pedido
)

# Configuração inicial do CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Caminho para o seu banco de dados SQLite
DB_PATH = "database/cartorio.db"

# ==================== Mapeamento de Status ====================
# Importante: Assumimos que os IDs de status são 1 para 'Em Aberto' e 2 para 'Reaberto - Não Concluído'.
# Se os IDs reais da API forem diferentes, você precisará ajustar este dicionário.
STATUS_MAP = {
    "Todos": "Todos",
    "Em Aberto": 1,
    "Reaberto - Não Concluído": 8,
    # Adicione outros status aqui conforme necessário
}

# Mapeamento reverso para exibir o nome completo na tabela
STATUS_MAP_REVERSE = {v: k for k, v in STATUS_MAP.items() if v != "Todos"}

class PedidoApp(ctk.CTk):
    """
    Classe principal da aplicação de integração com a ONR.
    Gerencia a interface de usuário e a interação com a API e o banco de dados.
    """
    def __init__(self):
        super().__init__()
        self.title("Integração E-Protocolo")
        self.geometry("900x550")
        self.minsize(width=900, height=550)
        self.maxsize(width=900, height=550)
        
        self.selected_pedido = None
        # O cache de pedidos agora é uma lista de dicionários com todos os detalhes
        # A conversão de zeep para dict será feita na função de atualização
        self.pedidos_onr_cache = []
        
        # A ordem das colunas foi atualizada para corresponder ao novo schema do banco de dados.
        self.column_order = (
            "IDContrato", "Protocolo", "IDStatus", "IDCartorio", "DataRemessa", "Solicitante", "Telefone",
            "Instituicao", "Email", "TipoDocumento", "TipoServico", "ImportacaoExtratoXML",
            "ApresentanteNome", "ApresentanteCPFCNPJ", "ApresentanteEmail", "ApresentanteVia",
            "ApresentanteEndereco", "ApresentanteNumero", "ApresentanteComplemento", "ApresentanteBairro",
            "ApresentanteCidade", "ApresentanteEstado", "ApresentanteCEP", "ApresentanteDDD",
            "ApresentanteTelefone", "PrenotacaoDataInclusao", "PrenotacaoDataVencimento", 
            "PrenotacaoDataReenvio", "ValorServico", "DataResposta", "Resposta", "AceiteNome", 
            "AceiteData", "TipoCobranca", "CertidaoInteiroTeor", "TipoIsencao", "NrProcesso", 
            "FolhasProcesso", "DataGratuidade", "FundamentoLegal", "UrlArquivoGratuidade", 
            "ProtocoloOrigem", "TipoConstricao", "ProcessoConstricao", "VaraConstricao", 
            "UsuarioConstricao", "NumeroProcessoConstricao", "NaturezaProcessoConstricao", 
            "ValorDividaConstricao", "DataAutoTermoConstricao", "UrlArquivoMandado", 
            "NomeComprador", "CPFCNPJComprador", "NomeVendedor", "CPFCNPJVendedor"
        )
        
        # Inicializa o banco de dados antes de qualquer outra operação
        self._inicializar_db()

        # Layout principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=150, corner_radius=1)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        # Botão para atualizar a lista diretamente da API
        self.btn_listar_onr = ctk.CTkButton(self.sidebar, text="Atualizar", command=self.listar_pedidos_onr_gui)
        self.btn_listar_onr.pack(padx=10, pady=10, fill="x")

        # Botão para listar pedidos salvos no banco de dados local
        self.btn_carregar_db = ctk.CTkButton(self.sidebar, text="Listar Pedidos Salvos", command=self.mostrar_lista_db)
        self.btn_carregar_db.pack(padx=10, pady=10, fill="x")

        # Área principal
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="news")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.frame_filtros = self.criar_frame_filtros()
        self.frame_lista = self.criar_frame_lista()
        self.frame_detalhes = self.criar_frame_detalhes()

        # Inicia mostrando os pedidos salvos no DB
        self.mostrar_lista_db()
        self.update_idletasks()
        # Após carregar o DB, já atualiza a lista da API para o cache
        #self.listar_pedidos_onr_gui()

    def _inicializar_db(self):
        """
        Cria a tabela 'pedidos_onr' se ela não existir, usando a função do arquivo de serviço.
        """
        criar_tabela_se_nao_existir()

    def listar_pedidos_onr_gui(self):
        """
        Busca pedidos na ONR, armazena em cache (convertendo para dicionários)
        e recarrega a lista na interface.
        Não salva no banco de dados local neste momento.
        """
        try:
            self.frame_lista.grid_rowconfigure(0, weight=0)
            loading_label = ctk.CTkLabel(self.frame_lista, text="Buscando pedidos na ONR... Aguarde.", text_color="blue", fg_color="white")
            loading_label.grid(row=0, column=0, padx=10, pady=10, sticky="s")
            self.update_idletasks()

            # Puxa a lista básica de pedidos da API.
            resposta_lista = listar_pedidos()

            if not resposta_lista.RETORNO or not resposta_lista.Pedidos:
                messagebox.showinfo("Info", "Nenhum pedido em aberto encontrado na ONR.")
                loading_label.destroy()
                self.main_frame.grid_rowconfigure(0, weight=1)
                return

            # Extrai a lista de objetos de pedidos básicos.
            pedidos_basicos = resposta_lista.Pedidos.ListPedidosAC_Pedidos_WSResp
            # Garante que seja sempre uma lista, mesmo se houver apenas um pedido.
            if not isinstance(pedidos_basicos, list):
                pedidos_basicos = [pedidos_basicos]
            
            loading_label.configure(text="Obtendo detalhes dos pedidos...")
            self.update_idletasks()

            # Puxa os detalhes completos usando a função do seu arquivo de serviço.
            pedidos_detalhados_zeep = get_detalhes_pedidos_listados(pedidos_basicos)
            
            if not pedidos_detalhados_zeep:
                messagebox.showinfo("Info", "Nenhum detalhe de pedido foi encontrado.")
                loading_label.destroy()
                self.main_frame.grid_rowconfigure(0, weight=1)
                return

            # CORREÇÃO: Converte cada objeto Zeep em um dicionário antes de armazenar no cache
            pedidos_detalhados_dict = [serialize_object(p) for p in pedidos_detalhados_zeep]
            self.pedidos_onr_cache = pedidos_detalhados_dict

            loading_label.destroy()
            self.main_frame.grid_rowconfigure(0, weight=1)
            messagebox.showinfo("Sucesso", f"{len(self.pedidos_onr_cache)} pedidos carregados da ONR com sucesso!")
            
            # Atualiza a lista na interface com os dados do cache
            self.mostrar_lista()

        except Exception as e:
            try:
                loading_label.destroy()
            except:
                pass
            self.main_frame.grid_rowconfigure(0, weight=1)
            messagebox.showerror("Erro", f"Falha ao listar pedidos da ONR:\n{e}")

    # ================= Frame da Lista =================
    def criar_frame_lista(self):
        """Cria e configura o frame que contém a lista de pedidos."""
        frame = ctk.CTkFrame(self.main_frame)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # A tabela agora exibe as colunas mais importantes e relevantes.
        self.tree = self.criar_tabela(frame)
        self.tree.grid(row=1, column=0, sticky="snew", padx=10, pady=0)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.bind("<Double-1>", self.selecionar_pedido)

        return frame

    def criar_tabela(self, parent):
        """
        Cria e configura o Treeview para exibir uma seleção de colunas relevantes
        da lista de pedidos.
        """
        # Exibiremos apenas algumas colunas para a tabela da GUI, 
        # para não ficar muito larga, mas o cache continua completo.
        visible_columns = ["IDContrato", "IDStatus", "Protocolo", "Instituicao", "TipoDocumento", "DataRemessa"]
        tree = ttk.Treeview(parent, columns=visible_columns, show="headings", height=20)

        tree.column("IDContrato", width=0, stretch=False)
        tree.heading("IDStatus", text="Status")
        tree.column("IDStatus", anchor="w", width=70)
        tree.heading("Protocolo", text="Protocolo")
        tree.column("Protocolo", anchor="w", width=50)
        tree.heading("Instituicao", text="Instituição")
        tree.column("Instituicao", anchor="w", width=150)
        tree.heading("TipoDocumento", text="Tipo Documento")
        tree.column("TipoDocumento", anchor="w", width=120)
        tree.heading("DataRemessa", text="Data Pedido")
        tree.column("DataRemessa", anchor="w", width=80)
        
        return tree

    def carregar_pedidos_do_cache(self):
        """
        Carrega os pedidos do cache (lista em memória) com base nos filtros aplicados.
        Como o cache agora armazena dicionários, o acesso é feito com .get().
        """
        self.tree.delete(*self.tree.get_children())
        
        if not self.pedidos_onr_cache:
            return

        status_filtro_text = self.status_var.get()
        # Usa o mapa para obter o ID do status
        status_filtro_id = STATUS_MAP.get(status_filtro_text, "Todos")

        data_inicial_filtro = self.data_inicial_entry.get()
        data_final_filtro = self.data_final_entry.get()
        
        for p in self.pedidos_onr_cache:
            # Ponto de correção: Verifica se o ID do status do pedido corresponde ao filtro
            if status_filtro_id != "Todos" and p.get("IDStatus") != status_filtro_id:
                continue
            if data_inicial_filtro and p.get("DataRemessa", "") < data_inicial_filtro:
                continue
            if data_final_filtro and p.get("DataRemessa", "") > data_final_filtro:
                continue

            # Lógica adicionada: Usa 'Instituicao' se não estiver vazia, caso contrário, usa 'Solicitante'
            instituicao_para_mostrar = p.get("Instituicao")
            if not instituicao_para_mostrar:
                instituicao_para_mostrar = p.get("Solicitante", "")

            # CORREÇÃO: A lista de valores agora tem 6 elementos,
            # alinhando-se corretamente com as 6 colunas do Treeview.
            valores = [
                p.get("IDContrato"),
                # Usa o mapa reverso para exibir o nome do status
                STATUS_MAP_REVERSE.get(p.get("IDStatus"), p.get("IDStatus")),
                p.get("Protocolo"),
                instituicao_para_mostrar,
                p.get("TipoDocumento"),
                p.get("DataRemessa")
            ]
            self.tree.insert("", "end", values=valores)

    def carregar_pedidos_do_db(self):
        """
        Carrega os pedidos do banco de dados local para a Treeview, aplicando os filtros.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT IDContrato, IDStatus, Protocolo, Instituicao, TipoDocumento, DataRemessa FROM pedidos_onr")
            pedidos = cursor.fetchall()
            
            self.tree.delete(*self.tree.get_children())

            status_filtro_text = self.status_var.get()
            status_filtro_id = STATUS_MAP.get(status_filtro_text, "Todos")
            data_inicial_filtro = self.data_inicial_entry.get()
            data_final_filtro = self.data_final_entry.get()

            for p in pedidos:
                pedido_dict = {
                    "IDContrato": p[0],
                    "IDStatus": p[1],
                    "Protocolo": p[2],
                    "Instituicao": p[3],
                    "Solicitante": p[4],
                    "TipoDocumento": p[5],
                    "DataRemessa": p[6]
                }
                
                # Aplica os filtros nos dados do DB
                if status_filtro_id != "Todos" and pedido_dict["IDStatus"] != status_filtro_id:
                    continue
                if data_inicial_filtro and pedido_dict.get("DataRemessa", "") < data_inicial_filtro:
                    continue
                if data_final_filtro and pedido_dict.get("DataRemessa", "") > data_final_filtro:
                    continue

                # Lógica adicionada: Usa 'Instituicao' se não estiver vazia, caso contrário, usa 'Solicitante'
                instituicao_para_mostrar = pedido_dict["Instituicao"]
                if not instituicao_para_mostrar:
                    instituicao_para_mostrar = pedido_dict.get("Solicitante", "")

                # Usa o mapa reverso para exibir o nome do status
                valores_para_treeview = [
                    pedido_dict["IDContrato"],
                    STATUS_MAP_REVERSE.get(pedido_dict["IDStatus"], pedido_dict["IDStatus"]),
                    pedido_dict["Protocolo"],
                    instituicao_para_mostrar, # Valor atualizado aqui
                    pedido_dict["TipoDocumento"],
                    pedido_dict["DataRemessa"]
                ]
                self.tree.insert("", "end", values=valores_para_treeview)

        except sqlite3.Error as e:
            messagebox.showerror("Erro no Banco de Dados", f"Ocorreu um erro ao carregar os pedidos do banco de dados:\n{e}")
        finally:
            conn.close()

    def selecionar_pedido(self, event=None):
        """
        Lida com a seleção de um pedido na lista, buscando os detalhes no cache.
        """
        item = self.tree.focus()
        if not item:
            return
        
        valores = self.tree.item(item, "values")
        id_contrato = valores[0]

        # Busca o pedido completo no cache (lista em memória).
        # Como o cache armazena dicionários, o acesso é feito por chave.
        self.selected_pedido = next(
            (p for p in self.pedidos_onr_cache if str(p.get("IDContrato")) == str(id_contrato)), None
        )

        if self.selected_pedido:
            self.mostrar_detalhes()
        else:
            # Caso o pedido não esteja no cache, tenta buscar no DB (cenário de segurança)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pedidos_onr WHERE IDContrato = ?", (id_contrato,))
            row = cursor.fetchone()
            colunas = [desc[0] for desc in cursor.description]
            conn.close()
            if row:
                self.selected_pedido = dict(zip(colunas, row))
                self.mostrar_detalhes()
            else:
                messagebox.showerror("Erro", "Pedido não encontrado.")
                self.selected_pedido = None
            
    def criar_frame_filtros(self):
        """Cria a interface de filtros para a lista de pedidos."""
        self.frame_filtros = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frame_filtros.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0)) 
        
        linha1 = ctk.CTkFrame(self.frame_filtros, fg_color="transparent")
        linha1.pack(fill="x", pady=10, padx=5)

        ctk.CTkLabel(linha1, text="Status:").pack(side="left", padx=(10, 5))
        self.status_var = ctk.StringVar(value="Todos")
        # As opções de status agora usam as chaves do STATUS_MAP para o filtro em memória
        status_opcoes = list(STATUS_MAP.keys())
        self.status_combo = ctk.CTkComboBox(
            linha1, values=status_opcoes, variable=self.status_var, width=150,
            command=lambda _: self.carregar_pedidos_do_cache() if self.frame_lista.winfo_ismapped() else self.carregar_pedidos_do_db()
        )
        self.status_combo.pack(side="left", padx=5)

        ctk.CTkLabel(linha1, text="Data Inicial:").pack(side="left", padx=5)
        self.data_inicial_entry = ctk.CTkEntry(linha1, width=120, placeholder_text="AAAA-MM-DD")
        self.data_inicial_entry.pack(side="left", padx=5)

        ctk.CTkLabel(linha1, text="Data Final:").pack(side="left", padx=5)
        self.data_final_entry = ctk.CTkEntry(linha1, width=120, placeholder_text="AAAA-MM-DD")
        self.data_final_entry.pack(side="left", padx=5)
        
        linha2 = ctk.CTkFrame(self.frame_filtros, fg_color="transparent")
        linha2.pack(fill="x", pady=6, padx=5)
        linha2.grid_columnconfigure(1, weight=1)

        # Atualizado o botão de filtro para usar a função correta dependendo do frame visível
        def aplicar_filtro():
            if self.frame_lista.winfo_ismapped():
                if self.btn_listar_onr.winfo_ismapped():
                    self.carregar_pedidos_do_cache()
                else:
                    self.carregar_pedidos_do_db()
        
        ctk.CTkButton(linha2, text="Aplicar Filtros", command=aplicar_filtro).pack(side="right", padx=5)

        return self.frame_filtros

    # ================= Frame de Detalhes =================
    def criar_frame_detalhes(self):
        """Cria e configura o frame que exibe os detalhes de um pedido."""
        frame = ctk.CTkFrame(self.main_frame)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.tree_detalhes = ttk.Treeview(frame, columns=("Campo", "Valor"), show="headings", height=15)
        self.tree_detalhes.heading("Campo", text="Campo")
        self.tree_detalhes.heading("Valor", text="Valor")
        self.tree_detalhes.column("Campo", width=200, anchor="w")
        self.tree_detalhes.column("Valor", width=200, anchor="w")
        self.tree_detalhes.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        vsb_det = ttk.Scrollbar(frame, orient="vertical", command=self.tree_detalhes.yview)
        vsb_det.grid(row=0, column=1, sticky="ns")
        self.tree_detalhes.configure(yscrollcommand=vsb_det.set)

        botoes_frame = ctk.CTkFrame(frame)
        botoes_frame.grid(row=1, column=0, pady=5, sticky="ew")

        self.anexo_button = ctk.CTkButton(botoes_frame, text="Abrir Anexo", command=self.abrir_anexo)
        self.anexo_button.pack(side="left", padx=5)

        self.btn_cadastrar = ctk.CTkButton(botoes_frame, text="Cadastrar no sistema", command=self.cadastrar, state="disabled")
        self.btn_cadastrar.pack(side="right", padx=5)
        
        self.btn_voltar_lista = ctk.CTkButton(botoes_frame, text="Voltar", command=self.mostrar_lista)
        self.btn_voltar_lista.pack(side="right", padx=5)

        self.alerta = ctk.CTkLabel(frame, text="", text_color="red")
        self.alerta.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        return frame

    def mostrar_lista(self):
        """Exibe o frame da lista de pedidos carregados da API."""
        self.frame_detalhes.grid_forget()
        self.frame_filtros.grid(row=0, column=0, sticky="new", padx=10, pady=(10, 0))
        self.frame_lista.grid(row=1, column=0, sticky="new", padx=10, pady=(0, 10))
        # Chama a função para carregar do cache
        self.carregar_pedidos_do_cache()
    
    def mostrar_lista_db(self):
        """Exibe o frame da lista de pedidos salvos no banco de dados."""
        self.frame_detalhes.grid_forget()
        self.frame_filtros.grid(row=0, column=0, sticky="new", padx=10, pady=(10, 0))
        self.frame_lista.grid(row=1, column=0, sticky="new", padx=10, pady=(0, 10))
        # Chama a função para carregar do DB
        self.carregar_pedidos_do_db()

    def mostrar_detalhes(self):
        """
        Exibe o frame de detalhes do pedido selecionado, mostrando apenas os campos
        e valores especificados.
        """
        if not self.selected_pedido:
            messagebox.showerror("Erro", "Selecione um pedido primeiro.")
            return

        self.frame_lista.grid_forget()
        self.frame_filtros.grid_forget()
        self.frame_detalhes.grid(row=0, column=0, sticky="nsew")

        self.tree_detalhes.delete(*self.tree_detalhes.get_children())
        
        # Lista dos campos que você deseja exibir
        campos_desejados = [
            "Protocolo",
            "Solicitante",
            "Telefone",
            "TipoDocumento",
            "NomeVendedor",
            "CPFCNPJVendedor",
            "NomeComprador",
            "CPFCNPJComprador"
        ]

        for campo in campos_desejados:
            valor = self.selected_pedido.get(campo, "Não disponível")
            self.tree_detalhes.insert("", "end", values=(campo, valor))

        self.validar_campos()

    def abrir_anexo(self):
        """Abre o anexo do pedido no navegador padrão."""
        # Acessa a URL usando .get() pois o selected_pedido é um dicionário
        if self.selected_pedido and self.selected_pedido.get("UrlArquivoMandado"):
            webbrowser.open(self.selected_pedido["UrlArquivoMandado"])
        else:
            messagebox.showinfo("Info", "Anexo não disponível.")

    def validar_campos(self):
        """Ativa ou desativa o botão de cadastrar baseado na seleção de um pedido."""
        if self.selected_pedido:
            self.btn_cadastrar.configure(state="normal")
        else:
            self.btn_cadastrar.configure(state="disabled")

    def cadastrar(self):
        """
        Salva o pedido selecionado no banco de dados local.
        """
        if self.selected_pedido:
            # selected_pedido já é um dicionário, então pode ser salvo diretamente
            salvar_detalhes_pedido(self.selected_pedido)
            messagebox.showinfo("Sucesso", f"Pedido {self.selected_pedido.get('Protocolo')} cadastrado com sucesso!")
            
            # Recarrega a lista de pedidos da API para a interface
            self.listar_pedidos_onr_gui()
        else:
            messagebox.showerror("Erro", "Nenhum pedido selecionado para cadastro.")


if __name__ == "__main__":
    app = PedidoApp()
    app.mainloop()