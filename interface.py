import customtkinter as ctk
from tkinter import messagebox
import sqlite3
import webbrowser
from tkinter import ttk
from services.cadastrar_pedidos import exibir_detalhes_pedidos
from services.lista_pedidos import listar_pedidos
from services.detalhes_pedido import get_pedido_ac_v7

# Configuração inicial do CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Caminho para o seu banco de dados SQLite
DB_PATH = "database/cartorio.db"

class PedidoApp(ctk.CTk):
    """
    Classe principal da aplicação de integração com a ONR.
    Gerencia a interface de usuário e a interação com o banco de dados.
    """
    def __init__(self):
        super().__init__()
        self.title("Integração ONR")
        self.geometry("900x550")
        self.minsize(width=900, height=550)
        self.maxsize(width=900, height=550)
        
        self.selected_pedido = None
        
        # Usamos este nome para a tupla de ordenação e consultas SQL.
        # A API ainda retorna o campo como 'IDPedido'.
        self.column_order = ("IDStatus", "Protocolo", "DataRemessa", "Solicitante", "TipoServico", "ValorServico")

        # Inicializa o banco de dados antes de qualquer outra operação
        self._inicializar_db()

        # Layout principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=1)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.btn_listar_onr = ctk.CTkButton(self.sidebar, text="Atualizar da ONR", command=self.listar_pedidos_onr_gui)
        self.btn_listar_onr.pack(padx=10, pady=10, fill="x")

        self.btn_carregar_db = ctk.CTkButton(self.sidebar, text="Listar Pedidos Salvos", command=self.mostrar_lista)
        self.btn_carregar_db.pack(padx=10, pady=10, fill="x")

        # Área principal
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=0)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.frame_filtros = self.criar_frame_filtros()
        self.frame_lista = self.criar_frame_lista()
        self.frame_detalhes = self.criar_frame_detalhes()

        self.mostrar_lista()

    def _inicializar_db(self):
        """
        Cria a tabela 'pedidos_onr' se ela não existir.
        Garante que a estrutura do banco de dados está correta, usando 'IDStatus'.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pedidos_onr (
                    IDStatus INT PRIMARY KEY,
                    Protocolo TEXT,
                    DataRemessa TEXT,
                    Solicitante TEXT,
                    TipoServico TEXT,
                    ValorServico TEXT
                )
            """)
            conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Erro de Inicialização do DB", f"Ocorreu um erro ao criar a tabela 'pedidos_onr':\n{e}")
        finally:
            conn.close()

    def listar_pedidos_onr_gui(self):
        """
        Busca novos pedidos na ONR, atualiza o banco de dados local
        e recarrega a lista na interface.
        """
        try:
            self.frame_lista.grid_rowconfigure(0, weight=0)
            loading_label = ctk.CTkLabel(self.frame_lista, text="Buscando pedidos na ONR... Aguarde.", text_color="blue", fg_color="white")
            loading_label.grid(row=0, column=0, padx=10, pady=10, sticky="s")
            self.update_idletasks()

            pedidos_basicos = listar_pedidos()
            
            if not pedidos_basicos:
                messagebox.showinfo("Info", "Nenhum pedido encontrado na ONR.")
                loading_label.destroy()
                self.main_frame.grid_rowconfigure(0, weight=1)
                return

            pedidos_detalhados = []
            erros_detalhes = []

            for pedido_id in pedidos_basicos:
                try:
                    detalhes = get_pedido_ac_v7(pedido_id)
                    pedidos_detalhados.append(detalhes)
                except Exception as e:
                    erros_detalhes.append(f"Erro ao obter detalhes do pedido {pedido_id}: {e}")

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            for pedido in pedidos_detalhados:
                campos_db = self.column_order
                # Mapeia 'IDPedido' da API para 'IDStatus' do DB
                valores = (
                    pedido.get("IDContrato", ""), 
                    pedido.get("Protocolo", ""),
                    pedido.get("IDStatus", ""),
                    pedido.get("DataRemessa", ""),
                    pedido.get("Solicitante", ""),
                    pedido.get("TipoServico", ""),
                    pedido.get("ValorServico", "")
                )
                
                cursor.execute(
                    f"INSERT OR REPLACE INTO pedidos_onr ({', '.join(campos_db)}) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    valores
                )
            conn.commit()
            conn.close()

            loading_label.destroy()
            self.main_frame.grid_rowconfigure(0, weight=1)
            messagebox.showinfo("Sucesso", f"{len(pedidos_detalhados)} pedidos atualizados do ONR com sucesso!")
            
            self.mostrar_lista()

        except Exception as e:
            loading_label.destroy()
            self.main_frame.grid_rowconfigure(0, weight=1)
            messagebox.showerror("Erro", f"Falha ao listar pedidos da ONR:\n{e}")

    # ================= Frame da Lista =================
    def criar_frame_lista(self):
        """Cria e configura o frame que contém a lista de pedidos."""
        frame = ctk.CTkFrame(self.main_frame)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        self.tree = self.criar_tabela(frame)
        self.tree.grid(row=1, column=0, sticky="new", padx=10, pady=10)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.bind("<Double-1>", self.selecionar_pedido)

        return frame

    def criar_tabela(self, parent):
        """Cria e configura o Treeview para exibir a lista de pedidos."""
        tree = ttk.Treeview(parent, columns=self.column_order, show="headings", height=15)

        # Configura as colunas da tabela
        tree.heading("IDStatus", text="ID Status")
        tree.column("IDStatus", anchor="w", width=80)
        tree.heading("Protocolo", text="Protocolo")
        tree.column("Protocolo", anchor="w", width=100)
        tree.heading("DataRemessa", text="Data Remessa")
        tree.column("DataRemessa", anchor="w", width=120)
        tree.heading("Solicitante", text="Solicitante")
        tree.column("Solicitante", anchor="w", width=200)
        tree.heading("TipoServico", text="Tipo Serviço")
        tree.column("TipoServico", anchor="w", width=120)
        tree.heading("ValorServico", text="Valor")
        tree.column("ValorServico", anchor="w", width=80)
        
        return tree

    def carregar_pedidos(self):
        """
        Carrega os pedidos do banco de dados local com base nos filtros aplicados.
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        status = self.status_var.get()
        data_inicial = self.data_inicial_entry.get()
        data_final = self.data_final_entry.get()
        tipo_servico = self.tipo_servico_var.get()

        query = f"SELECT {', '.join(self.column_order)} FROM pedidos_onr WHERE 1=1"
        parametros = []

        if status != "Todos":
            query += " AND Status = ?"
            parametros.append(status)
        if data_inicial:
            query += " AND DataRemessa >= ?"
            parametros.append(data_inicial)
        if data_final:
            query += " AND DataRemessa <= ?"
            parametros.append(data_final)
        if tipo_servico != "Todos":
            query += " AND TipoServico = ?"
            parametros.append(tipo_servico)
        
        try:
            cursor.execute(query, tuple(parametros))
            pedidos = cursor.fetchall()
            
            self.tree.delete(*self.tree.get_children())
            for p in pedidos:
                self.tree.insert("", "end", values=p)

        except sqlite3.Error as e:
            messagebox.showerror("Erro no Banco de Dados", f"Ocorreu um erro ao filtrar os pedidos:\n{e}")
        finally:
            conn.close()

    def selecionar_pedido(self, event=None):
        """Lida com a seleção de um pedido na lista."""
        item = self.tree.focus()
        if not item:
            return
        
        valores = self.tree.item(item, "values")
        # O primeiro valor é o ID do status
        id_status = valores[0]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Busca o pedido completo no banco de dados local
        cursor.execute("SELECT * FROM pedidos_onr WHERE IDStatus = ?", (id_status,))
        row = cursor.fetchone()
        colunas = [desc[0] for desc in cursor.description]
        conn.close()

        if row:
            self.selected_pedido = dict(zip(colunas, row))
            self.mostrar_detalhes()
        else:
            self.alerta.configure(text="Pedido não encontrado no banco de dados.", text_color="red")
            self.selected_pedido = None

    def criar_frame_filtros(self):
        """Cria a interface de filtros para a lista de pedidos."""
        self.frame_filtros = ctk.CTkFrame(self.main_frame)
        self.frame_filtros.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        linha1 = ctk.CTkFrame(self.frame_filtros)
        linha1.pack(fill="x", pady=10, padx=5)

        ctk.CTkLabel(linha1, text="Status:").pack(side="left", padx=(10, 5))
        self.status_var = ctk.StringVar(value="Todos")
        status_opcoes = ["Todos", "Em Aberto", "Reaberto/Não Concluído"]
        self.status_combo = ctk.CTkComboBox(
            linha1, values=status_opcoes, variable=self.status_var, width=150
        )
        self.status_combo.pack(side="left", padx=5)

        ctk.CTkLabel(linha1, text="Data Inicial:").pack(side="left", padx=5)
        self.data_inicial_entry = ctk.CTkEntry(linha1, width=120, placeholder_text="AAAA-MM-DD")
        self.data_inicial_entry.pack(side="left", padx=5)

        ctk.CTkLabel(linha1, text="Data Final:").pack(side="left", padx=5)
        self.data_final_entry = ctk.CTkEntry(linha1, width=120, placeholder_text="AAAA-MM-DD")
        self.data_final_entry.pack(side="left", padx=5)
        
        linha2 = ctk.CTkFrame(self.frame_filtros)
        linha2.pack(fill="x", pady=6, padx=5)
        linha2.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(linha2, text="Tipo Serviço:").pack(side="left", padx=(5, 5))
        self.tipo_servico_var = ctk.StringVar(value="Todos")
        tipos_servico = ["Todos", "Certidão", "Registro", "Averbação"]
        self.tipo_servico_combo = ctk.CTkComboBox(
            linha2, values=tipos_servico, variable=self.tipo_servico_var, width=150
        )
        self.tipo_servico_combo.pack(side="left", padx=5)

        ctk.CTkButton(linha2, text="Aplicar Filtros", command=self.carregar_pedidos).pack(side="right", padx=5)

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
        """Exibe o frame da lista de pedidos e carrega os dados do banco de dados."""
        self.frame_detalhes.grid_forget()
        self.frame_lista.grid(row=1, column=0, sticky="new", padx=10, pady=(0, 10))
        self.frame_filtros.grid(row=0, column=0, sticky="new", padx=10, pady=(10, 0))
        self.carregar_pedidos()

    def mostrar_detalhes(self):
        """Exibe o frame de detalhes do pedido selecionado."""
        if not self.selected_pedido:
            self.alerta.configure(text="Selecione um pedido primeiro.")
            return

        self.frame_lista.grid_forget()
        self.frame_filtros.grid_forget()
        self.frame_detalhes.grid(row=0, column=0, sticky="nsew")

        self.tree_detalhes.delete(*self.tree_detalhes.get_children())

        campos_exibir = [
            "IDStatus",
            "Solicitante",
            "TelefoneSolicitante",
            "TipoDocumento",
            "NomeVendedor",
            "CPFCNPJVendedor",
            "NomeComprador",
            "CPFCNPJComprador",
            "Protocolo"
        ]

        for campo in campos_exibir:
            valor = self.selected_pedido.get(campo, "")
            self.tree_detalhes.insert("", "end", values=(campo, valor))

        self.validar_campos()

    def abrir_anexo(self):
        """Abre o anexo do pedido no navegador padrão."""
        if self.selected_pedido and self.selected_pedido.get("UrlArquivoMandado"):
            webbrowser.open(self.selected_pedido["UrlArquivoMandado"])
        else:
            self.alerta.configure(text="Anexo não disponível.")

    def validar_campos(self):
        """Ativa ou desativa o botão de cadastrar baseado na seleção de um pedido."""
        if self.selected_pedido:
            self.btn_cadastrar.configure(state="normal")
        else:
            self.btn_cadastrar.configure(state="disabled")

    def cadastrar(self):
        """
        Método de exemplo para o cadastro do pedido.
        Aqui você chamaria a sua função de cadastro.
        """
        self.alerta.configure(text="Pedido cadastrado com sucesso!", text_color="green")


if __name__ == "__main__":
    app = PedidoApp()
    app.mainloop()
