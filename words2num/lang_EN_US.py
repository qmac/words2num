from __future__ import division, unicode_literals, print_function
import re
from .core import NumberParseException, placevalue
from decimal import Decimal, localcontext


VOCAB = {
    'zero': (0, 'Z'),
    'a': (None, 'A'),
    'one': (1, 'D'),
    'two': (2, 'D'),
    'three': (3, 'D'),
    'four': (4, 'D'),
    'five': (5, 'D'),
    'six': (6, 'D'),
    'seven': (7, 'D'),
    'eight': (8, 'D'),
    'nine': (9, 'D'),
    'ten': (10, 'M'),
    'eleven': (11, 'M'),
    'twelve': (12, 'M'),
    'thirteen': (13, 'M'),
    'fourteen': (14, 'M'),
    'fifteen': (15, 'M'),
    'sixteen': (16, 'M'),
    'seventeen': (17, 'M'),
    'eighteen': (18, 'M'),
    'nineteen': (19, 'M'),
    'twenty': (20, 'T'),
    'thirty': (30, 'T'),
    'forty': (40, 'T'),
    'fifty': (50, 'T'),
    'sixty': (60, 'T'),
    'seventy': (70, 'T'),
    'eighty': (80, 'T'),
    'ninety': (90, 'T'),
    'hundred': (100, 'H'),
    'thousand': (10**3, 'X'),
    'million': (10**6, 'X'),
    'billion': (10**9, 'X'),
    'trillion': (10**12, 'X'),
    'quadrillion': (10**15, 'X'),
    'quintillion': (10**18, 'X'),
    'sextillion': (10**21, 'X'),
    'septillion': (10**24, 'X'),
    'octillion': (10**27, 'X'),
    'nonillion': (10**30, 'X'),
    'decillion': (10**33, 'X'),
    'undecillion': (10**36, 'X'),
    'duodecillion': (10**39, 'X'),
    'tredecillion': (10**42, 'X'),
    'quattuordecillion': (10**45, 'X'),
    'quindecillion': (10**48, 'X'),
    'sexdecillion': (10**51, 'X'),
    'septendecillion': (10**54, 'X'),
    'octodecillion': (10**57, 'X'),
    'novemdecillion': (10**60, 'X'),
    'vigintillion': (10**63, 'X'),
    'centillion': (10**303, 'X'),
    'point': (None, 'P'),
}


class FST:
    def __init__(self):
        def f_zero(self, n):
            assert n == 0
            self.value = n
            self.place = 0

        def f_add(self, n):
            self.value += n
            self.place = 0

        def f_mul(self, n):
            output = self.value * n
            self.value = 0
            return output

        def f_mul_hundred(self, n):
            assert n == 100
            self.value *= n
            self.place = 0

        def f_ret(self, _):
            return self.value

        def f_none(self, _):
            pass

        def f_hundred(self, n):
            assert n == 100
            self.value = n
            self.place = 0

        def f_begin_decimal(self, _):
            self.place = -1

        def f_add_decimal(self, n):
            if self.place >= 0:
                raise NumberParseException("Invalid sequence")
            self.value += n * Decimal(10) ** Decimal(self.place)
            self.place -= 1

        self.value = 0
        self.place = 0
        self.state = 'S'
        # self.states = {'S', 'D', 'T', 'M', 'H', 'X', 'Z', 'A', 'F'}
        self.edges = {
            ('S', 'Z'): f_zero,    # 0
            ('S', 'D'): f_add,     # 9
            ('S', 'T'): f_add,     # 90
            ('S', 'M'): f_add,     # 19
            ('S', 'A'): f_none,    # 100
            ('D', 'H'): f_mul_hundred,     # 900
            ('D', 'X'): f_mul,     # 9000
            ('D', 'D'): f_add_decimal,     # 9.99
            ('D', 'Z'): f_add_decimal,     # 9.09
            ('D', 'P'): f_begin_decimal,   # 9.99
            ('D', 'F'): f_ret,     # 9
            ('T', 'D'): f_add,     # 99
            ('T', 'H'): f_mul_hundred,
            ('T', 'X'): f_mul,     # 90000
            ('T', 'P'): f_begin_decimal,   # 90.99
            ('T', 'F'): f_ret,     # 90
            ('M', 'H'): f_mul_hundred,
            ('M', 'X'): f_mul,     # 19000
            ('M', 'P'): f_begin_decimal,   # 19.99
            ('M', 'F'): f_ret,     # 19
            ('H', 'D'): f_add,     # 909
            ('H', 'T'): f_add,     # 990
            ('H', 'M'): f_add,     # 919
            ('H', 'X'): f_mul,     # 900000
            ('H', 'P'): f_begin_decimal,   # 900.99
            ('H', 'F'): f_ret,     # 900
            ('X', 'D'): f_add,     # 9009
            ('X', 'T'): f_add,     # 9090
            ('X', 'M'): f_add,     # 9019
            ('X', 'A'): f_add,     # 9100
            ('X', 'P'): f_begin_decimal,   # 9000.99
            ('X', 'F'): f_ret,     # 9000
            ('Z', 'D'): f_add_decimal,     # 9.09
            ('Z', 'P'): f_begin_decimal,   # 9.09
            ('Z', 'F'): f_ret,     # 0
            ('A', 'H'): f_hundred,         # 100
            ('P', 'D'): f_add_decimal,     # 9.99
            ('P', 'Z'): f_add_decimal       # 9.09
        }

    def transition(self, token):
        value, label = token
        try:
            edge_fn = self.edges[(self.state, label)]
        except KeyError:
            raise NumberParseException("Invalid number state from "
                                       "{0} to {1}".format(self.state, label))
        self.state = label
        return edge_fn(self, value)


def tokenize(text):
    tokens = re.split(r"[\s,\-]+(?:and)?", text.lower())
    try:
        # don't use generator here because we want to raise the exception
        # here now if the word is not found in vocabulary (easier debug)
        parsed_tokens = [VOCAB[token] for token in tokens if token]
    except KeyError as e:
        raise ValueError("Invalid number word: "
                         "{0} in {1}".format(e, text))
    return parsed_tokens


def compute(tokens):
    """Compute the value of given tokens.
    TODO: memoize placevalue checking at every step
    """
    fst = FST()
    outputs = []
    last_placevalue = None
    for token in tokens:
        out = fst.transition(token)
        # DEBUG
        # print("tok({0}) out({1}) val({2})".format(token, out, fst.value))
        if out:
            outputs.append(out)
            if last_placevalue and last_placevalue <= placevalue(outputs[-1]):
                raise NumberParseException("Invalid sequence "
                                           "{0}".format(outputs))
            last_placevalue = placevalue(outputs[-1])
    outputs.append(fst.transition((None, 'F')))
    if last_placevalue and last_placevalue <= placevalue(outputs[-1]):
        raise NumberParseException("Invalid sequence "
                                   "{0}".format(outputs))
    # DEBUG
    # print("-> {0}".format(outputs))
    total = sum(outputs)
    total = float(total) if isinstance(total, Decimal) else total
    return total


def evaluate(text):
    tokens = tokenize(text)
    if not tokens:
        raise ValueError("No valid tokens in {0}".format(text))
    with localcontext() as ctx:
        # Locally sets decimal precision to 15 for all computations
        ctx.prec = 15
        output = compute(tokens)
    return output
