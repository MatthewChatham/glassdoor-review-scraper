'''
multiscrape.py
----------
Jeremiah Haremza
May 9, 2018

Given a tuple of items use main.py to scrape reviews from multiple companies on Glassdoor.
Use 1 tuple per company.
List of tuples to itterate over for each command execution is named pages
each tuple in the list takes the format (url, limit, output_file_name)
each Item in the tuple is a string, hence it will need to be enclosed in quotes.
'''

import os

pages = [
            ('"https://www.glassdoor.com/Overview/Working-at-Two-Sigma-EI_IE241045.11,20.htm"', "62", "two_sigma"),
            ('"https://www.glassdoor.com/Overview/Working-at-Jane-Street-EI_IE255549.11,22.htm"', "68", "jane_street"),
            ('"https://www.glassdoor.com/Overview/Working-at-Citadel-EI_IE14937.11,18.htm"', "258", "citadel"),
            ('"https://www.glassdoor.com/Overview/Working-at-Hudson-River-Trading-EI_IE470937.11,31.htm"', "9", "hrt"),
            ('"https://www.glassdoor.com/Overview/Working-at-D-E-Shaw-and-Co-Investment-Firm-EI_IE29290.11,42.htm"', "110", "deshaw"),
            ('"https://www.glassdoor.com/Overview/Working-at-AKUNA-CAPITAL-EI_IE608116.11,24.htm"', "85", "akuna"),
            ('"https://www.glassdoor.com/Overview/Working-at-Optiver-EI_IE243355.11,18.htm"', "195", "optiver"),
            ('"https://www.glassdoor.com/Overview/Working-at-Susquehanna-International-Group-SIG-EI_IE24446.11,46.htm"', "420", "sig"),
            ('"https://www.glassdoor.com/Overview/Working-at-Millennium-EI_IE850344.11,21.htm"', "82", "millenium"),
            ('"https://www.glassdoor.com/Overview/Working-at-Quantlab-EI_IE262109.11,19.htm"', "19", "quantlab"),
            ('"https://www.glassdoor.com/Overview/Working-at-IMC-Trading-EI_IE278100.11,22.htm"', "90", "imc"),
            ('"https://www.glassdoor.com/Overview/Working-at-Old-Mission-Capital-EI_IE484782.11,30.htm"', "12", "oldmissioncapital"),
            ('"https://www.glassdoor.com/Overview/Working-at-TransMarket-Group-EI_IE233421.11,28.htm"', "42", "tmg"),
            ('"https://www.glassdoor.com/Overview/Working-at-Chicago-Trading-Company-EI_IE257151.11,34.htm"', "55", "ctc"),
            ('"https://www.glassdoor.com/Overview/Working-at-Five-Rings-Capital-EI_IE375785.11,29.htm"', "5", "fiverings")
        ]

for page in pages:
    command = "python main.py --headless --url " + page[0] + " --limit " + page[1] + " -f " + page[2] + ".csv"
    os.system(command)
