# Glassdoor Review Scraper
This script will scrape reviews for a given company.

You can install it by cloning or downloading the repo and running `pip install -r requirements.txt` inside the directory. You'll also need to create a `secret.json` file containing the keys `username` and `password` with your Glassdoor login information, or pass those arguments at the command line.

Run the script as follows, taking Wells Fargo as an example. You can pass `--headless` to prevent the Chrome window from being visible, and the `--limit` option will limit how many reviews get scraped. The`-f` option specifies the output file, which defaults to `glassdoor_reviews.csv`.  

`python main.py --headless -c secret.json --url https://www.glassdoor.com/Overview/Working-at-Wells-Fargo-EI_IE8876.11,22.htm --limit 1000 -f wells_fargo_reviews.csv`

Based on some simple benchmarking, it appears that it takes about 1.5 seconds per review that you want to scrape. So it will take about 25 minutes to scrape 1,000 reviews, or a little over 4 hours to scrape 10,000 reviews.
