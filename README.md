# Explicações dos Scripts

## `browsersextrator.py`

Este script foi projetado para extrair dados armazenados por navegadores e aplicativos de desktop, como tokens do Discord, cookies, senhas e histórico de navegação de vários navegadores, incluindo Google Chrome, Brave, Opera e Yandex.

**Atenção: Uso restrito a fins educacionais.**

### Funcionalidades Principais:
- **Fechamento de Processos do browsers**
- **Extração de Senhas**
- **Múltiplos Perfis**
- **Salvamento de Senhas**



## `testenovoextrator.py`

Expande a funcionalidade de extração de dados, incluindo informações sobre o sistema operacional e chave de licença do Windows, além de enviar dados para webhooks.

**Atenção: Uso restrito a fins educacionais.**

### Funcionalidades Principais:
- **Informações do Sistema**
- **Coleta de Tokens e Informações do Navegador**
- **Coleta de Geolocalização**
- **Envio de Resultados para Webhooks**



## `chromeextrator.py`

Script especializado em extrair senhas do Google Chrome.

**Atenção: Este script deve ser usado apenas para fins educacionais.**

### Funcionalidades Principais:
- **Fechamento de Processos do Chrome**
- **Extração de Senhas**
- **Múltiplos Perfis**
- **Salvamento de Senhas**



## `keylogger.py`

Este script é um keylogger projetado para capturar as teclas pressionadas, tirar capturas de tela, capturar imagens da câmera e enviar tudo diretamente para um webhook no Discord.

**Atenção: Uso restrito a fins educacionais.**

### Funcionalidades Principais:
- **Captura de Teclas**: Armazena todas as teclas pressionadas, substituindo teclas especiais como `space` por um espaço real, `enter` por uma nova linha e outras teclas especiais como `backspace`, `shift` e `ctrl` por identificadores legíveis.
- **Envio de Teclas para o Discord**: As teclas capturadas são enviadas para o Discord em intervalos configurados, por padrão a cada 120 segundos ou após a captura de 10 teclas.
- **Captura de Tela**: Tira uma captura de tela em intervalos aleatórios (entre 120 e 180 segundos) e envia a imagem diretamente para o Discord, sem salvar localmente.
- **Captura de Imagem da Câmera**: Captura uma imagem da câmera do dispositivo e envia diretamente para o Discord, sem salvar localmente.
- **Webhook do Discord**: Todas as informações capturadas (teclas, capturas de tela e imagens da câmera) são enviadas diretamente para webhooks configurados no Discord, sem armazenar nada localmente no computador.


