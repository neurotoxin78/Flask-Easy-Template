
from flask import render_template, request, redirect, flash, current_app
from flask.ext.security import Security, login_required, logout_user, roles_required, current_user, utils
from flask.ext.admin import Admin, expose, AdminIndexView, base
from flask.ext.admin.contrib.sqla import ModelView
from models import *
from forms import *
import sendgrid
from decorators import threaded_async


security = Security(app, user_datastore)
# --------- FLASK Security has a very nice documentation. read more here -> https://pythonhosted.org/Flask-Security/

@app.route('/')
@app.route('/index')
@app.route('/index/<int:page>')
def index(page=1):
    m_tasks = SampleTasksTable()

    list_records = m_tasks.list_all(page, app.config['LISTINGS_PER_PAGE'])

    return render_template("index.html", list_records=list_records)


@app.route('/add_record', methods=['GET', 'POST'])
@login_required
def add_record():
    form = TasksAddForm(request.form)

    if request.method == 'POST':
        if form.validate():
            new_expense = SampleTasksTable()

            title = form.title.data
            description = form.description.data

            logging.info("adding " + title)

            new_expense.add_data(current_user.get_id(), title, description)

            flash("Expense added successfully", category="success")

    return render_template("add_record.html", form=form)



# --------- Secret page example, available only to admin -------------
@app.route('/secret')
@roles_required('admin')
def secret():
    return render_template('secret.html')



@app.route('/logout')
def log_out():
    logout_user()
    return redirect(request.args.get('next') or '/')


# Executes before the first request is processed. You might want to delete this after it's done to keep things clean
@app.before_first_request
def before_first_request():
    logging.info("-------------------- initializing everything ---------------------")
    db.create_all()

    user_datastore.find_or_create_role(name='admin', description='Administrator')
    user_datastore.find_or_create_role(name='end-user', description='End user')

    encrypted_password = utils.encrypt_password('123123')
    if not user_datastore.get_user('me@me.com'):
        user_datastore.create_user(email='me@me.com', password=encrypted_password, active=True, confirmed_at=datetime.datetime.now())

    encrypted_password = utils.encrypt_password('123123')
    if not user_datastore.get_user('enduser@enduser.com'):
        user_datastore.create_user(email='enduser@enduser.com', password=encrypted_password, active=True, confirmed_at=datetime.datetime.now())

    db.session.commit()

    user_datastore.add_role_to_user('me@me.com', 'admin')
    user_datastore.add_role_to_user('enduser@enduser.com', 'end-user')
    db.session.commit()




@threaded_async
def send_email(app, to, subject, body):
    with app.app_context():
        sg = sendgrid.SendGridClient('origof', 'parola123')
        message = sendgrid.Mail()
        message.add_to(to)
        message.set_subject(subject)
        message.set_html(body)
        message.set_from('FlaskShop No-Reply <noreplay@flaskshop.com>')
        try:
            status, msg = sg.send(message)
            print("Status: " + str(status) + " Message: " + str(msg))
            if status == 200:
                return True
        except Exception, ex:
            print("------------ ERROR SENDING EMAIL ------------" + str(ex.message))
    return False



@app.route('/contact', methods=['GET', 'POST'])
def contact():
    recaptcha = current_app.config['RECAPTCHA_SITE_KEY']
    email_sent = False

    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        message = request.form['message']
        recaptcha_response = request.form['g-recaptcha-response']

        # TODO: as a homework for you: check recaptcha & make emails work
        #send_email(app, to= current_app.config['ADMIN_EMAIL'], subject="Contact Form Flask Shop", body=email + " " + name + " " + message)

        email_sent = True

    return render_template("contact.html", RECAPTCHA_SITE_KEY=recaptcha, email_sent = email_sent)

# -------------------------- ADMIN PART ------------------------------------
# --------- FLASK ADMIN has a very nice documentation. read more here -> http://flask-admin.readthedocs.org/en/latest/


class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.has_role('admin')


# ------- visible only to admin user, else returns "not found" -----------
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.has_role('admin'):
            return render_template('other/404.html'), 404
        return self.render('admin/index.html')


class TasksAdminView(MyModelView):
    can_create = True

    def is_accessible(self):
        return current_user.has_role('admin')

    def __init__(self, session, **kwargs):
        super(TasksAdminView, self).__init__(SampleTasksTable, session, **kwargs)


class UserAdminView(MyModelView):
    column_exclude_list = ('password')

    def is_accessible(self):
        return current_user.has_role('admin')

    def __init__(self, session, **kwargs):
        super(UserAdminView, self).__init__(User, session, **kwargs)


class RoleView(MyModelView):
    def is_accessible(self):
        return current_user.has_role('admin')

    def __init__(self, session, **kwargs):
        super(RoleView, self).__init__(Role, session, **kwargs)


admin = Admin(app, 'Flask-Easy Admin', index_view=MyAdminIndexView())
admin.add_view(TasksAdminView(db.session))
admin.add_view(UserAdminView(db.session))
admin.add_view(RoleView(db.session))
admin.add_link(base.MenuLink('Web Home', endpoint="index"))
admin.add_link(base.MenuLink('Logout', endpoint="log_out"))

# --------------------------  END ADMIN PART ---------------------------------



# --------------------------- QUICK SEO PART ----------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('other/404.html'), 404


@app.errorhandler(403)
def page_forbiden(e):
    return render_template('other/403.html'), 403


# ----------------------------- END QUICK SEO PART ----------------------