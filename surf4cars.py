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

"""
Western Cape, 
Price <= 150 000
Hatchback
Mileage <= 90 000
Manual transmission, Petrol fuel, Used
"""
DOMAIN = 'https://www.surf4cars.co.za/showroom/'
# ROOT = 'https://www.surf4cars.co.za/showroom/showroom.aspx?s_makestr=&s_rangestr=&s_modelstr=&s_minvalue=0&s_maxvalue=0&s_province=2&s_maxmileage=90000&s_yearfrom=2014&uid=&s_trans=2&s_fuel=3&s_body=8&s_seller=0&s_dg=&s_provinceStr=Western+Cape&s_vehicletype=used&s_colour=0&sortby=0&s_modelrangeid=&s_regionid=0&s_region=&page=1'
ROOT = 'https://www.surf4cars.co.za/showroom/?s_makestr=&s_rangestr=&s_modelstr=&s_minvalue=0&s_maxvalue=0&s_province=2&s_maxmileage=0&s_yearfrom=0&uid=&s_trans=0&s_fuel=0&s_body=0&s_seller=0&s_dg=&s_provinceStr=Western%20Cape&s_vehicletype=used&s_colour=0&sortby=0&s_modelrangeid=&s_regionid=0&s_region='
WEBSITE = 'surf4carscoza'
PICKLE_PATH = 'surf4cars_wc.pkl'
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
    estimate = int(
        soup.select('.btn-group.btn-group-justified')[0].select('.btn.btn-link')[-1].get('href', None).split('=')[-1]
    ) * 25
    print(' done', flush=True)

    if not os.path.exists('surf4cars_links.txt'):
        listing_links = []
        pbar = tqdm(total=math.ceil(estimate / 25))
        while True:
            time.sleep(1)
            # driver.execute_script("window.scrollTo(0, 0);")
            soup = BeautifulSoup(driver.page_source, 'lxml')
            pbar.set_description(f'{len(listing_links)} done')
            pbar.refresh()
            listing_links.extend([DOMAIN + a.get('href') for a in soup.select('.VehicleName')])
            listing_links = list(set(listing_links))
            try:
                next_links = []
                attempts_left = 10
                while attempts_left:
                    next_links = driver.find_elements_by_css_selector('.btn.btn-link')
                    attempts_left -= 1
                    if next_links:
                        next_links[-2].click()
                        break
                if attempts_left == 0:
                    break
                pbar.update(n=1)

            except selexcept.ElementClickInterceptedException:  # We've reached the end
                break
        pbar.close()
        with open('surf4cars_links.txt', 'w') as f:
            f.writelines([l + '\n' for l in listing_links])
    else:
        with open('surf4cars_links.txt', 'r') as f:
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
            driver.get(listing_links[cars_count])
            cars_count += 1
            uid_strings = [str(int(num)) for num in df.get('uid', []) if num]

            soup = BeautifulSoup(driver.page_source, 'lxml')
            parts = listing_links[cars_count].split('&')
            curr_uid = [int(part.replace('vehicleid=', '')) for part in parts if 'vehicleid' in part][0]
            # curr_uid = int(soup.select('#FullwidthContentPlaceholder_LblRef')[0].text.replace('Ref: ', ''))
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
    car_dict = {}
    try:
        car_dict['link'] = link
        car_dict['date_updated'] = datetime.datetime.now()
        car_dict['uid'] = [int(part.replace('vehicleid=', '')) for part in link.split('&') if 'vehicleid' in part][0]
        car_dict['website'] = WEBSITE

        breadcrumbs = [l.text.lower().strip() for l in soup.select('.breadcrumb')[0].select('a')]
        car_dict['make'] = breadcrumbs[3]
        car_dict['model'] = breadcrumbs[4].replace(car_dict['make'], '').strip()

        price = soup.select('#FullwidthContentPlaceholder_LblPrice')[0].text.strip().lower()
        if 'poa' in price:
            car_dict['price'] = None
        else:
            car_dict['price'] = float(re.sub(r'(\xa0|r|,|\s+)', '', price).strip())

        car_dict['title'] = soup.select('h1')[0].text.strip()

        title = car_dict['title'].lower()
        mmv = re.sub('(20\d\d|for sale|\d-door|\ddr|(for )?R((\s|,)?\d{,3})+(\.\d+)?|negotiable)', '', title)
        car_dict['mmv_string'] = re.sub(r'\s{2,}', '', mmv).strip()

        data = [td.text.lower().strip() for td in soup.select('.table.table-condensed')[0].select('td')]
        data_dict = {k: v for k, v in zip(data[::2], data[1::2])}

        try:
            car_dict['kms'] = int(re.sub(r'\s+|km', '', data_dict.get('mileage', None)))
        except ValueError:
            car_dict['kms'] = None
        car_dict['transmission'] = data_dict.get('transmission', None)
        car_dict['year'] = int(re.search(r'(20|19)\d\d', title).group())
        car_dict['color'] = data_dict.get('colour', None)
        car_dict['fuel_type'] = None

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
