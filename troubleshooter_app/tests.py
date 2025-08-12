'''
test_get_partition_id_success: This test ensures that the get_partition_id function in services.py can successfully retrieve a partition_id from the database when the provided serial_number, job_number, and job_start exist. It also confirms that the correct SQL query is constructed and executed.

test_get_partition_id_not_found: This test checks the opposite scenario: if the provided criteria do not match any records in the database, the function should gracefully return None, preventing potential errors later in the application flow.

from unittest.mock import MagicMock, patch
from django.test import TestCase
from troubleshooter_app.services import get_partition_id
import pandas as pd

class ServicesTestCase(TestCase):

    @patch('troubleshooter_app.services.pd.read_sql')
    def test_get_partition_id_success(self, mock_read_sql):
        # Mock the DataFrame that would be returned by the database query
        mock_df = pd.DataFrame({'partition_id': [11377]})
        mock_read_sql.return_value = mock_df

        # Create a mock td_engine that supports connect() as context manager
        mock_td_engine = MagicMock()
        mock_conn = MagicMock()
        mock_td_engine.connect.return_value.__enter__.return_value = mock_conn

        # Call the function with sample data
        partition_id = get_partition_id(mock_td_engine, 'SN123', 'JN456', '2025-08-11')

        # Assert that the function returns the expected partition_id
        self.assertEqual(partition_id, 11377)

        # Build the expected SQL
        expected_sql = """
            SELECT partition_id
            FROM PRD_RP_PRODUCT_VIEW.FNFM_FLEET_METADATA
            WHERE
            serial_number = 'SN123' AND
            job_number = 'JN456' AND
            CAST(job_start AS CHAR(26)) = '2025-08-11';"""
        
        # Assert pd.read_sql was called with the correct arguments
        mock_read_sql.assert_called_with(expected_sql, mock_conn)

    @patch('troubleshooter_app.services.pd.read_sql')
    def test_get_partition_id_not_found(self, mock_read_sql):
        # Mock an empty DataFrame to simulate no results
        mock_read_sql.return_value = pd.DataFrame()

        mock_td_engine = MagicMock()
        mock_conn = MagicMock()
        mock_td_engine.connect.return_value.__enter__.return_value = mock_conn

        partition_id = get_partition_id(mock_td_engine, 'SN999', 'JN888', '2025-01-01')

        self.assertIsNone(partition_id)'''

# troubleshooter_app/tests.py
'''
test_limit_check_api_missing_parameters: This test verifies that your limit_check_api endpoint correctly handles bad requests. It ensures that if required parameters like partition_id and triple_subject are missing, the API returns a 400 Bad Request status code and a clear error message.

test_limit_check_api_success: This test confirms the end-to-end functionality of your API endpoint with valid inputs. It checks that the API returns a 200 OK status code and a JSON response with the expected boolean result (True in this case) from the limit_check function. It also verifies that the limit_check service function is called with the correct arguments.
from unittest.mock import MagicMock, patch
from django.test import TestCase, Client
from django.urls import reverse


class APIViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('troubleshooter_app.api_views.td_engine')
    @patch('troubleshooter_app.api_views.limit_check')
    def test_limit_check_api_missing_parameters(self, mock_limit_check, mock_td_engine):
        url = reverse('troubleshooter_app:api_limit_check')

        # Mock a successful engine connection
        mock_td_engine.return_value = MagicMock()

        # Send a GET request without the required parameters
        response = self.client.get(url)

        # Assert that a 400 Bad Request error is returned
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Missing required parameters', response.content)

    @patch('troubleshooter_app.api_views.td_engine')
    @patch('troubleshooter_app.api_views.limit_check')
    def test_limit_check_api_success(self, mock_limit_check, mock_td_engine):
        url = reverse('troubleshooter_app:api_limit_check')

        # Mock the Teradata engine and connection using MagicMock for context manager support
        mock_conn = MagicMock()
        mock_td_engine.connect.return_value.__enter__.return_value = mock_conn

        # Mock the result of the limit_check function
        mock_limit_check.return_value = True

        # Send a GET request with valid parameters
        response = self.client.get(url, {
            'partition_id': '12345',
            'triple_subject': 'FNFM_Uplink_Telemetry_Check'
        })

        # Assert that a 200 OK status code is returned
        self.assertEqual(response.status_code, 200)

        # Assert the JSON response content
        self.assertJSONEqual(response.content, {'result': True})

        # Verify that the service function was called with the correct arguments
        mock_limit_check.assert_called_with(mock_conn, '12345', 'FNFM_Uplink_Telemetry_Check')'''




'''from unittest.mock import Mock, patch
from django.test import TestCase, Client
from django.urls import reverse
import pandas as pd

# ------------------------------
# Forms & views tests
# ------------------------------

class FormsAndViewsTestCase(TestCase):
    def setUp(self):
        """
        Set up the test client and mock a valid Teradata engine and ontology graph.
        We mock these here to ensure all tests for views can run without
        a real database or ontology file.
        """
        self.client = Client()
        self.troubleshooter_url = reverse('troubleshooter_app:troubleshooter')
        self.results_url = reverse('troubleshooter_app:troubleshooter_results')

    # --- Tests for the `get_form_choices` API endpoint ---

    @patch('troubleshooter_app.views.get_metadata')
    @patch('troubleshooter_app.views.td_engine')
    def test_get_form_choices_serial_number(self, mock_td_engine, mock_get_metadata):
        """
        Tests fetching the initial list of serial numbers.
        
        Fix: Mock `get_metadata` to return a DataFrame.
        Fix: Use the correct query parameter name, `parent_field`.
        Fix: The assertion now correctly expects a list of lists.
        """
        mock_df = pd.DataFrame({
            'serial_number': ['SN-001', 'SN-002', 'SN-001'],
            'job_number': ['J-101', 'J-102', 'J-103'],
            'job_start': ['2025-01-01', '2025-01-02', '2025-01-03']
        })
        mock_get_metadata.return_value = mock_df
        mock_td_engine.return_value = Mock()  # Ensure the engine is not None

        response = self.client.get(reverse('troubleshooter_app:get_form_choices'),
                                   {'parent_field': 'serial_number'})

        self.assertEqual(response.status_code, 200)
        # The view should return unique sorted values
        self.assertEqual(
            response.json(),
            {'choices': [['SN-001', 'SN-001'], ['SN-002', 'SN-002']]}
        )

    @patch('troubleshooter_app.views.get_metadata')
    @patch('troubleshooter_app.views.td_engine')
    def test_get_form_choices_job_number(self, mock_td_engine, mock_get_metadata):
        """
        Tests fetching job numbers based on a selected serial number.
        
        Fix: Mock `get_metadata` to return a DataFrame.
        Fix: Use the correct query parameters: `parent_field` and `parent_value`.
        Fix: The assertion now correctly expects a list of lists.
        """
        mock_df = pd.DataFrame({
            'serial_number': ['SN-001', 'SN-001', 'SN-002'],
            'job_number': ['J-101', 'J-102', 'J-201'],
            'job_start': ['2025-01-01', '2025-01-02', '2025-01-03']
        })
        mock_get_metadata.return_value = mock_df
        mock_td_engine.return_value = Mock()

        response = self.client.get(reverse('troubleshooter_app:get_form_choices'),
                                   {'parent_field': 'job_number', 'parent_value': 'SN-001'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'choices': [['J-101', 'J-101'], ['J-102', 'J-102']]}
        )

    # --- Tests for the `troubleshooter_view` function ---

    @patch('troubleshooter_app.views.get_teradata_engine')
    @patch('troubleshooter_app.views.load_ontology_graph')
    @patch('troubleshooter_app.views.get_all_failure_labels')
    def test_troubleshooter_view_get(self, mock_get_all_failure_labels, mock_load_ontology_graph, mock_get_teradata_engine):
        """
        Tests the initial page load with a GET request.
        
        Fix: Patch the functions that initialize the global variables.
        """
        mock_get_teradata_engine.return_value = Mock()
        mock_load_ontology_graph.return_value = Mock()
        mock_get_all_failure_labels.return_value = ['flow rate is null', 'pump calibration failed']
        
        response = self.client.get(self.troubleshooter_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "On which failure do you want to start?")
        self.assertContains(response, 'flow rate is null')

    @patch('troubleshooter_app.views.get_teradata_engine')
    @patch('troubleshooter_app.views.load_ontology_graph')
    @patch('troubleshooter_app.views.get_partition_id')
    @patch('troubleshooter_app.views.execute_troubleshooting_logic')
    @patch('troubleshooter_app.views.get_root_cause_analysis')
    @patch('troubleshooter_app.views.Network')
    @patch('troubleshooter_app.views.get_all_failure_labels')
    def test_troubleshooter_view_post_success(self, mock_get_failures, mock_network, mock_get_root_cause, mock_execute_logic, mock_get_partition_id, mock_load_ontology_graph, mock_get_teradata_engine):
        """
        Tests a successful form submission with a POST request.
        
        Fix: Added the missing `failure_selectbox` to the POST data.
        Fix: Patched the functions that initialize the global variables.
        """
        mock_get_teradata_engine.return_value = Mock()
        mock_load_ontology_graph.return_value = Mock()
        mock_get_failures.return_value = ['failure']
        
        mock_get_partition_id.return_value = 11377
        
        mock_df_clean = pd.DataFrame({
            'Subject': ['A'], 'Predicate': ['hasRootCause'], 'Object': ['B'], 'Status': [True]
        })
        mock_execute_logic.return_value = (mock_df_clean, {})
        
        mock_get_root_cause.return_value = [['RootCause A', 'Trigger B', 'DataChannel C 🔴']]
        mock_network_instance = Mock()
        mock_network.return_value = mock_network_instance
        
        post_data = {
            'serial_number': 'SN-001',
            'job_number': 'J-101',
            'job_start': '2025-01-01',
            'failure_selectbox': 'failure'
        }
        
        response = self.client.post(self.troubleshooter_url, post_data)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.results_url)
        
        session = self.client.session
        self.assertIn('troubleshooter_results', session)
        self.assertEqual(session['troubleshooter_results']['partition_id'], 11377)

    @patch('troubleshooter_app.views.get_teradata_engine')
    @patch('troubleshooter_app.views.load_ontology_graph')
    @patch('troubleshooter_app.views.get_all_failure_labels')
    def test_troubleshooter_view_post_missing_parameters(self, mock_get_failures, mock_load_ontology_graph, mock_get_teradata_engine):
        """
        Tests a form submission with a missing parameter.
        
        Fix: The view returns a 200 and re-renders the page, so we assert for 200.
        Fix: We assert for the presence of the error message in the response content.
        Fix: Patched the functions that initialize the global variables.
        """
        mock_get_teradata_engine.return_value = Mock()
        mock_load_ontology_graph.return_value = Mock()
        mock_get_failures.return_value = ['failure']

        post_data = {
            'serial_number': 'SN-001',
            'job_number': 'J-101',
            'failure_selectbox': 'failure'
        }

        response = self.client.post(self.troubleshooter_url, post_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please select all fields', response.content)
        self.assertNotIn('troubleshooter_results', self.client.session)

    @patch('troubleshooter_app.views.get_teradata_engine')
    @patch('troubleshooter_app.views.load_ontology_graph')
    @patch('troubleshooter_app.views.get_all_failure_labels')
    @patch('troubleshooter_app.views.get_partition_id')
    def test_troubleshooter_view_post_no_partition_id(self, mock_get_partition_id, mock_get_failures, mock_load_ontology_graph, mock_get_teradata_engine):
        """
        Tests a form submission where no partition_id is found.
        
        Fix: The view returns a 200 and re-renders the page, so we assert for 200.
        Fix: We assert for the presence of the error message in the response content.
        Fix: Patched the functions that initialize the global variables.
        """
        mock_get_teradata_engine.return_value = Mock()
        mock_load_ontology_graph.return_value = Mock()
        mock_get_failures.return_value = ['failure']
        
        mock_get_partition_id.return_value = None
        
        post_data = {
            'serial_number': 'SN-999',
            'job_number': 'J-999',
            'job_start': '2025-01-01',
            'failure_selectbox': 'failure'
        }
        
        response = self.client.post(self.troubleshooter_url, post_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Could not find partition_id', response.content)
        self.assertNotIn('troubleshooter_results', self.client.session)


# ------------------------------
# Troubleshooter results view tests
# ------------------------------

class TroubleshooterResultsViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_results_view_with_session_data(self):
        session = self.client.session
        session['troubleshooter_results'] = {
            'partition_id': 'P123',
            'messages': ['Test message'],
            'df_clean_html': '<p>Clean</p>',
            'root_cause_table_html': '<p>Root cause</p>',
            'graph_html_path': '/path/to/graph.html',
        }
        session.save()

        response = self.client.get(reverse('troubleshooter_app:troubleshooter_results'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'P123')
        self.assertContains(response, 'Test message')

    def test_results_view_without_session_data(self):
        response = self.client.get(reverse('troubleshooter_app:troubleshooter_results'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('troubleshooter_app:troubleshooter'))'''
      

'''from unittest.mock import Mock, patch
from django.test import TestCase, Client
from django.urls import reverse
import pandas as pd
from troubleshooter_app import views # Import the views module to patch its global objects

# ------------------------------
# Forms & views tests
# ------------------------------

class FormsAndViewsTestCase(TestCase):
    def setUp(self):
        """
        Set up the test client and patch global module-level variables
        for the entire test case. This is the most reliable way to
        handle module-level initialization that might fail in tests.
        """
        # Patch the global td_engine and g variables
        self.td_engine_patch = patch.object(views, 'td_engine', new=Mock())
        self.g_patch = patch.object(views, 'g', new=Mock())
        
        # Start the patches
        self.mock_td_engine = self.td_engine_patch.start()
        self.mock_g = self.g_patch.start()
        self.addCleanup(self.td_engine_patch.stop)
        self.addCleanup(self.g_patch.stop)

        # Initialize the test client and URLs
        self.client = Client()
        self.troubleshooter_url = reverse('troubleshooter_app:troubleshooter')
        self.results_url = reverse('troubleshooter_app:troubleshooter_results')

    # --- Tests for the `get_form_choices` API endpoint ---
    @patch('troubleshooter_app.views.get_metadata')
    def test_get_form_choices_serial_number(self, mock_get_metadata):
        """
        Tests fetching the initial list of serial numbers.
        """
        mock_df = pd.DataFrame({
            'serial_number': ['SN-001', 'SN-002', 'SN-001'],
            'job_number': ['J-101', 'J-102', 'J-103'],
            'job_start': ['2025-01-01', '2025-01-02', '2025-01-03']
        })
        mock_get_metadata.return_value = mock_df

        response = self.client.get(reverse('troubleshooter_app:get_form_choices'),
                                   {'parent_field': 'serial_number'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'choices': [['SN-001', 'SN-001'], ['SN-002', 'SN-002']]}
        )

    @patch('troubleshooter_app.views.get_metadata')
    def test_get_form_choices_job_number(self, mock_get_metadata):
        """
        Tests fetching job numbers based on a selected serial number.
        """
        mock_df = pd.DataFrame({
            'serial_number': ['SN-001', 'SN-001', 'SN-002'],
            'job_number': ['J-101', 'J-102', 'J-201'],
            'job_start': ['2025-01-01', '2025-01-02', '2025-01-03']
        })
        mock_get_metadata.return_value = mock_df

        response = self.client.get(reverse('troubleshooter_app:get_form_choices'),
                                   {'parent_field': 'job_number', 'parent_value': 'SN-001'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'choices': [['J-101', 'J-101'], ['J-102', 'J-102']]}
        )
    
    # --- Tests for the `troubleshooter_view` function ---

    @patch('troubleshooter_app.views.get_all_failure_labels')
    def test_troubleshooter_view_get(self, mock_get_all_failure_labels):
        """
        Tests the initial page load with a GET request.
        """
        mock_get_all_failure_labels.return_value = ['flow rate is null', 'pump calibration failed']
        response = self.client.get(self.troubleshooter_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "On which failure do you want to start?")
        self.assertContains(response, 'flow rate is null')

    @patch('troubleshooter_app.views.get_all_failure_labels')
    @patch('troubleshooter_app.views.Network')
    @patch('troubleshooter_app.views.get_root_cause_analysis')
    @patch('troubleshooter_app.views.execute_troubleshooting_logic')
    @patch('troubleshooter_app.views.get_partition_id')
    def test_troubleshooter_view_post_success(self, mock_get_partition_id, mock_execute_logic, mock_get_root_cause, mock_network, mock_get_failures):
        """
        Tests a successful form submission with a POST request.
        """
        mock_get_failures.return_value = ['failure']
        mock_get_partition_id.return_value = 11377
        
        mock_df_clean = pd.DataFrame({
            'Subject': ['A'], 'Predicate': ['hasRootCause'], 'Object': ['B'], 'Status': [True]
        })
        mock_execute_logic.return_value = (mock_df_clean, {})
        
        mock_get_root_cause.return_value = [['RootCause A', 'Trigger B', 'DataChannel C 🔴']]
        mock_network_instance = Mock()
        mock_network.return_value = mock_network_instance
        
        post_data = {
            'serial_number': 'SN-001',
            'job_number': 'J-101',
            'job_start': '2025-01-01',
            'failure_selectbox': 'failure'
        }
        
        response = self.client.post(self.troubleshooter_url, post_data)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.results_url)
        
        session = self.client.session
        self.assertIn('troubleshooter_results', session)
        self.assertEqual(session['troubleshooter_results']['partition_id'], 11377)

    @patch('troubleshooter_app.views.get_all_failure_labels')
    def test_troubleshooter_view_post_missing_parameters(self, mock_get_failures):
        """
        Tests a form submission with a missing parameter.
        """
        mock_get_failures.return_value = ['failure']

        post_data = {
            'serial_number': 'SN-001',
            'job_number': 'J-101',
            'failure_selectbox': 'failure'
        }

        response = self.client.post(self.troubleshooter_url, post_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please select all fields', response.content)
        self.assertNotIn('troubleshooter_results', self.client.session)

    @patch('troubleshooter_app.views.get_partition_id')
    @patch('troubleshooter_app.views.get_all_failure_labels')
    def test_troubleshooter_view_post_no_partition_id(self, mock_get_failures, mock_get_partition_id):
        """
        Tests a form submission where no partition_id is found.
        """
        mock_get_failures.return_value = ['failure']
        mock_get_partition_id.return_value = None
        
        post_data = {
            'serial_number': 'SN-999',
            'job_number': 'J-999',
            'job_start': '2025-01-01',
            'failure_selectbox': 'failure'
        }
        
        response = self.client.post(self.troubleshooter_url, post_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Could not find partition_id', response.content)
        self.assertNotIn('troubleshooter_results', self.client.session)


# ------------------------------
# Troubleshooter results view tests
# ------------------------------

class TroubleshooterResultsViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_results_view_with_session_data(self):
        session = self.client.session
        session['troubleshooter_results'] = {
            'partition_id': 'P123',
            'messages': ['Test message'],
            'df_clean_html': '<p>Clean</p>',
            'root_cause_table_html': '<p>Root cause</p>',
            'graph_html_path': '/path/to/graph.html',
        }
        session.save()

        response = self.client.get(reverse('troubleshooter_app:troubleshooter_results'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'P123')
        self.assertContains(response, 'Test message')

    def test_results_view_without_session_data(self):
        response = self.client.get(reverse('troubleshooter_app:troubleshooter_results'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('troubleshooter_app:troubleshooter'))'''
        
        
        
''' The dots (.) in the output .....F.. indicate that seven of your tests passed successfully. This is great news! It means that your application's logic for the following scenarios is working as expected:

Fetching serial number choices.

Fetching job number choices.

Handling the initial GET request to the troubleshooter page.

Handling a POST request with missing parameters.

Handling a POST request where a partition_id is not found.

Rendering the results page when session data is present.

Redirecting correctly when no results are found in the session.

Failed Test
The single F in the output indicates that one test failed. The detailed traceback that follows pinpoints the specific test and the reason for the failure.

Failed Test Name: test_troubleshooter_view_post_success

Reason for Failure: The AssertionError: 'troubleshooter_results' not found in... message means the test expected to find a dictionary named 'troubleshooter_results' in the Django session, but it was not there.'''


from unittest.mock import Mock, patch
from django.test import TestCase, Client
from django.urls import reverse
import pandas as pd
from troubleshooter_app import views # Import the views module to patch its global objects

# ------------------------------
# Forms & views tests
# ------------------------------

class FormsAndViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.troubleshooter_url = reverse('troubleshooter_app:troubleshooter')
        self.results_url = reverse('troubleshooter_app:troubleshooter_results')

    # --- Tests for the `get_form_choices` API endpoint ---
    @patch('troubleshooter_app.views.get_metadata')
    @patch('troubleshooter_app.views.get_teradata_engine')
    def test_get_form_choices_serial_number(self, mock_get_teradata_engine, mock_get_metadata):
        """
        Tests fetching the initial list of serial numbers.
        """
        mock_get_teradata_engine.return_value = Mock()
        mock_df = pd.DataFrame({
            'serial_number': ['SN-001', 'SN-002', 'SN-001'],
            'job_number': ['J-101', 'J-102', 'J-103'],
            'job_start': ['2025-01-01', '2025-01-02', '2025-01-03']
        })
        mock_get_metadata.return_value = mock_df

        response = self.client.get(reverse('troubleshooter_app:get_form_choices'),
                                   {'parent_field': 'serial_number'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'choices': [['SN-001', 'SN-001'], ['SN-002', 'SN-002']]}
        )

    @patch('troubleshooter_app.views.get_metadata')
    @patch('troubleshooter_app.views.get_teradata_engine')
    def test_get_form_choices_job_number(self, mock_get_teradata_engine, mock_get_metadata):
        """
        Tests fetching job numbers based on a selected serial number.
        """
        mock_get_teradata_engine.return_value = Mock()
        mock_df = pd.DataFrame({
            'serial_number': ['SN-001', 'SN-001', 'SN-002'],
            'job_number': ['J-101', 'J-102', 'J-201'],
            'job_start': ['2025-01-01', '2025-01-02', '2025-01-03']
        })
        mock_get_metadata.return_value = mock_df

        response = self.client.get(reverse('troubleshooter_app:get_form_choices'),
                                   {'parent_field': 'job_number', 'parent_value': 'SN-001'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'choices': [['J-101', 'J-101'], ['J-102', 'J-102']]}
        )

    # --- Tests for the `troubleshooter_view` function ---
    @patch('troubleshooter_app.views.get_teradata_engine')
    @patch('troubleshooter_app.views.load_ontology_graph')
    @patch('troubleshooter_app.views.get_all_failure_labels')
    def test_troubleshooter_view_get(self, mock_get_all_failure_labels, mock_load_ontology_graph, mock_get_teradata_engine):
        """
        Tests the initial page load with a GET request.
        """
        mock_get_teradata_engine.return_value = Mock()
        mock_load_ontology_graph.return_value = Mock()
        mock_get_all_failure_labels.return_value = ['flow rate is null', 'pump calibration failed']
        
        response = self.client.get(self.troubleshooter_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "On which failure do you want to start?")
        self.assertContains(response, 'flow rate is null')

    @patch('troubleshooter_app.views.get_teradata_engine')
    @patch('troubleshooter_app.views.load_ontology_graph')
    @patch('troubleshooter_app.views.get_all_failure_labels')
    @patch('troubleshooter_app.views.Network')
    @patch('troubleshooter_app.views.get_root_cause_analysis')
    @patch('troubleshooter_app.views.execute_troubleshooting_logic')
    @patch('troubleshooter_app.views.get_partition_id')
    def test_troubleshooter_view_post_success(self, mock_get_partition_id, mock_execute_logic, mock_get_root_cause, mock_network, mock_get_failures, mock_load_ontology_graph, mock_get_teradata_engine):
        """
        Tests a successful form submission with a POST request.
        """
        mock_get_teradata_engine.return_value = Mock()
        mock_load_ontology_graph.return_value = Mock()
        mock_get_failures.return_value = ['failure']
        
        mock_get_partition_id.return_value = 11377
        
        mock_df_clean = pd.DataFrame({
            'Subject': ['A'], 'Predicate': ['hasRootCause'], 'Object': ['B'], 'Status': [True]
        })
        mock_execute_logic.return_value = (mock_df_clean, {})
        
        mock_get_root_cause.return_value = [['RootCause A', 'Trigger B', 'DataChannel C 🔴']]
        mock_network_instance = Mock()
        mock_network.return_value = mock_network_instance
        
        post_data = {
            'serial_number': 'SN-001',
            'job_number': 'J-101',
            'job_start': '2025-01-01',
            'failure_selectbox': 'failure'
        }
        
        response = self.client.post(self.troubleshooter_url, post_data)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.results_url)
        
        session = self.client.session
        self.assertIn('troubleshooter_results', session)
        self.assertEqual(session['troubleshooter_results']['partition_id'], 11377)

    @patch('troubleshooter_app.views.get_teradata_engine')
    @patch('troubleshooter_app.views.load_ontology_graph')
    @patch('troubleshooter_app.views.get_all_failure_labels')
    def test_troubleshooter_view_post_missing_parameters(self, mock_get_failures, mock_load_ontology_graph, mock_get_teradata_engine):
        """
        Tests a form submission with a missing parameter.
        """
        mock_get_teradata_engine.return_value = Mock()
        mock_load_ontology_graph.return_value = Mock()
        mock_get_failures.return_value = ['failure']

        post_data = {
            'serial_number': 'SN-001',
            'job_number': 'J-101',
            'failure_selectbox': 'failure'
        }

        response = self.client.post(self.troubleshooter_url, post_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please select all fields', response.content)
        self.assertNotIn('troubleshooter_results', self.client.session)

    @patch('troubleshooter_app.views.get_teradata_engine')
    @patch('troubleshooter_app.views.load_ontology_graph')
    @patch('troubleshooter_app.views.get_all_failure_labels')
    @patch('troubleshooter_app.views.get_partition_id')
    def test_troubleshooter_view_post_no_partition_id(self, mock_get_partition_id, mock_get_failures, mock_load_ontology_graph, mock_get_teradata_engine):
        """
        Tests a form submission where no partition_id is found.
        """
        mock_get_teradata_engine.return_value = Mock()
        mock_load_ontology_graph.return_value = Mock()
        mock_get_failures.return_value = ['failure']
        
        mock_get_partition_id.return_value = None
        
        post_data = {
            'serial_number': 'SN-999',
            'job_number': 'J-999',
            'job_start': '2025-01-01',
            'failure_selectbox': 'failure'
        }
        
        response = self.client.post(self.troubleshooter_url, post_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Could not find partition_id', response.content)
        self.assertNotIn('troubleshooter_results', self.client.session)


# ------------------------------
# Troubleshooter results view tests
# ------------------------------

class TroubleshooterResultsViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_results_view_with_session_data(self):
        session = self.client.session
        session['troubleshooter_results'] = {
            'partition_id': 'P123',
            'messages': ['Test message'],
            'df_clean_html': '<p>Clean</p>',
            'root_cause_table_html': '<p>Root cause</p>',
            'graph_html_path': '/path/to/graph.html',
        }
        session.save()

        response = self.client.get(reverse('troubleshooter_app:troubleshooter_results'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'P123')
        self.assertContains(response, 'Test message')

    def test_results_view_without_session_data(self):
        response = self.client.get(reverse('troubleshooter_app:troubleshooter_results'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('troubleshooter_app:troubleshooter'))










