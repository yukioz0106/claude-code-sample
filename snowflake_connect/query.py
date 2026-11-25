# %% [markdown]
# # SnowflakeデータのDataFrame取得ヘルパー
# OAuth接続はsnowflake_oauth.pyに委譲する。

# %%
import pandas as pd

from snowflake_oauth import connect_snowflake


def run_query(sql: str, params=None) -> pd.DataFrame:
    """SQLを実行し、結果をpandas.DataFrameで返す。接続は毎回開閉する。"""
    connection = connect_snowflake()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [item[0] for item in cursor.description]
            rows = cursor.fetchall()
        return pd.DataFrame(rows, columns=columns)
    finally:
        connection.close()


# %% 動作確認（読み取りのみ）
if __name__ == "__main__":
    df = run_query("SELECT CURRENT_DATABASE() AS DATABASE_NAME, CURRENT_SCHEMA() AS SCHEMA_NAME")
    print(df)
