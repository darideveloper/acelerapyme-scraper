from dotenv import load_dotenv
from libs.web_scraping import WebScraping

load_dotenv()


class Scraper(WebScraping):
    
    def __init__(self):
        
        # Pages
        self.home = "https://www.acelerapyme.gob.es/kit-digital/"
        self.home += "catalogo-digitalizadores?f%5B0%5D=provincia_opera_digitalizador"
        self.home += "%3A8624#digitalizador"
        
        # Initialize and load home page
        super().__init__()
        self.set_page(self.home)
        
    def get_filters(self) -> dict:
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
        pass
    
    def extract_business(self) -> list:
        pass
    
    def autorun(self):
        """ Main scraping workflow """
        
        # Get page filters
        filters = self.get_filters()
        print(filters)
    

if __name__ == "__main__":
    scraper = Scraper()
    scraper.autorun()