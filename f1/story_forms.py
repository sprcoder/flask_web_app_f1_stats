from flask_wtf import FlaskForm
from flask_wtf.form import _Auto
from wtforms import EmailField, PasswordField, SubmitField, StringField, DateField, IntegerField, SelectMultipleField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from wtforms.validators import ValidationError

# sr2484 | Apr 22
class StoryForm(FlaskForm):
    shortdesc = StringField("Title*", validators=[DataRequired(), Length(10)])
    longdesc = TextAreaField("Description*", validators=[DataRequired(), Length(50)])
    image = StringField("image*", validators=[DataRequired()])
    selectdriver = SelectMultipleField("Drivers")

class CreateForm(StoryForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    submit = SubmitField("Create Story")
  
class EditForm(StoryForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    submit = SubmitField("Update Story")
