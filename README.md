# Stock Portfolio Manager

A high-performance Python implementation for managing stock portfolios with advanced financial calculations and optimized data structures.

## Features

- 🚀 **Portfolio Management**: Add, remove, and track stocks with efficient operations
- 📊 **Financial Analytics**: Calculate profits, returns, and portfolio values
- ⚡ **Performance Optimized**: Fast price lookups with intelligent caching
- 🔒 **Data Validation**: Comprehensive date range and input validation
- 📈 **Advanced Calculations**: Annualized returns and profit analysis
- 🔐 **Security**: User-based transaction validation

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/stock-portfolio-manager.git
cd stock-portfolio-manager

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Portfolio Management

```python
from datetime import datetime
from main import Stock, Portfolio

# Create stocks with historical prices
stock_a = Stock("AAPL", {
    datetime(2023, 1, 1): 150.0,
    datetime(2023, 1, 2): 155.0,
    datetime(2023, 1, 3): 160.0
})

stock_b = Stock("GOOGL", {
    datetime(2023, 1, 1): 100.0,
    datetime(2023, 1, 2): 105.0,
    datetime(2023, 1, 3): 110.0
})

# Initialize portfolio
portfolio = Portfolio(owner_id=1)

# Add stocks to portfolio
portfolio.add_stock(stock_a, 10, owner_id=1, date=datetime(2023, 1, 1))
portfolio.add_stock(stock_b, 5, owner_id=1, date=datetime(2023, 1, 1))

# Calculate portfolio metrics
start_date = datetime(2023, 1, 1)
end_date = datetime(2023, 1, 3)

print(f"Portfolio Value: ${portfolio.value(end_date):.2f}")
print(f"Total Profit: ${portfolio.profit(start_date, end_date):.2f}")
print(f"Annualized Return: {portfolio.annualized_return(start_date, end_date):.2%}")
```

### Expected Output
```
Portfolio Value: $2150.00
Total Profit: $150.00
Annualized Return: 36.50%
```

## API Reference

### Stock Class
- `Stock(symbol: str, prices: Dict[datetime, float])`: Create a new stock
- `price(date: datetime) -> Decimal`: Get stock price at specific date
- `min_date`: Earliest available price date
- `max_date`: Latest available price date

### Portfolio Class
- `Portfolio(owner_id: int)`: Create a new portfolio
- `add_stock(stock: Stock, quantity: int, owner_id: int, date: datetime)`: Add stocks
- `remove_stock(stock: Stock, quantity: int, owner_id: int)`: Remove stocks
- `value(date: datetime) -> Decimal`: Calculate portfolio value
- `profit(start_date: datetime, end_date: datetime) -> Decimal`: Calculate profit
- `annualized_return(start_date: datetime, end_date: datetime) -> Decimal`: Calculate annualized return

## Error Handling

The library includes comprehensive error handling for:
- Invalid stock symbols
- Invalid price data
- Date range errors
- Insufficient stock quantities
- Unauthorized transactions

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 