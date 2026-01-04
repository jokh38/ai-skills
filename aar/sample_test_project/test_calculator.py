"""Test calculator module with failing tests for ARR demo"""
import pytest
from calculator import (
    add,
    subtract,
    multiply,
    divide,
    calculate_average,
    factorial,
    is_prime,
    fibonacci,
)


def test_add():
    """Test add function"""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_subtract():
    """Test subtract function"""
    assert subtract(5, 3) == 2
    assert subtract(10, 10) == 0
    assert subtract(-5, -3) == -2


def test_multiply():
    """Test multiply function"""
    assert multiply(2, 3) == 6
    assert multiply(-2, 3) == -6
    assert multiply(0, 5) == 0


def test_divide():
    """Test divide function"""
    assert divide(6, 2) == 3
    assert divide(-10, 2) == -5
    assert divide(5, 2) == 2.5


def test_divide_by_zero():
    """Test divide by zero handling"""
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)


def test_calculate_average():
    """Test calculate_average function"""
    assert calculate_average([1, 2, 3, 4, 5]) == 3
    assert calculate_average([10, 20, 30]) == 20
    assert calculate_average([-1, 0, 1]) == 0


def test_calculate_average_empty_list():
    """Test calculate_average with empty list"""
    with pytest.raises(ZeroDivisionError):
        calculate_average([])


def test_factorial():
    """Test factorial function"""
    assert factorial(0) == 1
    assert factorial(1) == 1
    assert factorial(5) == 120
    assert factorial(3) == 6


def test_is_prime():
    """Test is_prime function"""
    assert is_prime(2) == True
    assert is_prime(3) == True
    assert is_prime(5) == True
    assert is_prime(11) == True
    assert is_prime(1) == False
    assert is_prime(4) == False
    assert is_prime(9) == False
    assert is_prime(15) == False


def test_fibonacci():
    """Test fibonacci function"""
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1
    assert fibonacci(5) == 5
    assert fibonacci(10) == 55
    assert fibonacci(2) == 1
