import os
import json
from time import sleep
from dotenv import load_dotenv
from libs.web_scraping import WebScraping
from libs.xlsx import SpreadsheetManager

# Env variables
load_dotenv()
USE_FILTERS = os.getenv("USE_FILTERS", "False") == "True"


# Paths
CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))


class Scraper(WebScraping):
    
    def __init__(self):
        
        # Pages
        self.home = "https://www.acelerapyme.gob.es/kit-digital/catalogo-digitalizadores"
        
        # Initialize and load home page
        super().__init__()
        self.set_page(self.home)
        self.refresh_selenium()
        
        # Files paths
        self.filters_path = os.path.join(CURRENT_FOLDER, "filters.json")
        self.sheets_path = os.path.join(CURRENT_FOLDER, "data.xlsx")
        
        # Spreadsheet manager
        self.sheets = SpreadsheetManager(self.sheets_path)
        
        # Create sheet
        sheet_name = "businesses filters" if USE_FILTERS else "Businesses"
        self.sheets.create_set_sheet(sheet_name)
        
    def __get_filters__(self) -> dict:
        """ Get filters from the page

        Returns:
            dict: filters with id and name by category
            
            Example:
            {
                "solutions": {
                    "id": "name",
                    ...
                },
                "provinces": {
                    "id": "name",
                    ...
                },
                "cnae": {
                    "id": "name",
                    ...
                },
            }
        """
        
        print("Getting filters...")
        
        selectors = {
            "wrappers": {
                "solutions": '.block-facet-blocktipo-solucion-kit-digital',
                "provinces": '.block-facet-blockprovincia-opera-digitalizador',
                "cnae": '.block-facet-blockcnae-opera-digitalizador',
            },
            "filter_elem": '.facet-item a span',
        }
        
        self.refresh_selenium()
        
        # Loop wrappers
        items = {}
        for wrapper_name, wrapper_selector in selectors["wrappers"].items():
            
            items_wrapper = {}
            selector_items = f"{wrapper_selector} {selectors['filter_elem']}"
            items_elems = self.get_elems(selector_items)
            for item_elem in items_elems:
                text = item_elem.text
                id = item_elem.get_attribute("id")
                if not (id and text):
                    continue
                items_wrapper[id] = text
            
            items[wrapper_name] = items_wrapper
        
        return items
    
    def set_filter(self, province: str, solution: str, cnae: str):
        """ Click in filters using the id

        Args:
            province (str): province id
            solution (str): solution id
            cnae (str): cnae id
        """
        
        self.click_js(f"#{province}")
        self.refresh_selenium()
        self.click_js(f"#{solution}")
        self.refresh_selenium()
        self.click_js(f"#{cnae}")
        self.refresh_selenium()
        
    def go_next_filter(self, selector_wrapper: str):
        """ Click in the next filter

        Args:
            selector_wrapper (str): selector of the filter wrapper
        """
        
        selectors = {
            "filter_elem": '.facet-item a span',
            "filter_elem_active": '.facet-item a.is-active span',
        }
        
        selector_active = f"{selector_wrapper} {selectors['filter_elem_active']}"
        selector_filters = f"{selector_wrapper} {selectors['filter_elem']}"
        
        # Check if there is a filter active
        filter_activated = self.get_elems(selector_active)
        if not filter_activated:
            # Click first filter
            self.click_js(selector_filters)
            self.refresh_selenium()
            return True
        
        # Click next filter
        filters_elems = self.get_elems(f"{selector_wrapper} {selectors['filter_elem']}")
        last_filter_found = False
        last_filter_id = ""
        for filter_elem in filters_elems:
            
            # Found last element
            if filter_elem.text == filter_activated[0].text:
                last_filter_found = True
                last_filter_id = filter_elem.get_attribute("id")
                continue
            
            # Deactivate last filter and activate current
            if last_filter_found:
                elem_id = filter_elem.get_attribute("id")
                for id in [last_filter_id, elem_id]:
                    self.click_js(f"#{id}")
                    self.refresh_selenium()
                break
            
        return last_filter_found
    
    def extract_business_page(self) -> list:
        pass
    
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
        for province_id, province_name in filters_provinces.items():
            for solution_id, solution_name in filters_solutions.items():
                for cnae_id, cnae_name in filters_cnae.items():
                    filters_combinations.append({
                        "province_id": province_id,
                        "province_name": province_name,
                        "solution_id": solution_id,
                        "solution_name": solution_name,
                        "cnae_id": cnae_id,
                        "cnae_name": cnae_name,
                    })
        
        # Save csv file
        with open(self.filters_path, "w", newline="") as file:
            json.dump(filters_combinations, file, indent=4)
            
        # Return filters
        return filters_combinations
    
    def extract_data(self):
        """ Extract data from all pages and save in excel file """
        
        while True:
            # Extract businesses from page
            page_data = self.extract_business_page()
            sleep(5)
            
            # Go next page
            more_pages = self.go_next_page()
            if not more_pages:
                break
            
            # Save data in excel
            self.sheets.write_data(page_data)
            self.sheets.save()
    
    def autorun(self):
        """ Main scraping workflow """
        
        if USE_FILTERS:
            filters = self.__get_filters_combinations__()
            for filter in filters:
                
                # Apply filters
                self.set_filter(
                    filter["province_id"],
                    filter["solution_id"],
                    filter["cnae_id"]
                )
                
                # Extract data
                self.extract_data()
                
        else:
            # Extract without filters
            self.extract_data()
                    

if __name__ == "__main__":
    scraper = Scraper()
    scraper.autorun()