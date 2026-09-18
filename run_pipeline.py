"""Run from any directory: python run_pipeline.py [--stage quality|business|models|report|all]."""
from pathlib import Path
import argparse
from src.pipeline import quality,business,data_science,executive_report,run

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['quality','business','models','report','all'],default='all')
    args=parser.parse_args()
    {'quality':quality,'business':business,'models':data_science,'report':executive_report,'all':run}[args.stage](Path(__file__).resolve().parent)
