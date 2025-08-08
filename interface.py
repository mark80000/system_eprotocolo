import customtkinter as ctk
import sqlite3
import webbrowser
from tkinter import ttk

# Configuração inicial
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

DB_PATH = "database/cartorio.db"

class PedidoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Integração ONR")
        self.geometry("1000x600")
        
        self.selected_pedido = None

        # Layout principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)

        self.btn_listar = ctk.CTkButton(self.sidebar, text="Listar Pedidos", command=self.mostrar_lista)
        self.btn_listar.pack(padx=10, pady=10, fill="x")

        # Área principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        # Criar frames da área principal
        self.frame_lista = self.criar_frame_lista()
        self.frame_detalhes = self.criar_frame_detalhes()

        self.mostrar_lista()

    # ================= Frame Lista =================
    def criar_frame_lista(self):
        frame = ctk.CTkFrame(self.main_frame)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        filtro_label = ctk.CTkLabel(frame, text="Tipo de Serviço")
        filtro_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.filtro_combo = ctk.CTkComboBox(frame, values=["Todos", "Registro / Averbação", "Outro"])
        self.filtro_combo.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.filtro_combo.set("Todos")
        self.filtro_combo.bind("<<ComboboxSelected>>", lambda e: self.carregar_pedidos())

        # Criando Treeview para lista
        colunas = ("Protocolo", "Solicitante", "TipoDocumento", "TipoServico")
        self.tree = ttk.Treeview(frame, columns=colunas, show="headings", height=20)

        for col in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="w", width=200)

        self.tree.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        # Scroll vertical
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=1, column=2, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)

        # Duplo clique para selecionar
        self.tree.bind("<Double-1>", self.selecionar_pedido)

        return frame

    def carregar_pedidos(self):
        tipo = self.filtro_combo.get()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if tipo == "Todos":
            cursor.execute("SELECT Protocolo, Solicitante, TipoDocumento, TipoServico FROM pedidos_onr")
        else:
            cursor.execute("SELECT Protocolo, Solicitante, TipoDocumento, TipoServico FROM pedidos_onr WHERE TipoServico = ?", (tipo,))

        pedidos = cursor.fetchall()
        conn.close()

        self.tree.delete(*self.tree.get_children())

        for p in pedidos:
            self.tree.insert("", "end", values=p)

    def selecionar_pedido(self, event=None):
        item = self.tree.focus()
        if not item:
            return
        valores = self.tree.item(item, "values")
        protocolo = valores[0]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pedidos_onr WHERE Protocolo = ?", (protocolo,))
        row = cursor.fetchone()
        colunas = [desc[0] for desc in cursor.description]
        conn.close()

        if row:
            self.selected_pedido = dict(zip(colunas, row))
            self.mostrar_detalhes()

    # ================= Frame Detalhes =================
    def criar_frame_detalhes(self):
        frame = ctk.CTkFrame(self.main_frame)
        frame.grid_columnconfigure(0, weight=1)

        self.tree_detalhes = ttk.Treeview(frame, columns=("Campo", "Valor"), show="headings", height=15)
        self.tree_detalhes.heading("Campo", text="Campo")
        self.tree_detalhes.heading("Valor", text="Valor")
        self.tree_detalhes.column("Campo", width=200, anchor="w")
        self.tree_detalhes.column("Valor", width=600, anchor="w")
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

        self.alerta = ctk.CTkLabel(frame, text="", text_color="red")
        self.alerta.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        return frame

    def mostrar_lista(self):
        self.frame_detalhes.grid_forget()
        self.frame_lista.grid(row=0, column=0, sticky="nsew")
        self.carregar_pedidos()

    def mostrar_detalhes(self):
        if not self.selected_pedido:
            self.alerta.configure(text="Selecione um pedido primeiro.")
            return

        self.frame_lista.grid_forget()
        self.frame_detalhes.grid(row=0, column=0, sticky="nsew")

        self.tree_detalhes.delete(*self.tree_detalhes.get_children())

        campos_exibir = [
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
        if self.selected_pedido and self.selected_pedido.get("UrlArquivoMandado"):
            webbrowser.open(self.selected_pedido["UrlArquivoMandado"])
        else:
            self.alerta.configure(text="Anexo não disponível.")

    def validar_campos(self):
        if self.selected_pedido:
            self.btn_cadastrar.configure(state="normal")
        else:
            self.btn_cadastrar.configure(state="disabled")

    def cadastrar(self):
        self.alerta.configure(text="Pedido cadastrado com sucesso!", text_color="green")


if __name__ == "__main__":
    app = PedidoApp()
    app.mainloop()