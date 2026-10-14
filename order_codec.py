from struct import Struct

# Little-endian layout:
# Q = order ID: unsigned 8-byte integer
# B = side: unsigned 1-byte integer
# d = price: 8-byte floating-point number
# Q = quantity: unsigned 8-byte integer
ORDER_STRUCT = Struct("<QBdQ")
ORDER_SIZE = ORDER_STRUCT.size

BUY = 1
SELL = 2