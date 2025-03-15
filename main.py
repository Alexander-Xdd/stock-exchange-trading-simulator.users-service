from fastapi import FastAPI, HTTPException
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from decimal import Decimal

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
def open_account(username: str, name:str, balance: str):

    try:
        query = f"""
            INSERT INTO accounts (user_id, name, balance, init_balance)
            VALUES ((SELECT id FROM users WHERE username = %s), %s, %s, %s);
        """
        params = (username, name, Decimal(balance), Decimal(balance))

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
                SELECT price_units, price_nano FROM share_details WHERE instrument_id = %s ORDER BY data DESC;
            """
        if instrument_obj["instrument_name_id"] == 2:
            query = f"""
                SELECT price_units, price_nano FROM currency_details WHERE instrument_id = %s ORDER BY data DESC;
            """
        if instrument_obj["instrument_name_id"] == 3:
            query = f"""
                SELECT price_units, price_nano FROM etf_details WHERE instrument_id = %s ORDER BY data DESC;
            """
        params = (instrument_obj["id"],)

        data = psql.fetch_data(query, params)
        instrument_obj = instrument_obj | {
            "price_units": data[0][0],
            "price_nano": str(data[0][1])[0:2]
        }


        query = f"""
            SELECT balance FROM accounts WHERE user_id = (SELECT id FROM users WHERE username = %s) AND id = %s;
        """
        params = (username, account_id)

        data = psql.fetch_data(query, params)
        account_obj = {
            "id": account_id,
            "balance": data[0][0],
        }
        print(account_obj, instrument_obj)

        purchase_instrument_price = Decimal(instrument_obj["price_units"]) + Decimal('0.' + instrument_obj["price_nano"])
        instrument_price = (Decimal(instrument_obj["price_units"]) + Decimal('0.' + instrument_obj["price_nano"])) * quantity
        new_balance = account_obj["balance"] - instrument_price

        if new_balance < 0:
            raise HTTPException(status_code=400, detail="Insufficient funds in the account")

        print(purchase_instrument_price ,instrument_price, new_balance)
        query = f"""
            BEGIN;
            INSERT INTO accounts_details (account_id, instrument_id, purchase_price, quantity, sum_price)
            VALUES (%s, %s, %s, %s, %s);
            UPDATE accounts SET balance = %s WHERE id = %s;
            COMMIT;
        """
        params = (account_obj["id"], instrument_obj["id"], purchase_instrument_price,
                  quantity, instrument_price,
                  new_balance, account_obj["id"])
        psql.execute(query, params)
        psql.disconnect()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_accounts")
def get_accounts(username: str):
    try:
        psql = PostgresAdapter()
        psql.connect()

        query = f"""
            SELECT id FROM accounts WHERE user_id = (SELECT id FROM users WHERE username = %s);
        """
        params = (username,)
        data = psql.fetch_data(query, params)
        if data == []:
            return data

        accounts_mas = []
        for account_id in data:
            query = f"""
                SELECT name, init_balance, balance FROM accounts WHERE id = %s;
            """
            params = (account_id[0],)
            account_data = psql.fetch_data(query, params)

            query = f"""
                SELECT id FROM accounts_details WHERE account_id = %s;
            """
            params = (account_id[0],)
            account_details_data = psql.fetch_data(query, params)

            pl_sum = 0
            current_sum_price_full = 0
            account_details = []
            for intsr in account_details_data:
                query = """
                    SELECT id, instrument_id, purchase_price, quantity, sum_price, data
                    FROM accounts_details WHERE id = %s;
                """
                params = (intsr[0],)
                d = psql.fetch_data(query, params)
                if d == []:
                    continue

                query = """
                    SELECT figi, instrument_name_id, name FROM instruments WHERE id = %s;
                """
                params = (d[0][1],)
                i = psql.fetch_data(query, params)

                if i[0][1] == 1:
                    query = f"""
                        SELECT price_units, price_nano FROM share_details WHERE instrument_id = %s ORDER BY data DESC;
                    """
                if i[0][1] == 2:
                    query = f"""
                        SELECT price_units, price_nano FROM currency_details WHERE instrument_id = %s ORDER BY data DESC;
                    """
                if i[0][1] == 3:
                    query = f"""
                        SELECT price_units, price_nano FROM etf_details WHERE instrument_id = %s ORDER BY data DESC;
                    """
                params = (d[0][1],)
                price = psql.fetch_data(query, params)

                current_price_units = price[0][0]
                current_price_nano = str(price[0][1])[0:2]
                current_price = Decimal(current_price_units) + Decimal('0.' + current_price_nano)

                pl = current_price * d[0][3] - d[0][4]
                current_sum_price = current_price * d[0][3]
                pl_perc = round(100 * pl / d[0][4], 2)
                if pl_perc < 0:
                    pl_perc = -pl_perc

                pl_sum += pl
                current_sum_price_full += current_sum_price

                if pl < 0:
                    sing = "-"
                    pl_str = str(-pl)
                elif pl > 0:
                    sing = "+"
                    pl_str = str(pl)
                else:
                    sing = ""
                    pl_str = str(pl)

                account_details.append({
                    "id": d[0][0],
                    "instrument_id": d[0][1],
                    "purchase_price": d[0][2],
                    "quantity": d[0][3],
                    "sum_price": d[0][4],
                    "data": d[0][5],
                    "figi": i[0][0],
                    "name": i[0][2],
                    "current_price": current_price,
                    "current_sum_price": current_sum_price,
                    "pl": pl,
                    "sing": sing,
                    "pl_str": pl_str,
                    "pl_perc": pl_perc,
                })

            if pl_sum < 0:
                sing_sum = "-"
                pl_sum_str = str(-pl_sum)
            elif pl_sum > 0:
                sing_sum = "+"
                pl_sum_str = str(pl_sum)
            else:
                sing_sum = ""
                pl_sum_str = str(pl_sum)

            if account_data[0][1] != account_data[0][2]:
                pl_perc_sum = round(100 * pl_sum / (account_data[0][1] - account_data[0][2]), 2)
            else:
                pl_perc_sum = 0

            if pl_perc_sum < 0:
                pl_perc_sum = -pl_perc_sum

            accounts_mas.append({
                "id": account_id[0],
                "name": account_data[0][0],
                "init_balance": account_data[0][1],
                "balance": account_data[0][2],
                "pl_sum": pl_sum,
                "sing_sum": sing_sum,
                "pl_sum_str": pl_sum_str,
                "current_sum_price_full": current_sum_price_full,
                "pl_perc_sum": pl_perc_sum,
                "details": account_details,
            })

        psql.disconnect()
        return accounts_mas
    except Exception as e:
        print (e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level=SERVER_LOG_LEVEL)
