from datetime import datetime
from typing import Dict, Optional
from functools import lru_cache, cached_property
import copy
from decimal import Decimal
import re
from threading import Lock

# ---- Exceptions ----
class StockError(Exception):
    """Base exception for Stock-related errors"""
    def __init__(self, message: str, stock_name: Optional[str] = None):
        self.stock_name = stock_name
        self.message = message
        super().__init__(f"{message} (Stock: {stock_name})" if stock_name else message)

class InvalidStockNameError(StockError):
    """Raised when stock symbol is invalid"""
    def __init__(self, message: str, stock_name: str):
        super().__init__(f"Invalid stock symbol: {message}", stock_name)

class InvalidPriceError(StockError):
    """Raised when price data is invalid"""
    def __init__(self, message: str, stock_name: str, date: Optional[datetime] = None, price: Optional[float] = None):
        details = []
        if date:
            details.append(f"Date: {date.date()}")
        if price is not None:
            details.append(f"Price: {price}")
        detail_str = f" ({', '.join(details)})" if details else ""
        super().__init__(f"Invalid price data: {message}{detail_str}", stock_name)

class DateRangeError(StockError):
    """Raised when a date is outside the valid range for a stock"""
    def __init__(self, date: datetime, stock_name: str, min_date: datetime, max_date: datetime):
        message = f"Date {date.date()} is outside the valid range [{min_date.date()}, {max_date.date()}]"
        super().__init__(message, stock_name)



class PortfolioError(Exception):
    """Base exception for Portfolio-related errors"""
    def __init__(self, message: str, portfolio_id: Optional[int] = None):
        self.portfolio_id = portfolio_id
        self.message = message
        super().__init__(f"{message} (Portfolio: {portfolio_id})" if portfolio_id else message)

class InvalidTransactionError(PortfolioError):
    """Raised when a transaction is invalid"""
    def __init__(self, message: str, portfolio_id: Optional[int] = None, user_id: Optional[int] = None):
        details = []
        if user_id is not None:
            details.append(f"User ID: {user_id}")
        detail_str = f" ({', '.join(details)})" if details else ""
        super().__init__(f"Invalid transaction: {message}{detail_str}", portfolio_id)

class InsufficientStockError(PortfolioError):
    """Raised when trying to remove more stock than available"""
    def __init__(self, stock_name: str, requested: int, available: int):
        message = f"Cannot remove {requested} shares of {stock_name}, only {available} available"
        super().__init__(message)

class CacheError(Exception):
    """Raised when there are issues with caching"""
    def __init__(self, message: str):
        super().__init__(f"Cache error: {message}")

# ---- Core Classes ----
class Stock:
    """
    Represents a stock with its price history (Example: AAPL from 2023 to 2024).
    """
    _STOCK_NAME_PATTERN = re.compile(r'^[A-Z0-9]{1,10}$') # use of regex: more flexible than string length check
    _MAX_PRICE = Decimal('1000000.00') # use of decimal: more exact for money transactions than (int, float)
    _MIN_PRICE = Decimal('0.01')
    
    def __init__(self, symbol: str, prices: Dict[datetime, float]):
        self._symbol = symbol  # Renamed from _name to _symbol
        self._validate_symbol(symbol) # validation of name (Not empty, only uppercase letters and numbers)
        self._validate_prices(prices) # validation of prices (Not empty, at least two dates, positive, max and min price)
        
        self._prices = {date: Decimal(str(price)) for date, price in prices.items()}
        self._min_date = min(self._prices.keys())
        self._max_date = max(self._prices.keys())
        self._lock = Lock() # lock for thread safety

    def _validate_symbol(self, symbol: str) -> None:
        if not symbol or not symbol.strip():
            raise InvalidStockNameError("Stock symbol cannot be empty", symbol)
        if not self._STOCK_NAME_PATTERN.match(symbol):
            raise InvalidStockNameError(
                "Stock symbol must be 1-10 characters long and contain only uppercase letters and numbers",
                symbol
            )

    def _validate_prices(self, prices: Dict[datetime, float]) -> None:
        if not prices:
            raise InvalidPriceError("Prices dictionary cannot be empty", self._symbol)
        if len(prices) < 2:
            raise InvalidPriceError("At least two dates are required", self._symbol)
        
        for date, price in prices.items():
            if not isinstance(date, datetime):
                raise InvalidPriceError(f"Invalid date type: {type(date)}", self._symbol, date=date)
            if not isinstance(price, (int, float)):
                raise InvalidPriceError(f"Invalid price type: {type(price)}", self._symbol, date=date, price=price)
            if price <= 0:
                raise InvalidPriceError(f"Price must be positive: {price}", self._symbol, date=date, price=price)
            if Decimal(str(price)) > self._MAX_PRICE:
                raise InvalidPriceError(f"Price exceeds maximum allowed value: {price}", self._symbol, date=date, price=price)
            if Decimal(str(price)) < self._MIN_PRICE:
                raise InvalidPriceError(f"Price below minimum allowed value: {price}", self._symbol, date=date, price=price)

    def __eq__(self, other):
        return isinstance(other, Stock) and self._symbol == other._symbol

    def __hash__(self):
        return hash(self._symbol)

    def __repr__(self):
        return f"Stock(symbol='{self._symbol}', prices={len(self._prices)} points)"

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def min_date(self) -> datetime:
        return self._min_date

    @property
    def max_date(self) -> datetime:
        return self._max_date

    @cached_property
    def prices(self) -> Dict[datetime, Decimal]:
        with self._lock:
            return self._prices.copy()  # Only copy the dictionary, not the Decimal values for security

    @lru_cache(maxsize=4096)  # Increased cache size for better hit rate
    def price(self, date: datetime) -> Decimal:
        if not isinstance(date, datetime):
            raise InvalidPriceError("Date must be a datetime object", self._symbol, date=date)
            
        if date < self._min_date or date > self._max_date:
            raise DateRangeError(date, self._symbol, self._min_date, self._max_date)
        
        price = self._prices.get(date)
        if price is None:
            raise InvalidPriceError(f"No price data available for date {date.date()}", self._symbol, date=date)
        return price

class Portfolio:
    """
    Represents a portfolio of stocks with optimized performance.
    """
    _MAX_QUANTITY = 1_000_000_000  # 1 billion shares
    _MAX_USER_ID = 2**31 - 1  # Maximum 32-bit signed integer
    
    def __init__(self, owner_id: int):
        self._owner_id = owner_id
        self._holdings = {}  # Dictionary: Stock -> quantity
        self._transactions = []  # List to track who added stocks and when
        self._lock = Lock()
        self._value_cache = {}  # Cache for portfolio values
        self._cache_lock = Lock()
        self._last_cache_cleanup = datetime.now()
        self._CACHE_CLEANUP_INTERVAL = 3600  # Clean cache every hour

    def _cleanup_cache(self, current_time: Optional[datetime] = None):
        try:
            current_time = current_time or datetime.now()
            if (current_time - self._last_cache_cleanup).total_seconds() > self._CACHE_CLEANUP_INTERVAL:
                with self._cache_lock:
                    self._value_cache.clear()
                    self._last_cache_cleanup = current_time
        except Exception as e:
            raise CacheError(f"Failed to cleanup cache: {str(e)}")

    @property
    def holdings(self) -> Dict['Stock', int]:
        with self._lock:
            return self._holdings.copy()

    def _validate_ownership(self, user_id: int) -> None:
        if user_id != self._owner_id:
            raise InvalidTransactionError(
                "Only the portfolio owner can perform this action",
                user_id=user_id
            )

    def _validate_quantity(self, quantity: int) -> None:
        if not isinstance(quantity, int):
            raise InvalidTransactionError(f"Quantity must be an integer, got {type(quantity)}")
        if quantity <= 0:
            raise InvalidTransactionError("Quantity must be positive")
        if quantity > self._MAX_QUANTITY:
            raise InvalidTransactionError(f"Quantity exceeds maximum allowed value: {quantity}")

    def add_stock(self, stock: Stock, quantity: int, added_by: int, purchase_date: datetime, timestamp: Optional[datetime] = None):
        self._validate_ownership(added_by)
        self._validate_quantity(quantity)
        
        try:
            with self._lock:
                current_quantity = self._holdings.get(stock, 0)
                new_quantity = current_quantity + quantity
                if new_quantity > self._MAX_QUANTITY:
                    raise InvalidTransactionError(
                        f"Adding {quantity} shares would exceed maximum allowed quantity",
                        self._portfolio_id,
                        added_by
                    )
                
                self._holdings[stock] = new_quantity
                self._transactions.append({
                    'type': 'add',
                    'stock': stock.symbol,
                    'quantity': quantity,
                    'added_by': added_by,
                    'timestamp': timestamp or datetime.now(),
                    'purchase_date': purchase_date,
                    'new_quantity': new_quantity
                })
        except Exception as e:
            raise PortfolioError(f"Failed to add stock: {str(e)}", self._portfolio_id)

    def remove_stock(self, stock: Stock, quantity: int, removed_by: int, timestamp: Optional[datetime] = None):
        self._validate_ownership(removed_by)
        self._validate_quantity(quantity)
        
        try:
            with self._lock:
                current_quantity = self._holdings.get(stock, 0)
                if current_quantity < quantity:
                    raise InsufficientStockError(
                        stock.symbol,
                        quantity,
                        current_quantity
                    )
                
                new_quantity = current_quantity - quantity
                if new_quantity == 0:
                    del self._holdings[stock]
                else:
                    self._holdings[stock] = new_quantity
                    
                self._transactions.append({
                    'type': 'remove',
                    'stock': stock.symbol,
                    'quantity': quantity,
                    'removed_by': removed_by,
                    'timestamp': timestamp or datetime.now(),
                    'new_quantity': new_quantity
                })
        except InsufficientStockError:
            raise
        except Exception as e:
            raise PortfolioError(f"Failed to remove stock: {str(e)}")

    def get_quantity(self, stock: Stock) -> int:
        with self._lock:
            return self._holdings.get(stock, 0)

    def value(self, date: datetime) -> Decimal:
        if not isinstance(date, datetime):
            raise InvalidPriceError("Date must be a datetime object", "Portfolio", date=date)
            
            
        self._cleanup_cache()
        
        cache_key = (date, tuple(self._holdings.items()))
        with self._cache_lock:
            if cache_key in self._value_cache:
                return self._value_cache[cache_key]
            
            total = Decimal('0')
            with self._lock:
                for stock, quantity in self._holdings.items():
                    total += stock.price(date) * Decimal(str(quantity))
            
            self._value_cache[cache_key] = total
            return total

    def profit(self, start_date: datetime, end_date: datetime) -> Decimal:
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            raise InvalidPriceError("Dates must be datetime objects", "Portfolio", date=start_date)
        if end_date < start_date:
            raise InvalidTransactionError("End date must be after start date", self._portfolio_id)
            
        return self.value(end_date) - self.value(start_date)

    @lru_cache(maxsize=1024)  # Increased cache size
    def annualized_return(self, start_date: datetime, end_date: datetime) -> Decimal:
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            raise InvalidPriceError("Dates must be datetime objects", "Portfolio", date=start_date)
        if end_date <= start_date:
            raise InvalidTransactionError("End date must be after start date", self._portfolio_id)
        
        days = Decimal(str((end_date - start_date).days))
        if days <= 0:
            raise InvalidTransactionError("End date must be after start date to compute return", self._portfolio_id)
        
        initial_value = self.value(start_date)
        final_value = self.value(end_date)
        if initial_value == 0:
            raise InvalidTransactionError("Initial portfolio value is zero, cannot compute return", self._portfolio_id)
        
        years = days / Decimal('365.2425')  # Using average length of a year including leap years
        return (final_value / initial_value) ** (Decimal('1') / years) - Decimal('1')

    def get_transactions(self):
        with self._lock:
            return copy.deepcopy(self._transactions)

# ---- Example Usage ----
def main():
    # Create sample stocks

    stock_a = Stock(
        symbol="STOCKA",
        prices={
            datetime(2023, 1, 1): 150,
            datetime(2024, 1, 1): 180,
        }
    )
    stock_b = Stock(
        symbol="STOCKB",
        prices={
            datetime(2023, 1, 1): 250,
            datetime(2024, 1, 1): 300,
        }
    )

    # Create portfolio
    portfolio = Portfolio(owner_id=1)
    portfolio.add_stock(stock_a, quantity=10, added_by=1, purchase_date=datetime(2023, 1, 1)) # Assumes that portfolio can be shared between users
    portfolio.add_stock(stock_b, quantity=5, added_by=1, purchase_date=datetime(2023, 1, 1))

    # Calculate profit
    start = datetime(2023, 1, 1)
    end = datetime(2024, 1, 1)
    profit = portfolio.profit(start, end)
    print(f"Profit: ${profit:.2f}")

    # Calculate annualized return
    annual_return = portfolio.annualized_return(start, end)
    print(f"Annualized Return: {annual_return:.2%}")

    # Show transactions
    print("\nTransactions:")
    for t in portfolio.get_transactions():
        print(f"{t['timestamp']}: {t['added_by']} added {t['quantity']} shares of {t['stock']} (purchased on {t['purchase_date'].date()})")

if __name__ == "__main__":
    main()
