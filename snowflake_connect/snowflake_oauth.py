# %% [markdown]
# # Snowflake OAuth認証と接続確認
# 環境変数と接続設定の準備はREADME.mdを参照してください。
# import時には認証・接続しません。トークンはリポジトリ外へ保存します。

# %% 認証・接続関数の定義
import json
import os
import re
import tempfile
import time
from pathlib import Path
from uuid import UUID

import requests
import snowflake.connector
import yaml
from dotenv import load_dotenv
from snowflake.connector.errors import Error as SnowflakeError

# %% 2. 設定と認証の関数（ここでは通信しない）
TIMEOUT_SECONDS = 60 * 60
MODULE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = MODULE_DIR / "snowflake_oauth.yml"
ENV_PATH = MODULE_DIR.parent / ".env"
SNOWFLAKE_KEYS = (
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_OAUTH_USER",
    "SNOWFLAKE_ROLE",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
)
ENTRA_KEYS = ("MSAL_SF_TENANT_ID", "MSAL_SF_CLIENT_ID", "MSAL_SF_APPLICATION_ID_URI")
PUBLIC_KEYS = SNOWFLAKE_KEYS[2:]
PRIVATE_KEYS = SNOWFLAKE_KEYS[:2] + ENTRA_KEYS
OPTION_KEYS = (
    "SNOWFLAKE_AUTHENTICATOR",
    "OAUTH_TOKEN_CACHE",
    "OAUTH_EXPIRY_MARGIN_SECONDS",
)


def load_config(path):
    """共通設定はYAML、個人・Entra設定は設定済みの環境変数から読み取る。"""
    if ENV_PATH.is_file():
        load_dotenv(ENV_PATH)
    if not path.is_file():
        raise FileNotFoundError(f"接続設定が見つかりません: {path}")
    with path.open(encoding="utf-8") as stream:
        public = yaml.safe_load(stream)
    if not isinstance(public, dict):
        raise ValueError("YAMLの接続設定はキーと値の形式にしてください。")
    private = {key: os.environ.get(key) for key in PRIVATE_KEYS}
    misplaced = [key for key in public if key not in PUBLIC_KEYS + OPTION_KEYS]
    if misplaced:
        raise ValueError(
            "YAMLの配置対象ではない項目があります: " + ", ".join(map(str, misplaced))
        )
    for label, settings, required_keys in (
        ("YAML", public, PUBLIC_KEYS),
        ("環境変数", private, PRIVATE_KEYS),
    ):
        missing = [
            key
            for key in required_keys
            if not isinstance(settings.get(key), str) or not settings[key].strip()
        ]
        if missing:
            raise ValueError(f"{label}に未設定の項目があります: " + ", ".join(missing))
    config = {**public, **private}
    required = SNOWFLAKE_KEYS + ENTRA_KEYS
    for key in required:
        config[key] = config[key].strip()
    for key in ("MSAL_SF_TENANT_ID", "MSAL_SF_CLIENT_ID"):
        try:
            config[key] = str(UUID(config[key]))
        except ValueError:
            raise ValueError(f"{key}にはEntra IDのGUIDを設定してください。") from None
    if config.get("SNOWFLAKE_AUTHENTICATOR") != "oauth":
        raise ValueError("SNOWFLAKE_AUTHENTICATORはoauthを設定してください。")
    uri = config["MSAL_SF_APPLICATION_ID_URI"].rstrip("/")
    if uri.endswith("/.default"):
        raise ValueError(
            "MSAL_SF_APPLICATION_ID_URIは末尾の/.defaultを除いて設定してください。"
        )
    config["MSAL_SF_APPLICATION_ID_URI"] = uri
    cache_location = config.get(
        "OAUTH_TOKEN_CACHE", "~/.snowflake/snowflake_oauth_token_cache.json"
    )
    if not isinstance(cache_location, str) or not cache_location.strip():
        raise ValueError(
            "OAUTH_TOKEN_CACHEにはトークンキャッシュの絶対パスを指定してください。"
        )
    cache_path = Path(cache_location).expanduser()
    if not cache_path.is_absolute() or cache_path.name in {"", ".", ".."}:
        raise ValueError(
            "OAUTH_TOKEN_CACHEには~/.snowflake/配下などの絶対パスを指定してください。"
        )
    config["cache_path"] = cache_path
    config["expiry_margin"] = int(config.get("OAUTH_EXPIRY_MARGIN_SECONDS", 300))
    if config["expiry_margin"] < 0:
        raise ValueError("OAUTH_EXPIRY_MARGIN_SECONDSは0以上にしてください。")
    return config


def cache_context(config):
    # 別のユーザー・接続先・Entraアプリのトークンを誤って再利用しない。
    return {key: config[key] for key in SNOWFLAKE_KEYS + ENTRA_KEYS}


def read_token_cache(config):
    path = config["cache_path"]
    if not path.exists():
        return None
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(cached, dict):
            raise ValueError("キャッシュ形式が不正")
        if cached.get("context") != cache_context(config):
            return None
        if (
            not isinstance(cached.get("access_token"), str)
            or not cached["access_token"]
        ):
            raise ValueError("access_tokenがありません")
        if not isinstance(cached.get("expires_at"), (int, float)):
            raise ValueError("expires_atが不正")
    except (ValueError, OSError):
        raise RuntimeError(
            "トークンキャッシュを読み込めません。該当ファイルを削除して認証セルを再実行してください。"
        ) from None
    return cached


def save_token_cache(config, result, previous_refresh_token=None):
    token = result.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("認証レスポンスにaccess_tokenがありません。")
    if str(result.get("token_type", "Bearer")).lower() != "bearer":
        raise RuntimeError("認証レスポンスのtoken_typeがBearerではありません。")
    expires_in = int(result.get("expires_in", 0))
    if expires_in <= 0:
        raise RuntimeError("認証レスポンスの有効期限が不正です。")
    cached = {
        "context": cache_context(config),
        "access_token": token,
        "refresh_token": result.get("refresh_token") or previous_refresh_token,
        "expires_at": time.time() + expires_in,
    }
    path = config["cache_path"]
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".oauth_", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(cached, stream, ensure_ascii=False)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return token


def entra_post(session, url, data):
    try:
        response = session.post(
            url, data=data, timeout=TIMEOUT_SECONDS, allow_redirects=False
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Entra IDとの通信に失敗しました（{type(exc).__name__}）。"
        ) from None
    try:
        result = response.json()
    except ValueError:
        raise RuntimeError(
            f"Entra IDがJSON以外を返しました（HTTP {response.status_code}）。"
        ) from None
    if not isinstance(result, dict):
        raise RuntimeError("Entra IDのレスポンス形式が不正です。")
    if not 200 <= response.status_code < 300 and "error" not in result:
        raise RuntimeError(
            f"Entra IDがエラーを返しました（HTTP {response.status_code}）。"
        )
    return result


def raise_oauth_error(result):
    # レスポンス全体・トークンを例外やInteractive出力へ埋め込まない。
    error = str(result.get("error", "unknown_error"))
    error = error if re.fullmatch(r"[A-Za-z0-9_]+", error) else "unknown_error"
    codes = re.findall(r"AADSTS\d+", str(result.get("error_description", "")))
    suffix = f" / {', '.join(sorted(set(codes)))}" if codes else ""
    raise RuntimeError(
        f"Entra OAuth認証に失敗しました: {error}{suffix}。"
        "アプリ設定・権限・条件付きアクセスと実行環境を確認してください。"
    )


def acquire_access_token(config, session):
    authority = (
        f"https://login.microsoftonline.com/{config['MSAL_SF_TENANT_ID']}/oauth2/v2.0"
    )
    token_url = authority + "/token"
    # offline_accessで、refresh tokenを取得する。
    scope = config["MSAL_SF_APPLICATION_ID_URI"] + "/.default offline_access"
    cached = read_token_cache(config)
    if cached and cached["expires_at"] > time.time() + config["expiry_margin"]:
        print("有効なOAuthトークンのキャッシュを使用します。")
        return cached["access_token"]
    if cached and cached.get("refresh_token"):
        result = entra_post(
            session,
            token_url,
            {
                "client_id": config["MSAL_SF_CLIENT_ID"],
                "grant_type": "refresh_token",
                "refresh_token": cached["refresh_token"],
                "scope": scope,
            },
        )
        if "access_token" in result:
            token = save_token_cache(config, result, cached["refresh_token"])
            print("OAuthトークンを更新しました。")
            return token
        if result.get("error") not in {
            "invalid_grant",
            "interaction_required",
            "login_required",
            "consent_required",
        }:
            raise_oauth_error(result)
        print("ブラウザーでの再認証が必要です。")
    flow = entra_post(
        session,
        authority + "/devicecode",
        {
            "client_id": config["MSAL_SF_CLIENT_ID"],
            "scope": scope,
        },
    )
    if "error" in flow:
        raise_oauth_error(flow)
    if not all(
        flow.get(key)
        for key in ("device_code", "user_code", "verification_uri", "expires_in")
    ):
        raise RuntimeError("デバイスコード認証の開始レスポンスが不正です。")
    interval = max(1.0, float(flow.get("interval", 5)))
    deadline = time.monotonic() + int(flow["expires_in"])
    print("次のURLをブラウザーで開き、コードを入力してください。", flush=True)
    print("URL:", flow["verification_uri"], flush=True)
    print("コード:", flow["user_code"], flush=True)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError(
                "デバイスコードの有効期限が切れました。認証セルを再実行してください。"
            )
        time.sleep(min(interval, remaining))
        if time.monotonic() >= deadline:
            continue
        result = entra_post(
            session,
            token_url,
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": config["MSAL_SF_CLIENT_ID"],
                "device_code": flow["device_code"],
            },
        )
        if "access_token" in result:
            token = save_token_cache(config, result)
            print(
                "OAuth認証が完了しました。トークンを設定されたキャッシュ先へ保存しました。"
            )
            return token
        error = result.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        raise_oauth_error(result)


def connect_snowflake():
    """設定とOAuthキャッシュを使い、呼び出し側で閉じる接続を作成する。"""
    config = load_config(CONFIG_PATH)
    with requests.Session() as auth_session:
        access_token = acquire_access_token(config, auth_session)
    try:
        return snowflake.connector.connect(
            account=config["SNOWFLAKE_ACCOUNT"],
            user=config["SNOWFLAKE_OAUTH_USER"],
            authenticator="oauth",
            token=access_token,
            role=config["SNOWFLAKE_ROLE"],
            warehouse=config["SNOWFLAKE_WAREHOUSE"],
            database=config["SNOWFLAKE_DATABASE"],
            schema=config["SNOWFLAKE_SCHEMA"],
            login_timeout=TIMEOUT_SECONDS,
            network_timeout=TIMEOUT_SECONDS,
            socket_timeout=TIMEOUT_SECONDS,
            session_parameters={
                "QUERY_TAG": "snowflake_connect",
                "STATEMENT_TIMEOUT_IN_SECONDS": TIMEOUT_SECONDS,
            },
        )
    except SnowflakeError as exc:
        raise RuntimeError(
            f"Snowflake接続失敗: errno={exc.errno}, sqlstate={exc.sqlstate}。"
            "OAuthの対象リソース、ユーザーとロールの利用権限を確認してください。"
        ) from None


def test_connection():
    """読み取りのみの接続確認を行い、成功・失敗によらず接続を閉じる。"""
    connection = connect_snowflake()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT CURRENT_USER() AS USER_NAME,
                       CURRENT_ROLE() AS ROLE_NAME,
                       CURRENT_SECONDARY_ROLES() AS SECONDARY_ROLES,
                       CURRENT_WAREHOUSE() AS WAREHOUSE_NAME,
                       CURRENT_DATABASE() AS DATABASE_NAME,
                       CURRENT_SCHEMA() AS SCHEMA_NAME,
                       CURRENT_VERSION() AS SNOWFLAKE_VERSION
            """)
            context = dict(
                zip([item[0] for item in cursor.description], cursor.fetchone())
            )
            cursor.execute("SELECT 1 AS CONNECTION_TEST")
            if cursor.fetchone()[0] != 1:
                raise RuntimeError("SELECT 1の接続確認に失敗しました。")
            return context
    finally:
        connection.close()


# %% OAuth接続テスト（読み取りのみ）
if __name__ == "__main__":
    connection_context = test_connection()
    print("Snowflake OAuth接続テスト成功")
    for key, value in connection_context.items():
        print(f"{key}: {value}")
    print("SELECT 1: 成功 / 接続: 終了")
