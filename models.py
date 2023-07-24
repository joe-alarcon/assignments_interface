from app import db, app
from datetime import date, timedelta, datetime
from flask_login import UserMixin
import json
from function_utils import get_assignment_int

def sort_by_datetime(object_to_compare):
    date = object_to_compare.date
    time = object_to_compare.time
    return datetime(date.year, date.month, date.day, hour=time.hour, minute=time.minute)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    def get_id(self):
        return self.id


class Semester(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, index=False)
    holidays = db.Column(db.JSON, nullable=True)
    active = db.Column(db.Integer)
    start = db.Column(db.Date(), unique=True, index=True)
    end = db.Column(db.Date(), unique=True, index=True)
    semester_gpa = db.Column(db.Numeric(), default=-1.0)
    courses = db.relationship("Course", back_populates="semester",
                              lazy='subquery', cascade='all, delete-orphan')

    @staticmethod
    def get_semester(string):
        return Semester.query.filter_by(name=string).first()

    @staticmethod
    def get_all():
        return Semester.query.order_by(Semester.start).all()
    
    @staticmethod
    def get_all_by_year():
        sem_dict = {}
        for sem in Semester.get_all():
            key = sem.name[-2:]
            if key not in sem_dict:
                sem_dict[key] = [sem]
            else:
                sem_dict[key].append(sem)
        return list(sem_dict.values())

    @staticmethod
    def get_active_semester():
        return Semester.query.filter_by(active=1).first()
    
    @staticmethod
    def get_semester_from_day(day):
        all = Semester.get_all()
        for sem in all:
            if sem.start <= day and day <= sem.end:
                return sem
        return None

    def get_all_semester_assignments(self):
        to_return = []
        for course in self.courses:
            to_return.extend(course.get_all_course_assignments())
        return to_return

    def get_all_semester_exams(self):
        to_return = []
        for course in self.courses:
            to_return.extend(course.get_all_course_exams())
        return to_return

    def get_semester_holidays(self):
        return json.loads(self.holidays)
    
    def get_assignments_day(self, day):
        to_return = []
        for course in self.courses:
            to_return.extend(course.course_assignments_day(day))
        return to_return
    
    def get_exams_day(self, day):
        to_return = []
        for course in self.courses:
            to_return.extend(course.course_exams_day(day))
        return to_return
    
    def get_holidays(self):
        return list(map(lambda d: date.fromisoformat(d), self.holidays))
    
    def calculate_final_gpa(self):
        if self.semester_gpa != -1:
            return self.semester_gpa
        gpa_dict = {"A+": 4.0, "A": 4.0, "A-": 3.7}
        final_gpa = 0
        count = 0
        for course in self.courses:
            letter_grade = course.final_grade
            if "Tutor" in course.name or letter_grade == "P":
                continue
            if letter_grade == "z":
                return -1
            final_gpa += gpa_dict[letter_grade]
            count += 1
        if count == 0:
            return -1
        result = final_gpa / float(count)
        self.semester_gpa = result
        db.session.commit()
        return result


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, index=True)
    grade_data = db.Column(db.JSON, default={})
    dirty = db.Column(db.JSON, default={})
    course_policies = db.Column(db.JSON, default=[])
    url_link = db.Column(db.String(250))
    course_info = db.Column(db.JSON, default={})
    final_grade = db.Column(db.String(2), default="z")
    semester_id = db.Column(db.Integer, db.ForeignKey(Semester.id), nullable=False)
    semester = db.relationship("Semester", back_populates="courses")
    course_assignments = db.relationship("Assignment", back_populates="course",
                                        lazy='subquery', cascade='all, delete-orphan')
    course_exams = db.relationship("Examination", back_populates="course",
                                         lazy='subquery', cascade='all, delete-orphan')

    @staticmethod
    def get_course(string: str):
        return Course.query.filter_by(name=string).first()

    def get_all_course_assignments(self):
        return self.course_assignments
    
    def course_assignments_day(self, day):
        return [x for x in self.course_assignments if x.due == day]

    def get_all_course_exams(self):
        return self.course_exams
    
    def course_exams_day(self, day):
        return [x for x in self.course_exams if x.date == day]

    def get_grade_percentages(self):
        return [data["Weight"] for data in self.get_grade_data().values()]

    def get_grade_breakdown(self):
        return self.get_grade_data().keys()
    
    def get_grade_data(self):
        return self.grade_data
    
    def get_course_policies(self):
        return self.course_policies

    def get_course_information(self):
        return self.course_info
    
    def check_dirty(self):
        return [rubric for rubric, dirty_bit in self.dirty.items() if dirty_bit == 1]
    
    def check_midterm_clobbers(self, num_process, error):
        averages_dict = self.get_grade_data()
        if ("MT Clobber Score" not in self.get_course_policies()) or (averages_dict["final"]["Grade"] == -1):
            return
        min_mt_grade = 11
        min_mt = ""
        for rubric in self.get_grade_breakdown():
            if "mt" not in rubric:
                continue
            if averages_dict[rubric]["Grade"] < min_mt_grade:
                min_mt_grade = averages_dict[rubric]["Grade"]
                min_mt = rubric
        if min_mt_grade < averages_dict["final"]["Grade"]:
            averages_dict[min_mt]["Rubric Score"] = num_process(averages_dict["final"]["Grade"] * averages_dict[min_mt]["Weight"], error)
            averages_dict[min_mt]["Course Policy"] = "MT Clobber applied"
        return

    def final_score(self):
        assignment_dictionary = {}
        for grade_type in self.get_grade_breakdown():
            assignment_dictionary[grade_type] = []

        for assignment in self.get_all_course_assignments():
            try:
                assignment_dictionary[assignment.type].append(assignment)
            except KeyError:
                continue

        for exam in self.get_all_course_exams():
            try:
                assignment_dictionary[exam.name].append(exam)
            except KeyError:
                continue

        averages_by_breakdown = []
        for assignment_list in assignment_dictionary.items():
            average = sum(assignment_list) / float(len(assignment_list))
            averages_by_breakdown.append(average)

        combined = zip(averages_by_breakdown, self.get_grade_percentages())
        grades_by_breakdown = list(map(lambda item: item[0] * item[1], combined))
        return sum(grades_by_breakdown) * 100
    
    def update_assignments(self, assignment):
        """
        The assignment is to be deleted --> update the names for assignments that have the same name and are in
        the same assignment category (and that are due after assignment).
        """
        assignment_name = assignment.name
        assignment_int, assignment_size = get_assignment_int(assignment_name)
        if assignment_size == 0:
            return
        
        for assign in filter(lambda a: a.type == assignment.type, self.get_all_course_assignments()):
            old_name = assign.name
            a_integer, a_size = get_assignment_int(old_name)
            if a_size == 0:
                continue
            if (a_integer > assignment_int) and (old_name[:a_size] == assignment_name[:assignment_size]):
                    # print(a_integer, assignment_int, a_name, assignment_name[:assignment_size])
                    assign.name = f"{old_name[:a_size]}{a_integer - 1}"
                    db.session.commit()

    def update_future_matching(self, a_name: str, a_type: str, due: date):
        """
        The assignment is to be created --> update the names for future assignments that have the same name and are in
        the same assignment category. 
        """
        a_int, a_size = get_assignment_int(a_name)
        if a_size == 0:
            return
        
        for assignment in filter(lambda a: a.type == a_type and a_name[:a_size] in a.name and due < a.due, self.get_all_course_assignments()):
            old_name = assignment.name
            a_int, a_size = get_assignment_int(old_name)
            if a_size == 0:
                continue
            assignment.name = f"{old_name[:a_size]}{a_int+1}"
            db.session.commit()



class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), index=True)
    type = db.Column(db.String(50))
    due = db.Column(db.Date(), index=True)
    completed = db.Column(db.Boolean(), default=False)
    grade = db.Column(db.Numeric(), default=-1.0)
    course_id = db.Column(db.Integer, db.ForeignKey(Course.id), nullable=False)
    course = db.relationship("Course", back_populates="course_assignments")

    @staticmethod
    def assignments_due_today():
        return Assignment.query.filter_by(due=date.today()).all()
    
    @staticmethod
    def overdue_assignments_not_done():
        lst = Assignment.query.filter_by(completed=False).all()
        return [a for a in lst if a.due < date.today()]

    @staticmethod
    def get_from_id(num):
        return Assignment.query.filter_by(id=num).first()


class Examination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), index=True)
    date = db.Column(db.Date(), index=True)
    location = db.Column(db.String(100))
    grade = db.Column(db.Numeric(), default=-1.0)
    course_id = db.Column(db.Integer, db.ForeignKey(Course.id), nullable=False)
    course = db.relationship("Course", back_populates="course_exams")
    time = db.Column(db.Time())

    @staticmethod
    def exams_today():
        return Examination.query.filter_by(date=date.today()).all()

    @staticmethod
    def get_from_id(num):
        return Examination.query.filter_by(id=num).first()

    @staticmethod
    def exams_from_given_day(d):
        return sorted(Examination.query.filter_by(date=d).all(), key=sort_by_datetime)

    @staticmethod
    def exams_in_a_week():
        t = timedelta(days=1)
        today = date.today()
        to_return = []
        for day in range(1, 8):
            to_return.extend(Examination.exams_from_given_day(today + (t * day)))
        return to_return


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    priority = db.Column(db.Integer, default=1)
    date = db.Column(db.Date(), default=None)
    time = db.Column(db.Time(), default=None)
    overdue = db.Column(db.Boolean(), default=None)

    @staticmethod
    def get_task(num):
        return Task.query.filter_by(id=num).first()

    @staticmethod
    def get_all_tasks():
        return Task.query.order_by(-Task.priority).all()

    @staticmethod
    def get_all_today_tasks():
        return Task.query.filter_by(date=date.today()).order_by(-Task.priority).all()

    @staticmethod
    def get_all_pending():
        return Task.query.filter_by(overdue=False).order_by(-Task.priority).all()

    @staticmethod
    def get_all_overdue():
        return Task.query.filter_by(overdue=True).order_by(-Task.priority).all()

    @staticmethod
    def update_overdue_tasks():
        for task in Task.get_all_pending():
            if task.date is not None and task.date < date.today():
                task.overdue = True
        db.session.commit()

    @staticmethod
    def get_tasks_day(day):
        return Task.query.filter_by(date=day).order_by(-Task.priority).all()


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    location = db.Column(db.String(100))
    date = db.Column(db.Date())
    time = db.Column(db.Time())

    @staticmethod
    def get_from_id(num):
        return Event.query.filter_by(id=num).first()

    @staticmethod
    def get_all_today_events():
        return Event.events_from_given_day(date.today())

    @staticmethod
    def events_from_given_day(day):
        return sorted(Event.query.filter_by(date=day).all(), key=sort_by_datetime)

    @staticmethod
    def get_events_this_week():
        return Event.get_events_from_time_frame(7)

    @staticmethod
    def get_events_in_two_week():
        return Event.get_events_from_time_frame(14)

    @staticmethod
    def get_events_from_time_frame(number):
        t = timedelta(days=1)
        today = date.today()
        to_return = []
        for day in range(number):
            to_return.extend(Event.events_from_given_day(today + (t * day)))
        return to_return

    @staticmethod
    def delete_past_events():
        yesterday = date.today() - timedelta(days=1)
        all = Event.query.order_by(Event.date).all()
        all_past = [event for event in all if event.date <= yesterday]
        if all_past == []:
            return
        for event in all_past:
            db.session.delete(event)
        db.session.commit()


class Birthdays(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), index=True)
    date = db.Column(db.Date(), index=True)

    @staticmethod
    def today_birthdays():
        return list(filter(lambda x: (x.date.month == date.today().month) and (x.date.day == date.today().day), 
        Birthdays.all_birthdays()))

    @staticmethod
    def all_birthdays():
        return Birthdays.query.order_by(Birthdays.date).all()

    @staticmethod
    def birthdays_this_month():
        return list(filter(lambda x: x.date.month == date.today().month, Birthdays.all_birthdays()))
    
    @staticmethod
    def search_month(searched_month):
        return list(filter(lambda x: x.date.month == searched_month, Birthdays.all_birthdays()))

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(150))
    link = db.Column(db.String(200))

    @staticmethod
    def all():
        return Reminder.query.all()
    
    @staticmethod
    def get(num):
        return Reminder.query.filter_by(id=num).first()


# with app.app_context():
    # db.create_all()

"""
db.create_all()
db.session.add(Semester(name="sp23"))
db.session.commit()
"""

"""
def add_column(engine, table_name, column):
    column_name = column.compile(dialect=engine.dialect)
    column_type = column.type.compile(engine.dialect)
    engine.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table_name, column_name, column_type))

column = db.Column('holidays', db.JSON, nullable=True)
add_column(engine, table_name, column)
"""