import os
import json
from time import sleep
from dotenv import load_dotenv
from libs.web_scraping import WebScraping
from libs.xlsx import SpreadsheetManager

# Env variables
load_dotenv()
USE_FILTERS = os.getenv("USE_FILTERS", "False") == "True"


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
    
    def __set_filter__(self, province: str, solution: str, cnae: str) -> bool:
        """ Click in filters using the id

        Args:
            province (str): province name
            solution (str): solution name
            cnae (str): cnae name
            
        Returns:
            bool: True if filters were clicked, False otherwise
        """
        
        selectors_wrappers = self.global_selectors["wrappers"]
        filters = {
            selectors_wrappers["provinces"]: province,
            selectors_wrappers["solutions"]: solution,
            selectors_wrappers["cnae"]: cnae,
        }
        
        for filter_wrapper_selector, filter_value in filters.items():
            try:
                self.click_js(f"#{filter}")
            except Exception:
                return False
            self.refresh_selenium(time_units=5)
            
        return True
        
    def __extract_business_page__(self) -> list:
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
    
    def __extract_save_data__(self):
        """ Extract data from all pages and save in excel file """
        
        # Debug
        return True
        
        while True:
            # Extract businesses from page
            page_data = self.__extract_business_page__()
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
        
        # Extract data with and without filters
        if USE_FILTERS:
            print("Getting data with filters...")
            filters = self.__get_filters_combinations__()
            for filter in filters:
                
                # Show filter status
                status = f"Getting data with filters: {filter['province']}, "
                status += f"{filter['solution']}, {filter['cnae']}..."
                print(status)
                
                # Apply filters
                self.__load_home_page__()
                filter_available = self.__set_filter__(
                    filter["province"],
                    filter["solution"],
                    filter["cnae"]
                )
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