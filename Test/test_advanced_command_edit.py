import unittest
from WebUI.app import app, db
from WebUI.app.models import User, AdvancedCommand

class TestAdvancedCommandEdit(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()
            # create users
            u1 = User(username='alice', email='alice@example.com')
            u1.set_password('password')
            u2 = User(username='bob', email='bob@example.com')
            u2.set_password('password')
            db.session.add_all([u1, u2])
            db.session.commit()
            self.u1 = u1
            self.u2 = u2
            # create an advanced command by alice
            ac = AdvancedCommand(name='patrol', description='patrol', category='test', base_commands='[]', author=u1, version=1, status='approved')
            db.session.add(ac)
            db.session.commit()
            self.ac = ac

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username, password):
        return self.app.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

    def test_owner_can_edit(self):
        # login alice
        rv = self.login('alice', 'password')
        self.assertIn(rv.status_code, (200, 302))
        # access edit page
        rv = self.app.get(f'/advanced_commands/edit/{self.ac.id}')
        self.assertEqual(rv.status_code, 200)
        # post edit with bump
        rv = self.app.post(f'/advanced_commands/edit/{self.ac.id}', data={'name':'patrol2','description':'new','category':'test','base_commands':'[]','version':1,'bumpVersionCheck':'1'}, follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        with app.app_context():
            ac = AdvancedCommand.query.get(self.ac.id)
            self.assertEqual(ac.name, 'patrol2')
            self.assertEqual(ac.version, 2)

    def test_non_owner_cannot_edit(self):
        # login bob
        self.login('bob', 'password')
        rv = self.app.get(f'/advanced_commands/edit/{self.ac.id}', follow_redirects=True)
        # should redirect away (no permission)
        self.assertNotEqual(rv.status_code, 200)

if __name__ == '__main__':
    unittest.main()
