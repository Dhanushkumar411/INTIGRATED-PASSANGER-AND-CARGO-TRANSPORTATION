import unittest
from app import app
from models import init_db

class TestDhanushTransport(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'DHANUSH', response.data)
        self.assertIn(b'Dual-Transit', response.data)

    def test_passenger_portal(self):
        response = self.client.get('/passenger')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Passenger Transit Division', response.data)

    def test_cargo_portal(self):
        response = self.client.get('/cargo')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Freight & Cargo Logistics Division', response.data)

    def test_tracking_search(self):
        response = self.client.get('/track')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Universal Dual-Transit Tracking', response.data)

    def test_tracking_passenger_pnr(self):
        response = self.client.get('/track/PNR-DT-882101')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Aditya Sharma', response.data)
        self.assertIn(b'PASSENGER RECORD', response.data)

    def test_tracking_cargo_awb(self):
        response = self.client.get('/track/AWB-DT-10081')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'TechSpark Systems', response.data)
        self.assertIn(b'CARGO RECORD', response.data)

    def test_fleet_dispatch(self):
        response = self.client.get('/fleet')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Fleet & Dual-Capacity Dispatcher', response.data)

    def test_analytics(self):
        response = self.client.get('/analytics')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dual-Transit Analytics & ESG Impact', response.data)

    def test_passenger_booking_flow(self):
        post_data = {
            'trip_id': 3,
            'passenger_name': 'Vikram Rathore',
            'passenger_phone': '+91 98450 99999',
            'passenger_email': 'vikram@example.com',
            'seat_number': 'A1-Window'
        }
        res = self.client.post('/passenger/book', data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Vikram Rathore', res.data)
        self.assertIn(b'PNR-DT-', res.data)

    def test_cargo_booking_flow(self):
        post_data = {
            'origin_hub_id': 1,
            'dest_hub_id': 2,
            'sender_name': 'Bangalore Silk Exports',
            'sender_phone': '+91 98800 11223',
            'sender_address': 'Chickpet, Bangalore',
            'receiver_name': 'Chennai Textile Traders',
            'receiver_phone': '+91 94440 22334',
            'receiver_address': 'Sowcarpet, Chennai',
            'weight_kg': 35.0,
            'cargo_type': 'Apparel & Fabrics',
            'preferred_mode': 'Cargo-Hitch (Express via Passenger Fleet)'
        }
        res = self.client.post('/cargo/book', data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Bangalore Silk Exports', res.data)
        self.assertIn(b'AWB-DT-', res.data)

    def test_simulate_trip_step(self):
        res = self.client.post('/fleet/simulate-step/1', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Simulated advance for', res.data)

if __name__ == '__main__':
    unittest.main()
