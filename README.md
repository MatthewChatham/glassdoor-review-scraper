# Disclaimer
This scraper is provided as a public service because Glasdoor doesn't have an API for reviews. Glassdoor TOS prohibit scraping and I make no representation that your account won't be banned if you use this program. Furthermore, should I be contacted by Glassdoor with a request to remove this repo, I will do so immediately.

# Introduction
Have you ever wanted to scrape reviews from Glassdoor, but bemoaned the site's lack of a public API for reviews? Worry no more! This script will go through pages and pages of reviews and scrape review data into a tidy CSV file. Pass it a company page and set a limit to scrape the 25 most conveniently available reviews, or control options like the number of reviews to scrape and the max/min review publication date.

It takes about 1.5 seconds per review to scrape. So it will take about 25 minutes to scrape 1,000 reviews, or a little over 4 hours to scrape 10,000 reviews. This script requires patience. 😁

# Installation
First, make sure that you're using Python 3.

1. Clone or download this repository.
2. Run `pip install -r requirements.txt` inside this repo. Consider doing this inside of a Python virtual environment.
3. Install [Chromedriver](http://chromedriver.chromium.org/) in the working directory.
4. Create a `secret.json` file containing the keys `username` and `password` with your Glassdoor login information, or pass those arguments at the command line. Note that the second method is less secure, but in any case you should consider creating a dummy Glassdoor account.

# Usage
```
usage: main.py [-h] [-u URL] [-f FILE] [--headless] [--username USERNAME]
               [-p PASSWORD] [-c CREDENTIALS] [-l LIMIT] [--start_from_url] 
               [--max_date MAX_DATE] [--min_date MIN_DATE]

optional arguments:
  -h, --help                                  show this help message and exit
  -u URL, --url URL                           URL of the company's Glassdoor landing page.
  -f FILE, --file FILE                        Output file.
  --headless                                  Run Chrome in headless mode.
  --username USERNAME                         Email address used to sign in to GD.
  -p PASSWORD, --password PASSWORD            Password to sign in to GD.
  -c CREDENTIALS, --credentials CREDENTIALS   Credentials file
  -l LIMIT, --limit LIMIT                     Max reviews to scrape
  --start_from_url                            Start scraping from the passed URL.
  
  --max_date MAX_DATE                         Latest review date to scrape. Only use this option
                                              with --start_from_url. You also must have sorted
                                              Glassdoor reviews ASCENDING by date.
                                              
  --min_date MIN_DATE                         Earliest review date to scrape. Only use this option
                                              with --start_from_url. You also must have sorted
                                              Glassdoor reviews DESCENDING by date.
```

Run the script as follows, taking Wells Fargo as an example. You can pass `--headless` to prevent the Chrome window from being visible, and the `--limit` option will limit how many reviews get scraped. The`-f` option specifies the output file, which defaults to `glassdoor_reviews.csv`.  

### Example 1
Suppose you want to get the top 1,000 most popular reviews for Wells Fargo. Run the command as follows:

`python main.py --headless --url "https://www.glassdoor.com/Overview/Working-at-Wells-Fargo-EI_IE8876.11,22.htm" --limit 1000 -f wells_fargo_reviews.csv`

**Note**: To be safe, always surround the URL with quotes. This only matters in the presence of a query string.

### Example 2: Date Filtering
If you want to scrape all reviews in a date range, sort reviews on Glassdoor ascending/descending by date, find the page with the appropriate starting date, set the max/min date to the other end of your desired time range, and set limit to 99999.

Suppose you want to scrape all reviews from McDonald's that were posted in 2010:

1. Navigate to McDonald's Glassdoor page and sort reviews ascending by date.
2. Find the first page with a review from 2010, which happens to be [page 13](https://www.glassdoor.com/Reviews/McDonald-s-Reviews-E432_P13.htm?sort.sortType=RD&sort.ascending=true).
3. Send the command to the script:
`python main.py --headless --start_from_url --limit 9999 --max_date 2010-12-31 --url "https://www.glassdoor.com/Reviews/McDonald-s-Reviews-E432_P13.htm?sort.sortType=RD&sort.ascending=true"`

If there's demand for it, we can automate this process to provide a simple interface for filtering by date.
