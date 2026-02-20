import os
import sys
import html
import logging
from pathlib import Path
from typing import Tuple, Dict, List

import oracledb
import deepl

# ---------------- Base paths (funciona em .py e .exe) ----------------
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)).resolve()

# ---------------- Logging ----------------
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "traduz-msg.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

def _pause():
    try:
        input("\nPressione Enter para fechar...")
    except Exception:
        pass

# ---------------- Carregar .env (EXPRESSO + DIAGNÓSTICO) ----------------
def load_env_or_die():

    dotenv_loaded = False
    try:
        from dotenv import load_dotenv
        # tenta nas 3 possibilidades:
        candidatos = [
            BASE_DIR / ".env",                     # dentro de _internal
            BASE_DIR.parent / ".env",              # raiz da pasta traduz-msg
            Path.cwd() / ".env"                    # local de execução
        ]
        for p in candidatos:
            if p.is_file():
                load_dotenv(dotenv_path=p, override=True)
                logging.info(".env carregado de %s", p)
                dotenv_loaded = True
                break

        if not dotenv_loaded:
            print("[ERRO] .env não encontrado em nenhuma das pastas esperadas:")
            for p in candidatos:
                print("  -", p)
            logging.warning(".env NÃO encontrado em candidatos")
    except Exception as e:
        print("Aviso: erro ao carregar .env:", e)

load_env_or_die()

# ---------------- Inicialização do Oracle Client ----------------
def resolve_client_dir() -> str | None:
    client_dir = os.getenv("ORACLE_CLIENT_DIR")
    if client_dir:
        p = Path(client_dir)
        if not p.is_absolute():
            p = BASE_DIR / p  # permite "instantclient_21_19" no .env
        if p.is_dir():
            return str(p)

    local_dir = BASE_DIR / "instantclient_21_19"
    if local_dir.is_dir():
        return str(local_dir)
    return None

CLIENT_DIR = resolve_client_dir()
if CLIENT_DIR:
    try:
        oracledb.init_oracle_client(lib_dir=CLIENT_DIR)
    except Exception as e:
        print("\n❌ ERRO ao inicializar o Oracle Client:", e)
        print("Verifique ORACLE_CLIENT_DIR no .env e a presença de oci.dll nessa pasta.")
        print("Logs:", LOG_FILE.resolve())
        _pause()
        sys.exit(1)
else:
    print("\n❌ ERRO: não foi possível localizar a pasta do Oracle Instant Client.")
    print("Defina ORACLE_CLIENT_DIR no .env (absoluto ou 'instantclient_21_19' ao lado do exe).")
    print("Logs:", LOG_FILE.resolve())
    _pause()
    sys.exit(1)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def get_env(name: str, default: str | None = None, *, required: bool = False) -> str:
    v = os.getenv(name, default)
    if required and (v is None or str(v).strip() == ""):
        print(f"[ERRO] Variável de ambiente '{name}' não definida.", file=sys.stderr)
        input("\nPressione Enter para fechar...")
        sys.exit(1)
    return str(v)

def traduzir_texto(texto: str, target_lang: str) -> str:
    """Traduz usando DeepL."""
    auth_key = get_env("DEEPL_AUTH_KEY", required=True)
    translator = deepl.Translator(auth_key)
    # target_lang: "es" (espanhol), "en-US" (inglês EUA), etc.
    result = translator.translate_text(texto, target_lang=target_lang)
    # Decodificar HTML entities caso venham do banco
    return html.unescape(result.text)

def make_bind_list(values_csv: str) -> Tuple[List[str], Dict[str, str]]:
    """
    Converte "10,20,30" em binds (:p0,:p1,:p2) e dict de valores.
    Remove vazios e espaços.
    """
    vals = [v.strip() for v in values_csv.split(",") if v.strip() != ""]
    binds: List[str] = []
    params: Dict[str, str] = {}
    for i, v in enumerate(vals):
        key = f"p{i}"
        binds.append(f":{key}")
        params[key] = v
    return binds, params

# -----------------------------------------------------------------------------
# Principal
# -----------------------------------------------------------------------------
def traduz_pedidos(pedido_csv: str) -> None:
    pedido_csv = (pedido_csv or "").strip()
    if not pedido_csv:
        print("Nenhum pedido informado.")
        return

    # Credenciais/DSN do Oracle via .env
    username = get_env("ORACLE_USER", required=True)
    password = get_env("ORACLE_PASSWORD", required=True)
    dsn = get_env("ORACLE_DSN", required=True)

    # Conexão (modo thick já está ativo via init_oracle_client)
    with oracledb.connect(user=username, password=password, dsn=dsn) as connection:
        binds, params = make_bind_list(pedido_csv)
        if not binds:
            print("Nenhum pedido válido informado.")
            return

        in_clause = ", ".join(binds)

        query = f"""
            SELECT I.DESCRICAO,
                   I.CODIGO,
                   I.TIPO,
                   I.SERVICO_ID,
                   CASE WHEN NOT EXISTS (SELECT 1
                                           FROM MENSAGEM_ERRO_ATM
                                          WHERE CODIGO = I.CODIGO
                                            AND IDIOMA_ID = 2)
                        THEN 'es'
                        ELSE NULL
                   END AS FALTA_TRADUCAO_ES,
                   CASE WHEN NOT EXISTS (SELECT 1
                                           FROM MENSAGEM_ERRO_ATM
                                          WHERE CODIGO = I.CODIGO
                                            AND IDIOMA_ID = 3)
                        THEN 'en-US'
                        ELSE NULL
                   END AS FALTA_TRADUCAO_EN
              FROM SERVICO_ATM@LK_ADMKND S,
                   MENSAGEM_ERRO_ATM I
             WHERE S.ID = I.SERVICO_ID
               AND S.PEDIDO IN ({in_clause})
               AND I.IDIOMA_ID = 1
               AND (
                    NOT EXISTS (SELECT 1 FROM MENSAGEM_ERRO_ATM WHERE CODIGO = I.CODIGO AND IDIOMA_ID = 2)
                 OR NOT EXISTS (SELECT 1 FROM MENSAGEM_ERRO_ATM WHERE CODIGO = I.CODIGO AND IDIOMA_ID = 3)
               )
             ORDER BY I.SERVICO_ID, I.CODIGO
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if not rows:
                print("Nenhum registro para traduzir.")
                return

            insert_sql = """
                INSERT INTO MENSAGEM_ERRO_ATM (
                    ID, CODIGO, DESCRICAO, SERVICO_ID, IDIOMA_ID, TIPO, USUARIO, DATA_HORA
                )
                VALUES (
                    :id, :codigo, :descricao, :servico_id, :idioma_id, :tipo, 'KUNDEN', SYSDATE
                )
            """

            for descricao, codigo, tipo, servico_id, falta_es, falta_en in rows:
                # ES
                if falta_es:
                    descricao_es = traduzir_texto(descricao, falta_es)
                    with connection.cursor() as c_id:
                        c_id.execute("SELECT NVL(MAX(ID),0) + 1 FROM MENSAGEM_ERRO_ATM")
                        (next_id,) = c_id.fetchone()
                    with connection.cursor() as c_ins:
                        c_ins.execute(
                            insert_sql,
                            dict(
                                id=next_id,
                                codigo=codigo,
                                descricao=descricao_es,
                                servico_id=servico_id,
                                idioma_id=2,
                                tipo=tipo,
                            ),
                        )

                # EN
                if falta_en:
                    descricao_en = traduzir_texto(descricao, falta_en)
                    with connection.cursor() as c_id:
                        c_id.execute("SELECT NVL(MAX(ID),0) + 1 FROM MENSAGEM_ERRO_ATM")
                        (next_id,) = c_id.fetchone()
                    with connection.cursor() as c_ins:
                        c_ins.execute(
                            insert_sql,
                            dict(
                                id=next_id,
                                codigo=codigo,
                                descricao=descricao_en,
                                servico_id=servico_id,
                                idioma_id=3,
                                tipo=tipo,
                            ),
                        )

                # Remover idiomas “antigos” não PT/ES/EN
                with connection.cursor() as c_del:
                    c_del.execute(
                        """
                        DELETE FROM MENSAGEM_ERRO_ATM
                         WHERE SERVICO_ID = :sid
                           AND IDIOMA_ID NOT IN (1,2,3)
                        """,
                        dict(sid=servico_id),
                    )

                print(f"Codigo: {codigo} - OK")

            connection.commit()
            print("Tradução realizada com sucesso.")

# -----------------------------------------------------------------------------
# Execução
# -----------------------------------------------------------------------------
def _pause():
    try:
        input("\nPressione Enter para fechar...")
    except Exception:
        pass

if __name__ == "__main__":
    try:
        pedidos = input("Digite os pedidos separados por vírgula: ")
        traduz_pedidos(pedidos)
        print(f"\nOK. Logs (se houver): {LOG_FILE.resolve()}")
        _pause()
    except Exception as e:
        logging.exception("Falha na execução")
        print("\nERRO na execução:")
        print(e)
        print(f"\nConsulte o log: {LOG_FILE.resolve()}")
        _pause()
