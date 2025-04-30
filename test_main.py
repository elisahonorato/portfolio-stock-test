import unittest
from datetime import datetime
from decimal import Decimal
from main import Stock, Portfolio, StockError, InvalidStockNameError, InvalidPriceError, DateRangeError, PortfolioError, InvalidTransactionError, InsufficientStockError

class TestStock(unittest.TestCase):
    def setUp(self):
        self.valid_prices = {
            datetime(2023, 1, 1): 150.0,
            datetime(2023, 1, 2): 155.0,
            datetime(2023, 1, 3): 160.0
        }
        self.stock = Stock("AAPL", self.valid_prices)

    def test_valid_stock_creation(self):
        self.assertEqual(self.stock.symbol, "AAPL")
        self.assertEqual(len(self.stock.prices), 3)
        self.assertEqual(self.stock.min_date, datetime(2023, 1, 1))
        self.assertEqual(self.stock.max_date, datetime(2023, 1, 3))

    def test_invalid_stock_name(self):
        with self.assertRaises(InvalidStockNameError):
            Stock("", self.valid_prices)
        with self.assertRaises(InvalidStockNameError):
            Stock("aapl", self.valid_prices)  # lowercase
        with self.assertRaises(InvalidStockNameError):
            Stock("AAPL123456789", self.valid_prices)  # too long

    def test_invalid_prices(self):
        with self.assertRaises(InvalidPriceError):
            Stock("AAPL", {})  # empty prices
        with self.assertRaises(InvalidPriceError):
            Stock("AAPL", {datetime(2023, 1, 1): 150.0})  # only one price
        with self.assertRaises(InvalidPriceError):
            Stock("AAPL", {datetime(2023, 1, 1): -150.0})  # negative price
        with self.assertRaises(InvalidPriceError):
            Stock("AAPL", {datetime(2023, 1, 1): 0})  # zero price

    def test_price_at_date(self):
        self.assertEqual(self.stock.price(datetime(2023, 1, 1)), Decimal('150.0'))
        self.assertEqual(self.stock.price(datetime(2023, 1, 2)), Decimal('155.0'))
        self.assertEqual(self.stock.price(datetime(2023, 1, 3)), Decimal('160.0'))

    def test_price_out_of_range(self):
        with self.assertRaises(DateRangeError):
            self.stock.price(datetime(2022, 12, 31))
        with self.assertRaises(DateRangeError):
            self.stock.price(datetime(2023, 1, 4))

class TestPortfolio(unittest.TestCase):
    def setUp(self):
        self.owner_id = 1
        self.other_user_id = 2
        self.portfolio = Portfolio(self.owner_id)
        self.stock_a = Stock("AAPL", {
            datetime(2023, 1, 1): 150.0,
            datetime(2023, 1, 2): 155.0
        })
        self.stock_b = Stock("GOOGL", {
            datetime(2023, 1, 1): 100.0,
            datetime(2023, 1, 2): 105.0
        })

    def test_add_stock_by_owner(self):
        self.portfolio.add_stock(self.stock_a, 10, self.owner_id, datetime(2023, 1, 1))
        self.assertEqual(self.portfolio.get_quantity(self.stock_a), 10)

    def test_add_stock_by_non_owner(self):
        with self.assertRaises(InvalidTransactionError) as context:
            self.portfolio.add_stock(self.stock_a, 10, self.other_user_id, datetime(2023, 1, 1))
        self.assertIn("Only the portfolio owner can perform this action", str(context.exception))

    def test_remove_stock_by_owner(self):
        self.portfolio.add_stock(self.stock_a, 10, self.owner_id, datetime(2023, 1, 1))
        self.portfolio.remove_stock(self.stock_a, 5, self.owner_id)
        self.assertEqual(self.portfolio.get_quantity(self.stock_a), 5)
        

    def test_remove_stock_by_non_owner(self):
        self.portfolio.add_stock(self.stock_a, 10, self.owner_id, datetime(2023, 1, 1))
        with self.assertRaises(InvalidTransactionError) as context:
            self.portfolio.remove_stock(self.stock_a, 5, self.other_user_id)
        self.assertIn("Only the portfolio owner can perform this action", str(context.exception))

    def test_insufficient_stock_removal(self):
        self.portfolio.add_stock(self.stock_a, 10, 1, datetime(2023, 1, 1))
        with self.assertRaises(InsufficientStockError):
            self.portfolio.remove_stock(self.stock_a, 15, 1)

    def test_portfolio_value(self):
        self.portfolio.add_stock(self.stock_a, 10, 1, datetime(2023, 1, 1))
        self.portfolio.add_stock(self.stock_b, 5, 1, datetime(2023, 1, 1))
        
        value = self.portfolio.value(datetime(2023, 1, 1))
        expected_value = Decimal('150.0') * 10 + Decimal('100.0') * 5
        self.assertEqual(value, expected_value)

    def test_portfolio_profit(self):
        self.portfolio.add_stock(self.stock_a, 10, 1, datetime(2023, 1, 1))
        self.portfolio.add_stock(self.stock_b, 5, 1, datetime(2023, 1, 1))
        
        profit = self.portfolio.profit(datetime(2023, 1, 1), datetime(2023, 1, 2))
        expected_profit = (Decimal('155.0') * 10 + Decimal('105.0') * 5) - (Decimal('150.0') * 10 + Decimal('100.0') * 5)
        self.assertEqual(profit, expected_profit)

    def test_annualized_return(self):
        self.portfolio.add_stock(self.stock_a, 10, 1, datetime(2023, 1, 1))
        self.portfolio.add_stock(self.stock_b, 5, 1, datetime(2023, 1, 1))
        
        annual_return = self.portfolio.annualized_return(datetime(2023, 1, 1), datetime(2023, 1, 2))
        self.assertIsInstance(annual_return, Decimal)

    def test_invalid_transactions(self):
        with self.assertRaises(InvalidTransactionError):
            self.portfolio.add_stock(self.stock_a, -10, 1, datetime(2023, 1, 1))
        with self.assertRaises(InvalidTransactionError):
            self.portfolio.add_stock(self.stock_a, 10, -1, datetime(2023, 1, 1))

    def test_get_transactions(self):
        self.portfolio.add_stock(self.stock_a, 10, 1, datetime(2023, 1, 1))
        self.portfolio.remove_stock(self.stock_a, 5, 1)
        
        transactions = self.portfolio.get_transactions()
        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0]['type'], 'add')
        self.assertEqual(transactions[1]['type'], 'remove')

if __name__ == '__main__':
    unittest.main() 