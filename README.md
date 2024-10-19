# Explicações dos Scripts

## `browsersextrator.py`

Este script foi projetado para extrair dados armazenados por navegadores e aplicativos de desktop, como tokens do Discord, cookies, senhas e histórico de navegação de vários navegadores, incluindo Google Chrome, Brave, Opera e Yandex. Ele usa bibliotecas como `sqlite3`, `win32crypt`, `AES` e outras para acessar bancos de dados locais e descriptografar informações sensíveis.

### Funcionalidades Principais:
- **Coleta de Tokens**: O script percorre vários caminhos de aplicativos em busca de tokens armazenados no `Local Storage`, e descriptografa utilizando chaves extraídas dos arquivos de estado local (`Local State`).
- **Extração de Histórico de Navegação**: Copia o banco de dados de histórico de navegação e extrai informações como URLs visitadas, títulos das páginas e contagem de visitas.
- **Extração de Dados de Preenchimento Automático**: Acessa o banco de dados `Autofill` dos navegadores para extrair informações preenchidas automaticamente em formulários.
- **Extração de Cartões de Crédito**: Descriptografa números de cartões de crédito armazenados e exibe os dados, incluindo nome no cartão e data de expiração.
- **Salvamento dos Resultados**: Os dados extraídos são salvos em arquivos de texto localizados na área de trabalho do usuário, utilizando caminhos dinâmicos.

---

## `extrator.py`

Este script expande a funcionalidade de extração de dados, com ênfase na coleta de tokens e dados de navegação, além de obter informações sobre o sistema operacional e a chave de licença do Windows.

### Funcionalidades Principais:
- **Informações do Sistema**: Coleta dados sobre o sistema, como o nome do computador, sistema operacional, chave do Windows, e endereço MAC.
- **Coleta de Tokens e Informações do Navegador**: Semelhante ao script anterior, extrai tokens de várias plataformas, como Discord e Steam, além de descriptografar senhas e cookies armazenados nos navegadores.
- **Coleta de Geolocalização**: Usa a API `ipinfo.io` para obter informações de geolocalização com base no IP público do usuário.
- **Envio de Resultados para Webhooks**: Pode enviar os resultados coletados para um webhook do Discord ou Telegram, conforme as configurações fornecidas.

---

## `chromeextrator.py`

Este script é especializado na extração de senhas armazenadas no navegador Google Chrome, lidando com múltiplos perfis de usuário.

### Funcionalidades Principais:
- **Fechamento de Processos do Chrome**: Antes de acessar os dados, o script força o fechamento de processos do Chrome para evitar conflitos com os bancos de dados bloqueados.
- **Extração de Senhas**: Descriptografa senhas armazenadas nos bancos de dados do Chrome, utilizando chaves de criptografia extraídas do arquivo `Local State`.
- **Múltiplos Perfis**: Processa vários perfis do Chrome, extraindo senhas de todos os perfis identificados no diretório do navegador.
- **Salvamento de Senhas**: As senhas descriptografadas são salvas em um arquivo `ChromePasswords.txt` localizado na área de trabalho do usuário.
