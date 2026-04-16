# scripts/ingest_data.py

import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text, inspect
import logging
import requests
from io import StringIO
from datetime import date
from dateutil.relativedelta import relativedelta
from time import sleep

# --- Configuration ---
# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection details (from our docker-compose.yml)
DB_HOST = 'localhost'
DB_PORT = '5433'
DB_NAME = 'market_data'
DB_USER = 'investor'
DB_PASS = 'password123'

# Create the database connection string
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create a database engine
try:
    engine = create_engine(DATABASE_URL)
    logging.info("Successfully connected to the PostgreSQL database.")
except Exception as e:
    logging.error(f"Failed to connect to the database: {e}")
    exit()

# List of assets to track
NSE_STOCKS = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS', '^NSEI'] # ^NSEI is Nifty 50
CRYPTO_SYMBOLS = ['BTC-INR', 'ETH-INR', 'DOGE-INR']

# Mutual Fund Scheme Codes (Example: Axis Bluechip Fund, Parag Parikh Flexi Cap)
MF_SCHEMES = {
    '120717': 'UTI Nifty 50 Index Fund - Direct Plan - IDCW',
    '118826': 'Mirae Asset Large Cap Fund Direct IDCW',
    '122639': 'Parag Parikh Flexi Cap Fund - Direct Plan - Growth',
    '120505': 'Axis Midcap Fund - Direct Plan - Growth'
}

MF_CODES = {
    '120505': '53',
    '118826': '45',
    '122639': '64',
    '120717': '28'
}

SCHEME_CODES_STR = list(MF_SCHEMES.keys())

FILE_HEADERS = {
    'main': 'Scheme Code;Scheme Name;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;Net Asset Value;Repurchase Price;Sale Price;Date',
    'alt': 'Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date'
}

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}


def get_last_ingest_date(table_name, engine):
    """
    Finds the most recent date for data in a given table.
    Returns None if the table is empty or doesn't exist.
    """
    try:
        # Use inspector at engine level to check table existence
        inspector = inspect(engine)
        if not inspector.has_table(table_name):
            logging.info(f"Table '{table_name}' does not exist. A full load will be performed.")
            return None

        # Use sqlalchemy.text() for textual SQL in SQLAlchemy 2.x
        with engine.connect() as connection:
            query = text(f"SELECT MAX(date) AS max_date FROM {table_name};")
            result = connection.execute(query).scalar()
            if result:
                logging.info(f"Last ingest date for '{table_name}' is {result}.")
                return result
            else:
                logging.info(f"Table '{table_name}' is empty. A full load will be performed.")
                return None
    except Exception as e:
        logging.error(f"Error checking last ingest date for '{table_name}': {e}")
        # In case of error, better to do a full load than to miss data
        return None


def process_dates(table_name, engine):
    """
    Determines the date range for fetching new data based on the last ingest date.
    Returns a tuple of (last_date, start_date, end_date) or None if no new data is needed.
    """

    # 1. Get the last date from the database
    last_date = get_last_ingest_date(table_name, engine)
    logging.info(f"Last ingest date for {table_name}: {last_date}")

    # Normalize last_date to a datetime.date (if not None)
    if last_date is not None:
        try:
            # handle pandas.Timestamp or strings
            last_date = pd.to_datetime(last_date).date()
        except Exception:
            pass

    # 2. Determine the start date for the API call
    if last_date is None:
        # If no data, fetch last 5 years
        start_date = date.today() - relativedelta(years=5)
    else:
        # Fetch data from the day after the last recorded date
        start_date = last_date + relativedelta(days=1)

    end_date = date.today()

    return last_date, start_date, end_date


def ingest_stock_data():
    """
    Fetches historical data for NSE stocks incrementally and loads it into the database.
    """

    logging.info(f"--------- Starting Data Ingestion Pipeline for Stocks ---------")

    table_name = 'stocks'
    logging.info(f"Starting stock data ingestion for: {', '.join(NSE_STOCKS)}")

    last_date, start_date, end_date = process_dates(table_name, engine)

    if start_date >= end_date:
        logging.info(f"Stock data is already up to date. No new data to fetch. Skipping Stock Ingestion.")
        return None

    try:
        # 3. Fetch new data
        logging.info(f"Fetching stock data from {start_date} to {end_date}")
        stock_data = yf.download(NSE_STOCKS, start=start_date, end=end_date, interval="1d", auto_adjust=False, progress=False)

        if not stock_data.empty:
            # (Data processing is the same as before)
            df = stock_data.stack(future_stack=True).reset_index()
            df = df.rename(columns={'Date': 'date', 'Ticker': 'ticker', 'Open': 'open', 'High': 'high', 
                                    'Low': 'low', 'Close': 'close', 'Adj Close': 'adj_close', 'Volume': 'volume'})
            df['date'] = pd.to_datetime(df['date']).dt.date
            df = df[['date', 'ticker', 'open', 'high', 'low', 'close', 'adj_close', 'volume']]
            logging.info(f"Successfully fetched {len(df)} new rows from {min(df.date)} to {max(df.date)} for stock data.")

            # 4. Append new data to the table
            df.to_sql(table_name, engine, if_exists='append', index=False)
            logging.info(f"Successfully appended {len(df)} new rows of stock data.")
        else:
            logging.warning(f"No new stock data downloaded for the period {start_date} to {end_date}.")

    except Exception as e:
        logging.error(f"An error occurred during stock data ingestion: {e}")

    logging.info(f"--------- Finished Data Ingestion Pipeline for Stocks ---------")


def ingest_crypto_data():
    """
    Fetches historical data for cryptocurrencies incrementally and loads it into the database.
    """

    logging.info(f"--------- Starting Data Ingestion Pipeline for Cryptocurrencies ---------")

    table_name = 'cryptocurrencies'
    logging.info(f"Starting crypto data ingestion for: {', '.join(CRYPTO_SYMBOLS)}")

    last_date, start_date, end_date = process_dates(table_name, engine)

    if start_date >= end_date:
        logging.info(f"Crypto data is already up to date. No new data to fetch. Skipping Crypto Ingestion.")
        return None

    try:
        logging.info(f"Fetching crypto data from {start_date} to {end_date}")
        crypto_data = yf.download(CRYPTO_SYMBOLS, start=start_date, end=end_date, interval="1d", auto_adjust=False, progress=False)

        if not crypto_data.empty:
            df = crypto_data.stack(future_stack=True).reset_index()
            df = df.rename(columns={'Date': 'date', 'Ticker': 'symbol', 'Open': 'open', 'High': 'high', 
                                    'Low': 'low', 'Close': 'close', 'Adj Close': 'adj_close', 'Volume': 'volume'})
            df['date'] = pd.to_datetime(df['date']).dt.date
            df = df[['date', 'symbol', 'open', 'high', 'low', 'close', 'adj_close', 'volume']]
            logging.info(f"Successfully fetched {len(df)} new rows from {min(df.date)} to {max(df.date)} for crypto data.")

            df.to_sql(table_name, engine, if_exists='append', index=False)
            logging.info(f"Successfully appended {len(df)} new rows of crypto data.")
        else:
            logging.warning(f"No new crypto data downloaded for the period {start_date} to {end_date}.")

    except Exception as e:
        logging.error(f"An error occurred during crypto data ingestion: {e}")

    logging.info(f"--------- Finished Data Ingestion Pipeline for Cryptocurrencies ---------")


def ingest_mutual_fund_data():
    """
    Incrementally updates AMFI NAV data for specified schemes.
    """

    logging.info("--------- Starting Data Ingestion Pipeline for Mutual Funds ---------")

    table_name = 'mutual_funds'
    logging.info("Starting HISTORICAL mutual fund NAV data ingestion (incremental).")

    last_date, start_date, end_date = process_dates(table_name, engine)

    if start_date >= end_date:
        logging.info(f"Mutual Fund data is already up to date. No new data to fetch. Skipping Mutual Fund Ingestion.")
        return None

    start_date_str = start_date.strftime('%d-%b-%Y')
    end_date_str = end_date.strftime('%d-%b-%Y')
    logging.info(f"Fetching MF data from {start_date_str} to {end_date_str}.")

    url = f"https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt={start_date_str}&todt={end_date_str}"

    try:
        # (API call and initial parsing is the same)
        raw_df = pd.DataFrame()
        for MF_CODE in MF_CODES.values():
            temp_url = f"{url}&mf={MF_CODE}"
            logging.info(f"Fetching data for MF code {MF_CODE} from URL: {temp_url}")
            response = requests.get(temp_url, headers=HEADERS)
            response.raise_for_status()
            if FILE_HEADERS['main'] in response.text:
                logging.info(f"Header found for MF code {MF_CODE}")
                data = StringIO(response.text)
                temp_raw_df = pd.read_csv(data, sep=';', on_bad_lines='skip').dropna(how='all')
                raw_df = pd.concat([raw_df, temp_raw_df], ignore_index=True)
                logging.info(f"Found {len(temp_raw_df)} new rows for MF code {MF_CODE}")
                sleep(1)
            else:
                raise ValueError(f"Unexpected file format for MF code {MF_CODE}. Header not found.")

        df_filtered = raw_df[raw_df['Scheme Code'].astype(str).isin(SCHEME_CODES_STR)].copy()

        if not df_filtered.empty:
            df_filtered['Net Asset Value'] = pd.to_numeric(df_filtered['Net Asset Value'], errors='coerce')
            df_filtered['Date'] = pd.to_datetime(df_filtered['Date'], format='%d-%b-%Y', errors='coerce').dt.date
            df_filtered = df_filtered.dropna(subset=['Net Asset Value', 'Date'])

            # Keep only rows after last_date (incremental)
            if last_date is not None:
                # both sides are python.date now
                mask = df_filtered['Date'] > last_date
                df_new = df_filtered.loc[mask, ['Scheme Code', 'Date', 'Net Asset Value']].copy()
            else:
                df_new = df_filtered[['Scheme Code', 'Date', 'Net Asset Value']].copy()

            if df_new.empty:
                logging.info("No new mutual fund rows found after last date.")
                return

            df_final_new = df_new.rename(columns={'Scheme Code': 'scheme_code', 'Date': 'date', 'Net Asset Value': 'price'})
            df_final_new['scheme_name'] = df_final_new['scheme_code'].astype(str).map(MF_SCHEMES)
            logging.info(f"Successfully fetched {len(df_final_new)} new rows from {min(df_final_new.date)} to {max(df_final_new.date)} for mutual funds data.")

            # # THIS IS THE OLD LOGIC
            # # Read the existing data from the database
            # df_existing = pd.DataFrame()
            # if last_date is not None:
            #     df_existing = pd.read_sql_table(table_name, engine)

            # # Combine the old and new data
            # df_combined = pd.concat([df_existing, df_final_new], ignore_index=True)
            # # Remove any potential duplicates and keep the latest entry
            # df_combined.drop_duplicates(subset=['scheme_code', 'date'], keep='last', inplace=True)

            # # Replace the entire table with the updated, combined data
            # df_combined.to_sql(table_name, engine, if_exists='replace', index=False)
            # logging.info(f"Successfully updated mutual fund data. Added {len(df_final_new)} new rows.")

            df_final_new.to_sql(table_name, engine, if_exists='append', index=False)
            logging.info(f"Successfully appended {len(df_final_new)} new rows of mutual fund data.")
        else:
            logging.warning(f"No new mutual fund data found for the period.")

    except Exception as e:
        logging.error(f"An error occurred during historical mutual fund data ingestion: {e}")

    logging.info("--------- Finished Data Ingestion Pipeline for Mutual Funds ---------")


if __name__ == "__main__":
    logging.info("--------- Starting Data Ingestion Pipeline ---------")

    ingest_stock_data()
    ingest_crypto_data()
    ingest_mutual_fund_data()

    logging.info("--------- Data Ingestion Pipeline Finished ---------")