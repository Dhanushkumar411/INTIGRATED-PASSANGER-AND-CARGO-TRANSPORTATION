import sqlite3
from datetime import datetime, timedelta
import random
from models import get_db_connection, init_db

def seed_database():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data to allow fresh re-seeding
    cursor.execute("DELETE FROM tracking_checkpoints")
    cursor.execute("DELETE FROM cargo_consignments")
    cursor.execute("DELETE FROM passenger_bookings")
    cursor.execute("DELETE FROM trips")
    cursor.execute("DELETE FROM routes")
    cursor.execute("DELETE FROM vehicles")
    cursor.execute("DELETE FROM hubs")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('hubs', 'vehicles', 'routes', 'trips', 'passenger_bookings', 'cargo_consignments', 'tracking_checkpoints')")

    # 1. Seed Hubs
    hubs = [
        (1, 'HUB-BLR', 'Dhanush Central Hub Bangalore', 'Bangalore', 'Karnataka', 'Majestic Inter-State Transit Complex, Bangalore', 12.9772, 77.5713, '+91 98450 11001'),
        (2, 'HUB-MAA', 'Dhanush Gateway Hub Chennai', 'Chennai', 'Tamil Nadu', 'Koyambedu Logistics & Transit Terminal, Chennai', 13.0694, 80.1948, '+91 98450 11002'),
        (3, 'HUB-HYD', 'Dhanush Deccan Hub Hyderabad', 'Hyderabad', 'Telangana', 'MGBS Integrated Transit & Cargo Center, Hyderabad', 17.3784, 78.4808, '+91 98450 11003'),
        (4, 'HUB-CJB', 'Dhanush Kongu Hub Coimbatore', 'Coimbatore', 'Tamil Nadu', 'Gandhipuram Transit Hub, Coimbatore', 11.0168, 76.9558, '+91 98450 11004'),
        (5, 'HUB-MYS', 'Dhanush Heritage Hub Mysore', 'Mysore', 'Karnataka', 'Suburban Transit & Freight Depot, Mysore', 12.3052, 76.6552, '+91 98450 11005'),
    ]

    cursor.executemany('''
    INSERT INTO hubs (id, code, name, city, state, address, lat, lng, phone)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', hubs)

    # 2. Seed Vehicles
    vehicles = [
        # Dual-transit hybrid vehicles (carrying passengers + hitching parcels in undercarriage & roof bays)
        ('KA-01-DT-1001', 'Dhanush Bharat Multi-Coach 01', 'Hybrid Passenger Bus', 36, 650.0, 4.5, 'Ramesh Kumar', '+91 98800 23401', 1, 'In Transit'),
        ('KA-01-DT-1002', 'Dhanush Bharat Multi-Coach 02', 'Hybrid Passenger Bus', 36, 650.0, 4.5, 'Suresh Babu', '+91 98800 23402', 1, 'Available'),
        ('TN-02-DT-2001', 'Dhanush Express Aero-Coach', 'Hybrid Passenger Bus', 32, 500.0, 3.8, 'Muthu Vel', '+91 98800 23403', 2, 'In Transit'),
        ('TS-09-DT-3001', 'Dhanush TwinWay Minivan', 'Express Cargo Minivan', 14, 300.0, 2.2, 'Venkat Reddy', '+91 98800 23404', 3, 'Available'),
        ('KA-05-DT-4001', 'Dhanush Cruiser Hybrid', 'Hybrid Passenger Bus', 40, 750.0, 5.0, 'Anand Shettigar', '+91 98800 23405', 1, 'Available'),
        # Dedicated heavy freight trucks (logistics only, 0 passenger seats)
        ('KA-01-DT-9001', 'Dhanush Heavy Freight Titan 10T', 'Heavy Freight Truck', 0, 10000.0, 35.0, 'Balwinder Singh', '+91 98800 23406', 1, 'In Transit'),
        ('TN-04-DT-9002', 'Dhanush Cargo Hauler 8T', 'Heavy Freight Truck', 0, 8000.0, 28.0, 'Karthik Raja', '+91 98800 23407', 2, 'Available'),
    ]

    cursor.executemany('''
    INSERT INTO vehicles (reg_number, name, vehicle_type, total_seats, total_cargo_kg, total_cargo_cbm, driver_name, driver_phone, current_hub_id, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', vehicles)

    # 3. Seed Routes
    # BLR (1), MAA (2), HYD (3), CJB (4), MYS (5)
    routes = [
        ('RT-BLR-MAA', 1, 2, 345.0, 6.5, 750.0, 14.0),
        ('RT-MAA-BLR', 2, 1, 345.0, 6.5, 750.0, 14.0),
        ('RT-BLR-HYD', 1, 3, 570.0, 9.0, 1150.0, 18.0),
        ('RT-HYD-BLR', 3, 1, 570.0, 9.0, 1150.0, 18.0),
        ('RT-BLR-CJB', 1, 4, 360.0, 7.0, 800.0, 15.0),
        ('RT-BLR-MYS', 1, 5, 145.0, 3.0, 320.0, 8.0),
    ]

    cursor.executemany('''
    INSERT INTO routes (route_code, origin_hub_id, dest_hub_id, distance_km, duration_hours, base_passenger_fare, base_cargo_rate_kg)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', routes)

    now = datetime.now()
    t1_dep = (now - timedelta(hours=2, minutes=30)).strftime('%Y-%m-%d %H:%M')
    t1_arr = (now + timedelta(hours=4)).strftime('%Y-%m-%d %H:%M')

    t2_dep = (now - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M')
    t2_arr = (now + timedelta(hours=6)).strftime('%Y-%m-%d %H:%M')

    t3_dep = (now + timedelta(hours=1, minutes=30)).strftime('%Y-%m-%d %H:%M')
    t3_arr = (now + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')

    t4_dep = (now - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M')
    t4_arr = (now + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')

    # 4. Seed Trips
    # Trip 1: BLR -> MAA (Hybrid Bus 1) - currently IN TRANSIT (midway between Bangalore and Chennai)
    # Approx midway lat/lng: 12.92, 79.13 (Vellore region)
    # Trip 2: BLR -> HYD (Hybrid Bus 3 / TN coach) - IN TRANSIT (near Anantapur: 14.68, 77.60)
    # Trip 3: BLR -> CJB (Hybrid Bus 2) - SCHEDULED
    # Trip 4: BLR -> MAA (Heavy Freight Titan) - IN TRANSIT (dedicated freight)
    trips = [
        ('TRIP-BLR-MAA-101', 1, 1, t1_dep, t1_arr, 'In Transit', 12.9200, 79.1333, 58, 28, 420.0),
        ('TRIP-BLR-HYD-202', 3, 3, t2_dep, t2_arr, 'In Transit', 14.6819, 77.6006, 45, 24, 380.0),
        ('TRIP-BLR-CJB-303', 5, 2, t3_dep, t3_arr, 'Scheduled', 12.9772, 77.5713, 0, 18, 190.0),
        ('TRIP-BLR-MAA-FR901', 1, 6, t4_dep, t4_arr, 'In Transit', 12.9800, 78.8500, 48, 0, 6800.0),
    ]

    cursor.executemany('''
    INSERT INTO trips (trip_code, route_id, vehicle_id, departure_time, arrival_time, status, current_lat, current_lng, progress_pct, booked_seats, booked_cargo_kg)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', trips)

    # 5. Seed Passenger Bookings
    passengers = [
        ('PNR-DT-882101', 1, 'Aditya Sharma', '+91 98410 55101', 'aditya.sharma@example.com', 'A1-Window', 750.0, 'Boarded', (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M'), 'QR-DT-882101-ADTY'),
        ('PNR-DT-882102', 1, 'Priya Krishnan', '+91 98410 55102', 'priya.k@example.com', 'A2-Aisle', 750.0, 'Boarded', (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M'), 'QR-DT-882102-PRIY'),
        ('PNR-DT-882103', 1, 'Rahul Verma', '+91 98410 55103', 'rahul.v@example.com', 'B3-Window', 750.0, 'Boarded', (now - timedelta(hours=18)).strftime('%Y-%m-%d %H:%M'), 'QR-DT-882103-RAHU'),
        ('PNR-DT-882104', 1, 'Deepa Sundaram', '+91 98410 55104', 'deepa.s@example.com', 'B4-Aisle', 750.0, 'Boarded', (now - timedelta(hours=12)).strftime('%Y-%m-%d %H:%M'), 'QR-DT-882104-DEEP'),
        ('PNR-DT-993201', 2, 'Kiran Rao', '+91 99001 77201', 'kiran.rao@example.com', 'C1-Window', 1150.0, 'Boarded', (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M'), 'QR-DT-993201-KIRA'),
        ('PNR-DT-774301', 3, 'Meera Nair', '+91 97400 88301', 'meera.nair@example.com', 'A1-Window', 800.0, 'Confirmed', (now - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M'), 'QR-DT-774301-MEER'),
    ]

    cursor.executemany('''
    INSERT INTO passenger_bookings (pnr, trip_id, passenger_name, passenger_phone, passenger_email, seat_number, fare_amount, status, booked_at, qr_code)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', passengers)

    # 6. Seed Cargo Consignments
    # Notice how consignments AWB-DT-10081 and AWB-DT-10082 travel ON THE SAME BUS as passenger Aditya Sharma (Trip 1)!
    # This demonstrates the signature "Cargo Hitching" innovation of Dhanush Transport!
    cargo_items = [
        ('AWB-DT-10081', 1, 1, 2, 'TechSpark Systems', '+91 98800 44101', 'Electronic City, Bangalore', 'NexGen Solutions Ltd', '+91 94440 33201', 'OMR Tech Corridor, Chennai', 42.5, 0.35, 'Electronics & Hardware', 'Cargo-Hitch (Express via Passenger Fleet)', 1250.0, 'In Transit', (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M')),
        ('AWB-DT-10082', 1, 1, 2, 'Mysore Sandal Artisans', '+91 98800 44102', 'Commercial Street, Bangalore', 'Heritage Boutiques', '+91 94440 33202', 'T. Nagar, Chennai', 18.0, 0.15, 'E-Commerce Parcel', 'Cargo-Hitch (Express via Passenger Fleet)', 550.0, 'In Transit', (now - timedelta(hours=14)).strftime('%Y-%m-%d %H:%M')),
        ('AWB-DT-10083', 1, 1, 2, 'MediCare Lab Diagnostics', '+91 98800 44103', 'Koramangala, Bangalore', 'Apollo Diagnostics Hub', '+91 94440 33203', 'Greams Road, Chennai', 12.0, 0.10, 'Perishable / Medical Samples', 'Cargo-Hitch (Express via Passenger Fleet)', 720.0, 'In Transit', (now - timedelta(hours=10)).strftime('%Y-%m-%d %H:%M')),
        ('AWB-DT-20091', 2, 1, 3, 'BioPharma India', '+91 98800 44104', 'Peenya Industrial Area, Bangalore', 'Hyderabad Biotech Park', '+91 94440 33204', 'Genome Valley, Hyderabad', 65.0, 0.50, 'Pharmaceuticals', 'Cargo-Hitch (Express via Passenger Fleet)', 2100.0, 'In Transit', (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M')),
        ('AWB-DT-90050', 4, 1, 2, 'Kirloskar Heavy Castings', '+91 98800 44105', 'Bommasandra Industrial Area, Bangalore', 'Ennore Port Foundry', '+91 94440 33205', 'Ennore Industrial Estate, Chennai', 4500.0, 16.0, 'Heavy Commercial Machineries', 'Dedicated Heavy Freight', 24500.0, 'In Transit', (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M')),
    ]

    cursor.executemany('''
    INSERT INTO cargo_consignments (awb, trip_id, origin_hub_id, dest_hub_id, sender_name, sender_phone, sender_address, receiver_name, receiver_phone, receiver_address, weight_kg, volume_cbm, cargo_type, transport_mode, price_amount, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', cargo_items)

    # 7. Seed Tracking Checkpoints for Live Demonstrations
    # Passenger PNR-DT-882101 milestones
    checkpoints = [
        # Aditya Sharma (PNR-DT-882101)
        ('PNR-DT-882101', 'PASSENGER', 'Ticket Confirmed & Seat Reserved', 'Bangalore Hub', (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M'), 'Seat A1-Window allocated on Dhanush Bharat Multi-Coach 01', 1),
        ('PNR-DT-882101', 'PASSENGER', 'Passenger Boarded & Luggage Scanned', 'Bangalore Hub', (now - timedelta(hours=2, minutes=35)).strftime('%Y-%m-%d %H:%M'), 'Digital boarding pass verified by Bus Captain Ramesh Kumar', 1),
        ('PNR-DT-882101', 'PASSENGER', 'Departed Origin Hub', 'Bangalore Hub', (now - timedelta(hours=2, minutes=25)).strftime('%Y-%m-%d %H:%M'), 'Vehicle rolled out via Hosur Highway corridor', 1),
        ('PNR-DT-882101', 'PASSENGER', 'En Route - Waypoint Vellore Toll Plaza', 'Vellore Highway', (now - timedelta(minutes=20)).strftime('%Y-%m-%d %H:%M'), 'Cruising at 74 km/h. Smooth traffic condition.', 1),
        ('PNR-DT-882101', 'PASSENGER', 'Destination Arrival & Disembarkation', 'Chennai Gateway Hub', (now + timedelta(hours=4)).strftime('%Y-%m-%d %H:%M'), 'Estimated arrival at Koyambedu Terminal', 0),

        # Cargo AWB-DT-10081 (Electronics hitching ride on the same bus!)
        ('AWB-DT-10081', 'CARGO', 'Consignment Booked & Waybill Issued', 'Bangalore Hub', (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M'), 'Weight 42.5 kg verified; Barcode label generated', 1),
        ('AWB-DT-10081', 'CARGO', 'Allocated to Express Cargo-Hitch Bay', 'Bangalore Hub', (now - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M'), 'Stored securely in lower climate-stabilized luggage deck of Coach 01', 1),
        ('AWB-DT-10081', 'CARGO', 'Dispatched on Coach KA-01-DT-1001', 'Bangalore Hub', (now - timedelta(hours=2, minutes=25)).strftime('%Y-%m-%d %H:%M'), 'Departed Bangalore Hub en-route to Chennai', 1),
        ('AWB-DT-10081', 'CARGO', 'In Transit via NH48 Checkpoint', 'Vellore Checkpoint', (now - timedelta(minutes=20)).strftime('%Y-%m-%d %H:%M'), 'Midway GPS ping confirmed. Temp & shock sensors normal.', 1),
        ('AWB-DT-10081', 'CARGO', 'Scheduled Hub Inward & Last-Mile Dispatch', 'Chennai Gateway Hub', (now + timedelta(hours=4, minutes=15)).strftime('%Y-%m-%d %H:%M'), 'Expected handover to local electric delivery van', 0),
    ]

    cursor.executemany('''
    INSERT INTO tracking_checkpoints (tracking_ref, ref_type, stage_name, location, status_timestamp, notes, is_completed)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', checkpoints)

    conn.commit()
    conn.close()
    print("Seeded database with initial hubs, vehicles, routes, trips, passenger bookings, and cargo shipments!")

if __name__ == '__main__':
    seed_database()
