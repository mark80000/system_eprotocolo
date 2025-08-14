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

# Mapeamento de Status, incluindo "Todos" para o filtro
STATUS_MAP = {
    "Em aberto": 1,
    "Reaberto - Não Concluído": 8,
}

# Mapeamento reverso para exibir o nome completo na tabela
STATUS_MAP_REVERSE = {v: k for k, v in STATUS_MAP.items() if v is not None}

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
        self.pedidos_onr_cache = []
        
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
        self.btn_listar_onr = ctk.CTkButton(self.sidebar, text="Atualizar", command=self.listar_pedidos_onr_gui, font=("Helvetica", 15))
        self.btn_listar_onr.pack(padx=10, pady=10, fill="x")
        
        # Novo botão para limpar a lista, já que agora ela acumula os pedidos
        self.btn_limpar_lista = ctk.CTkButton(self.sidebar, text="Limpar Lista", command=self.limpar_cache, font=("Helvetica", 15))
        self.btn_limpar_lista.pack(padx=10, pady=10, fill="x")

        # Botão para exibir a lista salva no banco de dados local
        self.btn_listar_db = ctk.CTkButton(self.sidebar, text="Pedidos Salvos", command=self.mostrar_lista_db, font=("Helvetica", 15))
        self.btn_listar_db.pack(padx=10, pady=10, fill="x")

        # Área principal
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="news")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.frame_filtros = self.criar_frame_filtros()
        self.frame_lista = self.criar_frame_lista()
        self.frame_detalhes = self.criar_frame_detalhes()

        self.mostrar_lista_db()
        self.update_idletasks()

    def _inicializar_db(self):
        criar_tabela_se_nao_existir()
    
    def limpar_cache(self):
        """Limpa o cache de pedidos da ONR e atualiza a tabela."""
        self.pedidos_onr_cache = []
        self.mostrar_lista()
        messagebox.showinfo("Info", "Lista de pedidos ONR limpa.")

    def listar_pedidos_onr_gui(self):
        """
        Busca pedidos na ONR, ADICIONA ao cache (evitando duplicatas)
        e recarrega a lista na interface.
        """
        try:
            self.frame_lista.grid_rowconfigure(0, weight=0)
            loading_label = ctk.CTkLabel(self.frame_lista, text="Buscando pedidos na ONR... Aguarde.", text_color="blue", fg_color="white")
            loading_label.grid(row=0, column=0, padx=10, pady=10, sticky="s")
            self.update_idletasks()
            
            status_filtro_text = self.status_var.get()
            status_id = STATUS_MAP.get(status_filtro_text)
            
            # Puxa a lista básica de pedidos da API, passando o status ID
            # Se status_id for None, o serviço irá omitir o filtro
            resposta_lista = listar_pedidos(id_status=status_id)
            
            # Verificação para evitar que o cache seja limpo se a API não retornar nada
            if not resposta_lista.RETORNO or not resposta_lista.Pedidos:
                messagebox.showinfo("Info", "Nenhum pedido encontrado na ONR com o filtro selecionado.")
                loading_label.destroy()
                self.main_frame.grid_rowconfigure(0, weight=1)
                self.carregar_pedidos_do_cache()
                return

            pedidos_basicos = resposta_lista.Pedidos.ListPedidosAC_Pedidos_WSResp
            if not isinstance(pedidos_basicos, list):
                pedidos_basicos = [pedidos_basicos]
            
            loading_label.configure(text="Obtendo detalhes dos pedidos...")
            self.update_idletasks()

            pedidos_detalhados_zeep = get_detalhes_pedidos_listados(pedidos_basicos)
            
            if not pedidos_detalhados_zeep:
                messagebox.showinfo("Info", "Nenhum detalhe de pedido foi encontrado.")
                loading_label.destroy()
                self.main_frame.grid_rowconfigure(0, weight=1)
                self.carregar_pedidos_do_cache()
                return

            # Cria um conjunto (set) dos IDs de contratos que já estão em cache para evitar duplicatas
            existing_ids = {p.get("IDContrato") for p in self.pedidos_onr_cache}

            novos_pedidos = []
            for p in pedidos_detalhados_zeep:
                pedido_dict = serialize_object(p)
                # Verifica se o ID do contrato já existe antes de adicionar
                if pedido_dict.get("IDContrato") not in existing_ids:
                    novos_pedidos.append(pedido_dict)
                    existing_ids.add(pedido_dict.get("IDContrato"))
            
            # Adiciona os novos pedidos ao cache existente
            self.pedidos_onr_cache.extend(novos_pedidos)

            loading_label.destroy()
            self.main_frame.grid_rowconfigure(0, weight=1)
            messagebox.showinfo("Sucesso", f"{len(novos_pedidos)} novos pedidos carregados da ONR com sucesso!")
            
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
        frame = ctk.CTkFrame(self.main_frame)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        self.tree = self.criar_tabela(frame)
        self.tree.grid(row=1, column=0, sticky="snew", padx=10, pady=0)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.bind("<Double-1>", self.selecionar_pedido)

        return frame

    def criar_tabela(self, parent):
        visible_columns = ["IDContrato", "IDStatus", "Protocolo", "Instituicao", "TipoDocumento", "DataRemessa"]
        tree = ttk.Treeview(parent, columns=visible_columns, show="headings", height=16)
        
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
        self.tree.delete(*self.tree.get_children())
        
        if not self.pedidos_onr_cache:
            return

        status_filtro_text = self.status_var.get()
        status_filtro_id = STATUS_MAP.get(status_filtro_text)

        data_inicial_filtro = self.data_inicial_entry.get()
        data_final_filtro = self.data_final_entry.get()
        
        for p in self.pedidos_onr_cache:
            if status_filtro_id is not None and p.get("IDStatus") != status_filtro_id:
                continue
            if data_inicial_filtro and p.get("DataRemessa", "") < data_inicial_filtro:
                continue
            if data_final_filtro and p.get("DataRemessa", "") > data_final_filtro:
                continue

            instituicao_para_mostrar = p.get("Instituicao")
            if not instituicao_para_mostrar:
                instituicao_para_mostrar = p.get("Solicitante", "")

            valores = [
                p.get("IDContrato"),
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
            self.tree.delete(*self.tree.get_children())
            
            status_filtro_text = self.status_var.get()
            status_filtro_id = STATUS_MAP.get(status_filtro_text)
            data_inicial_filtro = self.data_inicial_entry.get()
            data_final_filtro = self.data_final_entry.get()

            query = "SELECT * FROM pedidos_onr WHERE 1=1"
            params = []
            
            if status_filtro_id is not None:
                query += " AND IDStatus = ?"
                params.append(status_filtro_id)
            if data_inicial_filtro:
                query += " AND DataRemessa >= ?"
                params.append(data_inicial_filtro)
            if data_final_filtro:
                query += " AND DataRemessa <= ?"
                params.append(data_final_filtro)
            
            cursor.execute(query, params)
            pedidos = cursor.fetchall()
            
            colunas_db = [desc[0] for desc in cursor.description]

            for p in pedidos:
                pedido_dict = dict(zip(colunas_db, p))
                
                instituicao_para_mostrar = pedido_dict.get("Instituicao")
                if not instituicao_para_mostrar:
                    instituicao_para_mostrar = pedido_dict.get("Solicitante", "")

                valores_para_treeview = [
                    pedido_dict["IDContrato"],
                    STATUS_MAP_REVERSE.get(pedido_dict["IDStatus"], pedido_dict["IDStatus"]),
                    pedido_dict["Protocolo"],
                    instituicao_para_mostrar,
                    pedido_dict["TipoDocumento"],
                    pedido_dict["DataRemessa"]
                ]
                self.tree.insert("", "end", values=valores_para_treeview)

        except sqlite3.Error as e:
            messagebox.showerror("Erro no Banco de Dados", f"Ocorreu um erro ao carregar os pedidos do banco de dados:\n{e}")
        finally:
            conn.close()

    def selecionar_pedido(self, event=None):
        item = self.tree.focus()
        if not item:
            return
        
        valores = self.tree.item(item, "values")
        id_contrato = valores[0]

        self.selected_pedido = next(
            (p for p in self.pedidos_onr_cache if str(p.get("IDContrato")) == str(id_contrato)), None
        )

        if self.selected_pedido:
            self.mostrar_detalhes()
        else:
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
        self.frame_filtros = ctk.CTkFrame(self.main_frame, fg_color="#353535")
        self.frame_filtros.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0)) 
        
        linha1 = ctk.CTkFrame(self.frame_filtros, fg_color="transparent")
        linha1.pack(fill="x", pady=10, padx=5)

        ctk.CTkLabel(linha1, text="Status:", font=("Helvetica", 18)).pack(side="left", padx=(10, 5))
        self.status_var = ctk.StringVar(value="Em aberto")
        status_opcoes = list(STATUS_MAP.keys())
        self.status_combo = ctk.CTkComboBox(
            linha1, values=status_opcoes,font=("Helvetica", 14), variable=self.status_var, width=190,
            command=lambda _: self.carregar_pedidos_do_cache() if self.btn_listar_onr.winfo_ismapped() else self.carregar_pedidos_do_db()
        )
        self.status_combo.pack(side="left", padx=5)

        ctk.CTkLabel(linha1, text="Data Inicial:", font=("Helvetica", 18)).pack(side="left", padx=5)
        self.data_inicial_entry = ctk.CTkEntry(linha1, width=120, placeholder_text="AAAA-MM-DD")
        self.data_inicial_entry.pack(side="left", padx=5)

        ctk.CTkLabel(linha1, text="Data Final:", font=("Helvetica", 18)).pack(side="left", padx=5)
        self.data_final_entry = ctk.CTkEntry(linha1, width=120, placeholder_text="AAAA-MM-DD")
        self.data_final_entry.pack(side="left", padx=5)

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
        self.frame_lista.grid(row=1, column=0, sticky="new", padx=10, pady=(0, 100))
        self.carregar_pedidos_do_cache()
    
    def mostrar_lista_db(self):
        """Exibe o frame da lista de pedidos salvos no banco de dados."""
        self.frame_detalhes.grid_forget()
        self.frame_filtros.grid(row=0, column=0, sticky="new", padx=10, pady=(10, 0))
        self.frame_lista.grid(row=1, column=0, sticky="new", padx=10, pady=(0, 100))
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
            salvar_detalhes_pedido(self.selected_pedido)
            messagebox.showinfo("Sucesso", f"Pedido {self.selected_pedido.get('Protocolo')} cadastrado com sucesso!")
            self.listar_pedidos_onr_gui()
        else:
            messagebox.showerror("Erro", "Nenhum pedido selecionado para cadastro.")


if __name__ == "__main__":
    app = PedidoApp()
    app.mainloop()