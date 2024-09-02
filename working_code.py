import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests

URL = 'https://ngxgroup.com/exchange/trade/equities/listed-companies/'
MAIN_FOLDER = '/Users/amaansah/Documents/test'

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome()
    return driver

# Function to create folders and return a list of companies URLs
def company_folder(driver, base_url):
    driver.get(base_url)
    time.sleep(3)

    # Select 'All' from the dropdown menu to display all entries
    select_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, 'latestdiclosuresListed_length'))
        )
    select = Select(select_element)
    select.select_by_value('-1')  # Select "All"

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    companies = soup.select('table#latestdiclosuresListed tbody tr')

    all_companies_url = []
    folder_names = {}

    os.makedirs(MAIN_FOLDER, exist_ok=True)
    
    for company in companies:
        try:
            name = company.select_one('td a').get_text(strip=True)
            company_url = company.select_one('td a')['href']
            
            sanitized_name = name.replace('/', '_').replace('\\', '_')
            company_folder_path = os.path.join(MAIN_FOLDER, sanitized_name)
            
            os.makedirs(company_folder_path, exist_ok=True)

            all_companies_url.append(company_url)
            folder_names[company_url] = sanitized_name
        
        except Exception as e:
            print(f'Error processing company {name}: {e}')
    
    return all_companies_url, folder_names

# Function to create JSON file
def JSON_file(driver, url, folder_names):
    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    profile_data = {}
    profile_table = soup.select_one('table.table')
    
    if profile_table:
        rows = profile_table.select('tbody tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) == 2:
                key = cells[0].get_text(strip=True).replace(':', '')
                value = cells[1].get_text(strip=True)
                profile_data[key] = value

    sanitized_name = folder_names.get(url, url.split('/')[-1])
    company_folder_path = os.path.join(MAIN_FOLDER, sanitized_name)
    
    json_path = os.path.join(company_folder_path, 'profile.json')
    
    with open(json_path, 'w') as json_file:
        json.dump(profile_data, json_file, indent=4)



def save_pdfs(driver, table_name, sanitized_name, dropdown_name, folder_name, tab_xpath):
    print("Entering save pdf function")
    try:
        section_span = driver.find_element(By.XPATH, tab_xpath)
        driver.execute_script("arguments[0].click();", section_span)
        time.sleep(5)
        
        select_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.NAME, dropdown_name))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", select_element)
        
        select = Select(select_element)
        select.select_by_value('-1')  # Select "All"

        print("Waiting for new page")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href$=".pdf"]'))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        print(f"Processing {folder_name} for {sanitized_name}")

        pdf_links = soup.select(f'table#{table_name} tbody tr')

        if not pdf_links:
            print(f"No PDF links found for {folder_name} in {sanitized_name}.")
            return

        pdf_folder_path = os.path.join(MAIN_FOLDER, sanitized_name, folder_name)
        os.makedirs(pdf_folder_path, exist_ok=True)

        for pdf_link in pdf_links:
            pdf_url = pdf_link.find('a')['href'] if pdf_link.find('a') else None
            if not pdf_url:
                continue
            if not pdf_url.startswith('http'):
                pdf_url = f"{URL}{pdf_url}"
            pdf_name = pdf_url.split('/')[-1]
            pdf_path = os.path.join(pdf_folder_path, pdf_name)

            try:
                pdf_response = requests.get(pdf_url)
                with open(pdf_path, 'wb') as pdf_file:
                    pdf_file.write(pdf_response.content)
                print(f"Downloaded: {pdf_name}")
            except Exception as e:
                print(f"Error downloading {pdf_name}: {e}")

    except Exception as e:
        print(f"Error processing documents for {folder_name} in {sanitized_name}: {e}")

# Main execution
driver = setup_driver()
try:
    all_companies_url, folder_names = company_folder(driver, URL)
    print(f'Total companies found: {len(all_companies_url)}')

    if all_companies_url:
        first_link = all_companies_url[2]
        print(f'Processing first link: {first_link}')
        
        JSON_file(driver, first_link, folder_names)

        print("Loop")
        driver.get(first_link)
        
        
        # Download PDFs from each tab using the save_pdfs function
        #save_pdfs(driver, 'financialstatement', folder_names[first_link], 'financialstatement_length', 'Financials_Statements', "//span[text()='Financials Statements']")
        #save_pdfs(driver, 'latestdisclosures', folder_names[first_link], 'latestdisclosures_length', 'Corporate_Disclosures', "//span[text()='Corporate Disclosures']")
        save_pdfs(driver, 'latestdiclosuresDir', folder_names[first_link], 'latestdiclosuresDir_length', 'Director_Dealings', "//span[text()='Director Dealings']")

finally:
    driver.quit()