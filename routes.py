from app import app, db, login_manager
from flask import request, render_template, flash, redirect, url_for
from sqlalchemy.orm.attributes import flag_modified
from models import *
from flask_login import current_user, login_user, logout_user, login_required, UserMixin
from forms import *
from werkzeug.urls import url_parse
from datetime import timedelta, date
import calendar
from web_scrape import *
from function_utils import *

news_dict = {"world": [], "us": []}
update_dict = {"recorded_date": date.today(), "previous_referral": "/"}

def update_tasks_events():
    with app.app_context():
        Task.update_overdue_tasks()
        # Event.delete_past_events()

def daily_updates():
    update_tasks_events()
    news_dict["world"] = []
    news_dict["us"] = []

# Call update tasks events when initializing the program.
daily_updates()

########### ###### ###########
###########  HOME  ###########
########### ###### ###########

@app.route('/', methods=['GET', 'POST'])
def home():
    today_tasks = Task.get_all_today_tasks()
    pending_tasks = Task.get_all_tasks()
    overdue_tasks = Task.get_all_overdue()
    todays = Birthdays.today_birthdays()

    if update_dict["recorded_date"] < date.today() or not update_dict["recorded_date"]:
        daily_updates()
        update_dict["recorded_date"] = date.today()

    semester_form = SemesterForm()
    if semester_form.validate_on_submit():
        semester_string = semester_form.season.data + str(semester_form.year.data)
        semester_data = academic_calendar(semester_string)
        new_semester = Semester(name=semester_string, holidays=semester_data["Holidays"],
                                start=semester_data["Start"], end=semester_data["End"], active=0)
        db.session.add(new_semester)
        db.session.commit()
        return redirect(f"/semester/{semester_string}")

    todoform_ = ToDoForm()
    if todoform_.validate_on_submit():
        title = todoform_.title.data
        priority = todoform_.priority.data
        date_ = todoform_.date.data
        time_ = todoform_.time.data
        if priority is not None:
            new_task = Task(title=title, priority=priority, date=date_, time=time_, overdue=False)
        # elif priority is not None:
        #     new_task = Task(title=title, priority=priority)
        # elif include_date:
        #     new_task = Task(title=title, date=date_, time=time_, overdue=False)
        else:
            new_task = Task(title=title, date=date_, time=time_, overdue=False)
        db.session.add(new_task)
        db.session.commit()
        return redirect("/")

    return render_template('home.html', semesters_by_year=format_for_home(Semester.get_all()), today=Assignment.assignments_due_today(),
                           sem_form=semester_form, exams_in_a_week=Examination.exams_in_a_week(),
                           color_assign=color_assign, todoform=todoform_, p_tasks=pending_tasks, t_tasks=today_tasks,
                           o_tasks=overdue_tasks, overdue_assignments=Assignment.overdue_assignments_not_done(),
                           today_bdays=todays, exams_today=Examination.exams_today())


########### ###### ###########
###########  HOME  ###########
########### ###### ###########



########### ########### ###########
###########  REMINDERS  ###########
########### ########### ###########

@app.route('/reminders', methods=['GET', 'POST'])
def reminder_route():
    reminderform_ = ReminderForm()
    if reminderform_.validate_on_submit():
        content_ = reminderform_.content.data
        link_ = reminderform_.link.data
        if not isinstance(link_, str):
            link_ = ""
        new_reminder = Reminder(content=content_, link=link_)
        db.session.add(new_reminder)
        db.session.commit()
        return redirect("/reminders")
    
    return render_template('reminders.html', reminders=Reminder.all(), reminderform=reminderform_)

@app.route('/update_reminder_<int:num>', methods=['GET', 'POST'])
def update_rem(num):
    rem = Reminder.get(num)
    update_form = UpdateReminderForm()
    if update_form.is_submitted():
        if update_form.delete.data:
            db.session.delete(rem)
            db.session.commit()
            return redirect(url_for("reminder_route"))

        new_content = update_form.content.data
        if new_content:
            rem.content = new_content
        new_link = update_form.link.data
        if new_link:
            rem.link = new_link
        db.session.commit()
        return redirect(url_for("reminder_route"))
    
    return render_template("update_event.html", event_bool=False, up_form=update_form)


########### ########### ###########
###########  REMINDERS  ###########
########### ########### ###########



########### ###### ###########
###########  NEWS  ###########
########### ###### ###########

@app.route('/news', methods=['GET'])
def news():
    if news_dict["world"] == []:
        news_dict["world"] = get_news_world()
    if news_dict["us"] == []:
        news_dict["us"] = get_news_us()
    return render_template('news.html', w_news=news_dict["world"], us_news=news_dict["us"])



########### ######## ###########
###########  EVENTS  ###########
########### ######## ###########

@app.route('/events', methods=['GET', 'POST'])
def events():
    today_events = Event.get_all_today_events()
    week_events = Event.get_events_this_week()

    event_form = EventForm()
    if event_form.is_submitted():
        title = event_form.title.data
        location = event_form.location.data
        date_ = event_form.date.data
        time_ = event_form.time.data
        new_event = Event(title=title, location=location, date=date_, time=time_)
        db.session.add(new_event)
        db.session.commit()

        repeat_on_days = event_form.repeat_days_of_week.data
        end_date = event_form.end_repeat.data
        if repeat_on_days != [] and end_date is not None:
            repeat_on_days = parse_to_ints(repeat_on_days)
            plus_a_day = timedelta(days=1)
            date_ = date_ + plus_a_day
            while date_ < end_date:
                if date_.weekday() in repeat_on_days:
                    new_event = Event(title=title, location=location, date=date_, time=time_)
                    db.session.add(new_event)
                    db.session.commit()
                date_ = date_ + plus_a_day

        return redirect(url_for('events'))

    return render_template('events.html', today_events=today_events, week_events=week_events, event_form=event_form)

@app.route('/update_event_<int:num>', methods=['GET', 'POST'])
def update_event(num):
    event = Event.get_from_id(int(num))
    update_form = UpdateEventForm()

    if update_form.is_submitted():
        if update_form.delete.data:
            db.session.delete(event)
            db.session.commit()
            return redirect(url_for("events"))

        new_name = update_form.title.data
        if new_name:
            event.title = new_name
        new_loc = update_form.location.data
        if new_loc:
            event.location = new_loc
        new_date = update_form.date.data
        if new_date:
            event.date = new_date
        new_hour = update_form.time.data
        if new_hour:
            event.time = new_hour
        db.session.commit()
        return redirect(url_for("events"))

    return render_template("update_event.html", event_bool=True, up_form=update_form, event=event)


########### ######## ###########
###########  EVENTS  ###########
########### ######## ###########



########### ########## ###########
###########  CALENDAR  ###########
########### ########## ###########

@app.route('/calendar', methods=['GET', 'POST'])
def calendar_route():
    semester_ = Semester.get_active_semester()
    all_pending_tasks = Task.get_all_pending()
    all_exams = {}
    all_assignments = {}
    all_events = {}
    all_tasks = {}
    curr_date = date.today()
    one_day = timedelta(days=1)

    if semester_ is not None:
        sem_assignments = semester_.get_all_semester_assignments()
        sem_exams = semester_.get_all_semester_exams()

    for i in range(14):
        if semester_ is not None:
            all_exams[curr_date] = [task for task in sem_exams if task.date == curr_date]
            all_assignments[curr_date] = [task for task in sem_assignments if task.due == curr_date]
        all_tasks[curr_date] = [task for task in all_pending_tasks if task.date == curr_date]
        if i == 0:
            all_tasks[curr_date].extend(Task.get_all_overdue())
        all_events[curr_date] = Event.events_from_given_day(curr_date)[:]
        curr_date = curr_date + one_day

    day_info = {}
    search_form = DateSearchForm()
    if search_form.validate_on_submit():
        form_date = search_form.date.data
        semester_from_day = Semester.get_semester_from_day(form_date)
        day_tasks = Task.get_tasks_day(form_date)
        day_of_week = parse_to_str(form_date.weekday())
        day_schedule = []
        day_assignments = []
        day_exams = []

        if semester_from_day is not None:
            day_assignments = semester_from_day.get_assignments_day(form_date)
            day_exams = semester_from_day.get_exams_day(form_date)
            if form_date not in semester_from_day.get_holidays():
                for course in semester_from_day.courses:
                    for key, section in course.get_course_information().items():
                        if day_of_week in section["Week Days"]:
                            day_schedule.append({"Name": course.name, "Description": key, "Data": section})
            else:
                day_schedule.append({"Name": "No Classes", "Data": {"Time": "00:00:00", "Location": ""}, "Description": "Holiday"})

        for event in Event.events_from_given_day(form_date):
            day_schedule.append({"Name": event.title, "Data": {"Time": str(event.time), "Location": str(event.location), "ID": event.id}, "Description": "Event"})
        try:
            day_schedule.sort(key=lambda section: section["Data"]["Time"])
        except KeyError:
            pass
        day_info = {"assignments": day_assignments, "exams": day_exams, "tasks": day_tasks, "schedule": day_schedule, 
                    "in_date": str(form_date)}

    return render_template('calendar.html', all_assignments=all_assignments, all_exams=all_exams,
     all_tasks=all_tasks, all_events=all_events, list=list, parse_to_str=parse_to_str, search_form=search_form,
     day_info=day_info)


########### ########## ###########
###########  CALENDAR  ###########
########### ########## ###########



########### ########## ###########
###########  SCHEDULE  ###########
########### ########## ###########

@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    today = date.today()
    semester_ = Semester.get_active_semester()
    if semester_ is None:
        semester_ = Semester.get_semester_from_day(today)
    today_sections = []
    tomorrow_sections = []
    today_day_of_week = parse_to_str(today.weekday())
    tomorrow = today + timedelta(days=1)
    tomorrow_day_of_week = parse_to_str(tomorrow.weekday())

    if semester_ is not None:
        sem_courses = sorted(semester_.courses, key=lambda x: x.name)
        holidays = semester_.get_holidays()
        for course in sem_courses:
            for key, section in course.get_course_information().items():
                if today_day_of_week in section["Week Days"] and (today not in holidays):
                    today_sections.append({"Name": course.name, "Description": key, "Data": section})
                if tomorrow_day_of_week in section["Week Days"] and (tomorrow not in holidays):
                    tomorrow_sections.append({"Name": course.name, "Description": key, "Data": section})

    for event in Event.get_all_today_events():
        today_sections.append({"Name": event.title, "Data": {"Time": str(event.time), "Location": str(event.location)}, "Description": "Event"})
    for event in Event.events_from_given_day(tomorrow):
        tomorrow_sections.append({"Name": event.title, "Data": {"Time": str(event.time), "Location": str(event.location)}, "Description": "Event"})

    today_sections.sort(key=lambda section: section["Data"]["Time"])
    tomorrow_sections.sort(key=lambda section: section["Data"]["Time"])

    return render_template('schedule.html', today_sections=today_sections,
    tomorrow_sections=tomorrow_sections)


########### ########## ###########
###########  SCHEDULE  ###########
########### ########## ###########



########### ########### ###########
###########  BIRTHDAYS  ###########
########### ########### ###########

@app.route('/birthdays', methods=['GET', 'POST'])
def birthdays():
    todays = Birthdays.today_birthdays()
    months = Birthdays.birthdays_this_month()
    bday_form = AddBirthday()

    if bday_form.validate_on_submit():
        name = bday_form.name.data
        bday = bday_form.date.data
        new_bday = Birthdays(name=name, date=bday)
        db.session.add(new_bday)
        db.session.commit()
        return redirect(url_for('birthdays'))
    
    search_form = MonthSearchForm()
    birthdays_month_search = None
    if search_form.validate_on_submit():
        form_month = search_form.month.data
        try:
            searched_month = int(form_month[:2])
        except TypeError:
            searched_month = int(form_month[0])
        birthdays_month_search = Birthdays.search_month(searched_month)
    
    return render_template('birthdays.html', todays=todays, months=months, form=bday_form, b_months=birthdays_month_search,
    search_form=search_form, month_name=calendar.month_name[date.today().month])


########### ########### ###########
###########  BIRTHDAYS  ###########
########### ########### ###########



########### ########## ###########
###########  SEMESTER  ###########
########### ########## ###########


@app.route('/semester/<sem>', methods=['GET', 'POST'])
def semester(sem):
    semester_ = Semester.get_semester(sem)
    sem_assignments = sorted(semester_.get_all_semester_assignments(), key=lambda assignment: assignment.due)
    sem_courses = sorted(semester_.courses, key=lambda x: x.name)
    sem_exams = sorted(semester_.get_all_semester_exams(), key=sort_by_datetime)
    final_gpa = semester_.calculate_final_gpa()
    display_final_grades = any(list(map(lambda course: course.final_grade != "z", sem_courses)))

    course_form = CourseForm()
    if course_form.validate_on_submit():
        name = course_form.name.data
        url_link = course_form.url_link.data
        try:
            unparsed_info = get_course_information(url_link)
            parsed_info = {"Week Days": unparsed_info[0], "Time": unparsed_info[1], "Location": unparsed_info[2]}
            course_information = {"Lecture": parsed_info}
        except ValueError or TypeError or AttributeError:
            course_information = {}
        new_course = Course(name=name, url_link=url_link, course_info=course_information, course_policies=[])
        semester_.courses.append(new_course)
        db.session.commit()
        return redirect(f"/course/{name}")

    return render_template('semester_assignments.html', semester=semester_, assignments=sem_assignments,
                           courses=sem_courses, course_form=course_form, exams=sem_exams, color_assign=color_assign,
                           num_process=num_process, final_gpa=num_process(final_gpa, Standard_Error),
                           display_final_grades=display_final_grades)

@app.route('/sem_update/<sem_str>', methods=['GET'])
def update_semester(sem_str):
    sem = Semester.get_semester(sem_str)
    data = academic_calendar(sem_str)
    sem.holidays = data["Holidays"]
    sem.start = data["Start"]
    sem.end = data["End"]
    db.session.commit()
    return redirect(f"/semester/{sem_str}")

@app.route("/activate_<name>", methods=['GET'])
def activate_semester(name):
    selected_semester = Semester.get_semester(name)
    try:
        active_semester = Semester.get_active_semester()
        if active_semester and name != active_semester.name:
            active_semester.active = 0
            db.session.commit()
    except AttributeError:
        pass
    selected_semester.active = int(not bool(selected_semester.active))
    db.session.commit()
    return redirect(f"/semester/{name}")


########### ########## ###########
###########  SEMESTER  ###########
########### ########## ###########



########### ######### ###########
###########  COURSES  ###########
########### ######### ###########


@app.route('/course/<course_str>', methods=['GET', 'POST'])
def course(course_str):
    course_ = Course.get_course(course_str)
    c_assignments = sorted(course_.get_all_course_assignments(), key=lambda assignment: assignment.due)
    c_exams = sorted(course_.get_all_course_exams(), key=lambda exam: exam.date)

    breakdown = course_.get_grade_breakdown()
    percentage = course_.get_grade_percentages()
    combined = list(zip(breakdown, percentage))
    course_info = course_.get_course_information()
    course_policies = course_.get_course_policies()

    try:
        refresh = course_info["Lecture"]["Week Days"] == ""
    except KeyError:
        refresh = True

    list_of_dirty_rubric_items = course_.check_dirty()
    if list_of_dirty_rubric_items:
        # Compute Course statistics and mutate course grade data JSON if assignments/exams have been graded
        data_dict = course_.get_grade_data()
        exam_rubric_items = grade_types[-4:]
        exam_dirty_bit_on = False
        exam_drop = False
        for rubric in list_of_dirty_rubric_items:
            rubric_data_dict = data_dict[rubric]
            if rubric not in exam_rubric_items: # HW, Lab, Project, Quiz
                rubric_data_dict["Grade"], rubric_data_dict["Fully Graded"] = average([a.grade for a in c_assignments if a.type == rubric])
                if rubric + " Drop" in course_policies:
                    rubric_data_dict["Course Policy"] = f"{rubric} drop applied"
                else:
                    rubric_data_dict["Course Policy"] = f"{rubric} drop not applied"
            else: # Midterms or Final
                if "MT Z-Score Clobber applied" in rubric_data_dict["Course Policy"]:
                    continue
                try: # Try getting the grade of the exam based on the rubric name
                    rubric_data_dict["Grade"] = num_process([e.grade for e in c_exams if e.name == rubric][0], Standard_Error) # midterms and finals are unique
                except IndexError: # If failed, the midterm is dropped
                    rubric_data_dict["Grade"] = num_process([e.grade for e in c_exams if e.name == (rubric + "_drop")][0], Standard_Error)
                    exam_drop = True
                if exam_drop:
                    policy_string = "MT Drop"
                else:
                    policy_string = "MT Clobber not applied" if "mt" in rubric else ""
                rubric_data_dict["Fully Graded"], rubric_data_dict["Course Policy"] = rubric_data_dict["Grade"] >= 0, policy_string
                exam_dirty_bit_on = True
            if exam_drop:
                rubric_data_dict["Rubric Score"] = 0
            else:
                v = num_process(rubric_data_dict["Grade"] * rubric_data_dict["Weight"], Standard_Error)
                if v >= 0:
                    rubric_data_dict["Rubric Score"] = v
            course_.dirty[rubric] = 0
            course_.grade_data[rubric] = rubric_data_dict
        if exam_dirty_bit_on:
            course_.check_midterm_clobbers(num_process, Standard_Error)
        # Compute Total course Stats after updates have been registered
        total_course_sum = 0
        full_course_graded = True
        for data_dict in data_dict.values():
            if data_dict["Weight"] != 1:
                total_course_sum += data_dict["Rubric Score"] if data_dict["Rubric Score"] > 0 else 0
                full_course_graded = full_course_graded and data_dict["Fully Graded"]
        course_.grade_data["Total"]["Fully Graded"], course_.grade_data["Total"]["Rubric Score"] = full_course_graded, num_process(total_course_sum, Standard_Error)
        flag_modified(course_, "grade_data")
        flag_modified(course_, "dirty")
        db.session.commit()


    exam_form = ExamForm()
    if exam_form.validate_on_submit():
        name = exam_form.name.data
        location = exam_form.location.data
        date_ = exam_form.date.data
        hour = exam_form.hour.data
        new_exam = Examination(name=name, location=location, date=date_, time=hour)
        course_.course_exams.append(new_exam)
        db.session.commit()
        return redirect(f"/course/{course_str}")

    section_form = AddSection()
    if section_form.validate_on_submit():
        week_days = section_form.week_days.data
        start_time = section_form.start_time.data
        end_time = section_form.end_time.data
        time = str(start_time) + " – " + str(end_time)
        location = section_form.location.data
        description = section_form.description.data
        new_section = {description: {"Week Days": week_days, "Time": time, "Location": location}}
        course_.course_info.update(new_section)
        flag_modified(course_, "course_info")
        db.session.commit()
        return redirect(f"/course/{course_str}")
    
    course_form = CourseForm()
    if course_form.is_submitted():
        try:
            valid = False
            if course_form.grade_breakdown.data:
                course_.grade_data = formate_course_grade_data(course_form.grade_breakdown.data)
                course_.dirty = format_course_dirty(course_form.grade_breakdown.data)
                valid = True
            if course_form.grade_percentages.data and course_.get_grade_breakdown():
                list_of_percentages = course_form.grade_percentages.data.split(",")
                count = 0
                for key in course_.get_grade_data().keys():
                    if key != "Total":
                        course_.grade_data[key]["Weight"] = float(list_of_percentages[count])
                        count += 1
                flag_modified(course_, "grade_data")
                valid = True
            if course_form.course_policies.data:
                course_.course_policies = course_form.course_policies.data
                valid = True
            if course_form.final_grade.data:
                course_.final_grade = course_form.final_grade.data
                valid = True
            if valid:
                db.session.commit()
                return redirect(f"/course/{course_str}")
        except TypeError or IndexError:
            pass

    assignment_form = AssignmentForm()
    if assignment_form.is_submitted():
        name = assignment_form.name.data
        type_ = assignment_form.type.data
        if name == "":
            name = type_
        due = assignment_form.due.data
        update_future_assignments = False
        try:
            offset = int(name[-1]) - 1
            new_assignment = Assignment(name=name, type=type_, due=due)
            update_future_assignments = True
        except ValueError:
            offset = 0
            if assignment_form.repeat_weekly.data:
                new_assignment = Assignment(name=f"{name}-1", type=type_, due=due)
            else:
                new_assignment = Assignment(name=name, type=type_, due=due)
        course_.course_assignments.append(new_assignment)
        if update_future_assignments:
            course_.update_future_matching(name, type_, due)

        if assignment_form.repeat_weekly.data:
            plus_a_week = timedelta(weeks=1)
            count = 2 + offset
            try:
                int(name[-1])
                try:
                    int(name[-2])
                    name = name[:-3]
                except ValueError:
                    name = name[:-2]
            except ValueError:
                pass
            due = due + plus_a_week
            while due < assignment_form.end_repeat.data:
                new_assignment = Assignment(name=f"{name}-{count}", type=type_, due=due)
                course_.course_assignments.append(new_assignment)
                count += 1
                due = due + plus_a_week
        db.session.commit()
        return redirect(f"/course/{course_str}")

    return render_template('course_assignments.html', course=course_, assignments=c_assignments,
                           assign_form=assignment_form, grade_breakdown=combined, exams=c_exams, exam_form=exam_form,
                           course_information=course_info, section_form=section_form, num_process=num_process,
                           course_form=course_form, averages=course_.get_grade_data(), refresh=refresh)


@app.route('/refresh_course/<name>', methods=['GET'])
def refresh_course(name):
    course = Course.get_course(name)
    unparsed_info = get_course_information(course.url_link)
    course.course_info["Lecture"] = {"Week Days": unparsed_info[0], "Time": unparsed_info[1], "Location": unparsed_info[2]}
    flag_modified(course, "course_info")
    db.session.commit()
    return redirect(f'/course/{name}')


@login_manager.user_loader
def load_user(u_id):
    return User.query.get(int(u_id))


########### ######### ###########
###########  COURSES  ###########
########### ######### ###########



########### ######### ###########
###########  UPDATES  ###########
########### ######### ###########

@app.route('/update_a_<num>', methods=['GET', 'POST'])
def update_as(num):
    update_form = UpdateFormA()
    assignment = Assignment.get_from_id(num)
    back = request.referrer
    if request.method == 'GET':
        update_dict["previous_referral"] = back
    drop_available = ("drop" in assignment.type) or ((assignment.type + " Drop") in assignment.course.get_course_policies())

    if update_form.is_submitted():
        course = assignment.course
        delete = update_form.delete.data
        if delete:
            course.update_assignments(assignment)
            db.session.delete(assignment)
            db.session.commit()
        else:
            done = update_form.finished.data
            if done:
                assignment.completed = True

            new_grade = update_form.grade.data
            if new_grade:
                assignment.grade = new_grade
                course.dirty[assignment.type] = 1
                flag_modified(course, "dirty")

            new_name = update_form.name.data
            if new_name:
                assignment.name = new_name

            new_due = update_form.due.data
            if new_due:
                assignment.due = new_due

            use_drop = update_form.drop.data
            if use_drop and ("_drop" not in assignment.type):
                course.dirty[assignment.type] = 1
                flag_modified(course, "dirty")
                assignment.type = assignment.type + "_drop"
        db.session.commit()
        rtn_add = update_dict["previous_referral"]
        update_dict["previous_referral"] = url_for("home")
        return redirect(rtn_add)

    return render_template('update.html', up_form=update_form, form_type_a=True, coursework=assignment, back=back, drop_available=drop_available, z_score_clobber=False)


@app.route('/update_e_<num>', methods=['GET', 'POST'])
def update_e(num):
    update_form = UpdateFormE()
    exam = Examination.get_from_id(num)
    back = request.referrer
    if request.method == 'GET':
        update_dict["previous_referral"] = back
    z_score_clobber = "MT Clobber Z-Score" in exam.course.get_course_policies()
    drop_policy = ("mt Drop" in exam.course.get_course_policies()) and ("mt" in exam.name)

    if update_form.is_submitted():
        new_grade = update_form.grade.data
        course = exam.course
        if new_grade is not None:
            exam.grade = new_grade
            course.dirty[exam.name] = 1
            flag_modified(course, "dirty")

        new_name = update_form.name.data
        if new_name:
            exam.name = new_name

        new_loc = update_form.location.data
        if new_loc:
            exam.location = new_loc

        new_date = update_form.date.data
        if new_date:
            exam.date = new_date

        new_hour = update_form.hour.data
        if new_hour:
            exam.time = new_hour

        use_drop = update_form.drop.data
        if use_drop and ("_drop" not in exam.name):
            course.dirty[exam.name] = 1
            flag_modified(course, "dirty")
            exam.name = exam.name + "_drop"

        clobber_mt_z_score = update_form.z_score_c.data
        clobber_mt_z_score_grade = update_form.z_score_c_grade.data
        if z_score_clobber and (clobber_mt_z_score or course.get_grade_data()[exam.name]["Course Policy"] == "MT Z-Score Clobber applied"):
            if clobber_mt_z_score_grade:
                string = f"MT Z-Score Clobber applied: {clobber_mt_z_score_grade}"
                grade = float(clobber_mt_z_score_grade)
                course.grade_data[exam.name]["Rubric Score"] = grade * course.grade_data[exam.name]["Weight"]
                course.dirty[exam.name] = 1
                flag_modified(course, "dirty")
            else:
                string = "MT Z-Score Clobber applied"
            course.grade_data[exam.name]["Course Policy"] = string 
            flag_modified(course, "grade_data")
        db.session.commit()
        rtn_add = update_dict["previous_referral"]
        update_dict["previous_referral"] = url_for("home")
        return redirect(rtn_add)

    return render_template('update.html', up_form=update_form, form_type_a=False, coursework=exam, back=back, drop_available=drop_policy, z_score_clobber=z_score_clobber)


########### ######### ###########
###########  UPDATES  ###########
########### ######### ###########



########### ###### ###########
###########  TASK  ###########
########### ###### ###########

@app.route('/finished_task/<num>', methods=['GET', 'POST'])
def finished_task(num):
    task = Task.get_task(num)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('home'))
