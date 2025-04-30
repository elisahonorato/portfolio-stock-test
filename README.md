# Stock Portfolio Manager

Optimized Python implementation for managing stock portfolios and calculating returns.

## Features

- Portfolio management with optimized performance
- Profit and annualized return calculations
- Efficient price lookups with caching
- Date range validation

## Quick Start

```bash
python main.py
```

## Example

```python
from datetime import datetime
from main import Stock, Portfolio

# Create stocks
stock_a = Stock("Stock A", {datetime(2023,1,1): 150, datetime(2024,1,1): 180})
stock_b = Stock("Stock B", {datetime(2023,1,1): 250, datetime(2024,1,1): 300})

# Setup portfolio
portfolio = Portfolio()
portfolio.add_stock(stock_a, 10)
portfolio.add_stock(stock_b, 5)

# Calculate returns
start = datetime(2023, 1, 1)
end = datetime(2024, 1, 1)
print(f"Profit: ${portfolio.profit(start, end):.2f}")
print(f"Annual Return: {portfolio.annualized_return(start, end):.2%}")
```

## Output
```
Profit: $550.00
Annualized Return: 20.00%
``` 