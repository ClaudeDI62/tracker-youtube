import yfinance as yf
t = yf.Ticker("NFLX")
h = t.history(start="2026-06-25", end="2026-06-26")
print(f"NFLX Close on 2026-06-25: ${h.iloc[0]['Close']:.2f}")
t2 = yf.Ticker("CSU.TO")
h2 = t2.history(start="2026-07-03", end="2026-07-07")
print(f"\nCSU.TO (Constellation Software, Toronto):")
print(h2[["Close"]])
