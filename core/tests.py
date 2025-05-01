import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import InventoryItem, Location, Supplier
from core.views import detect_anomalies

class AnomalyDetectionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='tester', password='pass')
        InventoryItem.objects.create(user=self.user, name="Normal1", quantity=10, price=10)
        InventoryItem.objects.create(user=self.user, name="Normal2", quantity=12, price=10)
        InventoryItem.objects.create(user=self.user, name="Outlier", quantity=100, price=10)

    def test_anomaly_detects_outlier(self):
        InventoryItem.objects.create(user=self.user, name="Item1", quantity=1, price=10)
        InventoryItem.objects.create(user=self.user, name="Item2", quantity=2, price=10)
        InventoryItem.objects.create(user=self.user, name="Item3", quantity=3, price=10)
        InventoryItem.objects.create(user=self.user, name="Outlier", quantity=1000, price=10)

        items = InventoryItem.objects.filter(user=self.user)
        anomalies = detect_anomalies(items)

        print("Detected anomalies:", [item.name for item in anomalies])

        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0].name, "Outlier")



class InventoryAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='apiuser', password='pass')
        self.client = Client()
        self.client.login(username='apiuser', password='pass')

    def test_add_item(self):
        response = self.client.post('/api/add_item/', data=json.dumps({
            'name': 'Test Item',
            'quantity': 5,
            'price': 100,
            'supplier': 'ACME',
            'location': 'Main'
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(InventoryItem.objects.filter(name='Test Item').exists())

class InsightsViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='insightuser', password='pass')
        self.client = Client()
        self.client.login(username='insightuser', password='pass')


    def test_insights_view_renders(self):
        response = self.client.get(reverse('insights'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Insights")

class PermissionsTests(TestCase):
    def setUp(self):
        self.user1 = get_user_model().objects.create_user(username='user1', password='pass')
        self.user2 = get_user_model().objects.create_user(username='user2', password='pass')

        location = Location.objects.create(name='Test Location', user=self.user1)
        supplier = Supplier.objects.create(name='Test Supplier', user=self.user1)
        InventoryItem.objects.create(name='Hidden Item', user=self.user1, quantity=1, price=10, location=location, supplier=supplier)

        self.client.force_login(self.user2) 


    def test_user_cannot_access_other_users_items(self):
        response = self.client.get(reverse('get_dashboard_data'))
        print("RESPONSE STATUS:", response.status_code)
        print("RESPONSE CONTENT:", response.content.decode())

        self.assertEqual(response.status_code, 200)

        try:
            data = response.json()
        except ValueError:
            self.fail("Response was not JSON.")

        self.assertEqual(len(data['items']), 0)

