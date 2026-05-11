import sys
import os

sys.path.insert(0, os.path.abspath("."))
from utils.command_parser import parse_qdone

print(parse_qdone("!qdone binary search 2 dp 3"))
