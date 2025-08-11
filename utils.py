import os
import requests
import pandas as pd
import yfinance as yf
from nsetools import Nse
from bs4 import BeautifulSoup

nse = Nse()

TARGET_TICKERS = {
    'nifty': os.getenv('TICKERS_NIFTY', '^NSEI'),
    'banknifty': os.getenv('TICKERS_BANKNIFTY', '^NSEBANK'),
    'sensex': os.getenv('TICKERS_SENSEX', '^BSESN'),
    'sgx': os.getenv('TICKERS_SGX', '^N225'),
}


def fmt_pct(x):
    try:
        return f"{float(x):+.2f}%"
    except Exception:
        return str(x)


# 1) Opening clues
def get_opening_clues():
    parts = []
    parts.append("\U0001F4C8 Opening Clues\n")

    # Global indices — user can edit tickers in .env
    for name, ticker in TARGET_TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            data = t.history(period='1d')
            if not data.empty:
                last = data['Close'].iloc[-1]
                prev_close = data['Close'].iloc[-1] if len(data) == 1 else data['Close'].iloc[-1]
                parts.append(f"{name.upper()}: {last:.2f}")
        except Exception:
            continue

    # USDINR via yfinance (ticker: INR=X)
    try:
        usdinr = yf.Ticker('INR=X').history(period='1d')
        if not usdinr.empty:
            val = usdinr['Close'].iloc[-1]
            parts.append(f"USD/INR: {val:.4f}")
    except Exception:
        pass

    # Commodities: crude and gold
    for com_ticker, label in [('CL=F','Crude (WTI)'), ('GC=F','Gold')]:
        try:
            r = yf.Ticker(com_ticker).history(period='1d')
            if not r.empty:
                parts.append(f"{label}: {r['Close'].iloc[-1]:.2f}")
        except Exception:
            pass

    return "\n".join(parts)


# 2) FII/DII
def get_fii_dii():
    # NSE publishes a report page. We'll attempt to pull from NSE report page.
    try:
        url = 'https://www.nseindia.com/reports/fii-dii'
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        # The page includes tables/reports; scraping exact layout can change.
        # We'll return a short message and encourage to customize if needed.
        return "\U0001F4B0 FII / DII\nGet full FII/DII data from NSE reports (scraping may need custom parsing)."
    except Exception:
        return "\U0001F4B0 FII / DII\nData not available (fetch error)."


# 3) Top gainers / losers (using nsetools or fallback)
def get_top_gainers_losers(limit=5):
    try:
        gainers = nse.get_top_gainers()
        losers = nse.get_top_losers()
        def short_list(lst):
            lines = []
            for i, x in enumerate(lst[:limit]):
                lines.append(f"{i+1}. {x['symbol']} — {x.get('ltP', '')} ({x.get('pChange','')}%)")
            return '\n'.join(lines)
        return short_list(gainers), short_list(losers)
    except Exception:
        # fallback: use NSE web page (non-robust)
        return ("No gainers (nsetools failed)", "No losers (nsetools failed)")


# 4) Sector performance — best-effort via NSE index list
def get_sector_performance(limit=6):
    try:
        idxs = nse.get_index_list()
        # pick some sector indices
        sectors = ['NIFTY AUTO', 'NIFTY BANK', 'NIFTY IT', 'NIFTY PHARMA', 'NIFTY FMCG', 'NIFTY REALTY']
        lines = []
        for s in sectors[:limit]:
            try:
                q = nse.get_index_quote(s)
                if q:
                    lines.append(f"{s}: {q.get('lastPrice','')}, pChange={q.get('pChange','')}")
            except Exception:
                continue
        return '\n'.join(lines)
    except Exception:
        return ''


# 5) Closing summary — basic using yfinance
def get_closing_summary():
    out = []
    for k in ('nifty','banknifty','sensex'):
        t = TARGET_TICKERS.get(k)
        try:
            data = yf.Ticker(t).history(period='2d')
            if not data.empty and len(data)>=2:
                last = data['Close'].iloc[-1]
                prev = data['Close'].iloc[-2]
                ch = (last - prev)/prev*100
                out.append(f"{k.upper()}: {last:.2f} ({ch:+.2f}%)")
        except Exception:
            continue
    return "\U0001F4C9 Market Close\n" + "\n".join(out)