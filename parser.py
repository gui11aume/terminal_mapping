import gzip
import sys

import seeq

HIV_matcher = seeq.compile("CTTGTCTTCGTTGGGAGTGAATTAGCCCTTCCA", 5)
SIV_matcher = seeq.compile("TCTATGTCTTCTTGCACTGTAATAAATCCCTTCCA", 5)
S2_matcher = seeq.compile("AAAAAAAGATCGGAAGAGCACACGTCTGAACTCCAGTCAC", 6)
A_matcher = seeq.compile("AAAAAAAAAAAAAAAAAAAA", 3)


LINENO = 1
BARCODE = "AGCAAT"


def reverse_complement(seq):
    complement_dict = {"A": "T", "T": "A", "C": "G", "G": "C"}
    return "".join([complement_dict.get(x, "N") for x in reversed(seq)])


def process(text):
    global LINENO
    anchor = S2_matcher.match(text)
    if anchor is not None:
        prefix, _, suffix = anchor.tokenize()
        vir = SIV_matcher.matchAll(prefix)
        # vir = HIV_matcher.matchAll(prefix)
        process(suffix)
        if vir is None:
            return
        vir_pos = vir.matchlist[-1][1]
        a = A_matcher.match(prefix[vir_pos:])
        if a is None:
            return
        a_pos = a.matchlist[0][0] + vir_pos
        bcd_pos = anchor.matchlist[0][1]
        if a_pos > vir_pos:
            if text[bcd_pos : bcd_pos + 6] == BARCODE:
                print(f">{LINENO}-{text[bcd_pos:bcd_pos+6]}\n{prefix[vir_pos:a_pos]}")
                LINENO += 1


with gzip.open(sys.argv[1]) as f:
    for lineno, line in enumerate(f):
        if lineno % 4 == 1:
            process(line.decode("ascii").rstrip())
            process(reverse_complement(line.decode("ascii").rstrip()))
