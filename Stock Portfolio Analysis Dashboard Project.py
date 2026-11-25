"""
Vietnam Stock Portfolio Analysis Dashboard (Streamlit)

Run:
    pip install streamlit vnstock plotly matplotlib pandas numpy scipy
    streamlit run app.py

Required files in ./data/ :
    - Listing_companies_vnstock.csv                  (column 'ticker')
    - VN Index Historical Data.csv                   (Investing.com export)
    - Vietnam 10-Year Bond Yield Historical Data.csv (Investing.com export)
"""
from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from vnstock import (
    financial_flow,
    financial_ratio,
    stock_historical_data,
    stock_screening_insights,
)

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
TRADING_DAYS = 252
DURATIONS = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "3Y": 1095, "5Y": 1825, "10Y": 3650}

st.set_page_config(page_title="VN Stock Portfolio Dashboard", layout="wide")


# ----------------------------------------------------------------------------
# Data helpers
# ----------------------------------------------------------------------------
@st.cache_data
def load_tickers():
    df = pd.read_csv(DATA_DIR / "Listing_companies_vnstock.csv")
    return sorted(df["ticker"].dropna().unique().tolist())


@st.cache_data(show_spinner=False)
def get_history(ticker, start, end):
    """Daily OHLCV for one ticker, with a datetime 'Date' column."""
    df = stock_historical_data(ticker, start, end, "1D")
    df = df.rename(columns={"time": "Date"})
    df["Date"] = pd.to_datetime(df["Date"])
    return df


@st.cache_data(show_spinner=False)
def get_prices(tickers, start, end):
    """Close prices of several tickers, aligned on common dates."""
    cols = {t: get_history(t, start, end).set_index("Date")["close"] for t in tickers}
    return pd.DataFrame(cols).dropna()


@st.cache_data
def load_market_data():
    """VN-Index level and daily risk-free rate (from 10Y bond yield)."""
    vn = pd.read_csv(DATA_DIR / "VN Index Historical Data.csv")
    vn["Date"] = pd.to_datetime(vn["Date"], format="%m/%d/%Y")
    vn = vn.set_index("Date").sort_index()
    vnindex = vn["Price"].astype(str).str.replace(",", "").astype(float).rename("VNINDEX")

    bond = pd.read_csv(DATA_DIR / "Vietnam 10-Year Bond Yield Historical Data.csv")
    bond["Date"] = pd.to_datetime(bond["Date"], format="%m/%d/%Y")
    bond = bond.set_index("Date").sort_index()
    annual_rf = bond["Price"].astype(str).str.replace(",", "").astype(float) / 100
    daily_rf = (1 + annual_rf) ** (1 / TRADING_DAYS) - 1
    return vnindex, daily_rf.rename("rf_daily")


def add_indicators(df):
    df = df.copy()
    for n in (20, 60, 100):
        df[f"SMA{n}"] = df["close"].rolling(n).mean()
    sd = df["close"].rolling(20).std()
    df["BB_Mid"] = df["SMA20"]
    df["BB_Upper"] = df["BB_Mid"] + 2 * sd
    df["BB_Lower"] = df["BB_Mid"] - 2 * sd
    return df


# ----------------------------------------------------------------------------
# Sidebar: optional screener + ticker selection
# ----------------------------------------------------------------------------
def sidebar_select_ticker():
    st.sidebar.title("VN Stock Dashboard")
    candidates = load_tickers()

    with st.sidebar.expander("Stock screener (optional)"):
        try:
            params = {"exchangeName": "HOSE,HNX,UPCOM"}
            ind_df = stock_screening_insights(params, size=1700, drop_lang="vi")
            industries = ["-"] + sorted(ind_df["industryName.en"].dropna().unique())
        except Exception:
            industries = ["-"]
            st.warning("Could not load industries from vnstock.")

        industry = st.selectbox("Industry", industries)
        condition = st.text_input("Condition", placeholder="pe < 15 and roe > 15",
                                  help="pandas query on: epsGrowth5Year, pe, pb, roe, marketCap")
        sort_by = st.selectbox("Rank by", ["marketCap", "roe", "epsGrowth5Year", "pe", "pb"])
        top_n = st.number_input("Top N", 1, 20, 6)

        if industry != "-":
            try:
                df = stock_screening_insights({"industryName": industry}, size=1700, drop_lang="vi")
                df = df[["ticker", "epsGrowth5Year", "pe", "pb", "roe", "marketCap"]]
                if condition.strip():
                    df = df.query(condition)
                top = df.nlargest(int(top_n), sort_by)
                st.dataframe(top, hide_index=True)
                candidates = top["ticker"].tolist() or candidates
            except Exception as e:
                st.error(f"Screening failed: {e}")

    ticker = st.sidebar.selectbox("Select a ticker", ["-"] + candidates)
    tab = st.sidebar.radio(
        "Select tab",
        ["Summary", "Chart", "Statistics", "Financials",
         "Efficient Frontier & CAPM", "Monte Carlo Simulation", "Portfolio Trend"],
    )
    return ticker, tab


# ----------------------------------------------------------------------------
# Tab 1: Summary
# ----------------------------------------------------------------------------
def tab_summary(ticker):
    st.title("Summary")
    if ticker == "-":
        st.info("Select a ticker on the left to begin.")
        return
    st.subheader(ticker)

    table = financial_ratio(symbol=ticker, report_range="quarterly", is_all=False)
    c1, c2 = st.columns(2)
    c1.dataframe(table.iloc[4:10, [0, 1, 2]])
    c2.dataframe(table.iloc[11:17, [0, 1, 2]])

    df = get_history(ticker, str(date.today() - timedelta(days=3650)), str(date.today()))
    fig = px.area(df, x="Date", y="close", title=f"{ticker} closing price (10 years)")
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(buttons=[
            dict(count=1, label="1M", step="month", stepmode="backward"),
            dict(count=6, label="6M", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(count=3, label="3Y", step="year", stepmode="backward"),
            dict(count=5, label="5Y", step="year", stepmode="backward"),
            dict(label="MAX", step="all"),
        ]),
    )
    st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------------------------------
# Tab 2: Chart (price, SMA, volume, Bollinger Bands)
# ----------------------------------------------------------------------------
def tab_chart(ticker):
    st.title("Chart")
    if ticker == "-":
        st.info("Select a ticker on the left to begin.")
        return
    st.subheader(ticker)

    c1, c2, c3, c4 = st.columns(4)
    start_date = c1.date_input("Start date", date.today() - timedelta(days=120))
    end_date = c2.date_input("End date", date.today())
    duration = c3.selectbox("Duration (set '-' to use dates)", ["-"] + list(DURATIONS))
    plot_type = c4.selectbox("Plot", ["Line", "Candle"])

    # Indicators are computed on the full 10Y history, then sliced for display.
    df = add_indicators(get_history(ticker, str(date.today() - timedelta(days=3650)), str(date.today())))
    if duration != "-":
        start, end = date.today() - timedelta(days=DURATIONS[duration]), date.today()
    else:
        start, end = start_date, end_date
    view = df[(df["Date"] >= pd.Timestamp(start)) & (df["Date"] <= pd.Timestamp(end))]
    if view.empty:
        st.warning("No data in the selected range.")
        return

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if plot_type == "Line":
        fig.add_trace(go.Scatter(x=view["Date"], y=view["close"], mode="lines", name="Close"))
    else:
        fig.add_trace(go.Candlestick(x=view["Date"], open=view["open"], high=view["high"],
                                     low=view["low"], close=view["close"], name="Candle"))
    for n in (20, 60, 100):
        fig.add_trace(go.Scatter(x=view["Date"], y=view[f"SMA{n}"], mode="lines", name=f"{n}-day SMA"))
    fig.add_trace(go.Bar(x=view["Date"], y=view["volume"], name="Volume"), secondary_y=True)
    fig.update_yaxes(range=[0, view["volume"].max() * 3], showticklabels=False, secondary_y=True)
    fig.update_layout(title=f"{ticker} price, SMA and volume", yaxis_title="Price (VND)")
    st.plotly_chart(fig, use_container_width=True)

    bb = go.Figure()
    bb.add_trace(go.Scatter(x=view["Date"], y=view["close"], mode="lines", name="Price"))
    bb.add_trace(go.Scatter(x=view["Date"], y=view["BB_Upper"], mode="lines",
                            name="Upper band", line=dict(color="red")))
    bb.add_trace(go.Scatter(x=view["Date"], y=view["BB_Lower"], mode="lines", fill="tonexty",
                            name="Lower band", line=dict(color="green")))
    bb.add_trace(go.Scatter(x=view["Date"], y=view["BB_Mid"], mode="lines",
                            name="Middle band (SMA20)", line=dict(color="orange")))
    bb.update_layout(title=f"{ticker} with Bollinger Bands (20, 2)",
                     xaxis_title="Date", yaxis_title="Price (VND)")
    st.plotly_chart(bb, use_container_width=True)


# ----------------------------------------------------------------------------
# Tab 3: Statistics (yearly financial ratios)
# ----------------------------------------------------------------------------
RATIO_CHARTS = {
    "ROE & ROA": {"roe": "ROE", "roa": "ROA"},
    "Gross profit margin": {"grossProfitMargin": "Gross profit margin"},
    "Leverage & liquidity": {"assetOnEquity": "Asset / Equity",
                             "debtOnEquity": "Debt / Equity",
                             "currentPayment": "Current ratio"},
    "Valuation (P/E & P/B)": {"priceToEarning": "P/E", "priceToBook": "P/B"},
}


def tab_statistics(ticker):
    st.title("Statistics")
    if ticker == "-":
        st.info("Select a ticker on the left to begin.")
        return
    st.subheader(ticker)

    ratios = financial_ratio(symbol=ticker, report_range="yearly", is_all=False).T
    for title, cols in RATIO_CHARTS.items():
        fig = go.Figure()
        for col, label in cols.items():
            if col in ratios.columns:
                fig.add_trace(go.Scatter(x=ratios.index.astype(str), y=ratios[col],
                                         mode="lines+markers", name=label))
        if fig.data:
            fig.update_layout(title=f"{title} by year", xaxis_title="Year", yaxis_title="Value")
            st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------------------------------
# Tab 4: Financial statements
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_statement(ticker, report_type, report_range):
    df = financial_flow(symbol=ticker, report_type=report_type, report_range=report_range)
    if report_range == "quarterly":
        df = df.reset_index().rename(columns={"index": "quarter"}).set_index("quarter")
    return df.drop(columns=["ticker"]).T


def tab_financials(ticker):
    st.title("Financials")
    if ticker == "-":
        st.info("Select a ticker on the left to begin.")
        return
    st.subheader(ticker)

    statement = st.selectbox("Show", ["Income Statement", "Balance Sheet", "Cash Flow"])
    period = st.selectbox("Period", ["Yearly", "Quarterly"])
    report_type = {"Income Statement": "incomestatement",
                   "Balance Sheet": "balancesheet",
                   "Cash Flow": "cashflow"}[statement]
    st.table(get_statement(ticker, report_type, period.lower()))


# ----------------------------------------------------------------------------
# Tab 5: Efficient Frontier & CAPM
# ----------------------------------------------------------------------------
def efficient_frontier(prices, rf_annual, n_portfolios=5000):
    log_ret = np.log(prices / prices.shift(1)).dropna()
    mean, cov = log_ret.mean() * TRADING_DAYS, log_ret.cov() * TRADING_DAYS

    w = np.random.dirichlet(np.ones(len(prices.columns)), n_portfolios)
    rets = w @ mean.values
    vols = np.sqrt(np.einsum("ij,jk,ik->i", w, cov.values, w))
    sharpe = (rets - rf_annual) / vols
    return pd.DataFrame({"Return": rets, "Volatility": vols, "Sharpe": sharpe}), w


def compute_capm(prices):
    vnindex, rf_daily = load_market_data()
    returns = pd.concat([vnindex, prices], axis=1, join="inner").pct_change().dropna()

    idx = rf_daily.index.union(returns.index)
    rf = rf_daily.reindex(idx).ffill().bfill().reindex(returns.index)

    excess = returns.sub(rf, axis=0)
    beta = (excess.cov()["VNINDEX"] / excess["VNINDEX"].var()).drop("VNINDEX")

    rm, rf_a = returns["VNINDEX"].mean() * TRADING_DAYS, rf.mean() * TRADING_DAYS
    table = pd.DataFrame({
        "Beta": beta,
        "CAPM expected return": rf_a + beta * (rm - rf_a),
        "Historical annual return": returns[beta.index].mean() * TRADING_DAYS,
    }).round(4)
    return table, rm, rf_a


def tab_frontier_capm():
    st.title("Efficient Frontier & CAPM")
    tickers = st.multiselect("Select tickers in your portfolio", load_tickers())
    c1, c2 = st.columns(2)
    start = c1.date_input("Start date", date(2019, 5, 30))
    end = c2.date_input("End date", date(2024, 5, 30))

    if len(tickers) < 2:
        st.info("Select at least 2 tickers.")
        return

    prices = get_prices(tuple(tickers), str(start), str(end))
    if prices.empty:
        st.warning("No overlapping price data for these tickers.")
        return

    # --- CAPM (also gives the risk-free rate used for Sharpe) ---
    capm, rm, rf_a = compute_capm(prices)

    # --- Efficient Frontier ---
    st.subheader("Efficient Frontier (random portfolios)")
    pf, weights = efficient_frontier(prices, rf_a)
    i_max, i_min = pf["Sharpe"].idxmax(), pf["Volatility"].idxmin()

    fig = px.scatter(pf, x="Volatility", y="Return", color="Sharpe",
                     color_continuous_scale="Viridis", opacity=0.6)
    for i, name, color in [(i_max, "Max Sharpe", "red"), (i_min, "Min Volatility", "blue")]:
        fig.add_trace(go.Scatter(x=[pf.loc[i, "Volatility"]], y=[pf.loc[i, "Return"]],
                                 mode="markers", name=name,
                                 marker=dict(size=14, color=color, symbol="star")))
    fig.update_layout(xaxis_title="Annualized volatility", yaxis_title="Annualized return")
    st.plotly_chart(fig, use_container_width=True)

    st.write("**Portfolio weights**")
    st.dataframe(pd.DataFrame({
        "Max Sharpe": weights[i_max], "Min Volatility": weights[i_min],
    }, index=prices.columns).style.format("{:.1%}"))
    st.write(f"Max Sharpe: return {pf.loc[i_max, 'Return']:.2%}, "
             f"volatility {pf.loc[i_max, 'Volatility']:.2%}, Sharpe {pf.loc[i_max, 'Sharpe']:.2f} "
             f"(risk-free rate {rf_a:.2%})")

    # --- CAPM output ---
    st.subheader("CAPM")
    st.dataframe(capm)
    st.caption(f"Market return (VN-Index): {rm:.2%} | Risk-free rate (10Y bond): {rf_a:.2%}")


# ----------------------------------------------------------------------------
# Tab 6: Monte Carlo simulation + VaR
# ----------------------------------------------------------------------------
def tab_monte_carlo(ticker):
    st.title("Monte Carlo Simulation")
    if ticker == "-":
        st.info("Select a ticker on the left to begin.")
        return
    st.subheader(ticker)

    c1, c2 = st.columns(2)
    n_sims = c1.selectbox("Number of simulations", [200, 500, 1000])
    horizon = c2.selectbox("Time horizon (days)", [30, 60, 90])

    hist = get_history(ticker, str(date.today() - timedelta(days=365)), str(date.today()))
    close = hist["close"].to_numpy()
    daily_vol = pd.Series(close).pct_change().std()

    shocks = np.random.normal(0, daily_vol, (horizon, n_sims))
    paths = close[-1] * np.cumprod(1 + shocks, axis=0)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(paths, linewidth=0.7)
    ax.axhline(close[-1], color="red", label=f"Current price: {close[-1]:,.2f}")
    ax.set(title=f"Monte Carlo simulation for {ticker} ({horizon} days)", xlabel="Day", ylabel="Price")
    ax.legend()
    st.pyplot(fig)

    st.subheader("Value at Risk (VaR)")
    ending = paths[-1]
    p5 = np.percentile(ending, 5)
    fig2, ax2 = plt.subplots(figsize=(12, 5))
    ax2.hist(ending, bins=50)
    ax2.axvline(p5, color="red", linestyle="--", label=f"5th percentile: {p5:,.2f}")
    ax2.set(title="Distribution of ending price", xlabel="Price", ylabel="Frequency")
    ax2.legend()
    st.pyplot(fig2)
    st.write(f"VaR at 95% confidence: **{close[-1] - p5:,.2f} VND** per share over {horizon} days")


# ----------------------------------------------------------------------------
# Tab 7: Portfolio trend
# ----------------------------------------------------------------------------
def tab_portfolio_trend():
    st.title("Portfolio Trend")
    tickers = st.multiselect("Select tickers in your portfolio", load_tickers())
    rebase = st.checkbox("Rebase to 100 at start", value=True)
    if not tickers:
        st.info("Select at least 1 ticker.")
        return

    prices = get_prices(tuple(tickers), str(date.today() - timedelta(days=1825)), str(date.today()))
    if rebase:
        prices = prices / prices.iloc[0] * 100
    fig = px.line(prices)
    fig.update_layout(title="Portfolio trend (5 years)", xaxis_title="Date",
                      yaxis_title="Index (start = 100)" if rebase else "Close (VND)",
                      legend_title="Ticker")
    st.plotly_chart(fig, use_container_width=True)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def run():
    ticker, tab = sidebar_select_ticker()
    if tab == "Summary":
        tab_summary(ticker)
    elif tab == "Chart":
        tab_chart(ticker)
    elif tab == "Statistics":
        tab_statistics(ticker)
    elif tab == "Financials":
        tab_financials(ticker)
    elif tab == "Efficient Frontier & CAPM":
        tab_frontier_capm()
    elif tab == "Monte Carlo Simulation":
        tab_monte_carlo(ticker)
    elif tab == "Portfolio Trend":
        tab_portfolio_trend()


if __name__ == "__main__":
    run()
