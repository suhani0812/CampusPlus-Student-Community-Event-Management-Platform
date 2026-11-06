import unittest
from app import app
from helpers import get_db

class TestAcademicRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_unauthenticated_redirect(self):
        # Without session, should redirect
        res = self.client.get('/academics')
        self.assertEqual(res.status_code, 302)

    def test_page_1_courses_grid(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student', 'club_head']

        res = self.client.get('/academics')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Academics Hub', res.data)
        self.assertIn(b'B.Tech Computer Science', res.data)
        self.assertIn(b'btech-cse', res.data)

    def test_page_2_course_hub(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        res = self.client.get('/academics/btech-cse')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Lecture Notes', res.data)
        self.assertIn(b'Previous Year Papers', res.data)
        self.assertIn(b'Student Projects', res.data)
        self.assertIn(b'/academics/btech-cse/notes', res.data)
        self.assertIn(b'/academics/btech-cse/pyqs', res.data)
        self.assertIn(b'/academics/btech-cse/projects', res.data)

    def test_page_3a_notes(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        res = self.client.get('/academics/btech-cse/notes')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Data Structures &amp; Algorithms', res.data)
        self.assertIn(b'Notes &amp; Study Guides', res.data)

    def test_page_3a_pyqs(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        res = self.client.get('/academics/btech-cse/pyqs')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Data Structures &amp; Algorithms', res.data)
        self.assertIn(b'Previous Year Question Papers', res.data)

    def test_page_3b_projects(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        res = self.client.get('/academics/btech-cse/projects')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'CampusPulse', res.data)
        self.assertIn(b'SmartHealth', res.data)
        self.assertIn(b'Submit Course Project', res.data)

    def test_page_4_notes_files(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        # Subject 6 is Data Structures & Algorithms
        res = self.client.get('/academics/btech-cse/notes/6')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Data Structures &amp; Algorithms', res.data)
        self.assertIn(b'Binary Trees and AVL Balancing Notes', res.data)
        self.assertIn(b'Upload Notes', res.data)

    def test_page_4_pyqs_files(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        res = self.client.get('/academics/btech-cse/pyqs/6')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Data Structures &amp; Algorithms', res.data)
        self.assertIn(b'End Semester Exam Paper', res.data)
        self.assertIn(b'Upload PYQ Paper', res.data)

    def test_clubs_breadcrumbs(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        res = self.client.get('/clubs')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'<a href="/dashboard">Dashboard</a>', res.data)
        self.assertIn(b'<span class="current">Clubs</span>', res.data)

    def test_club_detail_breadcrumbs(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        res = self.client.get('/clubs/1')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'<a href="/dashboard">Dashboard</a>', res.data)
        self.assertIn(b'<a href="/clubs">Clubs</a>', res.data)

    def test_events_list(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        res = self.client.get('/events')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'<a href="/dashboard">Dashboard</a>', res.data)
        self.assertIn(b'<span class="current">Events</span>', res.data)
        self.assertIn(b'MIT-WPU Events', res.data)

    def test_event_detail(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        res = self.client.get('/events/1')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'<a href="/dashboard">Dashboard</a>', res.data)
        self.assertIn(b'<a href="/events">Events</a>', res.data)
        self.assertIn(b'About the Event', res.data)

    def test_accommodations_list(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        res = self.client.get('/accommodations')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'<a href="/dashboard">Dashboard</a>', res.data)
        self.assertIn(b'<span class="current">Accommodations</span>', res.data)
        self.assertIn(b'Student Accommodations', res.data)

    def test_accommodation_detail(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        res = self.client.get('/accommodations/1')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'<a href="/dashboard">Dashboard</a>', res.data)
        self.assertIn(b'<a href="/accommodations">Accommodations</a>', res.data)
        self.assertIn(b'Student Reviews', res.data)

    def test_accommodation_review(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 2
            sess['user_email'] = 'suhani.shah@mitwpu.edu.in'
            sess['roles'] = ['student']

        data = {'rating': '5', 'comment': 'Excellent place, very quiet for exam study.'}
        res = self.client.post('/accommodations/1/reviews', data=data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Your review has been published', res.data)
        self.assertIn(b'very quiet for exam study', res.data)

if __name__ == '__main__':
    unittest.main()
