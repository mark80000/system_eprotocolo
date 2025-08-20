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
from datetime import date, timedelta, datetime
import threading

# Configuração inicial do CustomTkinter
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# Caminho para o seu banco de dados SQLite
DB_PATH = "database/cartorio.db"

# Mapeamento de Status
STATUS_MAP = {
    "Em aberto": 1,
    "Reaberto - Não Concluído": 8,
}

# Mapeamento reverso
STATUS_MAP_REVERSE = {v: k for k, v in STATUS_MAP.items() if v is not None}

class PedidoApp(ctk.CTk):
    """
    Classe principal da aplicação de integração com a ONR.
    """
    def __init__(self):
        super().__init__()
        self.title("Integração E-Protocolo")
        self.geometry("900x530")
        self.minsize(width=900, height=530) # Corrigido para corresponder à geometria
        self.maxsize(width=900, height=530) # Corrigido para corresponder à geometria
        
        self.selected_pedido = None
        self.pedidos_onr_cache = []
        
        # Variáveis de estado para automação
        self.auto_cadastro_ativo = False
        self.auto_cadastro_job = None

        self._inicializar_db()

        # Estilo da Treeview
        style = ttk.Style(self)
        style.configure("Treeview", font=("Helvetica", 10), rowheight=25)
        style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))

        # Layout principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=50, corner_radius=1)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        self.btn_listar_onr = ctk.CTkButton(self.sidebar, text="Listar Pedidos", command=self.listar_pedidos_onr_gui, font=("Helvetica", 15))
        self.btn_listar_onr.pack(padx=10, pady=10)
        
        self.btn_limpar_lista = ctk.CTkButton(self.sidebar, text="Limpar Lista", command=self.limpar_cache, font=("Helvetica", 15))
        self.btn_limpar_lista.pack(padx=10, pady=10)
        
        self.btn_auto_cadastro = ctk.CTkButton(self.sidebar, text="Ativar Cadastro\nAutomático", command=self.iniciar_parar_cadastro_automatico, font=("Helvetica", 15), fg_color="#2c6e33")
        self.btn_auto_cadastro.pack(padx=10, pady=(30, 10))

        # Área Principal
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1) 
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.frame_filtros = self.criar_frame_filtros()
        self.frame_lista = self.criar_frame_lista()
        self.frame_detalhes = self.criar_frame_detalhes()
        
        # Barra de Status
        self.status_bar = ctk.CTkLabel(self, text="Pronto.", anchor="w", font=("Helvetica", 12))
        self.status_bar.grid(row=1, column=1, sticky="ew", padx=10, pady=(5, 5))
        
        self.mostrar_lista()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        if self.auto_cadastro_job:
            self.after_cancel(self.auto_cadastro_job)
        self.destroy()

    # =========================================================
    # FUNÇÕES DE CADASTRO AUTOMÁTICO (COM CORREÇÃO DE THREAD)
    # =========================================================
    def iniciar_parar_cadastro_automatico(self):
        self.auto_cadastro_ativo = not self.auto_cadastro_ativo
        if self.auto_cadastro_ativo:
            self.btn_auto_cadastro.configure(text="Desativar Cadastro\nAutomático", fg_color="dark red")
            self.btn_listar_onr.configure(state="disabled")
            self.status_bar.configure(text="Iniciando cadastro automático...")
            self.ciclo_automatico()
        else:
            self.btn_auto_cadastro.configure(text="Cadastro Automático", fg_color="#2c6e33")
            self.btn_listar_onr.configure(state="normal")
            if self.auto_cadastro_job:
                self.after_cancel(self.auto_cadastro_job)
                self.auto_cadastro_job = None
            self.status_bar.configure(text="Cadastro automático parado.")

    def ciclo_automatico(self):
        if not self.auto_cadastro_ativo:
            return

        # CORREÇÃO: Pega os valores da UI na thread principal
        try:
            data_inicial_api = datetime.strptime(self.data_inicial_entry.get(), "%d-%m-%Y").strftime("%Y-%m-%d")
            data_final_api = datetime.strptime(self.data_final_entry.get(), "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            self.status_bar.configure(text="Erro: Formato de data inválido. A automação foi parada.")
            self.iniciar_parar_cadastro_automatico() # Para a automação
            return

        # Passa as datas como argumento para a thread, que é mais seguro
        thread = threading.Thread(target=self.worker_cadastro_automatico, args=(data_inicial_api, data_final_api), daemon=True)
        thread.start()

    def worker_cadastro_automatico(self, data_inicial_api, data_final_api):
        """Executa a lógica de buscar e cadastrar em segundo plano."""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.after(0, lambda: self.status_bar.configure(text=f"Verificando pedidos... ({timestamp})"))

            resposta_lista = listar_pedidos(id_status=1, data_inicial=data_inicial_api, data_final=data_final_api)
            
            if not resposta_lista.RETORNO or not resposta_lista.Pedidos:
                msg = f"Nenhum pedido novo encontrado. Próxima verificação em 5 minutos."
                self.after(0, self.atualizar_gui_apos_ciclo, msg, 0)
                return

            pedidos_basicos = resposta_lista.Pedidos.ListPedidosAC_Pedidos_WSResp
            if not isinstance(pedidos_basicos, list):
                pedidos_basicos = [pedidos_basicos]
                
            pedidos_detalhados_zeep = get_detalhes_pedidos_listados(pedidos_basicos)
            
            if not pedidos_detalhados_zeep:
                msg = f"Nenhum detalhe encontrado. Próxima verificação em 5 minutos."
                self.after(0, self.atualizar_gui_apos_ciclo, msg, 0)
                return

            pedidos_cadastrados_count = 0
            for p in pedidos_detalhados_zeep:
                pedido_dict = serialize_object(p)
                try:
                    foi_salvo = salvar_detalhes_pedido(pedido_dict)
                    if foi_salvo:
                        pedidos_cadastrados_count += 1
                except sqlite3.IntegrityError:
                    pass # Pedido já existe, ignora
                except Exception as e:
                    print(f"Erro ao salvar pedido {pedido_dict.get('Protocolo')}: {e}")

            if pedidos_cadastrados_count > 0:
                msg = f"{pedidos_cadastrados_count} pedido(s) novo(s) cadastrado(s) às ({timestamp}). Verificando novamente em 5 min."
            else:
                msg = f"Nenhum pedido novo encontrado às {timestamp}. Verificando novamente em 5 min."
            
            self.after(0, self.atualizar_gui_apos_ciclo, msg, pedidos_cadastrados_count)

        except Exception as e:
            msg = f"Erro na automação: {str(e)[:50]}... Tentando novamente em 5 minutos."
            self.after(0, self.atualizar_gui_apos_ciclo, msg, 0)
            
    def atualizar_gui_apos_ciclo(self, message, num_cadastrados):
        """Atualiza a interface e reagenda o próximo ciclo."""
        self.status_bar.configure(text=message)
        
        if num_cadastrados > 0:
            self.listar_pedidos_onr_gui()
            self.carregar_pedidos_do_cache()

        if self.auto_cadastro_ativo:
            self.auto_cadastro_job = self.after(300000, self.ciclo_automatico)
            
    # =========================================================
    # MÉTODO `mostrar_detalhes` MODIFICADO
    # =========================================================
    
    def mostrar_detalhes(self):
        """Exibe o frame de detalhes com os campos essenciais para o cadastro."""
        if not self.selected_pedido:
            return

        self.frame_lista.grid_forget()
        self.frame_filtros.grid_forget()
        self.frame_detalhes.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)

        self.tree_detalhes.delete(*self.tree_detalhes.get_children())
        
        # Mapeia os nomes que você quer exibir para as chaves reais no dicionário do pedido
        campos_desejados = {
            "Protocolo": "Protocolo",
            "Data Pedido": "DataRemessa",
            "Solicitante": "Solicitante",
            "Telefone": "Telefone",
            "Documento": "TipoDocumento", # A API chama de "TipoDocumento"
            "Vendedor": "NomeVendedor",
            "CPF/CNPJ do Vendedor": "CPFCNPJVendedor",
            "Comprador": "NomeComprador",
            "CPF/CNPJ do Comprador": "CPFCNPJComprador",
        }

        for nome_amigavel, chave_real in campos_desejados.items():
            valor = self.selected_pedido.get(chave_real, "Não informado")
            if not valor:  # Garante que campos vazios também mostrem o placeholder
                valor = "Não informado"
            
            self.tree_detalhes.insert("", "end", values=(nome_amigavel, valor))

        self.validar_campos()
        
    # =========================================================
    # OUTROS MÉTODOS DA APLICAÇÃO
    # =========================================================
    
    def _inicializar_db(self):
        criar_tabela_se_nao_existir()
    
    def limpar_cache(self):
        if not self.pedidos_onr_cache:
            messagebox.showinfo("Info", "A lista já está limpa.")
            return
        self.pedidos_onr_cache = []
        self.mostrar_lista()
        messagebox.showinfo("Info", "Lista de pedidos temporários foi limpa.")

    def listar_pedidos_onr_gui(self):
        # ... (seu método listar_pedidos_onr_gui continua o mesmo)
        try:
            loading_label = ctk.CTkLabel(self.frame_lista, text="Buscando pedidos na ONR... Aguarde.", font=("Helvetica", 14), text_color="blue")
            loading_label.place(relx=0.5, rely=0.5, anchor="center")
            self.update_idletasks()
            
            status_id = STATUS_MAP.get(self.status_var.get())
            
            try:
                data_inicial_api = datetime.strptime(self.data_inicial_entry.get(), "%d-%m-%Y").strftime("%Y-%m-%d")
                data_final_api = datetime.strptime(self.data_final_entry.get(), "%d-%m-%Y").strftime("%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Erro de Data", "Formato de data inválido. Use DD-MM-AAAA.")
                loading_label.destroy()
                return

            resposta_lista = listar_pedidos(id_status=status_id, data_inicial=data_inicial_api, data_final=data_final_api)
            
            if not resposta_lista.RETORNO or not resposta_lista.Pedidos:
                messagebox.showinfo("Info", "Nenhum pedido encontrado na ONR com o filtro selecionado.")
                loading_label.destroy()
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
                return

            existing_ids = {p.get("IDContrato") for p in self.pedidos_onr_cache}
            novos_pedidos = []
            for p in pedidos_detalhados_zeep:
                pedido_dict = serialize_object(p)
                if pedido_dict.get("IDContrato") not in existing_ids:
                    novos_pedidos.append(pedido_dict)
                    existing_ids.add(pedido_dict.get("IDContrato"))
            
            self.pedidos_onr_cache.extend(novos_pedidos)

            loading_label.destroy()
            #messagebox.showinfo("Sucesso", f"{len(novos_pedidos)} novos pedidos carregados para a lista temporária.")
            
            self.mostrar_lista()

        except Exception as e:
            if 'loading_label' in locals(): loading_label.destroy()
            messagebox.showerror("Erro", f"Falha ao listar pedidos da ONR:\n{e}")

    def criar_frame_lista(self):
        frame = ctk.CTkFrame(self.main_frame)
        frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        
        self.tree = self.criar_tabela(frame)
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.bind("<Double-1>", self.selecionar_pedido)

        return frame

    def criar_tabela(self, parent):
        cols = {"Status": 150, "Protocolo": 100, "Instituição": 250, "Tipo Documento": 200, "Data Pedido": 150}
        tree = ttk.Treeview(parent, columns=list(cols.keys()), show="headings")
        
        for col, width in cols.items():
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor="w")
        
        tree.column("Data Pedido", anchor="center")
        
        return tree

    def carregar_pedidos_do_cache(self):
        self.tree.delete(*self.tree.get_children())
        
        for p in self.pedidos_onr_cache:
            data_remessa_display = self.formatar_data(p.get("DataRemessa", ""))
            
            valores = [
                STATUS_MAP_REVERSE.get(p.get("IDStatus"), p.get("IDStatus")),
                p.get("Protocolo"),
                p.get("Instituicao") or p.get("Solicitante", ""),
                p.get("TipoDocumento"),
                data_remessa_display
            ]
            self.tree.insert("", "end", values=valores, iid=p.get("IDContrato"))


    def carregar_pedidos_do_db(self):
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM pedidos_onr WHERE 1=1"
            params = []
            
            if status_id := STATUS_MAP.get(self.status_var.get()):
                query += " AND IDStatus = ?"
                params.append(status_id)
            
            if data_inicial := self.data_inicial_entry.get():
                query += " AND date(DataRemessa) >= ?"
                params.append(datetime.strptime(data_inicial, "%d-%m-%Y").strftime("%Y-%m-%d"))
            
            if data_final := self.data_final_entry.get():
                query += " AND date(DataRemessa) <= ?"
                params.append(datetime.strptime(data_final, "%d-%m-%Y").strftime("%Y-%m-%d"))

            query += " ORDER BY DataRemessa DESC"
            
            for p in cursor.execute(query, params).fetchall():
                data_remessa_display = self.formatar_data(p["DataRemessa"])
                
                valores = [
                    STATUS_MAP_REVERSE.get(p["IDStatus"], p["IDStatus"]),
                    p["Protocolo"],
                    p["Instituicao"] or p["Solicitante"],
                    p["TipoDocumento"],
                    data_remessa_display
                ]
                self.tree.insert("", "end", values=valores, iid=p["IDContrato"])

        except Exception as e:
            messagebox.showerror("Erro no Banco de Dados", f"Falha ao carregar pedidos:\n{e}")
        finally:
            conn.close()

    def formatar_data(self, data_str):
        if not data_str: return ""
        try:
            return datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y %H:%M:%S")
        except ValueError:
            try:
                return datetime.strptime(data_str.split(' ')[0], "%Y-%m-%d").strftime("%d-%m-%Y")
            except ValueError:
                return data_str

    def selecionar_pedido(self, event=None):
        selected_iid = self.tree.focus()
        if not selected_iid: return
        
        self.selected_pedido = next((p for p in self.pedidos_onr_cache if str(p.get("IDContrato")) == str(selected_iid)), None)

        if not self.selected_pedido:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            row = cursor.execute("SELECT * FROM pedidos_onr WHERE IDContrato = ?", (selected_iid,)).fetchone()
            conn.close()
            if row:
                self.selected_pedido = dict(row)
            else:
                messagebox.showerror("Erro", "Pedido não encontrado.")
                return
        
        self.mostrar_detalhes()
            
    def criar_frame_filtros(self):
        frame = ctk.CTkFrame(self.main_frame)
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        ctk.CTkLabel(frame, text="Status:", font=("Helvetica", 16)).pack(side="left", padx=(10, 5), pady=10)
        self.status_var = ctk.StringVar(value="Em aberto")
        self.status_combo = ctk.CTkComboBox(frame, values=list(STATUS_MAP.keys()), font=("Helvetica", 14), variable=self.status_var, width=190, command=lambda _: self.carregar_pedidos_do_cache())
        self.status_combo.pack(side="left", padx=5)

        data_hoje = date.today().strftime("%d-%m-%Y")
        data_ontem = (date.today() - timedelta(days=1)).strftime("%d-%m-%Y")

        ctk.CTkLabel(frame, text="Data Inicial:", font=("Helvetica", 16)).pack(side="left", padx=(15, 5))
        self.data_inicial_entry = ctk.CTkEntry(frame, width=120)
        self.data_inicial_entry.insert(0, data_ontem)
        self.data_inicial_entry.pack(side="left", padx=5)

        ctk.CTkLabel(frame, text="Data Final:", font=("Helvetica", 16)).pack(side="left", padx=(15, 5))
        self.data_final_entry = ctk.CTkEntry(frame, width=120)
        self.data_final_entry.insert(0, data_hoje)
        self.data_final_entry.pack(side="left", padx=5)
        
        return frame

    def criar_frame_detalhes(self):
        frame = ctk.CTkFrame(self.main_frame)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self.tree_detalhes = ttk.Treeview(frame, columns=("Campo", "Valor"), show="headings")
        self.tree_detalhes.heading("Campo", text="Campo")
        self.tree_detalhes.heading("Valor", text="Valor")
        self.tree_detalhes.column("Campo", width=200, anchor="w")
        self.tree_detalhes.column("Valor", width=450, anchor="w")
        self.tree_detalhes.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        vsb_det = ttk.Scrollbar(frame, orient="vertical", command=self.tree_detalhes.yview)
        vsb_det.grid(row=0, column=1, sticky="ns")
        self.tree_detalhes.configure(yscrollcommand=vsb_det.set)

        botoes_frame = ctk.CTkFrame(frame, fg_color="transparent")
        botoes_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")

        self.anexo_button = ctk.CTkButton(botoes_frame, text="Abrir Anexo", command=self.abrir_anexo)
        self.anexo_button.pack(side="left", padx=10)
        
        self.btn_voltar_lista = ctk.CTkButton(botoes_frame, text="Voltar", command=self.mostrar_lista)
        self.btn_voltar_lista.pack(side="right", padx=10)
        
        self.btn_cadastrar = ctk.CTkButton(botoes_frame, text="Cadastrar no Sistema", command=self.cadastrar, state="disabled")
        self.btn_cadastrar.pack(side="right", padx=10)

        return frame

    def mostrar_lista_db(self):
        self.frame_detalhes.grid_forget()
        self.frame_filtros.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.frame_lista.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.carregar_pedidos_do_db()
    
    def mostrar_lista(self):
        self.frame_detalhes.grid_forget()
        self.frame_filtros.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.frame_lista.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.carregar_pedidos_do_cache()

    def abrir_anexo(self):
        if self.selected_pedido and self.selected_pedido.get("UrlArquivoMandado"):
            webbrowser.open(self.selected_pedido["UrlArquivoMandado"])
        else:
            messagebox.showinfo("Info", "Anexo não disponível para este pedido.")

    def validar_campos(self):
        id_contrato = self.selected_pedido.get("IDContrato")
        conn = sqlite3.connect(DB_PATH)
        existe = conn.cursor().execute("SELECT 1 FROM pedidos_onr WHERE IDContrato = ?", (id_contrato,)).fetchone()
        conn.close()
        
        if existe:
            self.btn_cadastrar.configure(text="Já Cadastrado", state="disabled", fg_color="green")
        else:
            self.btn_cadastrar.configure(text="Cadastrar no Sistema", state="normal", fg_color=("#3a7ebf", "#1f538d"))

    def cadastrar(self):
        if self.selected_pedido:
            try:
                salvar_detalhes_pedido(self.selected_pedido)
                messagebox.showinfo("Sucesso", f"Pedido {self.selected_pedido.get('Protocolo')} cadastrado!")
                
                #id_cadastrado = self.selected_pedido.get('IDContrato')
                #self.pedidos_onr_cache = [p for p in self.pedidos_onr_cache if p.get('IDContrato') != id_cadastrado]
                self.mostrar_lista()
                 
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao cadastrar o pedido:\n{e}")

if __name__ == "__main__":
    app = PedidoApp()
    app.mainloop()