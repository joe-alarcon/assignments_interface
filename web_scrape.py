import requests
import json
from bs4 import BeautifulSoup

def get_course_information(url_string: str) -> list[str]:
    try:
        div1 = get_html_element_from_class(url_string, "handlebarData theme_is_whitehot")
    except requests.ConnectionError:
        return ["", "", ""]

    j = json.loads(div1['data-json'])
    unparsed_info = j['meetings'][0]

    week_days = unparsed_info['meetsDays']
    time = unparsed_info['startTime'] + " - " + unparsed_info['endTime']
    location = unparsed_info['location']['description']

    return [week_days, time, location]


def get_news_world():
    to_return = []
    try:
        to_return.extend(get_news_w_nyt())
    except requests.ConnectionError:
        pass
    return to_return

def get_news_us():
    to_return = []
    try:
        to_return.extend(get_news_us_nyt())
    except requests.ConnectionError:
        pass
    return to_return

def get_html_element_from_class(url_string, class_str):
    page = requests.get(url_string)
    soup = BeautifulSoup(page.content, 'html.parser')
    return soup.find(class_=class_str)

# NYT Functions
def get_news_us_nyt():
    ol1 = get_html_element_from_class(get_url_str_nyt("us"), "css-11jjg eb97p612")
    h2_elements = ol1.find_all(class_="css-1lktipf ef62v182")
    h2_elements.extend(ol1.find_all(class_="css-1lktipf ef62v183"))
    return return_formatted_info_nyt(h2_elements)

def get_news_w_nyt():
    ol1 = get_html_element_from_class(get_url_str_nyt("world"), "css-11jjg eb97p612")
    h2_elements = ol1.find_all(class_="css-n0sicn e1hr934v1")
    return return_formatted_info_nyt(h2_elements)

def get_url_str_nyt(section):
    return f"https://www.nytimes.com/international/section/{section}"

def return_formatted_info_nyt(title_elements):
    titles = []
    for element in title_elements:
        a_element = element.find("a")
        title = a_element.get_text()
        link = f"https://www.nytimes.com{a_element['href']}"
        titles.append((title, link))
    return titles

def academic_calendar_get(url):
    try:
        return requests.get(url)
    except requests.ConnectionError:
        return None
    