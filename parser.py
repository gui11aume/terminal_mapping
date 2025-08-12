"""
Parse gzipped FASTQ reads and extract sequence segments upstream of a viral motif
and before a poly-A stretch, around an adapter anchor sequence.

Algorithm overview:
- For each sequence line in the FASTQ file (and its reverse complement),
  locate an adapter anchor (S2). If found, split the read into prefix/match/suffix.
- Recursively process the suffix to handle multiple anchors per read.
- In the prefix upstream of the anchor, find the last occurrence of the viral motif
  (SIV by default; an HIV alternative is provided but commented out).
- From that viral motif forward, find a poly-A run and emit the sequence between the
  viral motif and the poly-A stretch as a FASTA record. Records are numbered.

Approximate matching is performed using the `seeq` library, with explicit thresholds
for the maximum number of allowed mismatches per motif.
"""

import argparse
import glob
import gzip

import seeq

# Pre-compiled approximate matchers with allowed mismatches.
# Increasing the mismatch threshold makes matching more tolerant but also riskier.
# Thresholds here are selected for practical tolerance to sequencing errors.
HIV_matcher = seeq.compile("CTTGTCTTCGTTGGGAGTGAATTAGCCCTTCCA", 5)
SIV_matcher = seeq.compile("TCTATGTCTTCTTGCACTGTAATAAATCCCTTCCA", 5)
S2_matcher = seeq.compile("AAAAAAAGATCGGAAGAGCACACGTCTGAACTCCAGTCAC", 6)
A_matcher = seeq.compile("AAAAAAAAAAAAAAAAAAAA", 3)


# 1-based counter for FASTA-like output record headers.
LINENO = 1


def reverse_complement(seq):
    """Return the reverse complement of a nucleotide sequence.

    Non-ATCG characters are mapped to "N" to maintain length and signal uncertainty.
    """
    complement_dict = {"A": "T", "T": "A", "C": "G", "G": "C"}
    return "".join([complement_dict.get(x, "N") for x in reversed(seq)])


def process(text, viral_matcher):
    """Process a single read string, extracting segments between viral motif and poly-A.

    Steps:
    1) Locate the adapter anchor (`S2_matcher`). If absent, stop.
    2) Split into `(prefix, match, suffix)` around the first anchor occurrence.
    3) Recursively call `process` on `suffix` to capture additional anchors in the read.
    4) In `prefix`, find the last viral motif occurrence (SIV by default).
    5) From that position forward, find a poly-A run and print the intervening sequence.

    The output is FASTA-like with monotonically increasing `LINENO` headers.
    """
    global LINENO
    # Find the adapter anchor. If not present, nothing to extract.
    anchor = S2_matcher.match(text)
    if anchor is not None:
        # Split read around the anchor: everything before it is the search space for the
        # viral motif; everything after may contain additional anchors to process.
        prefix, _, suffix = anchor.tokenize()
        # Find viral motif occurrences in the upstream region.
        vir = viral_matcher.matchAll(prefix)
        # Process the suffix first to capture additional anchors downstream in this read.
        process(suffix, viral_matcher)
        if vir is None:
            return
        # Use the last viral match (closest to the anchor) as the starting point.
        vir_pos = vir.matchlist[-1][1]
        # From the viral position forward, look for a poly-A run.
        a = A_matcher.match(prefix[vir_pos:])
        if a is None:
            return
        a_pos = a.matchlist[0][0] + vir_pos
        if a_pos > vir_pos:
            # Emit the segment between the viral motif and the poly-A stretch.
            print(f">{LINENO}\n{prefix[vir_pos:a_pos]}")
            LINENO += 1


def main():
    """Command-line entry point.

    Options:
    --virus {HIV,SIV}          Select which viral motif to use (default: HIV).
    inputs                      Path(s) or glob(s) to gzipped FASTQ file(s),
                                e.g. sample.fastq.gz or '*.fastq.gz'.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Extract segments between viral motif and poly-A around an adapter "
            "anchor from gzipped FASTQ."
        ),
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help=("Path(s) or glob pattern(s) to gzipped FASTQ file(s) (e.g. '*.fastq.gz')."),
    )
    parser.add_argument(
        "--virus",
        choices=["HIV", "SIV"],
        default="HIV",
        help="Viral motif to use for matching (default: HIV)",
    )
    args = parser.parse_args()

    viral_matcher = HIV_matcher if args.virus == "HIV" else SIV_matcher

    # Expand inputs as globs and concatenate files in the given order
    matched_files = []
    for pattern in args.inputs:
        expanded = sorted(glob.glob(pattern))
        if expanded:
            matched_files.extend(expanded)
        else:
            # If the pattern didn't match, treat it as a literal path
            matched_files.append(pattern)

    if not matched_files:
        parser.error("No input files matched the provided patterns/paths.")

    for path in matched_files:
        with gzip.open(path, "rb") as f:
            # FASTQ format: for each 4-line record, line 1 (0-based index 1) is the sequence.
            # Process both the sequence and its reverse complement to capture motif orientation.
            for lineno, line in enumerate(f):
                if lineno % 4 == 1:
                    seq = line.decode("ascii").rstrip()
                    process(seq, viral_matcher)
                    process(reverse_complement(seq), viral_matcher)


if __name__ == "__main__":
    main()
