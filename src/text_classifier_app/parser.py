from time import sleep

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from fake_useragent import UserAgent
from selenium.webdriver.common.by import By


source_name2tag = {
    "dzen.ru": {"class": "news-story-redesign__summarization-item"},
    "ria.ru": {"class": "article__block"},
    "news.mail.ru": {"tag": "p"}
}

def parse_page(url: str):

    web_site_name = url.split('/')[2]

    print(f"url: {url}")

    if web_site_name not in source_name2tag:
        return {
            'status':
                {
                    "code": 1,
                    "message": "Список поддерживаемых сайтов: {}".format(", ".join(source_name2tag.keys()))
                },
            'content':
                {
                'paragraphs': None
                }
        }

    # Specify the user agent string (if needed)
    user_agent = "your_user_agent_here"

    # Create a ChromeOptions object
    options = webdriver.ChromeOptions()

    # Set the user agent (if needed)
    options.add_argument(f'--user-agent={user_agent}')

    # # Add headless argument to run browser in headless mode
    options.add_argument('--headless')

    # # Add arguments to run browser in fullscreen mode
    options.add_argument('--start-fullscreen')

    # Create a WebDriver instance with the specified options
    driver = webdriver.Chrome(options=options)

    driver.get(url)

    # Wait for the page to load
    sleep(5)  # Adjust the sleep time based on your internet speed and page load time

    for key, value in source_name2tag[web_site_name].items():
        if key == 'class':
            elements = driver.find_elements(By.CLASS_NAME, value)
        elif key == 'tag':
            elements = driver.find_elements(By.TAG_NAME, value)
        if elements:
            break

    paragraphs = []
    # Iterate through the elements and print their text content
    for element in elements:
        if element.text:
            paragraphs.append(element.text)

    # Close the driver
    driver.quit()

    return {
        'status':
            {
                "code": 0,
                "message": "success"
            },
        'content':
            {
                'paragraphs': "\n".join(paragraphs)
            }
    }
