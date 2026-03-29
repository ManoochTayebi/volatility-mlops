# Data Ingestion APIs Comparison

This document compares the different financial market data APIs that were evaluated for this project.

## Alpha Vantage

* **Rate Limit:** 25 queries/day (free tier)
* **Geographic Coverage:** Access to international stocks using suffix notation (e.g., PA for Paris/France, DEX for Frankfurt/Germany). International stocks work only with daily data - more specifications require premium access.
* **Data Formats:** CSV or JSON
* **Query Parameters:**

| Key | Value |
|:---|:---|
| `function` | `TIME_SERIES_DAILY` or `TIME_SERIES_INTRADAY` |
| `symbol` | e.g., `AMZN` (US stock), `CS.PA`, `BMW.DEX` (FR, DE stocks - works only with `TIME_SERIES_INTRADAY`) |
| `outputsize` | `full` (all history data) or `compact` (last 100 days) |
| `datatype` | `csv` or `json` |
| `interval` | (works with `TIME_SERIES_INTRADAY` only) `60min`, `1min`, etc. |

* **Example Query:**
```
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=CS.PA&outputsize=full&apikey=API_KEY&datatype=csv
```

* **Documentation:** https://www.alphavantage.co/documentation/#intraday

* **Output Schema (daily or hourly data):**

| timestamp | open | high | low | close | volume |
|:---|:---|:---|:---|:---|:---|

## Financial Modeling Prep

* **Rate Limit:** 250 queries/day, 20 GB bandwidth/month
* **Geographic Coverage:** Limited to US stocks only (international stock exchange visibility requires premium access)
* **Data Formats:** JSON response only
* **Query Parameters:**

| Key | Value |
|:---|:---|
| `symbol` (required) | e.g., `IBM` |
| `from` (optional) | Date in format `YYYY-DD-MM` |
| `to` (optional) | Date in format `YYYY-DD-MM` |

* **Practical Usage:** Querying daily data using the interval keys `from` and `to`

* **Example Query:**
```
https://financialmodelingprep.com/stable/historical-chart/1min?symbol=AAPL&apikey=API_KEY
```

* **Documentation:** https://site.financialmodelingprep.com/developer/docs/stable/historical-price-eod-full

* **Output Schema (historical data):**

| symbol | date | open | high | low | close | volume | change | changePercent | vwap |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|

## Fin Hub

* **Rate Limit:** 60 requests/minute (generous free rate limit)
* **Data Access:** Only real-time data available on free tier - historical data requires paid access
* **Data Formats:** JSON response only
* **Practical Usage:** Suitable for heavy updates or multiple changes in a small time window

* **Query Parameters:**

| Key | Value |
|:---|:---|
| `symbol` (required) | e.g., `IBM` |

* **Example Query:**
```
https://finnhub.io/api/v1/quote?symbol=MSFT&token=TOKEN
```

* **Output Schema (daily data):**

| c | h | l | o | pc | t |
|:---|:---|:---|:---|:---|:---|

## Twelve Data (Currently Used)

* **Rate Limit:** 800 API calls/day (highest free tier)
* **Geographic Coverage:** Wide international coverage
* **Data Formats:** JSON response
* **Features:** Rich query parameters for time series data
* **Historical Data:** Full historical data support with flexible date ranges

* **Example Query:**
```
https://api.twelvedata.com/time_series?symbol=AAPL&apikey=API_KEY&start_date=1981-06-06&end_date=2025-01-10&interval=1day
```

* **Documentation:** https://twelvedata.com/docs#time-series

* **Output Schema (historical data):**

**Metadata (one line):**

| symbol | interval | currency | exchange_timezone | exchange | mic_code | type |
|:---|:---|:---|:---|:---|:---|:---|

**Values:**

| datetime | open | high | low | close | volume |
|:---|:---|:---|:---|:---|:---|

## Why TwelveData Was Chosen

TwelveData was selected as the primary data source for this project due to:

1. **Highest Free Tier Rate Limit:** 800 API calls/day vs. 250 (Financial Modeling Prep) or 25 (Alpha Vantage)
2. **Full Historical Data:** Complete historical data access without premium requirements
3. **Flexible Query Parameters:** Rich time series data configuration options
4. **International Coverage:** Wide geographic coverage without restrictions
5. **Date Range Flexibility:** Easy specification of start and end dates for historical queries

This repository currently uses Twelve Data through `src/twelve_data_client.py`, which is wired into the Supabase ingestion scripts under `scripts/`.
