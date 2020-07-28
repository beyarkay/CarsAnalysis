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

DOMAIN = 'https://www.cars.co.za'
"""
Western Cape, 
Price <= 150 000
Hatchback
Mileage <= 90 000
Year >= 2014
Manual transmission, Petrol fuel, Used
"""
# ROOT = 'https://www.cars.co.za/searchVehicle.php?new_or_used=Used&make_model=&vfs_area=Western+Cape&agent_locality=&price_range=50000+-+74999%7C75000+-+99999%7C100000+-+124999%7C125000+-+149999&os=&locality=&commercial_type=&body_type_exact=Hatchback&transmission=off&fuel_type=p&login_type=&mapped_colour=&vfs_year=2020+-+2020%7C2019+-+2019%7C2018+-+2018%7C2017+-+2017%7C2016+-+2016%7C2015+-+2015%7C2014+-+2014&vfs_mileage=0+-+4999%7C5000+-+9999%7C10000+-+49999%7C50000+-+74999%7C75000+-+99999&vehicle_axle_config=&keyword=&sort=vfs_price'
ROOT = 'https://www.cars.co.za/searchVehicle.php?new_or_used=Used&make_model=&vfs_area=Western+Cape&agent_locality=&price_range=&os='
WEBSITE = 'carscoza'
PICKLE_PATH = 'generated_files/cars_wc.pkl'
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
    text_estimate = soup.select('.pagination__page-number_right')[0].text
    text_estimate = re.sub(r'\s+', ' ', text_estimate)
    estimate = int(re.sub(r'\d+ - \d+ of ', '', text_estimate).strip())
    print(' done', flush=True)

    if not os.path.exists('generated_files/cars_links.txt'):
        listing_links = []
        pbar = tqdm(total=math.ceil(estimate / 20))
        while True:
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # print('sleeping...')
            # time.sleep(4)  # it takes a bit of time for the listings to load
            soup = BeautifulSoup(driver.page_source, 'lxml')
            pbar.set_description(f'{len(listing_links)} done')
            pbar.refresh()
            listing_links.extend(
                [DOMAIN + a.get('href') for a in soup.select('.vehicle-list__vehicle-name')])
            listing_links = list(set(listing_links))
            try:
                next_links = []
                attempts_left = 10
                while attempts_left:
                    next_links = driver.find_elements_by_css_selector('#results .fa-right-open-big')
                    attempts_left -= 1
                    if next_links:
                        # print('about to go to next')
                        # time.sleep(4)
                        driver.execute_script("window.scrollTo(0, 0);")
                        next_links[0].click()
                        break
                if attempts_left == 0:  # We've reached the last page
                    # print('were done')
                    break
                pbar.update(n=1)

            except (selexcept.ElementClickInterceptedException, selexcept.StaleElementReferenceException):  # sometimes an advert gets in the way
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                next_links = driver.find_elements_by_css_selector('#results .fa-right-open-big')
                next_links[-1].click()
            except selexcept.NoSuchElementException:
                break
        pbar.close()
        with open('generated_files/cars_links.txt', 'w') as f:
            f.writelines([l + '\n' for l in listing_links])
    else:
        with open('generated_files/cars_links.txt', 'r') as f:
            listing_links = [l.strip() for l in f.readlines()]

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
            curr_uid = int(listing_links[cars_count].split('/')[-2])
            pbar.set_description(f'{curr_uid}')
            # pbar.refresh()
            if curr_uid not in uid_strings:
                pbar.set_description(f'{curr_uid}...')
                # pbar.refresh()
                car_dict = soup_to_dict(soup, driver.current_url)
                # pprint(car_dict)
                cars.append(car_dict)
                if len(cars) >= 10:
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
        car_dict['uid'] = int(link.split('/')[-2])
        car_dict['website'] = WEBSITE

        # FIXME update soup_to_dict for carscoza
        breadcrumbs = [l.text.strip() for l in soup.select('.breadcrumb-bar')[0].select('li')]
        car_dict['make'] = breadcrumbs[2].lower().strip()
        car_dict['model'] = breadcrumbs[3].lower().replace(car_dict['make'], '').strip()

        price = soup.select('.vehicle-view__price')[0].text.strip().lower()
        if 'poa' in price:
            car_dict['price'] = None
        else:
            car_dict['price'] = float(re.sub(r'(\xa0|r|,)', '', price).strip())

        title = soup.select('.heading_size_xl')[0].text.strip()
        car_dict['title'] = re.sub(r'\s+', ' ', title).strip()

        title = title.lower()
        keys = [l.text.lower() for l in soup.select('.vehicle-details__label')]
        values = [re.sub(r'\xa0', '', l.text.lower()).strip() for l in soup.select('.vehicle-details__value')]
        data_dict = {k: v for k, v in zip(keys, values)}


        # TODO Cars.co.za allows _any_ value to be omitted and represents that with a '-'
        kms = re.sub(r'\s+|km', '', data_dict.get('mileage', None))
        try:
            car_dict['kms'] = int(kms)
        except ValueError:
            car_dict['kms'] = None
        car_dict['transmission'] = data_dict.get('transmission', None)
        car_dict['year'] = int(data_dict.get('year', None))
        car_dict['fuel_type'] = data_dict.get('fuel type', None)
        car_dict['color'] = data_dict.get('colour', None)

        # car_dict['variant'] = link.split('/')[6]
        mmv = re.sub('(20\d\d|for sale|\d-door|\ddr|(for )?R((\s|,)?\d{,3})+(\.\d+)?|negotiable)', '', title)
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
