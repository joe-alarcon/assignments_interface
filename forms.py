from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, RadioField, DateField, IntegerField, \
    SelectMultipleField, widgets, FloatField, TimeField, DateTimeField, SelectField
from wtforms.validators import DataRequired, Length


class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class MultiInputField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.NumberInput()


grade_types = ["hw", "pset", "lab", "project", "quiz", "participation", "reading", "mt1", "mt2", "mt3", "final"]
days_of_week = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
course_policies_list = ["MT Clobber Score", "MT Clobber Z-Score", "hw Drop", "lab Drop", "quiz Drop", "mt Drop"]
months = ["1 - Jan", "2 - Feb", "3 - Mar", "4 - Apr", "5 - May", "6 - Jun", "7 - Jul", "8 - Aug", "9 - Sep", "10 - Oct", "11 - Nov", "12 - Dec"]

class SemesterForm(FlaskForm):
    season = RadioField("Season", validators=[DataRequired()], choices=["fa", "sp", "su"])
    year = IntegerField("Year", validators=[DataRequired()])
    holidays = TextAreaField("Holidays")
    submit = SubmitField("Submit")


class CourseForm(FlaskForm):
    name = StringField("Name of Course")
    grade_breakdown = MultiCheckboxField("Grade Breakdowns", choices=grade_types)
    grade_percentages = TextAreaField("Grade Percentages")
    course_policies = MultiCheckboxField("Course Policies", choices=course_policies_list)
    final_grade = StringField("Final Grade")
    url_link = TextAreaField("Course Link")
    submit = SubmitField("Submit")


class AddSection(FlaskForm):
    week_days = StringField("Week Days", validators=[DataRequired()])
    start_time = TimeField("Start Time", validators=[DataRequired()])
    end_time = TimeField("End Time", validators=[DataRequired()])
    location = StringField("Location", validators=[DataRequired()])
    description = StringField("Description", validators=[DataRequired()])
    submit = SubmitField("Submit")


class AssignmentForm(FlaskForm):
    name = StringField("Name")
    type = RadioField("Type", validators=[DataRequired()], choices=grade_types[:7])
    due = DateField("Due date", validators=[DataRequired()])
    repeat_weekly = BooleanField("Repeat Weekly?")
    end_repeat = DateField("End Repetition")
    submit = SubmitField("Submit")


class ExamForm(FlaskForm):
    name = RadioField("Name", validators=[DataRequired()], choices=grade_types[7:])
    location = StringField("Location", validators=[DataRequired()])
    date = DateField("Date", validators=[DataRequired()])
    hour = TimeField("Time", validators=[DataRequired()])
    submit = SubmitField("Submit")


class UpdateFormA(FlaskForm):
    finished = BooleanField("Finished Assignment")
    grade = FloatField("Grade")
    name = StringField("Name")
    due = DateField("Due date")
    delete = BooleanField("Delete Assignment")
    drop = BooleanField("Use drop")
    submit = SubmitField("Submit")


class UpdateFormE(FlaskForm):
    grade = FloatField("Grade")
    name = RadioField("Name", choices=grade_types[7:])
    location = StringField("Location")
    date = DateField("Date")
    hour = TimeField("Time")
    z_score_c = BooleanField("Clobber MT with Z Score")
    z_score_c_grade = StringField("Clobbered Grade")
    drop = BooleanField("Use MT drop")
    submit = SubmitField("Submit")


class ToDoForm(FlaskForm):
    title = StringField("Task", validators=[DataRequired(), Length(max=100)])
    priority = IntegerField("Priority")
    # include_date = BooleanField("Include Date?")
    date = DateField("Date", validators=[DataRequired()])
    time = TimeField("Time", validators=[DataRequired()])
    submit = SubmitField("Submit")

class EventForm(FlaskForm):
    title = StringField("Event", validators=[DataRequired()])
    location = StringField("Location", validators=[DataRequired(), Length(max=100)])
    date = DateField("Date", validators=[DataRequired()])
    time = TimeField("Time", validators=[DataRequired()])
    repeat_days_of_week = MultiCheckboxField("Repeat on Days of the Week", choices=days_of_week)
    end_repeat = DateField("End Repetition")
    submit = SubmitField("Submit")

class UpdateEventForm(FlaskForm):
    title = StringField("Event")
    location = StringField("Location", validators=[Length(max=100)])
    date = DateField("Date")
    time = TimeField("Time")
    delete = BooleanField("Delete?")
    submit = SubmitField("Submit")

class AddBirthday(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    date = DateField("Date", validators=[DataRequired()])
    submit = SubmitField("Submit")

class MonthSearchForm(FlaskForm):
    month = SelectField("Month", validators=[DataRequired()], choices=months)
    submit = SubmitField("Submit")

class DateSearchForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()])
    submit = SubmitField("Submit")

class ReminderForm(FlaskForm):
    content = TextAreaField("Reminder", validators=[DataRequired()])
    link = StringField("Link")
    submit = SubmitField("Submit")
    
class UpdateReminderForm(FlaskForm):
    content = TextAreaField("Reminder")
    link = StringField("Link")
    delete = BooleanField("Delete?")
    submit = SubmitField("Submit")