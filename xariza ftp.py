import os
import json
import threading
from pathlib import Path
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from tkinter import Tk, filedialog, messagebox, StringVar, Entry, Label, Button, Text, Scrollbar, Frame, END, DISABLED, NORMAL, Toplevel
import time
import socket
class FTPServerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Servidor FTP Local")
        try:
            self.root.iconbitmap(os.path.abspath("ico.ico"))
        except:
            pass

        self.server = None
        self.is_running = False

        # Variáveis
        self.is_local_only = True  # Variável para controle de acesso local

        self.folder_path = StringVar()
        self.username = StringVar()
        self.password = StringVar()
        self.url_access = StringVar()
        self.log_text = None

        # Diretório para salvar configurações
        self.config_path = Path(os.getenv("APPDATA")) / "ftp_server_config.json"

        # Criação da interface
        self.create_widgets()

        # Carrega as configurações
        self.load_config()

    def create_widgets(self):
        frame_config = Frame(self.root)
        frame_config.pack(padx=10, pady=10, fill="x")

        Label(frame_config, text="Pasta de Origem:").grid(row=0, column=0, sticky="w")
        Entry(frame_config, textvariable=self.folder_path, width=50).grid(row=0, column=1)
        Button(frame_config, text="Selecionar", command=self.select_folder).grid(row=0, column=2)

        Label(frame_config, text="Usuário:").grid(row=1, column=0, sticky="w")
        Entry(frame_config, textvariable=self.username).grid(row=1, column=1)

        Label(frame_config, text="Senha:").grid(row=2, column=0, sticky="w")
        Entry(frame_config, textvariable=self.password, show="*").grid(row=2, column=1)

        frame_control = Frame(self.root)
        frame_control.pack(pady=10)
        Button(frame_control, text="Permitir Acesso na Rede", command=self.toggle_network_access).pack(side="left", padx=5)


        Button(frame_control, text="Iniciar Servidor", command=self.start_server).pack(side="left", padx=5)
        Button(frame_control, text="Parar Servidor", command=self.stop_server).pack(side="left", padx=5)

        frame_log = Frame(self.root)
        frame_log.pack(padx=10, pady=10, fill="both", expand=True)

        Label(frame_log, text="Log:").pack(anchor="w")
        self.log_text = Text(frame_log, state=DISABLED, height=10)
        self.log_text.pack(side="left", fill="both", expand=True)

        scrollbar = Scrollbar(frame_log, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text["yscrollcommand"] = scrollbar.set

        frame_url = Frame(self.root)
        frame_url.pack(padx=10, pady=5, fill="x")

        Label(frame_url, text="Como Acessar:").pack(anchor="w")
        self.url_text = Text(frame_url, state=DISABLED, height=2)
        self.url_text.pack(fill="x", expand=True)

        Button(self.root, text="Instruções", command=self.show_instructions).pack(pady=5)

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)

    def load_config(self):
        if self.config_path.exists():
            with open(self.config_path, "r") as config_file:
                config = json.load(config_file)
                self.folder_path.set(config.get("folder", ""))
                self.username.set(config.get("username", ""))
                self.password.set(config.get("password", ""))

    def save_config(self):
        config = {
            "folder": self.folder_path.get(),
            "username": self.username.get(),
            "password": self.password.get(),
        }
        with open(self.config_path, "w") as config_file:
            json.dump(config, config_file)
    def get_local_ip(self):
        try:
            # Cria um socket e se conecta a um servidor externo para descobrir o IP local
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            s.connect(('8.8.8.8', 1))  # Conecta-se ao servidor DNS do Google (8.8.8.8)
            ip = s.getsockname()[0]  # Obtém o endereço IP local
            s.close()
            return ip
        except Exception as e:
            return f"Erro ao obter o IP: {e}"

    def toggle_network_access(self):
        self.is_local_only = not self.is_local_only
        access_type = "local" if self.is_local_only else f"na rede use >>>{self.get_local_ip()}< para Acessar nos outros computadores da rede"
        self.log(f"Configuração alterada para acesso {access_type}.")

    def start_server(self):
        if self.is_running:
            self.log("O servidor já está em execução.")
            return

        folder = self.folder_path.get()
        username = self.username.get()
        password = self.password.get()

        if not folder or not username or not password:
            messagebox.showerror("Erro", "Pasta de origem, usuário e senha são obrigatórios.")
            return

        self.save_config()

        self.authorizer = DummyAuthorizer()
        self.authorizer.add_user(username, password, folder, perm="elradfmw")

        handler = FTPHandler
        handler.authorizer = self.authorizer
       # handler.log = self.log

        try:
            ip_address = "127.0.0.1" if self.is_local_only else "0.0.0.0"
            self.server = FTPServer((ip_address, 2121), handler)
            self.log("Servidor FTP iniciado na pasta: " + folder)

            self.update_url_access(username, password)

            self.is_running = True
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
        except Exception as e:
            self.log(f"Erro ao iniciar o servidor: {e}")

    def stop_server(self):
        if not self.is_running:
            self.log("O servidor não está em execução.")
            return

        self.server.close_all()
        self.is_running = False
        self.log("Servidor FTP parado.")
        self.clear_url_access()

    def log(self, message):
        self.log_text.config(state=NORMAL)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(END, f"[{timestamp}] {message}\n")
        self.log_text.config(state=DISABLED)
        self.log_text.see(END)

    def update_url_access(self, username, password):
        url = f"ftp://{username}:{password}@localhost:2121"
        self.url_text.config(state=NORMAL)
        self.url_text.delete(1.0, END)
        self.url_text.insert(END, url)
        self.url_text.config(state=DISABLED)

    def clear_url_access(self):
        self.url_text.config(state=NORMAL)
        self.url_text.delete(1.0, END)
        self.url_text.config(state=DISABLED)

    def show_instructions(self):
        instructions_window = Toplevel(self.root)
        instructions_window.title("Instruções")
        instructions_window.geometry("500x400")
        try:
         instructions_window.iconbitmap(os.path.abspath("ico.ico"))
        except:
            pass
        instructions_text = Text(instructions_window, wrap="word", height=25, width=60)
        instructions_text.pack(expand=True, fill="both")

        instructions = """
        Instruções para Acessar o Servidor FTP:

        1. **Acessando o Servidor FTP com FileZilla:**
            a. Abra o FileZilla Client.
            b. Insira as seguintes informações nos campos superiores:
               - Host: localhost
               - Nome de Usuário: O usuário que você configurou
               - Senha: A senha que você configurou
               - Porta: 2121
            c. Clique em "Quickconnect" para se conectar ao servidor FTP.

        2. **Acessando Externamente (Abrir as Portas no Roteador):**
            a. Identifique o IP local do seu computador:
               - No Windows: Use `ipconfig` no Prompt de Comando e veja o `Endereço IPv4`.
               - No macOS/Linux: Use `ifconfig` ou `hostname -I` no Terminal.
            b. Abra o navegador e acesse o IP do seu roteador (ex.: `192.168.1.1`).
            c. Faça login com o nome de usuário e senha do roteador.
            d. Encontre a seção de Port Forwarding ou Virtual Server.
            e. Adicione uma nova regra:
               - Porta Externa: 2121
               - Porta Interna: 2121
               - IP Local: O IP do seu computador (ex.: `192.168.x.x`)
               - Protocolo: TCP
               - Ative a regra.
            f. Salve as configurações e reinicie o roteador se necessário.

        3. **Acessando de Qualquer Lugar:**
            a. Descubra seu IP público visitando [WhatIsMyIP](https://www.whatismyip.com/).
            b. Use o IP público e a porta 2121 para conectar-se ao servidor FTP de qualquer lugar.

        **Nota:** Certifique-se de que seu firewall está configurado para permitir conexões na porta 2121.
        """
        instructions_text.insert(END, instructions)
        instructions_text.config(state=DISABLED)

if __name__ == "__main__":
    root = Tk()
    app = FTPServerApp(root)
    root.mainloop()
