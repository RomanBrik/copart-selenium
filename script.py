import json
import logging
import os
import re
import sys
import urllib
from datetime import datetime as dt
from itertools import count

from lxml import etree
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

chrome_driver_path = 'files/chromedriver'


class Copart:

    def __init__(self, query=None, *, url=None, filters=None, lot_filters=None):
        self.driver = webdriver.Chrome(
            executable_path=chrome_driver_path,
        )
        self.driver.minimize_window()
        self.main_window = self.driver.window_handles[0]
        self.query = query
        self.url = url
        search_type, message = self.search_type()

        date = dt.now().strftime('%d-%m-%y')

        try:
            search = self.driver.find_element_by_xpath('//*[@ng-if="searchText"]')
            search_text = re.search(r'for ([\w\s]+) .+', search.text) \
                .group(1) \
                .replace(' ', '_')
            dir_name = f'{search_text}_{date}'
        except NoSuchElementException:
            dir_name = date

        if os.path.isdir(f'data/{dir_name}'):
            for c in count(1):
                new_dir = f'{dir_name}({c})'
                if not os.path.isdir(f'data/{new_dir}'):
                    dir_name = new_dir
                    break

        os.makedirs(f'data/{dir_name}/pictures')
        self.folder = dir_name

        # logger
        logging.basicConfig(
            filename=f'data/{self.folder}/log.log',
            level=logging.INFO,
            filemode="w",
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.info('Program started!')
        logging.info(f'{search_type} - {message}')

        self.no_lots(query)

        if filters:
            # expand all filters to make them visible
            try:
                close_filters = self.driver.find_element_by_xpath('//*[@class="left closeall"]')
            except NoSuchElementException:
                close_filters = self.driver.find_element_by_xpath('//*[@class="closeall left"]')
            finally:
                if close_filters:
                    close_filters.click()
                self.driver.find_element_by_xpath('//*[@class="left openall"]').click()

            # scroll filters to make it load and visible for driver
            boxes = self.driver.find_elements_by_xpath('//div[@class="checkbox"]')
            for box in boxes:
                self.driver.execute_script("arguments[0].scrollIntoView();", box)

            # Select the filters
            if isinstance(filters, str):
                filters = [filters]

            for filter in filters:
                try:
                    elem = self.driver.find_element_by_xpath(
                        f'//input[@value="{filter}"]')
                except NoSuchElementException:
                    logging.info(f'Filter {filter} has been missed')
                    continue

                try:
                    if not elem.is_selected():
                        self.driver.execute_script("arguments[0].click();", elem)
                        WebDriverWait(self.driver, 3).until(
                            EC.visibility_of_all_elements_located(
                                (By.XPATH, '//div[@class="filters"]')))
                except (TimeoutException, StaleElementReferenceException) as e:
                    logging.error(f'{filter} {e}')

    def search_type(self):

        if self.query:
            parsed_query = urllib.parse.quote(self.query)
            url = f'https://www.copart.com/lotSearchResults/?free=true&query={parsed_query}'
            self.driver.get(url)

            # No results
            return ('query', self.query)

        elif self.url:
            self.driver.get(self.url)
            return ('url', self.url)

        # if not specified query and url we'll look all `Run and Drive` category
        else:
            url = (
                'https://www.copart.com/popular/category/run-and-drive?'
                'intcmp=web_homepage_categories_runanddrive_public_en&query=run-and-drive&free'
            )
            self.driver.get(url)
            return ('not provided search type', url)

    def no_lots(self, query):
        try:
            self.driver.find_element_by_xpath('//*[@data-uname="sorryMessage"]')
            raise ValueError('No data')
        except NoSuchElementException:
            pass
        except ValueError:
            logging.error(f"{query} didn't find the results")
            self.driver.quit()
            sys.exit(1)

    def scrape_lots(self, seller=False, photos=False):
        logging.info('Parsing started!')
        data = {}
        # New Tab
        self.driver.execute_script(f"window.open('','_blank');")
        self.driver.switch_to.window(self.main_window)

        # iterate over all or specified amout of pages
        try:
            pages = int(self.driver.find_element_by_xpath(
                '//div[@class="bottom"]//li[@class="paginate_button next"]'
                '/preceding-sibling::li[1]/a').get_attribute('text'))
        except NoSuchElementException:
            pages = 1

        for _ in range(pages):
            # Links to lot
            lots_url = self.links_on_page()
            # Switch to 2nd tab
            self.driver.switch_to.window(self.driver.window_handles[1])

            for url in lots_url:
                # Open lot url
                self.driver.get(url)
                # Wait until elements of page will be loaded
                self.wait_load_xpath('//*[@class="col-md-7 no-padding"]', 3)

                if seller:
                    try:
                        self.driver.find_element_by_xpath(f'//*[@data-uname="lotdetailSeller"]')
                    except NoSuchElementException:
                        continue

                        # Get all required information

                data[url.split("/")[-1]] = self.lot_detail()
                logging.info(f'Parsed {url}')

                if photos:
                    self.save_lot_photos(url)

            # Switch to 1st tab
            self.driver.switch_to.window(self.main_window)
            # And go to the next page
            self.next_page()
        logging.info('Job finished Succesufully!')
        self.driver.quit()
        with open(f'data/{self.folder}/lots.json', 'w') as f:
            json.dump(data, f, indent=2)

    def lot_detail(self):
        sel = etree.HTML(self.driver.page_source)
        url = self.driver.current_url
        lot = self.driver.current_url.split('/')[-1]
        seller = self.xpath_text(sel, '//*[@data-uname="lotdetailSeller"]')
        model_name = self.xpath_text(sel, '//span[@class="title"]')
        doc_type = self.xpath_text(sel, '//*[@data-uname="lotdetailTitledescriptionvalue"]')
        highlights = self.xpath_text(sel, '//*[@class="lot-details-desc highlights-popover-cntnt col-md-7"]')
        primary_damage = self.xpath_text(sel, '//*[@data-uname="lotdetailPrimarydamagevalue"]')
        est_value = self.xpath_text(sel, '//*[@data-uname="lotdetailEstimatedretailvalue"]')
        current_bid = self.xpath_text(sel, '//*[@for="Current Bid"]/following-sibling::span')

        return {
            'url': url,
            'lot': lot,
            'seller': seller,
            'model': model_name,
            'doc_type': doc_type,
            'highlights': highlights,
            'primary_damage': primary_damage,
            'est_value': est_value,
            'current_bid': current_bid,
        }

    def save_lot_photos(self, url):

        # create folder for each lot
        folder = f'data/{self.folder}/pictures/{url.split("/")[-1]}'
        os.makedirs(folder)

        self.driver.get(url + '/Photos')
        self.wait_load_xpath('//*[@class="lot-images padding10"]', 2)

        lot = self.driver.current_url.split('/')[-2]
        imgs = self.driver.find_elements_by_xpath('//div[@class="viewAllPhotosRelative"]/img')

        for num, img in enumerate(imgs, 1):
            filename = f'{folder}/{lot}_{num}.png'
            try:
                with open(filename, 'wb') as f:
                    f.write(img.screenshot_as_png)
            except:
                if os.path.exists(filename):
                    os.remove(filename)

    def links_on_page(self):
        lots = self.driver.find_elements_by_xpath('//*[@data-uname="lotsearchLotnumber"]')
        return [lot.get_attribute("href") for lot in lots]

    def next_page(self):
        try:
            self.driver.find_element_by_xpath('//*[@id="serverSideDataTable_next"]/a').click()
            WebDriverWait(self.driver, 5).until(
                EC.visibility_of_all_elements_located(
                    (By.XPATH, '//*[@data-uname="lotsearchLotnumber"]')
                )
            )
        except NoSuchElementException:
            pass

        except TimeoutException:
            WebDriverWait(self.driver, 3).until(
                EC.visibility_of_all_elements_located(
                    (By.XPATH, '//*[@data-uname="lotsearchLotnumber"]')
                )
            )

    def xpath_text(self, sel, xpath):
        try:
            elem = sel.xpath(xpath)
            return elem[0].text.strip() if elem else ''
        except NoSuchElementException:
            return 'Error `XPATH`'

    def wait_load_xpath(self, xpath, sec):
        for _ in range(2):
            try:
                WebDriverWait(self.driver, sec).until(
                    EC.visibility_of_element_located(
                        (By.XPATH, xpath)))
                break
            except TimeoutException:
                pass

