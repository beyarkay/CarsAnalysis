print('imports...', end='', flush=True)

import datetime
import math
import os
import re
import signal
import sys
import time
import traceback
from pprint import pprint

import pandas as pd
import selenium.common.exceptions as selexcept
from bs4 import BeautifulSoup
from selenium import webdriver
from tqdm import tqdm

DOMAIN = 'https://www.gumtree.co.za'
"""
Western Cape, 
Price <= 150 000
Hatchback
Mileage <= 90 000
Year >= 2014
Manual transmission, Petrol fuel, Used
"""
# ROOT = 'https://www.gumtree.co.za/s-cars-bakkies/western-cape/petrol~hatchback~manual/v1c9077l3100001a3fubttrp1?cy=2014,&pr=,150000&km=,90000&priceType=FIXED'
ROOT = 'https://www.gumtree.co.za/s-cars-bakkies/western-cape/hatchback/v1c9077l3100001a1btp1?priceType=FIXED'
WEBSITE = 'gumtreecoza'
PICKLE_PATH = 'generated_files/gumtree_wc.pkl'
print('done')


def main():
    def signal_handler(sig, frame):
        print('Quitting chromedriver, tqdm')
        driver.quit()
        # pbar.close() #TODO tqdm pbar doensn't exist here for some reason...
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    print('Reading Pickle')
    try:
        df = pd.read_pickle(PICKLE_PATH)
    except (FileNotFoundError, KeyError):
        df = pd.DataFrame()
        df.to_pickle(PICKLE_PATH)
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--window-size=1420,1080')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    #     driver = webdriver.Chrome(executable_path='/usr/bin/chromedriver', options=chrome_options)
    driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)

    df = grow_from_root_url(ROOT, driver=driver, df=df)


def grow_from_root_url(root_url, driver, df=None, verbose=True, limit=-1):
    if df is None:
        df = pd.DataFrame()
    # Navigate to the area landing page containing the listings for a given area
    print(f'Opening page {root_url}...', end='', flush=True)
    driver.get(root_url)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    estimate = int(soup.select('.ads-count')[0].text.replace('Ads\xa0', '').replace(',', '').strip())
    print(' done', flush=True)

    # Check that there actually are items on the page
    # no_properties_banner = driver.find_elements_by_css_selector('.text-center h4')
    # if no_properties_banner and no_properties_banner[0].text.lower() == 'no properties found':
    #     print(f'\t({len(df)}) No new properties in {root_url.split("/")[4].title()}')
    #     return df

    if not os.path.exists('generated_files/gumtree_links.txt'):
        listing_links = []
        pbar = tqdm(total=math.ceil(estimate / 20))
        while True:
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # print('sleeping...')
            time.sleep(4)  # it takes a bit of time for the listings to load
            soup = BeautifulSoup(driver.page_source, 'lxml')
            pbar.set_description(f'{len(listing_links)} done')
            pbar.refresh()
            listing_links.extend(
                [DOMAIN + l.select('a.related-ad-title')[0].get('href') for l in soup.select('.mult-lines-lt-1280')])
            listing_links = list(set(listing_links))
            try:
                next_links = []
                attempts_left = 10
                while attempts_left:
                    next_links = driver.find_elements_by_css_selector('a.icon-pagination-right')
                    attempts_left -= 1
                    if next_links:
                        # print('about to go to next')
                        time.sleep(4)
                        next_links[0].click()
                        break
                if attempts_left == 0:  # We've reached the last page
                    # print('were done')
                    break
                pbar.update(n=1)

            except selexcept.ElementClickInterceptedException:  # sometimes an advert gets in the way
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                next_links[0].click()
            except selexcept.NoSuchElementException:
                break
        pbar.close()
        # listing_links = list(set(listing_links))
        with open('generated_files/gumtree_links.txt', 'w') as f:
            f.writelines([l + '\n' for l in listing_links])
    else:
        with open('generated_files/gumtree_links.txt', 'r') as f:
            listing_links = [l.strip() for l in f.readlines()]

    # try:
    #     listing_cards[0].click()  # Now start going through every property page
    # except selexcept.ElementNotInteractableException:
    #     traceback.print_exc()
    #     print("Error opening: " + driver.current_url)
    # # A pop-up box appears if you click a property listed by more than one agent,
    # # the pop-up has a url similar to https://www.property24.com/.../11637#G842412
    # if len(driver.current_url.split('#')) != 1:
    #     time.sleep(1)  # need to wait a bit for the popup
    #     popup_box = driver.find_elements_by_css_selector('.js_dlm_body.p24_modalBody')
    #     listing_cards = popup_box[0].find_elements_by_css_selector('.p24_regularTile')
    #     listing_cards[0].get_attribute('innerHTML')
    #     listing_cards[0].click()  # NOW start going through every property page

    cars = []
    click_intercept_count = 0
    cars_count = 0
    print('Stepping through cars:')
    pbar = tqdm(total=len(listing_links))
    pbar_count = 0
    while limit == -1 or cars_count < limit:
        if pbar_count >= pbar.total:
            pbar.total *= 2
            pbar.refresh()
        pbar_count += 1
        pbar.update(n=1)
        pbar.refresh()
        try:  # In case of any error at all, print it and move on
            # The listing strings let us check if we've already scraped a particular item
            # TODO eventually will need a multi-index support to handle multiple websites and them re-using their ids
            # if 'uid' in df.columns:
            #     df.dropna(subset=['uid'], inplace=True)
            driver.get(listing_links[cars_count])
            cars_count += 1
            uid_strings = [str(int(num)) for num in df.get('uid', []) if num]

            soup = BeautifulSoup(driver.page_source, 'lxml')
            curr_uid = int(re.search(r'\d{9}', soup.title.text).group())
            pbar.set_description(f'{curr_uid}')
            # pbar.refresh()
            if curr_uid not in uid_strings:
                pbar.set_description(f'{curr_uid}...')
                # pbar.refresh()
                car_dict = soup_to_dict(soup, driver.current_url)
                # pprint(car_dict)
                if car_dict is not None and 'uid' in car_dict.keys():
                    cars.append(car_dict)
                else:
                    if verbose: print(" failed: p24 is None or p24 doesn't contain the key uid")
                if len(cars) >= 10:
                    # TODO include some sort of append_and_save method
                    df = append_and_save(df, pd.DataFrame(cars))
                    cars = []

        except Exception as e:
            print('Exception in grow_from_root_url:')
            traceback.print_exc()
            break
    pbar.close()
    if cars:
        df = append_and_save(df, pd.DataFrame(cars))
    return df


def soup_to_dict(soup, link):
    """ TODO maybe you can format this out as a module, from which you import a list of methods
    """
    car_dict = {}
    try:
        car_dict['link'] = link
        car_dict['date_updated'] = datetime.datetime.now()
        car_dict['uid'] = int(re.search(r'\d{9}', soup.title.text).group())
        car_dict['website'] = WEBSITE

        price = soup.select('.vip-summary')[0].select('.ad-price')[0].text.strip().lower()
        try:
            car_dict['price'] = float(re.sub(r'(\xa0|r|,)', '', price).strip())
        except ValueError:
            car_dict['price'] = None

        title = soup.select('.vip-summary')[0].select('.title')[0].text.strip()
        car_dict['title'] = title

        title = title.lower().strip()
        keys = [d.select('span.name')[0].text for d in soup.select('.attribute')]
        values = [d.select('span.value')[0].text for d in soup.select('.attribute')]
        data_dict = {k.lower().replace(':', ''): v.lower() for k, v in zip(keys, values)}

        car_dict['make'] = data_dict.get('make', None)
        car_dict['model'] = data_dict.get('model', None)
        car_dict['year'] = data_dict.get('year', None)
        car_dict['kms'] = data_dict.get('kilometers', None)
        car_dict['transmission'] = data_dict.get('transmission', None)
        car_dict['fuel_type'] = data_dict.get('fuel type', None)
        car_dict['color'] = data_dict.get('colour', None)

        # car_dict['variant'] = link.split('/')[6]
        mmv = re.sub('(20\d\d|for sale|\d-door|(for )?R((\s|,)?\d{,3})+(\.\d+)?|negotiable)', '', title)
        car_dict['mmv_string'] = re.sub(r'\s{2,}', '', mmv).strip()
        return car_dict
    except Exception as e:
        print('Exception in soup-to-dict:')
        traceback.print_exc()
        pprint(car_dict)
        return car_dict


def append_and_save(OG: pd.DataFrame, new: pd.DataFrame, path=PICKLE_PATH):
    # with open('replacements.csv', 'r') as replacements_file:
    #     l = [x.strip().split(',') for x in replacements_file.readlines()]
    # replacements = {line[0]: line[1] for line in l}
    # # Drop the columns we really don't care about
    # new.drop(BLACKLIST, axis=1, errors='ignore', inplace=True)

    # for from_name, to_name in replacements.items():
    #     if from_name in new.columns and to_name in new.columns:
    #         new[to_name].where(new[to_name].notnull(), new[from_name], inplace=True)
    #         new.drop(columns=[from_name], axis=1, inplace=True)
    #
    #     elif from_name in new.columns:
    #         new.rename(columns={from_name: to_name}, inplace=True)
    #         # new.drop(columns=[from_name], axis=1)
    # new = new.applymap(lambda x: x if type(x) is not str else x.lower().strip().replace(', ', ','))
    # print('Saving, but this wont work for different websites')

    if len(OG) > 0:
        OG = OG.append(new, ignore_index=True, sort=True)
        # OG.drop(BLACKLIST, axis=1, errors='ignore', inplace=True)
        # OG = OG.apply(clean_column)
        OG.to_pickle(path)
        return OG
    else:
        # new = new.apply(clean_column)
        new.to_pickle(path)
        return new


if __name__ == '__main__':
    main()
