# cython: language_level=3
# cython: boundscheck=False, wraparound=False, initializedcheck=False

"""C-level price-time matching core for the ChronosMatch prototype.

Validation and Python object conversion happen with the GIL held. The inner
book scan, fill calculation, and order removal run without the GIL.
"""

from libc.math cimport isfinite
from libc.stddef cimport size_t
from libc.stdint cimport uint8_t, uint64_t
from libc.stdlib cimport free, realloc

from trading_engine import Order


cdef uint64_t MAX_U64 = 18446744073709551615


ctypedef struct COrder:
    uint64_t order_id
    double price
    uint64_t quantity


ctypedef struct CTrade:
    uint64_t buy_order_id
    uint64_t sell_order_id
    uint64_t resting_order_id
    uint64_t quantity


cdef inline Py_ssize_t _best_buy(COrder* orders, Py_ssize_t count) noexcept nogil:
    cdef Py_ssize_t best = 0
    cdef Py_ssize_t i
    for i in range(1, count):
        if orders[i].price > orders[best].price:
            best = i
    return best


cdef inline Py_ssize_t _best_sell(COrder* orders, Py_ssize_t count) noexcept nogil:
    cdef Py_ssize_t best = 0
    cdef Py_ssize_t i
    for i in range(1, count):
        if orders[i].price < orders[best].price:
            best = i
    return best


cdef inline void _remove_order(
    COrder* orders,
    Py_ssize_t* count,
    Py_ssize_t index,
) noexcept nogil:
    cdef Py_ssize_t i
    for i in range(index, count[0] - 1):
        orders[i] = orders[i + 1]
    count[0] -= 1


cdef void _match_loop(
    COrder* buys,
    Py_ssize_t* buy_count,
    COrder* sells,
    Py_ssize_t* sell_count,
    CTrade* trades,
    Py_ssize_t* trade_count,
    uint8_t incoming_side,
) noexcept nogil:
    cdef Py_ssize_t buy_index
    cdef Py_ssize_t sell_index
    cdef uint64_t quantity
    cdef CTrade trade

    while buy_count[0] > 0 and sell_count[0] > 0:
        buy_index = _best_buy(buys, buy_count[0])
        sell_index = _best_sell(sells, sell_count[0])

        if buys[buy_index].price < sells[sell_index].price:
            break

        if buys[buy_index].quantity < sells[sell_index].quantity:
            quantity = buys[buy_index].quantity
        else:
            quantity = sells[sell_index].quantity

        trade.buy_order_id = buys[buy_index].order_id
        trade.sell_order_id = sells[sell_index].order_id
        trade.quantity = quantity

        # The incoming order trades at the resting order's price.
        if incoming_side == 0:
            trade.resting_order_id = sells[sell_index].order_id
        else:
            trade.resting_order_id = buys[buy_index].order_id

        trades[trade_count[0]] = trade
        trade_count[0] += 1

        buys[buy_index].quantity -= quantity
        sells[sell_index].quantity -= quantity

        if buys[buy_index].quantity == 0:
            _remove_order(buys, buy_count, buy_index)
        if sells[sell_index].quantity == 0:
            _remove_order(sells, sell_count, sell_index)


cdef class CythonMatchCore:
    """A focused matching core with the same price-time rules as ChronosMatch.

    This first Cython milestone covers order submission, matching, open-book
    access, and trade history. Higher-level reporting/cancel APIs remain on the
    Python engine until parity is added for them.
    """

    cdef COrder* _buys
    cdef Py_ssize_t _buy_count
    cdef Py_ssize_t _buy_capacity
    cdef COrder* _sells
    cdef Py_ssize_t _sell_count
    cdef Py_ssize_t _sell_capacity
    cdef CTrade* _trades
    cdef Py_ssize_t _trade_count
    cdef Py_ssize_t _trade_capacity
    cdef object _seen_order_ids
    cdef object _cancelled_order_ids
    cdef object _open_order_objects
    cdef object _price_by_order_id
    cdef object verbose

    def __cinit__(self, verbose=True):
        self._buys = NULL
        self._buy_count = 0
        self._buy_capacity = 0
        self._sells = NULL
        self._sell_count = 0
        self._sell_capacity = 0
        self._trades = NULL
        self._trade_count = 0
        self._trade_capacity = 0
        self._seen_order_ids = set()
        self._cancelled_order_ids = set()
        self._open_order_objects = {}
        self._price_by_order_id = {}
        self.verbose = verbose

    def __dealloc__(self):
        if self._buys != NULL:
            free(self._buys)
        if self._sells != NULL:
            free(self._sells)
        if self._trades != NULL:
            free(self._trades)

    cdef void _reserve_buys(self, Py_ssize_t requested) except *:
        cdef Py_ssize_t capacity
        cdef COrder* new_buffer
        if requested <= self._buy_capacity:
            return
        capacity = self._buy_capacity if self._buy_capacity else 8
        while capacity < requested:
            capacity *= 2
        new_buffer = <COrder*>realloc(
            self._buys,
            <size_t>capacity * sizeof(COrder),
        )
        if new_buffer == NULL:
            raise MemoryError()
        self._buys = new_buffer
        self._buy_capacity = capacity

    cdef void _reserve_sells(self, Py_ssize_t requested) except *:
        cdef Py_ssize_t capacity
        cdef COrder* new_buffer
        if requested <= self._sell_capacity:
            return
        capacity = self._sell_capacity if self._sell_capacity else 8
        while capacity < requested:
            capacity *= 2
        new_buffer = <COrder*>realloc(
            self._sells,
            <size_t>capacity * sizeof(COrder),
        )
        if new_buffer == NULL:
            raise MemoryError()
        self._sells = new_buffer
        self._sell_capacity = capacity

    cdef void _reserve_trades(self, Py_ssize_t requested) except *:
        cdef Py_ssize_t capacity
        cdef CTrade* new_buffer
        if requested <= self._trade_capacity:
            return
        capacity = self._trade_capacity if self._trade_capacity else 8
        while capacity < requested:
            capacity *= 2
        new_buffer = <CTrade*>realloc(
            self._trades,
            <size_t>capacity * sizeof(CTrade),
        )
        if new_buffer == NULL:
            raise MemoryError()
        self._trades = new_buffer
        self._trade_capacity = capacity

    def add_order(self, order):
        cdef object raw_id
        cdef object raw_quantity
        cdef object raw_price
        cdef object side
        cdef double price
        cdef uint64_t order_id
        cdef uint64_t quantity
        cdef uint8_t incoming_side
        cdef Py_ssize_t first_new_trade
        cdef Py_ssize_t opposite_count
        cdef Py_ssize_t i
        cdef COrder* buys_ptr
        cdef COrder* sells_ptr
        cdef CTrade* trades_ptr
        cdef Py_ssize_t* buy_count_ptr
        cdef Py_ssize_t* sell_count_ptr
        cdef Py_ssize_t* trade_count_ptr
        cdef CTrade trade
        cdef object buy_order
        cdef object sell_order

        if not isinstance(order, Order):
            raise TypeError("order must be an Order")

        raw_id = order.order_id
        if type(raw_id) is not int or raw_id <= 0:
            raise ValueError("Order ID must be a positive integer")
        if raw_id > MAX_U64:
            raise ValueError("Order ID must fit in an unsigned 64-bit integer")
        if raw_id in self._seen_order_ids:
            raise ValueError("Order ID has already been used")

        raw_quantity = order.quantity
        if type(raw_quantity) is not int:
            raise ValueError("Quantity must be a whole number")
        if raw_quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        if raw_quantity > MAX_U64:
            raise ValueError("Quantity must fit in an unsigned 64-bit integer")

        raw_price = order.price
        if type(raw_price) not in (int, float):
            raise ValueError("Price must be a number")
        try:
            price = float(raw_price)
        except OverflowError:
            raise ValueError("Price is too large") from None
        if not isfinite(price) or price <= 0:
            raise ValueError("Price must be finite and greater than zero")

        if not isinstance(order.side, str):
            raise ValueError("Side must be BUY or SELL")
        side = order.side.strip().upper()
        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")

        order_id = <uint64_t>raw_id
        quantity = <uint64_t>raw_quantity
        order.side = side
        if self.verbose:
            print(f"New order: {order}")

        if side == "BUY":
            incoming_side = 0
            self._reserve_buys(self._buy_count + 1)
            self._buys[self._buy_count].order_id = order_id
            self._buys[self._buy_count].price = price
            self._buys[self._buy_count].quantity = quantity
            self._buy_count += 1
            opposite_count = self._sell_count
        else:
            incoming_side = 1
            self._reserve_sells(self._sell_count + 1)
            self._sells[self._sell_count].order_id = order_id
            self._sells[self._sell_count].price = price
            self._sells[self._sell_count].quantity = quantity
            self._sell_count += 1
            opposite_count = self._buy_count

        self._seen_order_ids.add(raw_id)
        self._open_order_objects[raw_id] = order
        self._price_by_order_id[raw_id] = raw_price
        self._reserve_trades(self._trade_count + opposite_count)
        first_new_trade = self._trade_count

        buys_ptr = self._buys
        sells_ptr = self._sells
        trades_ptr = self._trades
        buy_count_ptr = &self._buy_count
        sell_count_ptr = &self._sell_count
        trade_count_ptr = &self._trade_count
        with nogil:
            _match_loop(
                buys_ptr,
                buy_count_ptr,
                sells_ptr,
                sell_count_ptr,
                trades_ptr,
                trade_count_ptr,
                incoming_side,
            )

        # Reflect fills in the caller's Python Order objects after leaving the
        # nogil section, and release references for fully filled orders.
        for i in range(first_new_trade, self._trade_count):
            trade = self._trades[i]
            buy_order = self._open_order_objects[trade.buy_order_id]
            sell_order = self._open_order_objects[trade.sell_order_id]
            buy_order.quantity -= trade.quantity
            sell_order.quantity -= trade.quantity
            if buy_order.quantity == 0:
                del self._open_order_objects[trade.buy_order_id]
            if sell_order.quantity == 0:
                del self._open_order_objects[trade.sell_order_id]

            if self.verbose:
                print(
                    f"MATCHED: {trade.quantity} units at "
                    f"price {self._price_by_order_id[trade.resting_order_id]}"
                )

    def cancel_order(self, order_id):
        """Cancel an open order, preserving the Python engine's behavior."""
        cdef uint64_t target_id
        cdef Py_ssize_t i
        cdef Py_ssize_t j

        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive whole number")
        if order_id > MAX_U64:
            return False

        target_id = <uint64_t>order_id
        for i in range(self._buy_count):
            if self._buys[i].order_id == target_id:
                for j in range(i, self._buy_count - 1):
                    self._buys[j] = self._buys[j + 1]
                self._buy_count -= 1
                self._cancelled_order_ids.add(order_id)
                del self._open_order_objects[order_id]
                return True

        for i in range(self._sell_count):
            if self._sells[i].order_id == target_id:
                for j in range(i, self._sell_count - 1):
                    self._sells[j] = self._sells[j + 1]
                self._sell_count -= 1
                self._cancelled_order_ids.add(order_id)
                del self._open_order_objects[order_id]
                return True

        return False

    def get_order_status(self, order_id):
        """Return OPEN, FILLED, CANCELLED, or UNKNOWN for an order ID."""
        if type(order_id) is not int or order_id <= 0:
            raise ValueError("Order ID must be a positive integer")
        if order_id > MAX_U64:
            return "UNKNOWN"
        if order_id in self._open_order_objects:
            return "OPEN"
        if order_id in self._cancelled_order_ids:
            return "CANCELLED"
        if order_id in self._seen_order_ids:
            return "FILLED"
        return "UNKNOWN"

    def get_top_of_book(self):
        """Return the best bid/ask prices, displayed sizes, and spread."""
        cdef Py_ssize_t best_index
        cdef Py_ssize_t i
        cdef object best_bid = None
        cdef object best_ask = None
        cdef object bid_quantity = 0
        cdef object ask_quantity = 0

        if self._buy_count:
            best_index = _best_buy(self._buys, self._buy_count)
            best_bid = self._buys[best_index].price
            for i in range(self._buy_count):
                if self._buys[i].price == self._buys[best_index].price:
                    bid_quantity += self._buys[i].quantity

        if self._sell_count:
            best_index = _best_sell(self._sells, self._sell_count)
            best_ask = self._sells[best_index].price
            for i in range(self._sell_count):
                if self._sells[i].price == self._sells[best_index].price:
                    ask_quantity += self._sells[i].quantity

        spread = (
            best_ask - best_bid
            if best_bid is not None and best_ask is not None
            else None
        )
        return {
            "best_bid": best_bid,
            "bid_quantity": bid_quantity,
            "best_ask": best_ask,
            "ask_quantity": ask_quantity,
            "spread": spread,
        }

    @property
    def buy_orders(self):
        return [
            self._open_order_objects[self._buys[i].order_id]
            for i in range(self._buy_count)
        ]

    @property
    def sell_orders(self):
        return [
            self._open_order_objects[self._sells[i].order_id]
            for i in range(self._sell_count)
        ]

    @property
    def trades(self):
        cdef Py_ssize_t i
        cdef CTrade trade
        cdef list result = []
        for i in range(self._trade_count):
            trade = self._trades[i]
            result.append({
                "buy_order_id": trade.buy_order_id,
                "sell_order_id": trade.sell_order_id,
                "price": self._price_by_order_id[trade.resting_order_id],
                "quantity": trade.quantity,
            })
        return result

    def pending_quantities(self):
        cdef Py_ssize_t i
        cdef object buy_total = 0
        cdef object sell_total = 0
        for i in range(self._buy_count):
            buy_total += self._buys[i].quantity
        for i in range(self._sell_count):
            sell_total += self._sells[i].quantity
        return {"BUY": buy_total, "SELL": sell_total}

    def total_traded_quantity(self):
        cdef Py_ssize_t i
        cdef object total = 0
        for i in range(self._trade_count):
            total += self._trades[i].quantity
        return total
