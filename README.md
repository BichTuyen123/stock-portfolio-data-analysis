# Stock Portfolio Data Analysis

An end-to-end analysis of a Vietnamese stock portfolio using Python, from
macro and sector analysis to stock selection, technical analysis, and
portfolio performance evaluation.

## Project Overview

This project screens a universe of **1,607 stocks listed on HOSE, HNX and
UPCoM** and applies a **value investing** approach (Benjamin Graham's
principles) to select **3 representative sectors, 1 stock per sector**:

| Ticker | Company | Sector | Exchange |
|---|---|---|---|
| CTG | VietinBank | Banking | HOSE |
| BIC | BIDV Insurance Corporation | Insurance | HOSE |
| SLS | Son La Sugar JSC | Food & Beverage | HNX |

Each stock is analyzed with technical indicators and financial ratios, and the
investment efficiency of the resulting portfolio is evaluated over a 5-year
window (May 2019 - May 2024). Everything is packaged as an interactive
**Streamlit dashboard**, with a written report in `reports/`.

## Workflow

1. **Market Analysis**
   - Macroeconomic analysis (PESTLE): political stability, 2024 GDP growth
     forecast of 5.5-6.0%, 2023 inflation of 3.25%, technology and
     green-economy trends
   - Sector analysis: Banking, Insurance and Food & Beverage selected for
     their growth outlook
2. **Investment Strategy**
   - Stock screening based on value investing: sufficiently large company
     size, 5-year EPS growth >= 4% per year, moderate P/E, moderate P/B,
     ROE above 3x the bank deposit rate
3. **Company Analysis**
   - Company overview
   - Financial ratio analysis: ROE, ROA, gross profit margin, asset/equity,
     debt/equity, current ratio, P/E, P/B
4. **Technical & Portfolio Analysis**
   - Price movement, trading volume, SMA 20/60/100 and Bollinger Bands
   - Efficient Frontier
   - Capital Asset Pricing Model (CAPM)
   - Monte Carlo Simulation and 95% Value at Risk (VaR)
   - 5-year price trend (Portfolio Trend)
5. **Conclusion**
   - Evaluation of the portfolio's investment performance based on the
     analyses above

## Tools & Libraries

Python, Streamlit, pandas, NumPy, Plotly, Matplotlib, vnstock

## Key Results

**CAPM expected return** (VN-Index as market, 10-year government bond yield as
risk-free rate):

| Ticker | Mean CAPM | Cumulative CAPM |
|---|---|---|
| BIC | 17.59% | 17.71% |
| CTG | 5.82% | 6.59% |
| SLS | 4.66% | 5.55% |

**Monte Carlo simulation** (200 scenarios, 30 days):

| Ticker | Price at simulation (VND) | 5th percentile (VND) | VaR 95% (VND) |
|---|---|---|---|
| BIC | 33,450 | 28,846.85 | 4,603.15 |
| CTG | 31,900 | 26,976.94 | 4,923.06 |
| SLS | 168,900 | 145,308.48 | 23,591.52 |

**Efficient Frontier:** simulated portfolios of the three stocks show
annualized expected returns of roughly 15%-36% against volatility of roughly
24%-36%.

**Technical and fundamental highlights (as of May 2024):**
- **BIC:** strong uptrend from late 2023, accelerating in Apr-May 2024 to
  above 34,000 VND; ROE and ROA rising; P/E down from about 12 to below 6.
- **SLS:** peaked near 200,000 VND in mid-2023, fell to about 140,000 VND by
  Jan 2024, then recovered to about 170,000 VND; ROE, ROA and gross margin
  rising, current ratio sharply improved.
- **CTG:** rallied to about 36,000 VND in Mar 2024, then corrected below its
  SMAs by May 2024; stable high ROE with low ROA, typical of a bank.

**Conclusion:** the three stocks meet the screening criteria and come from
different sectors, which helps diversification. BIC offers the highest
expected return, SLS is the most volatile in absolute price terms, and CTG has
steadier fundamentals with a recent technical pullback.

## Dashboard Features

| Tab | Description |
|---|---|
| Stock screener (sidebar) | Filter by industry with custom conditions on EPS growth, P/E, P/B, ROE, market cap |
| Summary | Key quarterly ratios and 10-year price chart |
| Chart | Line/candlestick, SMA, volume, Bollinger Bands |
| Statistics | Yearly trends of key financial ratios |
| Financials | Income statement, balance sheet, cash flow |
| Efficient Frontier & CAPM | Random portfolios, Max Sharpe / Min Volatility weights, beta and CAPM return |
| Monte Carlo Simulation | Simulated price paths and 95% VaR |
| Portfolio Trend | 5-year price comparison |

## Repository Structure

```
├── app.py                 # Streamlit dashboard
├── requirements.txt
├── data/                  # Listing, VN-Index and 10Y bond yield CSV files
├── reports/               # Full analysis report (PDF, Vietnamese)
└── README.md
```

## Getting Started

```bash
git clone https://github.com/BichTuyen123/stock-portfolio-data-analysis.git
cd stock-portfolio-data-analysis
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Limitations

- Only 3 stocks and no backtest against a benchmark such as VN-Index, so the
  results illustrate the method rather than prove a strategy's effectiveness.
- The Monte Carlo model assumes normally distributed daily returns with zero
  drift, which understates tail risk.
- Figures above reflect data up to May 2024.

*For educational purposes only; not investment advice.*
