from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, DecimalField, HiddenField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    full_name = StringField('Full Name', validators=[Optional()])

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('new_password')])

class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[Optional()])
    phone = StringField('Phone', validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional()])
    bio = TextAreaField('Bio', validators=[Optional()])
    profile_image = FileField('Profile Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Chỉ chấp nhận các định dạng hình ảnh: jpg, jpeg, png, gif')
    ])

class TopupForm(FlaskForm):
    amount = DecimalField('Amount', validators=[DataRequired()])
    bank_name = SelectField('Bank', choices=[
        ('vcb', 'Vietcombank'),
        ('tcb', 'Techcombank'),
        ('mb', 'MB Bank'),
        ('acb', 'ACB')
    ], validators=[DataRequired()])
    
class CommentForm(FlaskForm):
    comment = TextAreaField('Comment', validators=[DataRequired()])
    rating = SelectField('Rating', choices=[
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars'),
    ], validators=[DataRequired()])

class GiftcodeForm(FlaskForm):
    code = StringField('Giftcode', validators=[DataRequired()])

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
