"""
main.py
----------
Matthew Chatham, Hamid Vakilzadeh
updated Aug 12, 2022

Given a company's landing page on glassdoor and an output filename, scrape the
following information about each employee review:

Review date
Employee position
Employee location
Employee status (current/former)
Review title
Number of helpful votes
Pros text
Cons text
Advice to mgmt text
Ratings for each of the categories
Overall rating
"""

import datetime as dt
import json
import logging.config
import re
import time
from argparse import ArgumentParser
from pathlib import Path
from urllib import parse

import numpy as np
import pandas as pd
from selenium import webdriver as wd
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.service import Service
from schema import SCHEMA
from webdriver_manager.chrome import ChromeDriverManager

start = time.time()

DEFAULT_URL = ('https://www.glassdoor.com/Overview/Working-at-'
               'Premise-Data-Corporation-EI_IE952471.11,35.htm')

# Download chromedriver from : https://chromedriver.chromium.org/downloads
Path("Outputs").mkdir(parents=True, exist_ok=True)

parser = ArgumentParser()
parser.add_argument('-u', '--url',
                    help='URL of the company\'s glassdoor landing page.',
                    default=DEFAULT_URL)
parser.add_argument('-f', '--file', default='glassdoor_ratings.csv',
                    help='Output file.')
parser.add_argument('--headless', action='store_true',
                    help='Run Chrome in headless mode.')
parser.add_argument('--username', help='Email address used to sign in to GD.')
parser.add_argument('-p', '--password', help='Password to sign in to GD.')
parser.add_argument('-c', '--credentials', help='Credentials file')
parser.add_argument('-l', '--limit', default=25,
                    action='store', type=int, help='Max reviews to scrape')
parser.add_argument('--start_from_url', action='store_true',
                    help='Start scraping from the passed URL.')
parser.add_argument(
    '--max_date', help='Latest review date to scrape.\
    Only use this option with --start_from_url.\
    You also must have sorted glassdoor reviews ASCENDING by date.',
    type=lambda s: dt.datetime.strptime(s, "%Y-%m-%d"))
parser.add_argument(
    '--min_date', help='Earliest review date to scrape.\
    Only use this option with --start_from_url.\
    You also must have sorted glassdoor reviews DESCENDING by date.',
    type=lambda s: dt.datetime.strptime(s, "%Y-%m-%d"))
args = parser.parse_args()

if not args.start_from_url and (args.max_date or args.min_date):
    raise Exception(
        'Invalid argument combination:\
        No starting url passed, but max/min date specified.'
    )
elif args.max_date and args.min_date:
    raise Exception(
        'Invalid argument combination:\
        Both min_date and max_date specified.'
    )

if args.credentials:
    with open(args.credentials) as f:
        d = json.loads(f.read())
        args.username = d['username']
        args.password = d['password']
else:
    try:
        with open('secret.json') as f:
            d = json.loads(f.read())
            args.username = d['username']
            args.password = d['password']
    except FileNotFoundError:
        msg = 'Please provide glassdoor credentials.\
        Credentials can be provided as a secret.json file in the working\
        directory, or passed at the command line using the --username and\
        --password flags.'
        raise Exception(msg)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(lineno)d\
    :%(filename)s(%(process)d) - %(message)s')
ch.setFormatter(formatter)

logging.getLogger('selenium').setLevel(logging.CRITICAL)


def scrape(field, review, author):
    def scrape_date(review):
        date = review.find_element(By.CLASS_NAME,
                                   'common__EiReviewDetailsStyle__newUiJobLine').text.split('-')[0]
        res = date
        return res

    def scrape_emp_title(review):
        if 'Anonymous Employee' not in review.text:
            try:
                res = author.find_element(By.CLASS_NAME,
                                          'common__EiReviewDetailsStyle__newGrey').text.split('-')[1]
            except Exception:
                logger.warning('Failed to scrape employee_title')
                res = "N/A"
        else:
            res = "Anonymous"
        return res

    def scrape_location(review):
        if ' in ' in author.text:
            try:
                res = author.text.split(' in ')[1]
            except Exception:
                logger.warning('Failed to scrape employee_location')
                res = np.nan
        else:
            res = "N/A"
        return res

    def scrape_status(review):
        try:
            status_box = review.find_element(By.CLASS_NAME, 'pt-xsm')
            res = status_box.text
        except Exception:
            logger.warning('Failed to scrape employee_status')
            res = "N/A"
        return res

    def scrape_rev_title(review):
        return review.find_element(By.CLASS_NAME, 'reviewLink').text.strip('"')

    def scrape_helpful(review):
        helpful_votes = review.find_element(By.CLASS_NAME, 'gdReview')
        helpful_votes = helpful_votes.find_element(By.CLASS_NAME,
                                                   "common__EiReviewDetailsStyle__socialHelpfulcontainer")
        res = re.sub('[^0-9]', '', helpful_votes.text)
        if len(res) != 0:
            return int(res)
        else:
            return 0

    def expand_show_more(section):
        try:
            more_link = section.find_element(By.CLASS_NAME, 'v2__EIReviewDetailsV2__continueReading')
            more_link.click()
        except Exception:
            pass

    def scrape_pros(review):
        try:
            pros = review.find_element(By.CLASS_NAME, 'gdReview')
            expand_show_more(pros)
            pros = pros.find_element(By.CSS_SELECTOR, "*[data-test='pros']")
            res = pros.text
        except Exception:
            res = np.nan
        return res

    def scrape_cons(review):
        try:
            cons = review.find_element(By.CLASS_NAME, 'gdReview')
            expand_show_more(cons)
            cons = cons.find_element(By.CSS_SELECTOR, "*[data-test='cons']")
            res = cons.text
        except Exception:
            res = np.nan
        return res

    def scrape_advice(review):
        try:
            advice = review.find_element(By.CLASS_NAME, 'gdReview')
            expand_show_more(advice)
            advice = advice.find_element(By.CSS_SELECTOR, "*[data-test='advice-management']")
            res = advice.text
        except Exception:
            res = np.nan
        return res

    def scrape_overall_rating(review):
        try:
            overall_rating = review.find_element(By.CLASS_NAME, "ratingNumber")
            res = int(overall_rating.text[0])
        except Exception:
            res = np.nan
        return res

    def scrape_sub_rating(i):
        convert_rating_to_number = {'css-152xdkl': 1,
                                    'css-19o85uz': 2,
                                    'css-1ihykkv': 3,
                                    'css-1c07csa': 4,
                                    'css-1dc0bv4': 5,
                                    'css-xd4dom': 1,
                                    'css-18v8tui': 2,
                                    'css-vl2edp': 3,
                                    'css-1nuumx7': 4,
                                    'css-s88v13': 5}

        try:
            sub_rating_anchor = review.find_element(By.TAG_NAME, 'aside')
            # ActionChains(browser).move_to_element(sub_rating_anchor)
            sub_ratings = sub_rating_anchor.find_element(By.TAG_NAME, 'ul').find_elements(By.TAG_NAME, 'li')
            sub_ratings_res = {}
            # sub_rating_anchor.click()
            for line in sub_ratings:
                stars = line.find_element(By.CSS_SELECTOR, "*[font-size='sm']")
                res = convert_rating_to_number[stars.get_attribute('class').split()[0]]
                rating_name = line.find_element(By.CSS_SELECTOR, 'div:nth-child(1)').text
                sub_ratings_res[rating_name] = res
        except Exception:
            logger.warning('No subratings')
            sub_ratings_res = {}
        return sub_ratings_res

    def scrape_recommends(i):
        convert_shapes_to_text = {'css-1kiw93k-svg': 'No',  # cross
                                  'css-hcqxoa-svg': 'Yes',  # check mark
                                  'css-10xv9lv-svg': '',  # empty circle
                                  'css-1h93d4v-svg': 'Neutral'}  # line
        status_box = review.find_element(By.CLASS_NAME, 'recommends')
        recommendation_items = status_box.text.split('\n')
        circles = status_box.find_elements(By.TAG_NAME, 'svg')
        shapes = [convert_shapes_to_text[i.get_attribute('class').split()[1]] for i in circles]
        res = dict(zip(recommendation_items, shapes))
        return res

    funcs = [
        scrape_date,
        scrape_emp_title,
        scrape_location,
        scrape_status,
        scrape_rev_title,
        scrape_helpful,
        scrape_pros,
        scrape_cons,
        scrape_advice,
        scrape_overall_rating,
        scrape_sub_rating,
        scrape_recommends
    ]

    fdict = dict((s, f) for (s, f) in zip(SCHEMA, funcs))

    return fdict[field](review)


def extract_from_page():
    def is_featured(review):
        try:
            review.find_element(By.CLASS_NAME, 'featuredFlag')
            return True
        except NoSuchElementException:
            return False

    def extract_review(review):
        try:
            author = review.find_element(By.CLASS_NAME, 'common__EiReviewDetailsStyle__newUiJobLine')
        except NoSuchElementException:
            return None  # Account for reviews that have been blocked
        res = {}
        # import pdb;pdb.set_trace()
        for field in SCHEMA:
            res[field] = scrape(field, review, author)

        assert set(res.keys()) == set(SCHEMA)
        return res

    logger.info(f'Extracting reviews from page {page[0]}')

    res = pd.DataFrame([], columns=SCHEMA)

    reviews = browser.find_elements(By.CLASS_NAME, 'empReview')
    logger.info(f'Found {len(reviews)} reviews on page {page[0]}')

    # refresh page if failed to load properly, else terminate the search
    if len(reviews) < 1:
        browser.refresh()
        time.sleep(5)
        reviews = browser.find_elements(By.CLASS_NAME, 'empReview')
        logger.info(f'Found {len(reviews)} reviews on page {page[0]}')
        if len(reviews) < 1:
            valid_page[0] = False  # make sure page is populated

    for review in reviews:
        if not is_featured(review):
            data = extract_review(review)
            if data is not None:
                logger.info(f'Scraped data for "{data["review_title"]}" ({data["date"]})')
                res.loc[idx[0]] = data
            else:
                logger.info('Discarding a blocked review')
        else:
            logger.info('Discarding a featured review')
        idx[0] = idx[0] + 1

    if args.max_date and \
            (pd.to_datetime(res['date']).max() > args.max_date) or \
            args.min_date and \
            (pd.to_datetime(res['date']).min() < args.min_date):
        logger.info('Date limit reached, ending process')
        date_limit_reached[0] = True

    return res


def more_pages():
    try:
        current = browser.find_element(By.CLASS_NAME, 'selected')
        pages = browser.find_element(By.CLASS_NAME, 'pageContainer').text.split()
        if int(pages[-1]) != int(current.text):
            return True
        else:
            return False
    except NoSuchElementException:
        return False


def go_to_next_page():
    logger.info(f'Going to page {page[0] + 1}')
    next_ = browser.find_element(By.CLASS_NAME, 'nextButton')
    ActionChains(browser).click(next_).perform()
    time.sleep(5)  # wait for ads to load
    page[0] = page[0] + 1


def no_reviews():
    return False
    # TODO: Find a company with no reviews to test on


def navigate_to_reviews():
    logger.info('Navigating to company reviews')

    browser.get(args.url)
    time.sleep(1)

    if no_reviews():
        logger.info('No reviews to scrape. Bailing!')
        return False

    reviews_cell = browser.find_element(By.XPATH,
                                        '//a[@data-label="Reviews"]')
    reviews_path = reviews_cell.get_attribute('href')

    # reviews_path = driver.current_url.replace('Overview','Reviews')
    browser.get(reviews_path)
    time.sleep(1)
    return True


def sign_in_username():
    logger.info(f'Signing in to {args.username}')

    url = 'https://www.glassdoor.com/profile/login_input.htm'
    browser.get(url)

    email_field = browser.find_element(By.NAME, 'username')
    submit_btn = browser.find_element(By.NAME, 'submit')

    email_field.send_keys(args.username)
    # password_field.send_keys(args.password)
    submit_btn.click()

    time.sleep(3)


def sign_in_password():
    logger.info(f'trying password for {args.username}')

    password_field = browser.find_element(By.NAME, 'password')
    submit_btn = browser.find_element(By.NAME, 'submit')

    password_field.send_keys(args.password)
    submit_btn.click()

    time.sleep(3)
    browser.get(args.url)


def get_browser():
    logger.info('Configuring browser')
    chrome_options = wd.ChromeOptions()
    if args.headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('log-level=3')
    service = Service(ChromeDriverManager().install())
    browser = wd.Chrome(service=service, options=chrome_options)
    return browser


def get_current_page():
    logger.info('Getting current page number')
    current = browser.find_element(By.CLASS_NAME, "selected")
    return int(current.text)


def verify_date_sorting():
    logger.info('Date limit specified, verifying date sorting')
    ascending = parse.parse_qs(
        args.url)['sort.ascending'] == ['true']

    if args.min_date and ascending:
        raise Exception(
            'min_date required reviews to be sorted DESCENDING by date.')
    elif args.max_date and not ascending:
        raise Exception(
            'max_date requires reviews to be sorted ASCENDING by date.')


browser = get_browser()
page = [1]
idx = [0]
date_limit_reached = [False]
valid_page = [True]


def main():
    logger.info(f'Scraping up to {args.limit} reviews.')

    res = pd.DataFrame([], columns=SCHEMA)

    sign_in_username()
    sign_in_password()

    if not args.start_from_url:
        reviews_exist = navigate_to_reviews()
        if not reviews_exist:
            return
    elif args.max_date or args.min_date:
        verify_date_sorting()
        browser.get(args.url)
        page[0] = get_current_page()
        logger.info(f'Starting from page {page[0]}.')
        time.sleep(1)
    else:
        browser.get(args.url)
        page[0] = get_current_page()
        logger.info(f'Starting from page {page[0]}.')
        time.sleep(1)

    reviews_df = extract_from_page()
    res = res.append(reviews_df)

    # import pdb;pdb.set_trace()

    while more_pages() and \
            len(res) < args.limit and \
            not date_limit_reached[0] and \
            valid_page[0]:
        go_to_next_page()
        try:
            reviews_df = extract_from_page()
            res = res.append(reviews_df)
        except NoSuchElementException:
            break

    logger.info(f'Writing {len(res)} reviews to file {args.file}')
    res.to_csv(f'Outputs/{args.file}', index=False, encoding='utf-8')

    end = time.time()
    logger.info(f'Finished in {end - start} seconds')


if __name__ == '__main__':
    main()
    browser.close()
