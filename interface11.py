import customtkinter as ctk
from tkinter import messagebox
import psycopg2  # <-- Alterado de sqlite3
from psycopg2.extras import DictCursor  # <-- Novo: para facilitar o acesso aos dados
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

# --- NOVA CONFIGURAÇÃO DE CONEXÃO POSTGRESQL ---
# Preencha com os dados do seu banco de dados PostgreSQL
DB_CONFIG = {
    "dbname": "nome_do_banco",
    "user": "seu_usuario",
    "password": "sua_senha",
    "host": "localhost",  # ou o IP do servidor do banco
    "port": "5432"
}
# -------------------------------------------------

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
        self.minsize(width=900, height=530)
        self.maxsize(width=900, height=530)
        
        self.selected_pedido = None
        self.pedidos_onr_cache = []
        
        self.auto_cadastro_ativo = False
        self.auto_cadastro_job = None

        self._inicializar_db()

        style = ttk.Style(self)
        style.configure("Treeview", font=("Helvetica", 10), rowheight=25)
        style.configure("Treeview.Heading", font=("Helvetica", 12, "bold"))

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=50, corner_radius=1)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        self.btn_listar_onr = ctk.CTkButton(self.sidebar, text="Buscar na ONR", command=self.listar_pedidos_onr_gui, font=("Helvetica", 15))
        self.btn_listar_onr.pack(padx=10, pady=10)
        
        self.btn_limpar_lista = ctk.CTkButton(self.sidebar, text="Limpar Lista", command=self.limpar_cache, font=("Helvetica", 15))
        self.btn_limpar_lista.pack(padx=10, pady=10)
        
        self.btn_auto_cadastro = ctk.CTkButton(self.sidebar, text="Cadastro Automático", command=self.iniciar_parar_cadastro_automatico, font=("Helvetica", 15), fg_color="#2c6e33")
        self.btn_auto_cadastro.pack(padx=10, pady=(30, 10))

        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1) 
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.frame_filtros = self.criar_frame_filtros()
        self.frame_lista = self.criar_frame_lista()
        self.frame_detalhes = self.criar_frame_detalhes()
        
        self.status_bar = ctk.CTkLabel(self, text="Pronto.", anchor="w", font=("Helvetica", 12))
        self.status_bar.grid(row=1, column=1, sticky="ew", padx=10, pady=(5, 5))
        
        self.mostrar_lista_db() # Alterado para mostrar a lista do DB por padrão
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        if self.auto_cadastro_job:
            self.after_cancel(self.auto_cadastro_job)
        self.destroy()

    def iniciar_parar_cadastro_automatico(self):
        self.auto_cadastro_ativo = not self.auto_cadastro_ativo
        if self.auto_cadastro_ativo:
            self.btn_auto_cadastro.configure(text="Parar Automação", fg_color="dark red")
            self.btn_listar_onr.configure(state="disabled")
            self.status_bar.configure(text="Iniciando cadastro automático...")
            self.ciclo_automatico()
        else:
            self.btn_auto_cadastro.configure(text="Cadastro Automático", fg_color="#2c6e33")
            self.btn_listar_onr.configure(state="normal")
            if self.auto_cadastro_job:
                self.after_cancel(self.auto_cadastro_job)
            self.status_bar.configure(text="Cadastro automático parado.")

    def ciclo_automatico(self):
        if not self.auto_cadastro_ativo:
            return
        try:
            data_inicial_api = datetime.strptime(self.data_inicial_entry.get(), "%d-%m-%Y").strftime("%Y-%m-%d")
            data_final_api = datetime.strptime(self.data_final_entry.get(), "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            self.status_bar.configure(text="Erro: Formato de data inválido. A automação foi parada.")
            self.iniciar_parar_cadastro_automatico()
            return
        thread = threading.Thread(target=self.worker_cadastro_automatico, args=(data_inicial_api, data_final_api), daemon=True)
        thread.start()

    def worker_cadastro_automatico(self, data_inicial_api, data_final_api):
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
                try:
                    foi_salvo = salvar_detalhes_pedido(serialize_object(p))
                    if foi_salvo:
                        pedidos_cadastrados_count += 1
                except psycopg2.Error as e: # <-- Alterado para erro do psycopg2
                    print(f"Erro de banco de dados ao salvar pedido: {e}")
            
            if pedidos_cadastrados_count > 0:
                msg = f"{pedidos_cadastrados_count} pedido(s) novo(s) cadastrado(s) às {timestamp}."
            else:
                msg = f"Nenhum pedido novo encontrado às {timestamp}. Verificando novamente em 5 min."
            self.after(0, self.atualizar_gui_apos_ciclo, msg, pedidos_cadastrados_count)

        except Exception as e:
            msg = f"Erro na automação: {str(e)[:50]}... Tentando novamente em 5 minutos."
            self.after(0, self.atualizar_gui_apos_ciclo, msg, 0)

    def atualizar_gui_apos_ciclo(self, message, num_cadastrados):
        self.status_bar.configure(text=message)
        if num_cadastrados > 0:
            self.carregar_pedidos_do_db()
        if self.auto_cadastro_ativo:
            self.auto_cadastro_job = self.after(300000, self.ciclo_automatico)
            
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
        # ... (esta função não muda, pois não acessa o banco de dados diretamente) ...
        pass # A lógica existente está correta

    def carregar_pedidos_do_db(self):
        self.tree.delete(*self.tree.get_children())
        conn = None
        try:
            # Conexão com PostgreSQL
            conn = psycopg2.connect(**DB_CONFIG)
            # Usando DictCursor para acessar colunas pelo nome
            cursor = conn.cursor(cursor_factory=DictCursor)

            query = "SELECT * FROM pedidos_onr WHERE 1=1"
            params = []
            
            if status_id := STATUS_MAP.get(self.status_var.get()):
                # Placeholders mudam de '?' para '%s'
                query += " AND \"IDStatus\" = %s" 
                params.append(status_id)
            
            if data_inicial := self.data_inicial_entry.get():
                query += " AND date(\"DataRemessa\") >= %s"
                params.append(datetime.strptime(data_inicial, "%d-%m-%Y").strftime("%Y-%m-%d"))
            
            if data_final := self.data_final_entry.get():
                query += " AND date(\"DataRemessa\") <= %s"
                params.append(datetime.strptime(data_final, "%d-%m-%Y").strftime("%Y-%m-%d"))

            query += " ORDER BY \"DataRemessa\" DESC"
            
            cursor.execute(query, params)
            for p in cursor.fetchall():
                valores = [
                    STATUS_MAP_REVERSE.get(p["IDStatus"], p["IDStatus"]),
                    p["protocolo"], # Nomes de coluna em minúsculo no psycopg2 com DictCursor
                    p["instituicao"] or p["solicitante"],
                    p["tipodocumento"],
                    self.formatar_data(p["dataremessa"])
                ]
                self.tree.insert("", "end", values=valores, iid=p["idcontrato"])

        except psycopg2.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Falha ao conectar ou carregar pedidos do PostgreSQL:\n{e}")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro inesperado:\n{e}")
        finally:
            if conn:
                conn.close()

    def selecionar_pedido(self, event=None):
        selected_iid = self.tree.focus()
        if not selected_iid: return
        
        self.selected_pedido = next((p for p in self.pedidos_onr_cache if str(p.get("IDContrato")) == str(selected_iid)), None)

        if not self.selected_pedido:
            conn = None
            try:
                conn = psycopg2.connect(**DB_CONFIG)
                cursor = conn.cursor(cursor_factory=DictCursor)
                # Placeholders mudam de '?' para '%s'
                cursor.execute("SELECT * FROM pedidos_onr WHERE \"IDContrato\" = %s", (selected_iid,))
                row = cursor.fetchone()
                if row:
                    self.selected_pedido = dict(row)
                else:
                    messagebox.showerror("Erro", "Pedido não encontrado no banco de dados.")
                    return
            except psycopg2.Error as e:
                messagebox.showerror("Erro de Banco de Dados", f"Falha ao buscar pedido:\n{e}")
                return
            finally:
                if conn:
                    conn.close()
        
        self.mostrar_detalhes()

    def validar_campos(self):
        id_contrato = self.selected_pedido.get("IDContrato") or self.selected_pedido.get("idcontrato")
        conn = None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            # Placeholders mudam de '?' para '%s'
            cursor.execute("SELECT 1 FROM pedidos_onr WHERE \"IDContrato\" = %s", (id_contrato,))
            existe = cursor.fetchone()
        except psycopg2.Error as e:
            messagebox.showerror("Erro de Banco de Dados", f"Falha ao validar pedido:\n{e}")
            return
        finally:
            if conn:
                conn.close()
        
        if existe:
            self.btn_cadastrar.configure(text="Já Cadastrado", state="disabled", fg_color="green")
        else:
            self.btn_cadastrar.configure(text="Cadastrar no Sistema", state="normal", fg_color=("#3a7ebf", "#1f538d"))

    # ... O resto dos métodos da interface (criar frames, formatar data, etc.) não precisam de grandes mudanças ...
    # (O código restante da classe foi omitido por ser idêntico)