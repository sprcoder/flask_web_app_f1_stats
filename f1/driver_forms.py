from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SubmitField, StringField, DateField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from wtforms.validators import ValidationError

# sr2484 | Apr 22
class DriverForm(FlaskForm):
    drivername = StringField("driver name", validators=[DataRequired(), Length(3)])
    birthdate = DateField("birth date")
    podiums = IntegerField("podiums")
    championships = IntegerField("championships")
    image = StringField("image URL", validators=[DataRequired()])

# sr2484 | Apr 22
class CreateForm(DriverForm):
    def __init__(self, *args, **kwargs):
        super(CreateForm, self).__init__(*args, **kwargs)
    submit = SubmitField("Add Driver")

# sr2484 | Apr 22
class SearchForm(DriverForm):
    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        del self.birthdate
        del self.podiums
        del self.championships
        del self.image
    submit = SubmitField("Search")

# sr2484 | Apr 22
class EditForm(DriverForm):
    def __init__(self, *args, **kwargs):
        super(EditForm, self).__init__(*args, **kwargs)
    submit = SubmitField("Update")

# sr2484 | Apr 22
class FilterForm(DriverForm):
    def __init__(self, *args, **kwargs):
        super(FilterForm).__init__(*args, **kwargs)
        del self.drivername
        del self.birthdate
        del self.image
    team = StringField("driver team")
    birthplace = StringField("birth place")
