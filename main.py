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
import argparse
import logging
import logging.config
from selenium import webdriver as wd
from selenium.webdriver import ActionChains
import selenium
import numpy as np
from schema import SCHEMA
import json
import urllib
import datetime as dt

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
parser.add_argument('--start_from_url', action='store_true',
                    help='Start scraping from the passed URL.')
parser.add_argument(
    '--max_date', help='Latest review date to scrape.\
    Only use this option with --start_from_url.\
    You also must have sorted Glassdoor reviews ASCENDING by date.',
    type=lambda s: dt.datetime.strptime(s, "%Y-%m-%d"))
parser.add_argument(
    '--min_date', help='Earliest review date to scrape.\
    Only use this option with --start_from_url.\
    You also must have sorted Glassdoor reviews DESCENDING by date.',
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
        msg = 'Please provide Glassdoor credentials.\
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
logging.getLogger('selenium').setLevel(logging.CRITICAL)


def scrape(field, review, author):

    def scrape_date(review):
        jobtitle = author.find_element_by_class_name('authorJobTitle').text.strip('"')
        res = dt.datetime.strptime(jobtitle.split('-')[0].strip(' '),'%b %d, %Y').date()
        return res

    def scrape_emp_title(review):
        if 'Anonymous Employee' not in review.text:
            try:
                jobtitle = review.find_element_by_class_name('authorJobTitle').text.strip('"')
                res = jobtitle.split('-')[1].strip(' ')
            except Exception:
                logger.warning('Failed to scrape employee_title')
                res = "N/A"
        else:
            res = "Anonymous"
        return res

    def scrape_location(review):
        if 'in' in review.text:
            try:
                res = author.find_element_by_class_name(
                    'authorLocation').text
            except Exception:
                logger.warning('Failed to scrape employee_location')
                res = np.nan
        else:
            res = "N/A"
        return res

    def scrape_status(review):
        try:
            res = review.find_element_by_class_name('pt-xsm').text.strip('"')
        except Exception:
            logger.warning('Failed to scrape employee_status')
            res = "N/A"
        return res

    def scrape_rev_title(review):
        return review.find_element_by_class_name('mb-xxsm').text.strip('"')

    def scrape_helpful(review):
        try:
            helpful = review.find_element_by_class_name('common__EiReviewDetailsStyle__socialHelpfulcontainer').text
            if 'people found this review helpful' in helpful:
                res = int(helpful.split(' ')[0])
            else:
                res = 0
        except Exception:
            res = 0
        return res

    def scrape_pros(review):
        try:
            comments = review.find_elements_by_class_name('v2__EIReviewDetailsV2__fullWidth')
            res = np.nan
            for r in comments:
                if r.find_element_by_tag_name('p').text=='Pros':
                    res = r.find_element_by_tag_name('span').text
        except Exception:
            res = np.nan
        return res

    def scrape_cons(review):
        try:
            comments = review.find_elements_by_class_name('v2__EIReviewDetailsV2__fullWidth')
            res = np.nan
            for r in comments:
                if r.find_element_by_tag_name('p').text=='Cons':
                    res = r.find_element_by_tag_name('span').text
        except Exception:
            res = np.nan
        return res

    def scrape_advice(review):
        try:
            comments = review.find_elements_by_class_name('v2__EIReviewDetailsV2__fullWidth')
            res = np.nan
            for r in comments:
                if r.find_element_by_tag_name('span').get_attribute('data-test')=='advice-management':
                    res = r.find_element_by_tag_name('span').text
        except Exception:
            res = np.nan
        return res

    def scrape_overall_rating(review):
        try:
            ratings = review.find_element_by_class_name('ratingNumber')
            res = float(ratings.text[:3])
        except Exception:
            res = np.nan
        return res

    def _scrape_subrating(i):
        try:
            r = review.find_element_by_class_name('tooltipContainer').find_elements_by_tag_name('li')
            srdiv = r[i].find_elements_by_tag_name('div')
            srclass = srdiv[1].get_attribute('class')
            res = v.index(srclass)+1
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

    def _scrape_checkmark(i):
        try:
            r = review.find_element_by_class_name('recommends').find_elements_by_class_name('SVGInline-svg')
            att = r[i].get_attribute('class')
            if att=='SVGInline-svg css-hcqxoa-svg d-flex-svg':
                res = 'mark'
            elif att=='SVGInline-svg css-1h93d4v-svg d-flex-svg':
                res = 'line'
            elif att=='SVGInline-svg css-1kiw93k-svg d-flex-svg':
                res = 'cross'
            elif att=='SVGInline-svg css-10xv9lv-svg d-flex-svg':
                res = 'circle'
            else:
                res = np.nan
        except Exception:
            res = np.nan 
        return res

    def scrape_recommends(review):
        return _scrape_checkmark(0)
    
    def scrape_approve_ceo(review):
        return _scrape_checkmark(1)
        
    def scrape_outlook(review):
        return _scrape_checkmark(2)

    def scrape_featured(review):
        try:
            review.find_element_by_class_name('common__EiReviewDetailsStyle__newFeaturedReview')
            return True
        except selenium.common.exceptions.NoSuchElementException:
            return False  

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
        scrape_work_life_balance,
        scrape_culture_and_values,
        scrape_career_opportunities,
        scrape_comp_and_benefits,
        scrape_senior_management,
        scrape_recommends,
        scrape_outlook,
        scrape_approve_ceo,
        scrape_featured

    ]

    # mapping from subrating to integer value for 1,2,3,4,5 stars
    v = ['css-152xdkl','css-19o85uz','css-1ihykkv','css-1c07csa','css-1dc0bv4']

    fdict = dict((s, f) for (s, f) in zip(SCHEMA, funcs))

    return fdict[field](review)


def extract_from_page():

    def expand_show_more(review):
        try:
            continue_link = review.find_element_by_class_name('v2__EIReviewDetailsV2__newUiCta')
            continue_link.click()
        except Exception:
            pass

    def extract_review(review):
        try:
            author = review.find_element_by_class_name('authorInfo')
        except:
            return None # Account for reviews that have been blocked
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
    
    # refresh page if failed to load properly, else terminate the search
    if len(reviews) < 1:
        browser.refresh()
        time.sleep(5)
        reviews = browser.find_elements_by_class_name('empReview')
        logger.info(f'Found {len(reviews)} reviews on page {page[0]}')
        if len(reviews) < 1:
            valid_page[0] = False # make sure page is populated

    for review in reviews:
        expand_show_more(review)
        data = extract_review(review)
        if data != None:
            logger.info(f'Scraped data for "{data["review_title"]}"')
            res.loc[idx[0]] = data
        else:
            logger.info('Discarding a blocked review')
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
        current = browser.find_element_by_class_name('selected')
        pages = browser.find_element_by_class_name('pageContainer').text.split()
        if int(pages[-1]) != int(current.text):
            return True
        else:
            return False
    except selenium.common.exceptions.NoSuchElementException:
        return False


def go_to_next_page():
    logger.info(f'Going to page {page[0] + 1}')
    next_ = browser.find_element_by_class_name('nextButton')
    ActionChains(browser).click(next_).perform()
    time.sleep(5) # wait for ads to load
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

    reviews_cell = browser.find_element_by_xpath(
        '//a[@data-label="Reviews"]')
    reviews_path = reviews_cell.get_attribute('href')
    
    # reviews_path = driver.current_url.replace('Overview','Reviews')
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

    time.sleep(3)
    browser.get(args.url)



def get_browser():
    logger.info('Configuring browser')
    chrome_options = wd.ChromeOptions()
    if args.headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('log-level=3')
    browser = wd.Chrome(options=chrome_options)
    return browser


def get_current_page():
    logger.info('Getting current page number')
    current = browser.find_element_by_class_name('selected')
    return int(current.text)


def verify_date_sorting():
    logger.info('Date limit specified, verifying date sorting')
    ascending = urllib.parse.parse_qs(
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

    sign_in()

    if not args.start_from_url:
        reviews_exist = navigate_to_reviews()
        if not reviews_exist:
            return
    elif args.max_date or args.min_date:
        verify_date_sorting()
        browser.get(args.url)
        page[0] = get_current_page()
        logger.info(f'Starting from page {page[0]:,}.')
        time.sleep(1)
    else:
        browser.get(args.url)
        page[0] = get_current_page()
        logger.info(f'Starting from page {page[0]:,}.')
        time.sleep(1)

    reviews_df = extract_from_page()
    res = res.append(reviews_df)

    # import pdb;pdb.set_trace()

    while more_pages() and\
            len(res) < args.limit and\
            not date_limit_reached[0] and\
                valid_page[0]:
        go_to_next_page()
        try:
            reviews_df = extract_from_page()
            res = res.append(reviews_df)
        except:
            break

    logger.info(f'Writing {len(res)} reviews to file {args.file}')
    res.to_csv(args.file, index=False, encoding='utf-8')

    end = time.time()
    logger.info(f'Finished in {end - start} seconds')


if __name__ == '__main__':
    main()
