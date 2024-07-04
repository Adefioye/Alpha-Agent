import os
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from utils import decorate_all_methods, get_next_weekday

from functools import wraps
from typing import Annotated
from langchain_core.tools import tool


def init_fmp_api(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        global fmp_api_key
        if os.environ.get("FMP_API_KEY") is None:
            print("Please set the environment variable FMP_API_KEY to use the FMP API.")
            return None
        else:
            fmp_api_key = os.environ["FMP_API_KEY"]
            print("FMP api key found successfully.")
            return func(*args, **kwargs)

    return wrapper


@decorate_all_methods(init_fmp_api)
class FMPUtils:

    @tool
    def get_target_price(
        ticker_symbol: Annotated[str, "ticker symbol"],
        date: Annotated[str, "date of the target price, should be 'yyyy-mm-dd'"],
    ) -> str:
        """Get the target price for a given stock on a given date"""
        # API URL
        url = f"https://financialmodelingprep.com/api/v4/price-target?symbol={ticker_symbol}&apikey={fmp_api_key}"

        price_target = "Not Given"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            est = []

            date = datetime.strptime(date, "%Y-%m-%d")
            for tprice in data:
                tdate = tprice["publishedDate"].split("T")[0]
                tdate = datetime.strptime(tdate, "%Y-%m-%d")
                if abs((tdate - date).days) <= 1:
                    est.append(tprice["priceTarget"])

            if est:
                price_target = f"{np.min(est)} - {np.max(est)} (md. {np.median(est)})"
            else:
                price_target = "N/A"
        else:
            return f"Failed to retrieve data: {response.status_code}"

        return price_target

    @tool
    def get_sec_report(
        ticker_symbol: Annotated[str, "ticker symbol"],
        fyear: Annotated[
            str,
            "year of the 10-K report, should be 'yyyy' or 'latest'. Default to 'latest'",
        ] = "latest",
    ) -> str:
        """Get the url and filing date of the 10-K report for a given stock and year"""

        url = f"https://financialmodelingprep.com/api/v3/sec_filings/{ticker_symbol}?type=10-k&page=0&apikey={fmp_api_key}"

        filing_url = None
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            # print(data)
            if fyear == "latest":
                filing_url = data[0]["finalLink"]
                filing_date = data[0]["fillingDate"]
            else:
                for filing in data:
                    if filing["fillingDate"].split("-")[0] == fyear:
                        filing_url = filing["finalLink"]
                        filing_date = filing["fillingDate"]
                        break

            return f"Link: {filing_url}\nFiling Date: {filing_date}"
        else:
            return f"Failed to retrieve data: {response.status_code}"

    @tool
    def get_historical_market_cap(
        ticker_symbol: Annotated[str, "ticker symbol"],
        date: Annotated[str, "date of the market cap, should be 'yyyy-mm-dd'"],
    ) -> str:
        """Get the historical market capitalization for a given stock on a given date"""
        date = get_next_weekday(date).strftime("%Y-%m-%d")
        url = f"https://financialmodelingprep.com/api/v3/historical-market-capitalization/{ticker_symbol}?limit=100&from={date}&to={date}&apikey={fmp_api_key}"

        mkt_cap = None
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            mkt_cap = data[0]["marketCap"]
            return mkt_cap
        else:
            return f"Failed to retrieve data: {response.status_code}"

    @tool
    def get_historical_bvps(
        ticker_symbol: Annotated[str, "ticker symbol"],
        target_date: Annotated[str, "date of the BVPS, should be 'yyyy-mm-dd'"],
    ) -> str:
        """Get the historical book value per share for a given stock on a given date"""
        url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker_symbol}?limit=40&apikey={fmp_api_key}"
        response = requests.get(url)
        data = response.json()

        if not data:
            return "No data available"

        closest_data = None
        min_date_diff = float("inf")
        target_date = datetime.strptime(target_date, "%Y-%m-%d")
        for entry in data:
            date_of_data = datetime.strptime(entry["date"], "%Y-%m-%d")
            date_diff = abs(target_date - date_of_data).days
            if date_diff < min_date_diff:
                min_date_diff = date_diff
                closest_data = entry

        if closest_data:
            return closest_data.get("bookValuePerShare", "No BVPS data available")
        else:
            return "No close date data found"

    @tool
    def get_financial_metrics(
        ticker_symbol: Annotated[str, "ticker symbol"],
        years: Annotated[int, "number of the years to search from, default to 4"] = 4,
    ) -> pd.DataFrame:
        """Get the financial metrics for a given stock for the last 'years' years"""
        # Base URL setup for FMP API
        base_url = "https://financialmodelingprep.com/api/v3"
        # Create DataFrame
        df = pd.DataFrame()

        # Iterate over the last 'years' years of data
        for year_offset in range(years):
            # Construct URL for income statement and ratios for each year
            income_statement_url = f"{base_url}/income-statement/{ticker_symbol}?limit={years}&apikey={fmp_api_key}"
            ratios_url = (
                f"{base_url}/ratios/{ticker_symbol}?limit={years}&apikey={fmp_api_key}"
            )
            key_metrics_url = f"{base_url}/key-metrics/{ticker_symbol}?limit={years}&apikey={fmp_api_key}"

            # Requesting data from the API
            income_data = requests.get(income_statement_url).json()
            key_metrics_data = requests.get(key_metrics_url).json()
            ratios_data = requests.get(ratios_url).json()

            # Extracting needed metrics for each year
            if income_data and key_metrics_data and ratios_data:
                metrics = {
                    "Operating Revenue": income_data[year_offset]["revenue"] / 1e6,
                    "Adjusted Net Profit": income_data[year_offset]["netIncome"] / 1e6,
                    "Adjusted EPS": income_data[year_offset]["eps"],
                    "EBIT Margin": ratios_data[year_offset]["ebitPerRevenue"],
                    "ROE": key_metrics_data[year_offset]["roe"],
                    "PE Ratio": ratios_data[year_offset]["priceEarningsRatio"],
                    "EV/EBITDA": key_metrics_data[year_offset][
                        "enterpriseValueOverEBITDA"
                    ],
                    "PB Ratio": key_metrics_data[year_offset]["pbRatio"],
                }
                # Append the year and metrics to the DataFrame
                # Extracting the year from the date
                year = income_data[year_offset]["date"][:4]
                df[year] = pd.Series(metrics)

        df = df.sort_index(axis=1)
        df = df.round(2)

        return df