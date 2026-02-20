# 🐍 Guia de Instalação — Aplicação de Tradução Python (Windows + Oracle)

Este guia descreve **passo a passo** como instalar e executar o projeto `traduz-msg.py` no Windows, usando **Python 3.14**, **oracledb (modo thick)** e o **Oracle Instant Client 21.19**.

---

### ⚙️ 1. Pré-Requisitos
**Python 3.14** instalado  
Verifique com:
```powershell
python --version
```

---

### 🐍 2. Criar e Ativar o Ambiente Virtual
```powershell
python -m venv .venv
```
```powershell
. .\.venv\Scripts\Activate.ps1
```

Você deve ver algo como:
```powershell
(.venv) PS C:\projetos-python\traduz_msg_erp>
```

---

### 📥 3. Instalar Dependências
```powershell
python -m pip install --upgrade pip setuptools wheel
```
```powershell
pip install -r requirements.txt
```

---

### 🗝️ 4. Criar o Arquivo .env

Crie o arquivo .env na mesma pasta do arquivo `traduz-msg.py`:
```python
DEEPL_AUTH_KEY=TOKEN_DEEPL
ORACLE_USER=KUNDEN
ORACLE_PASSWORD=SENHA
ORACLE_DSN=10.0.2.20:1521/desenvknd.oraclevcn.com
ORACLE_CLIENT_DIR=C:\oracle\instantclient_21_19
```

⚠️ Nunca compartilhe esse arquivo. Ele contém credenciais sensíveis.

---

### 🧠 5. Baixar e Instalar o Oracle Instant Client 21.19

Acesse:
🔗 https://www.oracle.com/br/database/technologies/instant-client/winx64-64-downloads.html

Baixe Instant Client Package - Basic Light (ZIP)  
Exemplo: `instantclient-basiclite-windows.x64-21.19.0.0.0dbru.zip`

Extraia o ZIP dentro de uma pasta oracle no C:  
Exemplo: `C:\oracle\instantclient_21_19\`

---

### ▶️ 6. Executar o Script
```powershell
python traduz-msg.py
```

Digite os pedidos solicitados no prompt e aguarde a execução.

---

### 💡 7. Gerar o Executável .exe
```powershell
pyinstaller --onedir --console --noconfirm traduz-msg.py --hidden-import getpass --hidden-import dotenv --hidden-import html --hidden-import logging --hidden-import pathlib --hidden-import platform --add-data ".env;."
```

Executável gerado em: `dist\traduz-msg\traduz-msg.exe`

---

### ➡️ 8. Cria arquivo `requirements.txt`

É criado um arquivo `requirements.txt` com todas dependências do projeto
```powershell
pip freeze > requirements.txt
```