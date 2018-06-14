'''
main.py
----------
Matthew Chatham
June 6, 2018

Given a company's landing page on Glassdoor and an output filename, scrape the
following information about each employee review:

Review date
Employee position
Employee location
Employee status (current/former)
Review title
Employee years at company
Number of helpful votes
Pros text
Cons text
Advice to mgmttext
Ratings for each of 5 categories
Overall rating
'''

import time
import pandas as pd
from argparse import ArgumentParser
import logging
import logging.config
from selenium import webdriver as wd
import selenium
import numpy as np
from schema import SCHEMA
import json
import timeit

start = time.time()

DEFAULT_URL = ('https://www.glassdoor.com/Overview/Working-at-'
               'Premise-Data-Corporation-EI_IE952471.11,35.htm')

parser = ArgumentParser()
parser.add_argument('-u', '--url',
                    help='URL of the company\'s Glassdoor landing page.',
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
args = parser.parse_args()
if args.credentials:
    with open(args.credentials) as f:
        d = json.loads(f.read())
        args.username = d['username']
        args.password = d['password']


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
logging.getLogger('selenium').setLevel(logging.CRITICAL)


def scrape(field, review, author):

    def scrape_date(review):
        return review.find_element_by_tag_name(
            'time').get_attribute('datetime')

    def scrape_emp_title(review):
        if 'Anonymous Employee' not in review.text:
            try:
                res = author.find_element_by_class_name(
                    'authorJobTitle').text.split('-')[1]
            except Exception:
                logger.warning('Failed to scrape employee_title')
                res = np.nan
        else:
            res = np.nan
        return res

    def scrape_location(review):
        if 'in' in review.text:
            try:
                res = author.find_element_by_class_name(
                    'authorLocation').text
            except Exception:
                res = np.nan
        else:
            res = np.nan
        return res

    def scrape_status(review):
        try:
            res = author.text.split('-')[0]
        except Exception:
            logger.warning('Failed to scrape employee_status')
            res = np.nan
        return res

    def scrape_rev_title(review):
        return review.find_element_by_class_name('summary').text.strip('"')

    def scrape_years(review):
        first_par = review.find_element_by_class_name(
            'reviewBodyCell').find_element_by_tag_name('p')
        if '(' in first_par.text:
            res = first_par.text[first_par.text.find('(') + 1:-1]
        else:
            res = np.nan
        return res

    def scrape_helpful(review):
        try:
            helpful = review.find_element_by_class_name('helpfulCount')
            res = helpful[helpful.find('(') + 1: -1]
        except Exception:
            res = 0
        return res

    def scrape_pros(review):
        try:
            res = review.find_element_by_class_name('pros').text
        except Exception:
            res = np.nan
        return res

    def scrape_cons(review):
        try:
            res = review.find_element_by_class_name('cons').text
        except Exception:
            res = np.nan
        return res

    def scrape_advice(review):
        try:
            res = review.find_element_by_class_name('adviceMgmt').text
        except Exception:
            res = np.nan
        return res

    def scrape_overall_rating(review):
        try:
            ratings = review.find_element_by_class_name('gdStars')
            overall = ratings.find_element_by_class_name(
                'rating').find_element_by_class_name('value-title')
            res = overall.get_attribute('title')
        except Exception:
            res = np.nan
        return res

    def _scrape_subrating(i):
        try:
            ratings = review.find_element_by_class_name('gdStars')
            subratings = ratings.find_element_by_class_name(
                'subRatings').find_element_by_tag_name('ul')
            this_one = subratings.find_elements_by_tag_name('li')[i]
            res = this_one.find_element_by_class_name(
                'gdBars').get_attribute('title')
        except Exception:
            res = np.nan
        return res

    def scrape_work_life_balance(review):
        return _scrape_subrating(0)

    def scrape_culture_and_values(review):
        return _scrape_subrating(1)

    def scrape_career_opportunities(review):
        return _scrape_subrating(2)

    def scrape_comp_and_benefits(review):
        return _scrape_subrating(3)

    def scrape_senior_management(review):
        return _scrape_subrating(4)

    funcs = [
        scrape_date,
        scrape_emp_title,
        scrape_location,
        scrape_status,
        scrape_rev_title,
        scrape_years,
        scrape_helpful,
        scrape_pros,
        scrape_cons,
        scrape_advice,
        scrape_overall_rating,
        scrape_work_life_balance,
        scrape_culture_and_values,
        scrape_career_opportunities,
        scrape_comp_and_benefits,
        scrape_senior_management
    ]

    fdict = dict((s, f) for (s, f) in zip(SCHEMA, funcs))

    return fdict[field](review)


def extract_from_page():

    def is_featured(review):
        try:
            review.find_element_by_class_name('featuredFlag')
            return True
        except selenium.common.exceptions.NoSuchElementException:
            return False

    def extract_review(review):
        author = review.find_element_by_class_name('authorInfo')
        res = {}
        # import pdb;pdb.set_trace()
        for field in SCHEMA:
            res[field] = scrape(field, review, author)

        assert set(res.keys()) == set(SCHEMA)
        return res

    logger.info(f'Extracting reviews from page {page[0]}')

    res = pd.DataFrame([], columns=SCHEMA)

    reviews = browser.find_elements_by_class_name('empReview')
    logger.info(f'Found {len(reviews)} reviews on page {page[0]}')

    for review in reviews:
        if not is_featured(review):
            data = extract_review(review)
            logger.info(f'Scraped data for "{data["review_title"]}"')
            res.loc[idx[0]] = data
        else:
            logger.info('Discarding a featured review')
        idx[0] = idx[0] + 1

    return res


def more_pages():
    paging_control = browser.find_element_by_class_name('pagingControls')
    next_ = paging_control.find_element_by_class_name('next')
    try:
        next_.find_element_by_tag_name('a')
        return True
    except selenium.common.exceptions.NoSuchElementException:
        return False


def go_to_next_page():
    logger.info(f'Going to page {page[0] + 1}')
    paging_control = browser.find_element_by_class_name('pagingControls')
    next_ = paging_control.find_element_by_class_name(
        'next').find_element_by_tag_name('a')
    browser.get(next_.get_attribute('href'))
    time.sleep(1)
    page[0] = page[0] + 1


def no_reviews():
    return False
    # TODO: Find a company with no reviews to test on


def navigate_to_reviews():
    logger.info('Navigating to company overview')

    browser.get(args.url)
    time.sleep(1)

    if no_reviews():
        logger.info('No reviews to scrape. Bailing!')
        return False

    logger.info('Navigating to reviews')
    reviews_cell = browser.find_element_by_xpath(
        "//*[@id='EmpLinksWrapper']/div/a[2]")
    reviews_path = reviews_cell.get_attribute('href')
    browser.get(reviews_path)
    time.sleep(1)

    return True


def sign_in():
    logger.info(f'Signing in to {args.username}')

    url = 'https://www.glassdoor.com/profile/login_input.htm'
    browser.get(url)

    # import pdb;pdb.set_trace()

    email_field = browser.find_element_by_name('username')
    password_field = browser.find_element_by_name('password')
    submit_btn = browser.find_element_by_xpath('//button[@type="submit"]')

    email_field.send_keys(args.username)
    password_field.send_keys(args.password)
    submit_btn.click()

    time.sleep(1)


def get_browser():
    logger.info('Configuring browser')
    chrome_options = wd.ChromeOptions()
    if args.headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('log-level=3')
    browser = wd.Chrome(chrome_options=chrome_options)
    return browser


browser = get_browser()
page = [1]
idx = [0]


def main():
    res = pd.DataFrame([], columns=SCHEMA)

    sign_in()

    reviews_exist = navigate_to_reviews()
    if not reviews_exist:
        return

    reviews_df = extract_from_page()
    res = res.append(reviews_df)

    # import pdb;pdb.set_trace()

    while more_pages() and len(res) < args.limit:
        go_to_next_page()
        reviews_df = extract_from_page()
        res = res.append(reviews_df)

    logger.info(f'Writing {len(res)} reviews to file {args.file}')
    res.to_csv(args.file, index=False, encoding='utf-8')

    end = time.time()
    logger.info(f'Finished in {end - start} seconds')


if __name__ == '__main__':
    main()
