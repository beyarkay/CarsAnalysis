print('imports...', end='', flush=True)

import datetime
import re
import signal
import time
import traceback
from pprint import pprint

import pandas as pd
import selenium.common.exceptions as selexcept
from bs4 import BeautifulSoup
from selenium import webdriver
from tqdm import tqdm

DOMAIN = 'https://www.autotrader.co.za/'
"""
Western Cape, 
Price <= 150 000
Hatchback
Mileage <= 90 000
Manual transmission, Petrol fuel, Used
"""
# ROOT = 'https://www.autotrader.co.za/cars-for-sale/western-cape/p-9/hatchback-bodytype?price=less-than-150000&year=more-than-2014&mileage=less-than-90000&transmission=Manual&fueltype=Petrol&isused=True'
ROOT = 'https://www.autotrader.co.za/cars-for-sale/western-cape/p-9?isused=True'
WEBSITE = 'autotradercoza'
PICKLE_PATH = 'generated_files/autotrader_wc.pkl'
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
        soup.select('.e-results-total')[0].text.strip().replace(' ', ''))  # TODO this selector might not always work
    print(' done', flush=True)

    # Check that there actually are items on the page
    # no_properties_banner = driver.find_elements_by_css_selector('.text-center h4')
    # if no_properties_banner and no_properties_banner[0].text.lower() == 'no properties found':
    #     print(f'\t({len(df)}) No new properties in {root_url.split("/")[4].title()}')
    #     return df

    # Find a list of the listing cards
    listing_cards = []

    # do-while not listing cards
    while True:
        listing_cards = driver.find_elements_by_css_selector('.b-featured-result-tile')
        if listing_cards:
            break
        print('sleeping for listing_cards')
        time.sleep(0.5)

    try:
        listing_cards[0].click()  # Now start going through every property page
    except selexcept.ElementNotInteractableException:
        traceback.print_exc()
        print("Error opening: " + driver.current_url)
    cars = []
    click_intercept_count = 0
    total_cars_count = 0
    print('Stepping through cars:')
    pbar = tqdm(total=estimate)
    pbar_count = 0
    while limit == -1 or total_cars_count < limit:
        total_cars_count += 1
        if pbar_count >= pbar.total:
            pbar.total *= 2
            pbar.refresh()
        pbar_count += 1
        pbar.update(n=1)
        pbar.refresh()
        try:  # In case of any error at all, print it and move on
            uid_strings = [str(int(num)) for num in df.get('uid', []) if num]
            curr_uid = driver.current_url.split("/")[-1]
            pbar.set_description(f'{curr_uid}')
            pbar.refresh()
            if curr_uid not in uid_strings:
                pbar.set_description(f'{curr_uid}...')
                pbar.refresh()
                soup = BeautifulSoup(driver.page_source, 'lxml')
                car_dict = soup_to_dict(soup, driver.current_url)
                # pprint(car_dict)
                if car_dict is not None and 'uid' in car_dict.keys():
                    cars.append(car_dict)
                else:
                    if verbose: print(" failed: p24 is None or p24 doesn't contain the key uid")
                if len(cars) >= 10:
                    df = append_and_save(df, pd.DataFrame(cars))
                    cars = []
            next_links = driver.find_elements_by_css_selector('.b-listing-iterator-links a.e-link')
            # next_link = [l for l in next_links][0]
            next_link = [l for l in next_links if l.get_attribute('rel') == 'next'][0]
            next_link.click()
        except selexcept.ElementClickInterceptedException:
            # Sometimes the next property button gets hidden, if so then try 5 times before moving on to the next area
            click_intercept_count += 1
            if click_intercept_count > 5:
                click_intercept_count = 0
                if cars:
                    df = append_and_save(df, pd.DataFrame(cars))
                    cars = []
                traceback.print_exc()
                print(f'\t({len(df)}) next button Click exception: {root_url}')
                break

        except selexcept.NoSuchElementException as e:
            traceback.print_exc()
            print(f'\t({len(df)}) Finished with {root_url}')
            break
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
        car_dict['uid'] = int(link.split('/')[-1].strip())
        car_dict['website'] = WEBSITE

        price = soup.select('.e-price')[0].text.lower()
        if 'poa' in price:
            car_dict['price'] = None
        else:
            car_dict['price'] = float(price.replace('\xa0', '').replace('r', '').strip())
        title = soup.select('.e-listing-title')[0].text
        car_dict['title'] = title
        title = title.lower().strip()
        car_dict['make'] = link.split('/')[4]
        car_dict['model'] = link.split('/')[5]
        car_dict['variant'] = link.split('/')[6]
        mmv = re.sub('((20|19)\d\d|for sale|\d-door)', '', title)
        car_dict['mmv_string'] = re.sub(r'\s{2,}', '', mmv).strip()


        details = [li.text.strip() for li in soup.select('.b-quick-specs')[0].select('li')]
        car_dict['year'] = float(details[0])
        car_dict['kms'] = float(details[1].replace('\xa0', '').replace('km', '').strip())
        car_dict['transmission'] = details[2].lower()
        car_dict['fuel_type'] = details[3].lower()

        return car_dict
    except Exception as e:
        print('Exception in soup-to-dict:')
        traceback.print_exc()
        pprint(car_dict)
        return car_dict


def append_and_save(OG: pd.DataFrame, new: pd.DataFrame, path=PICKLE_PATH):
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
