from datetime import date, timedelta
import io
import PyPDF2
from web_scrape import academic_calendar_get
from forms import days_of_week

def parse_to_ints(repeat_on_days: str) -> list:
    """
    This function parses string literals describing the days of the week
    into integers so that form data using multiple repeats is compatible
    with the datetime.datetime.weekday() outputs.
    """
    to_return = []
    curr = 0
    for day_of_week in days_of_week:
        if day_of_week in repeat_on_days:
            to_return.append(curr)
        curr += 1
    return to_return

def color_assign(course_id: int) -> str:
    """
    Given the course_id number, return a string containing the course's assigned color.
    """

    """offset = 75
    total = 0
    for c in course_name:
        total += hash(c)
    color_value_list = []
    for i in range(3):
        color_value_list.append(max((total % 1000) % 255, offset))
        total //= 1000
    return f"rgb({color_value_list[0]},{color_value_list[1]},{color_value_list[2]})" """
    # rgb(75,242,102) -- rgb(117,180,215)
    # print(course_name + f": {total} => " + f"rgb({color_value_list[0]},{color_value_list[1]},{color_value_list[2]})")

    # list_of_colors = ["rgb(0,205,112)", "rgb(52,144,194)", "rgb(252,225,56)", "rgb(213, 98, 85)", "rgb(57, 126, 135)", "rgb(50,187,76)", "rgb(180,162,95)"]
    list_of_colors = ["rgb(153,0,0)", "rgb(0,153,0)", "rgb(0,0,153)", "rgb(0,153,153)", "rgb(153,76,0)", "rgb(102,0,102)", "rgb(153,153,0)"]
    return list_of_colors[course_id % 7]

def format_for_home(l: list) -> list:
    """
    Given a 1d list of items, return a list of 2d items such that each inner list has at most six items.
    """
    to_return = []
    if len(l) % 6 == 0:
        count = -1
        for i in range(len(l)):
            if i % 6 == 0:
                count += 1
                to_return.append([l[i]])
            else:
                to_return[count].append(l[i])
        return to_return
    rows = len(l) // 6 + 1
    columns = len(l) // rows
    iterable = iter(l)
    for i in range(rows):
        to_return.append([])
        for j in range(columns):
            to_return[i].append(next(iterable))
    end = rows - 1
    while True:
        try:
            to_return[end].append(next(iterable))
        except StopIteration:
            break
    return to_return

Standard_Error = 1000

def average(lst: list):
    """
    For a given lst of real numbers, compute their average. Uses knowledge of what values go into
    the database, interval [ 0.0 , 10.0 ], and that the default grade value is -1.
    """
    if not lst:
        return -1, False
    sum = 0
    count = len(lst)
    fully_graded = True
    for i in lst:
        if i != -1:
            sum += i
        elif count > 1:
            count -= 1
            fully_graded = False
    return num_process(float(sum) / float(count), Standard_Error), fully_graded

def parse_to_str(integer: int) -> str:
    """ Returns the day of the week associated to the number [0, 6] -> [Mo, Su]"""
    return days_of_week[integer]

def num_process(num, error=10) -> int:
    return round(num*error)/error


def formate_course_grade_data(list_of_breakdown: list) -> dict:
    """
    Function that takes in a list of rubric items and returns a formatted JSON dictionary to store course grading metadata
    """
    dict_to_return = {}
    for rubric in list_of_breakdown:
        dict_to_return[rubric] = {"Grade": 0, "Weight": 0, "Fully Graded": False, "Course Policy": "", "Rubric Score": -1}
    dict_to_return["Total"] = {"Grade": "", "Weight": 1, "Fully Graded": False, "Course Policy": "", "Rubric Score": -1}
    return dict_to_return

def format_course_dirty(list_of_breakdown: list) -> dict:
    """ Return a JSON dictionary mapping rubric items to 0 """
    return {r: 0 for r in list_of_breakdown}


def academic_calendar(semester_str: str) -> dict:
    """
    This function accesses and reads the UC Berkeley Academic Calendar PDFs found online and retrieves 
    semester start and end dates as well as holidays.
    """
    month_dict = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    
    if semester_str[:2] == "fa":
        prev = semester_str[2:]
        next = str(int(semester_str[2:]) + 1)
        name = "Fall"
        year = f"20{prev}"
        spring = False
        summer = False
    else:
        prev = str(int(semester_str[2:]) - 1)
        next = semester_str[2:]
        year = f"20{next}"
        if semester_str[:2] == "sp":
            name = "Spring"
            spring = True
            summer = False
        else:
            name = "Summer"
            spring = False
            summer = True
    url = f"https://registrar.berkeley.edu/wp-content/uploads/UCB_AcademicCalendar_20{prev}-{next}.pdf"
    page = academic_calendar_get(url)
    if page is None:
        return {"Holidays": [], "Start": "", "End": ""}
    with io.BytesIO(page.content) as f:
        pdf = PyPDF2.PdfReader(f)
        pdf_content = pdf.pages[0].extract_text()
    list_of_words_unprocessed = pdf_content.split("\n")
    list_of_words = []
    length = len(list_of_words_unprocessed)
    for i in range(length): #Because of PDF format, make a list where each entry is a word of the pdf
        phrase = list_of_words_unprocessed[i].split(" ")
        if len(phrase[0]) == 1: #Each item in the list phrase is a single character --> phrase is one word
            list_of_words.append("".join(phrase)) #Remove spaces
        else: #Each item in the list phrase is already a word --> phrase is a line
            list_of_words.extend(phrase) #Replace it with the phrase separated into words

    pointer = 1
    if summer:
        while (year != list_of_words[pointer-1]) or (name != list_of_words[pointer]) or ("Sessions" != list_of_words[pointer+1]):
            pointer += 1
    else:
        while (year != list_of_words[pointer-1]) or (name != list_of_words[pointer]) or ("Semester" != list_of_words[pointer+1]):
            pointer += 1
    year = int(year)
    pointer += 1
    if summer:
        while ("(Eight" != list_of_words[pointer-2]) or ("Weeks)" != list_of_words[pointer-1]) or ("Begins" != list_of_words[pointer]):
            pointer += 1
    else:
        while ("Instruction" != list_of_words[pointer-1]) or ("Begins" != list_of_words[pointer]):
            pointer += 1
    pointer += 2
    month = month_dict[list_of_words[pointer][:3]]
    pointer += 1
    day = int(list_of_words[pointer][:-1])
    start_date = date(year, month, day)
    pointer += 2
    
    holidays = set()
    while True:
        prev_word = list_of_words[pointer-1]
        curr_word = list_of_words[pointer]
        if "Holiday" == curr_word or ("Non-Instructional" == prev_word and "Day" == curr_word):
            pointer += 2
            month = month_dict[list_of_words[pointer][:3]]
            pointer += 1
            try:
                day = int(list_of_words[pointer])
            except ValueError:
                day = int(list_of_words[pointer][:-1])
            holidays.add(str(date(year, month, day)))
            pointer += 1
            if list_of_words[pointer] == "&":
                pointer += 2
                month = month_dict[list_of_words[pointer][:3]]
                pointer += 1
                try:
                    day = int(list_of_words[pointer])
                except ValueError:
                    day = int(list_of_words[pointer][:-1])
                holidays.add(str(date(year, month, day)))
                pointer += 1
        elif spring and ("Spring" == prev_word and "Recess" == curr_word):
            #Start date of spring break
            pointer += 2
            month = month_dict[list_of_words[pointer][:3]]
            pointer += 1
            try:
                day = int(list_of_words[pointer][:2])
            except ValueError:
                day = int(list_of_words[pointer][0])
            begin = date(year, month, day)
            holidays.add(str(begin))
            #End date of spring break
            pointer += 1
            month = month_dict[list_of_words[pointer][:3]]
            pointer += 1
            try:
                day = int(list_of_words[pointer][:2])
            except ValueError:
                day = int(list_of_words[pointer][0])
            end = date(year, month, day)
            #Days in between
            plus_one = timedelta(days=1)
            while begin < end:
                begin = begin + plus_one
                holidays.add(str(begin))
            holidays.add(str(end))
            pointer += 1
        elif ("Semester" == prev_word and "Ends" == curr_word) or (summer and ("E" == prev_word and "End" == curr_word)):
            pointer += 2
            month = month_dict[list_of_words[pointer][:3]]
            pointer += 1
            day = int(list_of_words[pointer][:-1]) + 1
            end_date = date(year, month, day)
            break
        pointer += 1
    
    return {"Holidays": sorted(list(holidays), key=lambda d: d), "Start": start_date, "End": end_date}

def debug_academic_calendar():
    list_of_words_unprocessed = ['2023-24 BERKELEY ACADEMIC CALENDAR ', '2023 Fall Semester ', 'Fall Semester Begins Wednesday, August 16, 2023', 'Convocation To Be Determined', 'Instruction Begins Wednesday, August 23, 2023', 'Academic and Administrative Holiday Monday, September 4, 2023', 'Academic and Administrative Holiday Friday, November 10, 2023', 'Non-Instructional Day Wednesday, November 22, 2023', 'Academic and Administrative Holiday Thursday, November 23 & Friday, November 24, 2023', 'Formal Classes End Friday, December 1, 2023', 'Reading/Review/Recitation Week Monday, December 4–Friday, December 8, 2023', 'Last Day of Instruction Friday, December 8, 2023', 'Final Examinations Monday, December 11–Friday, December 15, 2023', 'Fall Semester Ends Friday, December 15, 2023', 'Winter Commencement To Be Determined, commencement.berkeley.edu', 'Academic and Administrative Holiday++ Monday, December 25 & Tuesday, December 26, 2023', 'Academic and Administrative Holiday++ Monday, January 1 & Tuesday, January 2, 2024', '2024 Spring Semester ', 'Spring Semester Begins Tuesday, January 9, 2024', 'Academic and Administrative Holiday Monday, January 15, 2024', 'Instruction Begins Tuesday, January 16, 2024', 'Academic and Administrative Holiday Monday, February 19, 2024', 'Spring Recess Monday, March 25–Thursday, March 28, 2024', 'Academic and Administrative Holiday Friday, March 29, 2024', 'Cal Day To Be Determined, calday.berkeley.edu', 'Formal Classes End Friday, April 26, 2024', 'Reading/Review/Recitation Week Monday, April 29–Friday, May 3, 2024', 'Last Day of Instruction Friday, May 3, 2024', 'Final Examinations Monday, May 6–Friday, May 10, 2024', 'Spring Semester Ends Friday, May 10, 2024', 'Commencement Saturday, May 11, 2024', '2024 Summer Sessions ', 'Session A (Six Weeks) Begins Monday, May 20, 2024', 'Academic and Administrative Holiday Monday, May 27, 2024', 'Session B (Ten Weeks) Begins Monday, June 3, 2024', 'Session C (Eight Weeks) Begins Monday, June 17, 2024', 'Academic and Administrative Holiday Wednesday, June 19, 2024', 'Session A Ends Friday, June 28, 2024', 'Session D (Six Weeks) Begins Monday, July 1, 2024', 'Session F (Three Weeks) Begins Monday, July 1, 2024', 'Academic and Administrative Holiday Thursday, July 4, 2024', 'Session F Ends Friday, July 19, 2024', 'Session E (Three Weeks) Begins Monday, July 22, 2024', 'Sessions B, C, D, and E End Friday, August 9, 202 4', '++ = Pending approval                          Produced by the Office of the Registrar, October 14, 2021']
    list_of_words = []
    length = len(list_of_words_unprocessed)
    for i in range(length): #Because of PDF format, make a list where each entry is a word of the pdf
        phrase = list_of_words_unprocessed[i].split(" ")
        list_of_words.extend(phrase) #Replace it with the phrase separated into words
        
    year = "2023"
    name = "Fall"
    month_dict = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

    pointer = 1
    while (year != list_of_words[pointer-1]) or (name != list_of_words[pointer]) or ("Semester" != list_of_words[pointer+1]):
        pointer += 1
    year = int(year)
    pointer += 1
    while ("Instruction" != list_of_words[pointer-1]) or ("Begins" != list_of_words[pointer]):
        pointer += 1
    pointer += 5
    
    holidays = set()
    while True:
        prev_word = list_of_words[pointer-1]
        curr_word = list_of_words[pointer]
        #input(prev_word + " " + curr_word)
        if "Holiday" == curr_word or ("Non-Instructional" == prev_word and "Day" == curr_word):
            pointer += 2
            month = month_dict[list_of_words[pointer][:3]]
            pointer += 1
            try:
                day = int(list_of_words[pointer])
            except ValueError:
                day = int(list_of_words[pointer][:-1])
            holidays.add(",".join([str(year), str(month), str(day)]))
            pointer += 1
            if list_of_words[pointer] == "&":
                pointer += 2
                month = month_dict[list_of_words[pointer][:3]]
                pointer += 1
                try:
                    day = int(list_of_words[pointer])
                except ValueError:
                    day = int(list_of_words[pointer][:-1])
                holidays.add(",".join([str(year), str(month), str(day)]))
                pointer += 1
        elif ("Semester" == prev_word and "Ends" == curr_word):
            break
        pointer += 1
        
    print(holidays)

def convert(list_rubric):
    dict_str = str({r: 0 for r in list_rubric})
    as_array = []
    for s in dict_str:
        if s == "'":
            as_array.append('"')
        else:
            as_array.append(s)
    return "".join(as_array)

def convert2(l):
    to_return = {}
    for section in l:
        to_return[section[3]] = {"Week Days": section[0], "Time": section[1], "Location": section[2]}
    dict_str = str(to_return)
    as_array = []
    for s in dict_str:
        if s == "'":
            as_array.append('"')
        else:
            as_array.append(s)
    return "".join(as_array)