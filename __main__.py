import os
import json
from time import sleep
from dotenv import load_dotenv
from libs.web_scraping import WebScraping
from libs.xlsx import SpreadsheetManager

# Env variables
load_dotenv()
USE_FILTERS = os.getenv("USE_FILTERS", "False") == "True"
EXPLORE_SUBPAGES = os.getenv("EXPLORE_SUBPAGES", "False") == "True"


class Scraper(WebScraping):
    
    def __init__(self):
        
        # Pages
        self.home = "https://www.acelerapyme.gob.es/kit-digital/catalogo-digitalizadores"
        
        # Initialize and load home page
        super().__init__()
        self.__load_home_page__()
        
        # Files paths
        self.current_folder = os.path.dirname(os.path.abspath(__file__))
        self.filters_path = os.path.join(self.current_folder, "filters.json")
        self.sheets_path = os.path.join(self.current_folder, "data.xlsx")
        
        # Spreadsheet manager
        self.sheets = SpreadsheetManager(self.sheets_path)
        
        # Create sheet
        sheet_name = "businesses filters" if USE_FILTERS else "Businesses"
        self.sheets.create_set_sheet(sheet_name)
        
        # Css global selectors
        self.global_selectors = {
            "wrappers": {
                "solutions": '.block-facet-blocktipo-solucion-kit-digital',
                "provinces": '.block-facet-blockprovincia-opera-digitalizador',
                "cnae": '.block-facet-blockcnae-opera-digitalizador',
            },
            "filter_elem": '.facet-item a span',
        }
        
        # Current filters
        self.province = ""
        self.solution = ""
        self.cnae = ""
        
    def __clean_list__(self, items: list) -> list:
        """ Remove empty elements and duplicated from list
        
        Args:
            items (list): list of items to clean
            
        Returns:
            list: cleaned list
        """
        
        items = list(set(items))
        items = list(filter(lambda item: item != "" and item is not None, items))
        return items
        
    def __load_home_page__(self):
        """ Load home page """
        
        self.set_page(self.home)
        sleep(5)
        self.refresh_selenium()
        
    def __get_filters__(self) -> dict:
        """ Get filters from the page

        Returns:
            dict: filters with id and name by category
            
            Example:
            {
                "solutions": [...]
                "provinces": [...]
                "cnae": [...]
            }
        """
        
        print("Getting filters...")
                
        # Loop wrappers
        items = {}
        for wrapper_name, wrapper_selector in self.global_selectors["wrappers"].items():
            
            items_wrapper = []
            selector_items = f"{wrapper_selector} {self.global_selectors['filter_elem']}"
            items_elems = self.get_elems(selector_items)
            for item_elem in items_elems:
                text = item_elem.text
                if not (text):
                    continue
                items_wrapper.append(text)
            
            items[wrapper_name] = items_wrapper
        
        return items
    
    def __set_filter__(self) -> bool:
        """ Click in filters using the id
            
        Returns:
            bool: True if filters were clicked, False otherwise
        """
        
        selectors_wrappers = self.global_selectors["wrappers"]
        filters_selectors_values = {
            selectors_wrappers["provinces"]: self.province,
            selectors_wrappers["solutions"]: self.solution,
            selectors_wrappers["cnae"]: self.cnae,
        }
        
        filters_found = 0
        for filter_wrapper_selector, filter_value in filters_selectors_values.items():
            
            # Loop filter elements and click by value
            selector_elem = self.global_selectors['filter_elem']
            selector_filter = f"{filter_wrapper_selector} {selector_elem}"
            filter_elems = self.get_elems(selector_filter)
            
            for filter_elem in filter_elems:
                if filter_elem.text == filter_value:
                    
                    # Click with js (manually)
                    script = "arguments[0].click();"
                    self.driver.execute_script(script, filter_elem)
                    
                    filters_found += 1
                    break
                
        # Validate filters found
        if filters_found < 3:
            return False
            
        return True
    
    def __get_contact_info__(self, link: str) -> tuple:
        """ Get contact info from a page: email and phone
            And search in subpages
        
        Args:
            link (str): link to search contact info
            
        Returns:
            tuple: emails and phones found in page and subpages
            
            Example:
            (
                ["email1", "email2", ...],
                ["phone1", "phone2", ...]
            )
        """
        
        selectors = {
            "email": 'a[href^="mailto:"]',
            "phone": 'a[href^="tel:"]',
        }
        
        print(f"\t\tSearching contact info in page {link}...")
         
        # Set page in new tab
        self.set_page(link)
        sleep(5)
        self.refresh_selenium(back_tab=1)
        
        # Get subpages
        links = self.get_attribs("a", "href")
        links = self.__clean_list__(links)
        
        # Get email and phone with regex
        emails = self.get_texts(selectors["email"])
        phones = self.get_attribs(selectors["phone"], "href")
        phones = list(map(lambda phone: phone.replace("tel:", ""), phones))
        emails = self.__clean_list__(emails)
        phones = self.__clean_list__(phones)
        print("debug")
        
        return emails, phones
        
    def __extract_business_page__(self) -> list:
        """ Extract businesses from page
        
        Returns:
            list: businesses data
            
            Example:
            [
                {
                    "name": "name",
                    "links": ["link1", "link2", ...],
                    "province": "province",
                    "solution": "solution",
                    "cnae": "cnae",
                },
                ...
            ]
        """
                
        selectors = {
            "row": '.views-row',
            "name": '.views-field-nothing-1',
            "link": 'a'
        }
        
        page_data = []
        results = self.get_elems(selectors["row"])
        for result_index in range(len(results)):
            
            # Get each business data
            selector_result = f"{selectors['row']}:nth-child({result_index + 1})"
            selector_name = f"{selector_result} {selectors['name']}"
            selector_links = f"{selector_result} {selectors['link']}"
            
            name = self.get_text(selector_name)
            links = self.get_attribs(selector_links, "href")
            
            # Clean duplicates
            links = self.__clean_list__(links)
            
            # Extract data from each page
            self.open_tab()
            self.switch_to_tab(1)
            emails, phones = [], []
            for link in links:
                new_emails, new_phones = self.__get_contact_info__(link)
                emails += new_emails
                phones += new_phones
            self.close_tab()
            self.switch_to_tab(0)
            
            business_data = {
                "name": name,
                "links": links,
                "province": self.province,
                "solution": self.solution,
                "cnae": self.cnae,
            }
            page_data.append(business_data)
            
        return page_data
    
    def __get_filters_combinations__(self) -> dict:
        """ Create (if not exist) a json file with all filters combinations
        
        Returns:
            dict: filters combinations with id and name by category
            
            Example:
            [
                {
                    "province_id": "id",
                    "province_name": "name",
                    "solution_id": "id",
                    "solution_name": "name",
                    "cnae_id": "id",
                    "cnae_name": "name",
                },
                ...
            ]
        """
        
        # Return data if file exists
        if os.path.exists(self.filters_path):
            with open(self.filters_path, "r") as file:
                return json.load(file)
        
        # Get filters
        filters = self.__get_filters__()
        filters_combinations = []
        filters_provinces = filters["provinces"]
        filters_solutions = filters["solutions"]
        filters_cnae = filters["cnae"]
        
        # Create combinations
        for province in filters_provinces:
            for solution in filters_solutions:
                for cnae in filters_cnae:
                    filters_combinations.append({
                        "province": province,
                        "solution": solution,
                        "cnae": cnae,
                    })
        
        # Save csv file
        with open(self.filters_path, "w", newline="") as file:
            json.dump(filters_combinations, file, indent=4)
            
        # Return filters
        return filters_combinations
    
    def __go_next_page__(self) -> bool:
        """ Go to next page
        
        Returns:
            bool: True if there is a next page, False otherwise
        """
        
        selector_next = '.pager__item--next a'
        next_page_elem = self.get_elem(selector_next)
        if not next_page_elem:
            return False
        
        self.click_js(selector_next)
        self.refresh_selenium()
        
        return True
    
    def __extract_save_data__(self):
        """ Extract data from all pages and save in excel file """
        
        page = 1
        while True:
            
            # Extract businesses from page
            print(f"\tScraping page {page}...")
            page_data = self.__extract_business_page__()
            sleep(5)
            page_data = []
            
            # Go next page
            more_pages = self.__go_next_page__()
            if not more_pages:
                break
            
            # Save data in excel
            self.sheets.write_data(page_data)
            self.sheets.save()
    
    def autorun(self):
        """ Main scraping workflow """
        
        # Extract data with and without filters
        if USE_FILTERS:
            print("Getting data with filters...")
            filters = self.__get_filters_combinations__()
            for filter in filters:
                
                # Show filter status
                status = f"Getting data with filters: {filter['province']}, "
                status += f"{filter['solution']}, {filter['cnae']}..."
                print(status)
                
                # Save filters
                self.province = filter["province"]
                self.solution = filter["solution"]
                self.cnae = filter["cnae"]
                
                # Apply filters
                self.__load_home_page__()
                filter_available = self.__set_filter__()
                if not filter_available:
                    print("\tFilter not available, skipping...")
                    continue
                
                # Extract data
                self.__extract_save_data__()
                
        else:
            print("Getting data without filters...")
            self.__extract_save_data__()
                    

if __name__ == "__main__":
    scraper = Scraper()
    scraper.autorun()