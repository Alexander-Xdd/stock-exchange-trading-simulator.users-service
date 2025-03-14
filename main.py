from fastapi import FastAPI, HTTPException
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from config import SERVER_PORT, SERVER_HOST, SERVER_LOG_LEVEL
from pg_adapter import PostgresAdapter


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Укажите домен вашего фронтенда
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
)

@app.post("/open_account")
def open_account(username: str, name:str, balance_units: int, balance_nano: int):

    try:
        query = f"""
            INSERT INTO accounts (user_id, name, balance_units, balance_nano)
            VALUES ((SELECT id FROM users WHERE username = %s), %s, %s, %s);
        """
        params = (username, name, balance_units, balance_nano)

        psql = PostgresAdapter()
        psql.connect()
        psql.execute(query, params)
        psql.disconnect()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/close_account")
def close_account(username: str, account_id: int):
    try:
        query = f"""
            DELETE FROM accounts WHERE user_id = (SELECT id FROM users WHERE username = %s) AND id = %s;
        """
        params = (username, account_id)

        psql = PostgresAdapter()
        psql.connect()
        psql.execute(query, params)
        psql.disconnect()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/add_on_balance") #figi, имя пользователя, id счета, количество
def add_on_balance(figi: str, username: str, account_id: int, quantity: int):

    try:
        psql = PostgresAdapter()
        psql.connect()

        query = f"""
            SELECT id, instrument_name_id FROM instruments WHERE figi = %s;
        """
        params = (figi,)

        data = psql.fetch_data(query, params)
        instrument_obj = {
            "id": data[0][0],
            "instrument_name_id": data[0][1],
            "figi": figi
        }

        if instrument_obj["instrument_name_id"] == 1:
            query = f"""
                SELECT price_units, price_nano FROM share_details WHERE instrument_id = %s;
            """
        if instrument_obj["instrument_name_id"] == 2:
            query = f"""
                SELECT price_units, price_nano FROM currency_details WHERE instrument_id = %s;
            """
        if instrument_obj["instrument_name_id"] == 3:
            query = f"""
                SELECT price_units, price_nano FROM etf_details WHERE instrument_id = %s;
            """
        params = (instrument_obj["id"],)

        data = psql.fetch_data(query, params)
        instrument_obj = instrument_obj | {
            "price_units": data[0][0],
            "price_nano": str(data[0][1])[0:2]
        }


        query = f"""
            SELECT balance_units, balance_nano FROM accounts WHERE user_id = (SELECT id FROM users WHERE username = %s) AND id = %s;
        """
        params = (username, account_id)

        data = psql.fetch_data(query, params)
        account_obj = {
            "id": account_id,
            "balance_units": data[0][0],
            "balance_nano": str(data[0][1])[0:2]
        }
        print(account_obj, instrument_obj)

        nano = int(instrument_obj["price_nano"]) * quantity
        na_unit = str(nano)[:-2]
        if na_unit == "":
            na_unit = "0"
        na_nano = str(nano)[-2:]
        tepm_balance_nano = int(account_obj["balance_nano"]) - int(na_nano)
        if tepm_balance_nano < 0:
            new_balance_nano = 100 + tepm_balance_nano
            sum_price_units = (instrument_obj["price_units"] * quantity) + int(na_unit)
            new_balance_units = account_obj["balance_units"] - sum_price_units - 1
        else:
            new_balance_nano = tepm_balance_nano
            sum_price_units = (instrument_obj["price_units"] * quantity) + int(na_unit)
            new_balance_units = account_obj["balance_units"] - sum_price_units

        if new_balance_units < 0 or (new_balance_units == 0 and new_balance_nano < 0):
            raise HTTPException(status_code=400, detail="Insufficient funds in the account")

        print(new_balance_units, new_balance_nano)
        query = f"""
            BEGIN;
            INSERT INTO accounts_details (account_id, instrument_id, purchase_price_units, purchase_price_nano, quantity, sum_price_units, sum_price_nano)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            UPDATE accounts SET balance_units = %s, balance_nano = %s WHERE id = %s;
            COMMIT;
        """
        params = (account_obj["id"], instrument_obj["id"], instrument_obj["price_units"],
                  instrument_obj["price_nano"], quantity, sum_price_units, int(na_nano),
                  new_balance_units, new_balance_nano, account_obj["id"])
        psql.execute(query, params)
        psql.disconnect()

        raise HTTPException(status_code=200, detail="OK")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_accounts")
def get_accounts(username: str):
    try:
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level=SERVER_LOG_LEVEL)
